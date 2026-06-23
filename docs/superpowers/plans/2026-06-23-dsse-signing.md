# Real DSSE Signing (local ed25519) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sign the existing unsigned, signing-ready DSSE envelopes (certificate + attestation Statement) with a local ed25519 key over DSSE-PAE, offline and deterministically, with a `verify-dsse` path and a `keygen` helper.

**Architecture:** A new `signing.py` module holds a pure `pae()` and crypto signer/verifier functions (ed25519 via `cryptography`, guarded behind a `[sign]` extra). `keygen` and `verify-dsse` are new CLI subcommands; `certify --format dsse` and `export-attestation --format dsse` gain an opt-in `--key`. With no key, output is byte-identical to today. grammar/protocol and the DSSE models are untouched.

**Tech Stack:** Python 3, `cryptography>=42` (ed25519, behind `[sign]`), stdlib base64/hashlib (PAE + keyid), pydantic models (existing `DsseEnvelope`/`DsseSignature`), argparse CLI, pytest. Interpreter for all commands (run from repo root): `/Users/zbb2/Desktop/polymer-claims/.venv/bin/python` (`python` alone is NOT on PATH).

## Global Constraints

- **Backward-compatible / additive.** With no `--key`, DSSE output is byte-identical to today. `DsseEnvelope`/`DsseSignature` models are unchanged. grammar/protocol untouched.
- **Base install stays crypto-free.** `cryptography` only in the `[sign]` extra (and `dev`). The `signing` module must NOT import `cryptography` at module top — only inside functions via a `_require_crypto()` guard that re-raises a friendly `ModuleNotFoundError(..., name="cryptography")` (message naming `pip install 'polymer-claims[sign]'`).
- **Sign exactly the envelope's bytes.** The signed body is `base64.b64decode(env.payload)` — the exact bytes the envelope carries — PAE'd with `env.payload_type`. No re-serialization.
- **PAE format (DSSE spec):** `PAE(type, body) = b"DSSEv1" SP LEN(type) SP type SP LEN(body) SP body`, single ASCII spaces, `LEN` = ASCII-decimal byte length, `type` UTF-8, `body` raw bytes.
- **Determinism.** ed25519 (RFC 8032) signatures are deterministic; tests round-trip (no committed private keys). Keys generated in-test.
- **PEM formats:** private = PKCS8/`NoEncryption`; public = `SubjectPublicKeyInfo`. `keyid` = first 16 hex of `sha256(public-key DER SubjectPublicKeyInfo)`. `keyid` is informational, not trust-bearing; verification is by the supplied `--pub-key`.
- **Operator-error & robustness:** `--key`/`--keyid` are rejected (rc 1) on a non-`dsse` format, not silently ignored. `verify-dsse` treats malformed input (bad JSON, non-envelope, bad PEM, bad base64) as a failed verification (rc 1) — never a traceback. `verify_envelope` returns `False` (not raises) on malformed base64. The private key is created with `0o600` from the start (`os.open`, not write-then-chmod).
- **Single-signer by design:** `sign_envelope` replaces any existing signatures (multi-signer deferred). Current producers emit unsigned envelopes, so this is non-destructive in practice.
- Every commit message ends with the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` trailer.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `src/polymer_claims/signing.py` | Create | `pae` (pure); `_require_crypto`; `generate_keypair`, `keyid_for`, `sign_envelope`, `verify_envelope`, PEM load/serialize |
| `pyproject.toml` | Modify | Add `sign = ["cryptography>=42"]` extra; add `cryptography>=42` to `dev` |
| `src/polymer_claims/cli.py` | Modify | `keygen` + `verify-dsse` subcommands; `--key`/`--keyid` on `certify`, `--key` on `export-attestation` |
| `tests/test_signing.py` | Create | `pae` vector; round-trip/tamper/keyid/PEM/missing-dep |
| `tests/test_cli_signing.py` | Create | `keygen`→sign→`verify-dsse` smoke; backward-compat unsigned |

---

### Task 1: `pae` + crypto guard (pure core)

**Files:**
- Create: `src/polymer_claims/signing.py`
- Test: `tests/test_signing.py`

**Interfaces:**
- Produces: `pae(payload_type: str, body: bytes) -> bytes` (pure, stdlib); `_require_crypto() -> tuple` (imports `cryptography` lazily, re-raises a friendly `ModuleNotFoundError(name="cryptography")`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_signing.py`:

```python
from polymer_claims.signing import pae


def test_pae_basic_vector():
    # PAE(type, body) = b"DSSEv1 " + len(type) + " " + type + " " + len(body) + " " + body
    assert pae("X", b"YY") == b"DSSEv1 1 X 2 YY"


def test_pae_lengths_are_byte_counts():
    assert pae("application/vnd.in-toto+json", b"{}") == b"DSSEv1 28 application/vnd.in-toto+json 2 {}"


def test_pae_unicode_type_uses_utf8_byte_length():
    # "é" is 2 UTF-8 bytes, so LEN(type) counts bytes not chars
    assert pae("é", b"") == b"DSSEv1 2 \xc3\xa9 0 "
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_signing.py -v`
Expected: FAIL — `ModuleNotFoundError: polymer_claims.signing`.

- [ ] **Step 3: Create the module**

Create `src/polymer_claims/signing.py`:

```python
"""Local ed25519 DSSE-PAE signing for Polymer attestation/certificate envelopes.

`pae` is pure stdlib. Everything cryptographic goes through `_require_crypto()` so the base install
stays crypto-free — `cryptography` lives only in the [sign] extra. See
docs/superpowers/specs/2026-06-23-dsse-signing-design.md.
"""
from __future__ import annotations

import base64
import hashlib


def pae(payload_type: str, body: bytes) -> bytes:
    """DSSE Pre-Authentication Encoding: b"DSSEv1" SP len(type) SP type SP len(body) SP body.
    Single ASCII spaces; lengths are byte counts; type is UTF-8; body is raw bytes."""
    t = payload_type.encode("utf-8")
    return b" ".join(
        [b"DSSEv1", str(len(t)).encode("ascii"), t, str(len(body)).encode("ascii"), body]
    )


def _require_crypto():
    """Import the cryptography pieces lazily; re-raise a friendly hint if the [sign] extra is absent.
    Keeps `name="cryptography"` so callers (the CLI) can branch on it."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "polymer-claims signing needs the [sign] extra: pip install 'polymer-claims[sign]'",
            name="cryptography",
        ) from exc
    return ed25519, serialization, InvalidSignature
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_signing.py -v`
Expected: PASS (3 passed). `base64`/`hashlib` are imported for Task 2; ruff may warn they're unused now — if `ruff check src/polymer_claims/signing.py` flags F401, leave them (Task 2 uses both) OR add them in Task 2 instead. To keep Task 1 lint-clean, REMOVE the `import base64` / `import hashlib` lines in this task and re-add them in Task 2 Step 2.

- [ ] **Step 5: Ensure lint-clean, then commit**

Run: `ruff check src/polymer_claims/signing.py tests/test_signing.py`
Expected: clean (remove the two unused imports per Step 4 note if flagged).

```bash
git add src/polymer_claims/signing.py tests/test_signing.py
git commit -m "feat(signing): pure DSSE PAE + crypto-dependency guard

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: ed25519 signer/verifier + keys + `[sign]` extra

**Files:**
- Modify: `src/polymer_claims/signing.py`
- Modify: `pyproject.toml`
- Test: `tests/test_signing.py` (extend)

**Interfaces:**
- Consumes: `pae`, `_require_crypto` (Task 1); `DsseEnvelope`, `DsseSignature` from `polymer_claims.attestation`.
- Produces:
  - `generate_keypair() -> tuple[priv, pub]` — fresh ed25519 keypair objects.
  - `keyid_for(public_key) -> str` — first 16 hex of `sha256(pub DER SubjectPublicKeyInfo)`.
  - `sign_envelope(env: DsseEnvelope, private_key, *, keyid: str | None = None) -> DsseEnvelope` — returns a NEW envelope with `signatures=(DsseSignature(sig=<b64 raw sig>, keyid=keyid or keyid_for(pub)),)`.
  - `verify_envelope(env: DsseEnvelope, public_key) -> bool` — True iff ≥1 signature verifies (and ≥1 present).
  - `serialize_private_pem(priv) -> bytes` / `serialize_public_pem(pub) -> bytes`; `load_private_key(data: bytes) -> priv` / `load_public_key(data: bytes) -> pub`.

- [ ] **Step 1: Install the dependency + add the extra + update the lock**

First check whether `cryptography` is already importable (it was NOT at plan time):

Run: `/Users/zbb2/Desktop/polymer-claims/.venv/bin/python -c "import cryptography; print(cryptography.__version__)"`

If it imports, skip the install. If it raises `ModuleNotFoundError`, install it:

Run: `/Users/zbb2/.local/bin/uv pip install --python /Users/zbb2/Desktop/polymer-claims/.venv/bin/python 'cryptography>=42'`

> **Network note:** this environment restricts network. If the install fails with a network/permission error, it needs escalation — re-run with the sandbox disabled, or ask the human partner to run the `uv pip install` (and the `uv lock` below) themselves. Do not proceed to Step 3 until `import cryptography` succeeds; if it can't be installed, mark the task BLOCKED with the install error rather than weakening the crypto tests.

Edit `pyproject.toml` `[project.optional-dependencies]` (after the `calibrate` line) to add:

```toml
sign = ["cryptography>=42"]
```

And append `"cryptography>=42"` to the `dev = [...]` list.

Then update the lockfile (the repo has `uv.lock`; leaving it stale would drift fresh-checkout dev installs):

Run: `/Users/zbb2/.local/bin/uv lock` (also needs network — same escalation note applies). Stage the updated `uv.lock` with the commit.

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_signing.py`:

```python
import base64

from polymer_claims.attestation import DsseEnvelope
from polymer_claims.signing import (
    generate_keypair, keyid_for, load_private_key, load_public_key,
    serialize_private_pem, serialize_public_pem, sign_envelope, verify_envelope,
)


def _env(body: bytes = b'{"hello":"world"}', ptype: str = "application/vnd.in-toto+json"):
    return DsseEnvelope(payload=base64.b64encode(body).decode("ascii"), **{"payloadType": ptype})


def test_sign_then_verify_roundtrip():
    priv, pub = generate_keypair()
    signed = sign_envelope(_env(), priv)
    assert len(signed.signatures) == 1 and signed.signatures[0].sig
    assert verify_envelope(signed, pub) is True


def test_tampered_payload_fails_verify():
    priv, pub = generate_keypair()
    signed = sign_envelope(_env(), priv)
    tampered = signed.model_copy(update={"payload": base64.b64encode(b'{"hello":"evil"}').decode("ascii")})
    assert verify_envelope(tampered, pub) is False


def test_wrong_key_fails_verify():
    priv, _ = generate_keypair()
    _, other_pub = generate_keypair()
    signed = sign_envelope(_env(), priv)
    assert verify_envelope(signed, other_pub) is False


def test_unsigned_envelope_does_not_verify():
    _, pub = generate_keypair()
    assert verify_envelope(_env(), pub) is False


def test_keyid_is_deterministic_and_key_specific():
    priv, pub = generate_keypair()
    _, other_pub = generate_keypair()
    assert keyid_for(pub) == keyid_for(pub)
    assert keyid_for(pub) != keyid_for(other_pub)
    assert sign_envelope(_env(), priv).signatures[0].keyid == keyid_for(pub)
    assert sign_envelope(_env(), priv, keyid="custom").signatures[0].keyid == "custom"


def test_pem_roundtrip_still_verifies():
    priv, pub = generate_keypair()
    priv2 = load_private_key(serialize_private_pem(priv))
    pub2 = load_public_key(serialize_public_pem(pub))
    signed = sign_envelope(_env(), priv2)
    assert verify_envelope(signed, pub2) is True


def test_pae_binds_certificate_payload_type():
    # Certificate envelopes use a distinct payloadType; PAE must bind it, so a sig made for the
    # certificate type must NOT verify if the type is swapped to the in-toto default.
    priv, pub = generate_keypair()
    env = _env(body=b'{"c":1}', ptype="application/vnd.polymer.certificate+json")
    signed = sign_envelope(env, priv)
    assert signed.payload_type == "application/vnd.polymer.certificate+json"
    assert verify_envelope(signed, pub) is True
    swapped = signed.model_copy(update={"payloadType": "application/vnd.in-toto+json"})
    assert verify_envelope(swapped, pub) is False


def test_keyid_is_informational_not_trusted():
    # A misleading keyid does not change verification — it is by the supplied public key, not keyid.
    priv, pub = generate_keypair()
    signed = sign_envelope(_env(), priv, keyid="totally-wrong-keyid")
    assert verify_envelope(signed, pub) is True


def test_malformed_signature_base64_is_false_not_raise():
    from polymer_claims.attestation import DsseSignature
    _, pub = generate_keypair()
    bad = _env().model_copy(update={"signatures": (DsseSignature(sig="!!!not-base64!!!"),)})
    assert verify_envelope(bad, pub) is False


def test_missing_cryptography_is_friendly(monkeypatch):
    import builtins
    import polymer_claims.signing as signing
    real_import = builtins.__import__

    def _no_crypto(name, *a, **k):
        if name.startswith("cryptography"):
            raise ModuleNotFoundError(f"No module named {name!r}", name="cryptography")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _no_crypto)
    import pytest
    with pytest.raises(ModuleNotFoundError) as ei:
        signing.generate_keypair()
    assert ei.value.name == "cryptography"
    assert "[sign]" in str(ei.value)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_signing.py -v`
Expected: the new tests FAIL — `ImportError: cannot import name 'generate_keypair'`.

- [ ] **Step 4: Implement the signer**

In `src/polymer_claims/signing.py`, ensure the top imports include `base64` and `hashlib` (re-add if removed in Task 1), then add:

```python
from polymer_claims.attestation import DsseEnvelope, DsseSignature


def generate_keypair():
    ed25519, _serialization, _inv = _require_crypto()
    priv = ed25519.Ed25519PrivateKey.generate()
    return priv, priv.public_key()


def keyid_for(public_key) -> str:
    _ed, serialization, _inv = _require_crypto()
    der = public_key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return hashlib.sha256(der).hexdigest()[:16]


def sign_envelope(env: DsseEnvelope, private_key, *, keyid: str | None = None) -> DsseEnvelope:
    """Return a NEW envelope signed over PAE(payload_type, decoded payload) — covers exactly the
    bytes in the envelope's payload field. Single-signer by design: REPLACES any existing signatures
    (multi-signer trust policy is deferred, spec §9). `keyid` is an informational identifier, not
    trust-bearing (verification is by an explicitly-supplied public key)."""
    body = base64.b64decode(env.payload)
    raw_sig = private_key.sign(pae(env.payload_type, body))
    kid = keyid if keyid is not None else keyid_for(private_key.public_key())
    sig = DsseSignature(sig=base64.b64encode(raw_sig).decode("ascii"), keyid=kid)
    return env.model_copy(update={"signatures": (sig,)})


def verify_envelope(env: DsseEnvelope, public_key) -> bool:
    """True iff >=1 signature verifies against `public_key`. Malformed input (bad base64 in the
    payload or a signature) is treated as non-verifying (returns False, never raises). `keyid` is
    ignored — informational only this slice (spec §9)."""
    _ed, _serialization, InvalidSignature = _require_crypto()
    if not env.signatures:
        return False
    try:
        body = base64.b64decode(env.payload, validate=True)
    except ValueError:
        return False
    msg = pae(env.payload_type, body)
    for s in env.signatures:
        try:
            public_key.verify(base64.b64decode(s.sig, validate=True), msg)
            return True
        except (ValueError, InvalidSignature):
            continue
    return False


def serialize_private_pem(private_key) -> bytes:
    _ed, serialization, _inv = _require_crypto()
    return private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def serialize_public_pem(public_key) -> bytes:
    _ed, serialization, _inv = _require_crypto()
    return public_key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def load_private_key(data: bytes):
    _ed, serialization, _inv = _require_crypto()
    return serialization.load_pem_private_key(data, password=None)


def load_public_key(data: bytes):
    _ed, serialization, _inv = _require_crypto()
    return serialization.load_pem_public_key(data)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_signing.py -v`
Expected: PASS (all, ~10). `ruff check src/polymer_claims/signing.py tests/test_signing.py` → clean.

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/signing.py tests/test_signing.py pyproject.toml uv.lock
git commit -m "feat(signing): ed25519 DSSE sign/verify + keys + [sign] extra

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
(If `uv lock` could not run due to the network restriction, commit without `uv.lock` and note in the report that the lock update is pending — flag it for the human to run `uv lock`.)

---

### Task 3: `keygen` + `verify-dsse` CLI subcommands

**Files:**
- Modify: `src/polymer_claims/cli.py`
- Test: `tests/test_cli_signing.py`

**Interfaces:**
- Consumes: `generate_keypair`, `serialize_private_pem`, `serialize_public_pem`, `load_public_key`, `verify_envelope` (Task 2); `DsseEnvelope` from `attestation`; existing `main(argv)`.
- Produces: CLI `polymer-claims keygen --key OUT.key --pub-key OUT.pub [--force]` and `polymer-claims verify-dsse PATH --pub-key PATH`. `verify-dsse` reads a single DSSE-envelope JSON OR NDJSON of envelopes; rc 0 iff every envelope verifies, else 1.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_signing.py`:

```python
import json

from polymer_claims.cli import main


def test_keygen_writes_pem_pair(tmp_path):
    key = tmp_path / "k.key"
    pub = tmp_path / "k.pub"
    rc = main(["keygen", "--key", str(key), "--pub-key", str(pub)])
    assert rc == 0
    assert key.read_bytes().startswith(b"-----BEGIN PRIVATE KEY-----")
    assert pub.read_bytes().startswith(b"-----BEGIN PUBLIC KEY-----")


def test_keygen_refuses_overwrite_without_force(tmp_path, capsys):
    key = tmp_path / "k.key"
    pub = tmp_path / "k.pub"
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub)]) == 0
    rc = main(["keygen", "--key", str(key), "--pub-key", str(pub)])
    assert rc == 1 and "force" in capsys.readouterr().err.lower()
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub), "--force"]) == 0


def test_verify_dsse_roundtrip(tmp_path):
    from polymer_claims.attestation import DsseEnvelope
    from polymer_claims.signing import (
        generate_keypair, serialize_public_pem, sign_envelope,
    )
    import base64
    priv, pub = generate_keypair()
    env = DsseEnvelope(payload=base64.b64encode(b'{"x":1}').decode("ascii"))
    signed = sign_envelope(env, priv)
    env_path = tmp_path / "env.json"
    env_path.write_text(signed.model_dump_json(by_alias=True, exclude_none=True))
    pub_path = tmp_path / "k.pub"
    pub_path.write_bytes(serialize_public_pem(pub))
    assert main(["verify-dsse", str(env_path), "--pub-key", str(pub_path)]) == 0
    # tamper -> rc 1
    bad = json.loads(env_path.read_text())
    bad["payload"] = base64.b64encode(b'{"x":2}').decode("ascii")
    env_path.write_text(json.dumps(bad))
    assert main(["verify-dsse", str(env_path), "--pub-key", str(pub_path)]) == 1


def test_verify_dsse_malformed_inputs_return_rc1_not_traceback(tmp_path, capsys):
    from polymer_claims.signing import generate_keypair, serialize_public_pem
    _, pub = generate_keypair()
    pub_path = tmp_path / "k.pub"
    pub_path.write_bytes(serialize_public_pem(pub))
    # not-a-DSSE-envelope JSON
    p = tmp_path / "junk.json"
    p.write_text('{"not":"an envelope"}')
    assert main(["verify-dsse", str(p), "--pub-key", str(pub_path)]) == 1
    # not JSON at all
    p.write_text("this is not json")
    assert main(["verify-dsse", str(p), "--pub-key", str(pub_path)]) == 1
    # malformed public key
    badpub = tmp_path / "bad.pub"
    badpub.write_text("-----BEGIN PUBLIC KEY-----\nnope\n-----END PUBLIC KEY-----\n")
    p.write_text('{"payload":"e30=","payloadType":"application/vnd.in-toto+json","signatures":[]}')
    assert main(["verify-dsse", str(p), "--pub-key", str(badpub)]) == 1
    assert "Traceback" not in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_cli_signing.py -v`
Expected: FAIL — argparse invalid choice `keygen` / `verify-dsse`.

- [ ] **Step 3: Add the handlers**

Add `import os` to the stdlib import block at the top of `src/polymer_claims/cli.py` (after `import sys`). Then add near the other `_cmd_*` functions:

```python
def _sign_dep_error(exc: ModuleNotFoundError) -> int:
    if getattr(exc, "name", None) == "cryptography":
        print("signing needs the [sign] extra: pip install 'polymer-claims[sign]'", file=sys.stderr)
    else:
        print(f"signing import failed: {exc}", file=sys.stderr)
    return 1


def _parse_dsse_envelopes(text: str):
    """Parse a single DSSE-envelope JSON (compact OR pretty-printed) or an NDJSON of envelopes.
    Returns a list of DsseEnvelope, or None if the input is not parseable as either."""
    from pydantic import ValidationError

    from .attestation import DsseEnvelope
    stripped = text.strip()
    if not stripped:
        return []
    try:                                            # whole text = one envelope (handles pretty JSON)
        return [DsseEnvelope.model_validate_json(stripped)]
    except ValidationError:
        pass
    out = []                                        # else NDJSON: one compact envelope per line
    for ln in stripped.splitlines():
        if not ln.strip():
            continue
        try:
            out.append(DsseEnvelope.model_validate_json(ln))
        except ValidationError:
            return None
    return out


def _cmd_keygen(args: argparse.Namespace) -> int:
    try:
        from .signing import generate_keypair, serialize_private_pem, serialize_public_pem
        priv_k, pub_k = generate_keypair()
    except ModuleNotFoundError as exc:
        return _sign_dep_error(exc)
    key, pub = Path(args.key), Path(args.pub_key)
    if (key.exists() or pub.exists()) and not args.force:
        print(f"refusing to overwrite existing {key} / {pub} — use --force", file=sys.stderr)
        return 1
    # create the PRIVATE key with 0600 from the start (not write-then-chmod, which leaks via umask)
    fd = os.open(str(key), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(serialize_private_pem(priv_k))
    pub.write_bytes(serialize_public_pem(pub_k))
    print(f"wrote {key} (private, 0600) + {pub} (public)", file=sys.stderr)
    return 0


def _cmd_verify_dsse(args: argparse.Namespace) -> int:
    try:
        from .signing import load_public_key, verify_envelope
    except ModuleNotFoundError as exc:
        return _sign_dep_error(exc)
    try:
        public_key = load_public_key(Path(args.pub_key).read_bytes())
    except ModuleNotFoundError as exc:
        return _sign_dep_error(exc)
    except (ValueError, OSError) as exc:            # malformed PEM / unreadable file -> rc 1, no traceback
        print(f"verify-dsse: cannot load public key: {exc}", file=sys.stderr)
        return 1
    try:
        text = Path(args.path).read_text()
    except OSError as exc:
        print(f"verify-dsse: cannot read {args.path}: {exc}", file=sys.stderr)
        return 1
    envelopes = _parse_dsse_envelopes(text)
    if envelopes is None:
        print("verify-dsse: input is not a valid DSSE envelope or NDJSON of envelopes", file=sys.stderr)
        return 1
    if not envelopes:
        print("verify-dsse: no DSSE envelopes to verify", file=sys.stderr)
        return 1
    all_ok = True
    for i, env in enumerate(envelopes):
        ok = verify_envelope(env, public_key)
        all_ok = all_ok and ok
        print(f"  envelope[{i}]: {'VALID' if ok else 'INVALID'}", file=sys.stderr)
    print(f"verify-dsse: {'all signatures valid' if all_ok else 'INVALID signature(s)'}", file=sys.stderr)
    return 0 if all_ok else 1
```

> `_parse_dsse_envelopes` tries the whole text as one envelope first (so a pretty-printed single envelope works), then falls back to NDJSON. Any parse/validation failure becomes `None` → rc 1, never a traceback. `verify_envelope` (Task 2) already returns `False` for malformed base64 rather than raising.

- [ ] **Step 4: Register the subcommands**

In `_build_parser`, after an existing `sub.add_parser(...)` block:

```python
    p_kg = sub.add_parser("keygen", help="generate an ed25519 keypair (PEM) for DSSE signing")
    p_kg.add_argument("--key", required=True, help="output path for the private key PEM")
    p_kg.add_argument("--pub-key", required=True, help="output path for the public key PEM")
    p_kg.add_argument("--force", action="store_true", help="overwrite existing key files")
    p_kg.set_defaults(func=_cmd_keygen)

    p_vd = sub.add_parser("verify-dsse", help="verify a signed DSSE envelope (or NDJSON) against a public key")
    p_vd.add_argument("path", help="path to a DSSE envelope JSON or NDJSON of envelopes")
    p_vd.add_argument("--pub-key", required=True, help="path to the signer's public key PEM")
    p_vd.set_defaults(func=_cmd_verify_dsse)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_cli_signing.py -v`
Expected: PASS. `ruff check src/polymer_claims/cli.py tests/test_cli_signing.py` → clean.

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/cli.py tests/test_cli_signing.py
git commit -m "feat(cli): keygen + verify-dsse subcommands

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Opt-in `--key` on `certify` and `export-attestation`

**Files:**
- Modify: `src/polymer_claims/cli.py` (`_cmd_certify`, `_cmd_export_attestation`, `_build_parser`)
- Test: `tests/test_cli_signing.py` (extend)

**Interfaces:**
- Consumes: `load_private_key`, `sign_envelope` (Task 2); `_sign_dep_error`, `_cmd_verify_dsse` (Task 3); existing `certificate_dsse_envelope`, `dsse_envelope`, `build_attestation_statements`.
- Produces: `certify CLAIM --format dsse [--key PATH] [--keyid ID]` and `export-attestation … --format dsse [--key PATH]` — sign the DSSE envelope(s) in place when `--key` is given; byte-identical to today otherwise.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli_signing.py`. These reuse the existing attestation/certificate fixtures (a corpus with a LICENSED claim `c1`):

```python
from tests.attestation._fixtures import licensed_claim, licensing, corpus_with, mc, sat


def _corpus_path(tmp_path):
    corpus = corpus_with(licensed_claim("c1", licensing(sat(mc()))))
    p = tmp_path / "corpus.json"
    p.write_text(corpus.model_dump_json())
    return p


def test_certify_dsse_unsigned_is_byte_identical(tmp_path, capsys):
    cp = _corpus_path(tmp_path)
    rc = main(["certify", "c1", "--corpus", str(cp), "--format", "dsse", "--q", "0.05"])
    assert rc == 0
    cli_out = capsys.readouterr().out
    # direct pre-slice render (certify default --q is 0.05)
    from polymer_claims.attestation import build_certificate, certificate_dsse_envelope
    from polymer_claims.io import load_corpus
    cert = build_certificate(load_corpus(str(cp)), "c1", ledger=None, target_q=0.05)
    expected = certificate_dsse_envelope(cert).model_dump_json(by_alias=True, exclude_none=True) + "\n"
    assert cli_out == expected                       # byte-identical, unsigned


def test_export_attestation_dsse_unsigned_is_byte_identical(tmp_path):
    cp = _corpus_path(tmp_path)
    out_path = tmp_path / "att.ndjson"
    assert main(["export-attestation", str(cp), "--format", "dsse", "--out", str(out_path)]) == 0
    from polymer_claims.attestation import (
        build_attestation_statements, dsse_envelope, resolve_contract_index,
    )
    from polymer_claims.io import load_corpus
    corpus = load_corpus(str(cp))
    idx = resolve_contract_index(corpus)
    expected = "".join(
        dsse_envelope(s).model_dump_json(by_alias=True, exclude_none=True) + "\n"
        for s in build_attestation_statements(corpus, contract_index=idx)
    )
    assert out_path.read_text() == expected          # byte-identical, unsigned


def test_key_rejected_on_non_dsse_format(tmp_path, capsys):
    cp = _corpus_path(tmp_path)
    key, pub = tmp_path / "k.key", tmp_path / "k.pub"
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub)]) == 0
    assert main(["certify", "c1", "--corpus", str(cp), "--format", "json", "--key", str(key)]) == 1
    assert main(["export-attestation", str(cp), "--format", "bundle", "--key", str(key)]) == 1


def test_certify_dsse_signed_then_verify(tmp_path, capsys):
    cp = _corpus_path(tmp_path)
    key, pub = tmp_path / "k.key", tmp_path / "k.pub"
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub)]) == 0
    rc = main(["certify", "c1", "--corpus", str(cp), "--format", "dsse", "--key", str(key)])
    assert rc == 0
    out = capsys.readouterr().out
    env = json.loads(out)
    assert len(env["signatures"]) == 1 and env["signatures"][0]["sig"]
    signed_path = tmp_path / "cert.dsse.json"
    signed_path.write_text(out)
    assert main(["verify-dsse", str(signed_path), "--pub-key", str(pub)]) == 0


def test_export_attestation_dsse_signed(tmp_path):
    cp = _corpus_path(tmp_path)
    key, pub = tmp_path / "k.key", tmp_path / "k.pub"
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub)]) == 0
    out_path = tmp_path / "att.ndjson"
    rc = main(["export-attestation", str(cp), "--format", "dsse", "--key", str(key), "--out", str(out_path)])
    assert rc == 0
    lines = [ln for ln in out_path.read_text().splitlines() if ln.strip()]
    assert lines and all(json.loads(ln)["signatures"] for ln in lines)
    assert main(["verify-dsse", str(out_path), "--pub-key", str(pub)]) == 0
```

> If `tests/attestation/_fixtures.py` does not export `mc`/`sat`, read it and use whatever helpers build a LICENSED corpus with claim id `c1` (the `licensing(sat(mc()))` pattern was confirmed working in prior slices). The only requirement: a corpus JSON whose `c1` is LICENSED so `build_certificate`/`build_attestation_statements` produce an envelope.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_cli_signing.py -k "certify_dsse or export_attestation_dsse" -v`
Expected: the signed tests FAIL — `certify`/`export-attestation` don't accept `--key` yet (argparse error).

- [ ] **Step 3: Add `--key` handling to the two handlers**

In `_cmd_certify`, add a guard at the TOP of the function (right after the signature, before `corpus = load_corpus(...)`) so signing flags are rejected on the wrong format instead of silently ignored:

```python
    if (args.key or args.keyid) and args.format != "dsse":
        print("certify: --key/--keyid apply only to --format dsse", file=sys.stderr)
        return 1
```

Then replace the `elif args.format == "dsse":` branch:

```python
    elif args.format == "dsse":
        env = certificate_dsse_envelope(cert)
        if args.key:
            try:
                from .signing import load_private_key, sign_envelope
                env = sign_envelope(env, load_private_key(Path(args.key).read_bytes()), keyid=args.keyid)
            except ModuleNotFoundError as exc:
                return _sign_dep_error(exc)
        out = env.model_dump_json(by_alias=True, exclude_none=True)
```

In `_cmd_export_attestation`, add a guard at the TOP of the function (before `corpus = load_corpus(...)`):

```python
    if args.key and args.format != "dsse":
        print("export-attestation: --key applies only to --format dsse", file=sys.stderr)
        return 1
```

Then replace the `if args.format == "dsse":` body that builds `envelopes`:

```python
    if args.format == "dsse":
        envelopes = [dsse_envelope(s) for s in build_attestation_statements(corpus, contract_index=index)]
        if args.key:
            try:
                from .signing import load_private_key, sign_envelope
                priv = load_private_key(Path(args.key).read_bytes())
                envelopes = [sign_envelope(e, priv) for e in envelopes]
            except ModuleNotFoundError as exc:
                return _sign_dep_error(exc)
        output = "".join(e.model_dump_json(by_alias=True, exclude_none=True) + "\n" for e in envelopes)
        if args.out:
            Path(args.out).write_text(output)
        else:
            sys.stdout.write(output)
        return 0
```

- [ ] **Step 4: Register the new options**

In `_build_parser`, on the `certify` subparser (`p_cert`) add:

```python
    p_cert.add_argument("--key", default=None, help="ed25519 private key PEM; sign the DSSE envelope (dsse format only)")
    p_cert.add_argument("--keyid", default=None, help="override the DSSE signature keyid")
```

On the `export-attestation` subparser (`p_att`) add:

```python
    p_att.add_argument("--key", default=None, help="ed25519 private key PEM; sign each DSSE envelope (dsse format only)")
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_cli_signing.py -v`
Expected: PASS (all). `ruff check src/polymer_claims/cli.py tests/test_cli_signing.py` → clean.

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/cli.py tests/test_cli_signing.py
git commit -m "feat(cli): opt-in --key signing on certify + export-attestation dsse

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final Verification

- [ ] **All new tests green:**

Run: `cd /Users/zbb2/Desktop/polymer-claims && /Users/zbb2/Desktop/polymer-claims/.venv/bin/python -m pytest tests/test_signing.py tests/test_cli_signing.py -v`
Expected: all pass.

- [ ] **End-to-end:** `keygen` → `certify --format dsse --key` → `verify-dsse --pub-key` rc 0; tamper the saved envelope → `verify-dsse` rc 1.
- [ ] **Backward-compat:** `certify --format dsse` and `export-attestation --format dsse` WITHOUT `--key` produce envelopes with empty `signatures` (unsigned, unchanged).
- [ ] **No regressions in the broader CLI/attestation tests:** `pytest tests/test_cli.py tests/attestation/ -q`.
- [ ] **Lint:** `ruff check src/polymer_claims/signing.py src/polymer_claims/cli.py tests/test_signing.py tests/test_cli_signing.py` → clean.
- [ ] **No private keys committed:** `git status` shows no `.key`/`.pem` files staged (tests write them under `tmp_path`).

## Self-Review Notes (planner)

- **Spec coverage:** §2 PAE → Task 1; §3 signing module → Tasks 1–2; §4 CLI (keygen/verify-dsse) → Task 3, (`--key` on certify/export) → Task 4; §5 packaging → Task 2; §6 testing → tests in each task; §8 invariants → Global Constraints + Final Verification; §9 deferred → out of scope.
- **Crypto-free base:** the `cryptography` import is only inside `_require_crypto()` (Task 1), re-raised friendly; `pae` is pure; the missing-dep path is tested (Task 2).
- **Backward-compat:** Task 4 tests assert unsigned `signatures == []`; the signed branch is gated on `args.key` being truthy (default None).
- **Determinism:** ed25519 round-trip tests need no committed keys; keys are generated in-test under `tmp_path`.
- **Signatures cover the envelope bytes:** `sign_envelope`/`verify_envelope` both PAE over `base64.b64decode(env.payload)` — the same bytes — so a payload tamper is detected (tested).
- **API pinned against the real lib:** ed25519 generate/sign/verify + PKCS8/SubjectPublicKeyInfo PEM + `InvalidSignature` are the actual `cryptography` API.

**Review feedback applied (2026-06-23):**
1. `verify-dsse` parses single JSON (incl. pretty) OR NDJSON via `_parse_dsse_envelopes`; unparseable → rc 1.
2. Malformed payload/sig base64, bad JSON, bad PEM → rc 1 / `False`, never a traceback; tests added.
3. `--key`/`--keyid` rejected (rc 1) on non-`dsse` formats (certify + export-attestation); test added.
4. Private key written atomically with `0o600` via `os.open` (no umask leak window).
5. `uv.lock` updated after the pyproject change (Task 2 Step 1/6), with a network-escalation note.
6. `keyid` documented as informational, not trust-bearing; test (`test_keyid_is_informational_not_trusted`).
7. `sign_envelope` single-signer replacement documented (multi-signer deferred §9).
8. Backward-compat tests now assert **byte-identical** unsigned output for certify + export-attestation.
9. Certificate-payloadType signing covered — unit test asserts PAE binds the cert media type + the end-to-end certify-dsse test.
10. Task 2 Step 1 checks availability first, then installs with an explicit network/escalation note (BLOCK rather than weaken crypto tests if it can't install).
