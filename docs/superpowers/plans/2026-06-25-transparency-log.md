# Transparency-Log Signing + Offline-Verifiable Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local RFC-6962 Merkle *inclusion* log + C2SP signed checkpoint + an offline-verifiable, trust-gated Polymer bundle on top of the existing local ed25519 DSSE signing, behind a `TransparencyLog` seam that a networked Rekor backend can later drop into.

**Architecture:** Two new pure-package modules — `transparency.py` (Merkle math, C2SP checkpoint, `TransparencyLog` protocol, `LocalInclusionLog`) and `bundle.py` (`build_bundle`, trust-gated `verify_bundle`) — plus opt-in CLI wiring (`--transparency-log` on `certify`/`export-attestation`, a new `verify-bundle` subcommand, a reserved `--rekor-url`). All crypto reuses the shipped `[sign]` extra; with no flag, output is byte-identical to today.

**Tech Stack:** Python 3.11+, stdlib (`hashlib`, `base64`, `json`, `pathlib`), `cryptography>=42` (existing `[sign]` extra, ed25519), pydantic v2 (existing `DsseEnvelope`/`DsseSignature`), pytest, Hatchling.

**Spec:** `docs/superpowers/specs/2026-06-25-transparency-log-design.md` (v0.3).

## Global Constraints

- **Additive / byte-identical-when-off.** With no `--transparency-log` flag, `certify` / `export-attestation` output is byte-identical to today. `signing.py`'s existing functions, `attestation.py`'s `DsseEnvelope`/`DsseSignature`, grammar, and protocol are NOT modified (signing.py may gain *new* helper functions only).
- **Base install stays crypto-free.** All `cryptography` use goes through `signing._require_crypto()`; a missing dep surfaces `ModuleNotFoundError(name="cryptography")` → the friendly `pip install 'polymer-claims[sign]'` message via the existing `_sign_dep_error`, never a traceback. `pae`/Merkle math/`canonical_entry_bytes` stay import-free (stdlib only).
- **No new dependencies.** Reuse the `[sign]` extra (`cryptography>=42`) and stdlib only. No `sigstore`/`cosign`/`rekor-cli`.
- **Verification never raises** on malformed input (`verify_inclusion`, `verify_checkpoint`, `verify_bundle`) — return a negative/`INVALID` structured result.
- **Trust-gated success.** `verify-bundle` rc 0 requires BOTH pinned keys (`--pub-key` AND `--log-pub-key`) that MATCH the bundle; a supplied pin that mismatches is `INVALID` (never silently downgraded); fewer than both pinned (but otherwise valid) → `STRUCTURALLY_VALID_UNTRUSTED` (rc 2).
- **Determinism.** Clock and keys are injected (a `clock: Callable[[], str]` and explicit key paths); tests use fixed stubs and ephemeral in-process keys. No private keys committed.
- **Polymer media type, NOT a Sigstore type:** `application/vnd.polymer.bundle.v0.1+json`. The bundle is Sigstore-*inspired*, not wire-compatible (spec §4.4).
- **Hashing is RFC-6962-exact:** `leaf_hash = sha256(0x00 || entry)`, `node_hash = sha256(0x01 || left || right)`, split `k` = largest power of two strictly less than `n`.
- **Run everything with `.venv/bin/python` / `.venv/bin/pytest`** (`python` is not on PATH).

---

## File Structure

- **Create `src/polymer_claims/transparency.py`** — pure Merkle math (`canonical_entry_bytes`, `leaf_hash`, `node_hash`, `merkle_root`, `inclusion_proof`, `verify_inclusion`); C2SP checkpoint (`format_checkpoint_body`, `sign_checkpoint`, `verify_checkpoint`, `parse_checkpoint`, `CheckpointFields`); `LogEntry`, `TransparencyLog` protocol, `LocalInclusionLog`.
- **Create `src/polymer_claims/bundle.py`** — `TrustStatus`, `BundleVerification`, `build_bundle`, `verify_bundle`.
- **Modify `src/polymer_claims/signing.py`** — add two DER helpers (`serialize_public_der`, `load_public_der`); existing functions untouched.
- **Modify `src/polymer_claims/cli.py`** — `--transparency-log`/`--log-dir`/`--log-key` on `certify` & `export-attestation`; new `verify-bundle` subcommand; reserved `--rekor-url`; a `_cmd_verify_bundle` handler + a `_local_inclusion_log` helper.
- **Create tests:** `tests/test_transparency_merkle.py`, `tests/test_transparency_checkpoint.py`, `tests/test_transparency_log.py`, `tests/test_bundle.py`, `tests/test_cli_transparency.py`.
- **Modify docs (Task 6):** spec status line, roadmap H1.A1, README/ARCHITECTURE_CURRENT CLI lists, CONTINUE.md.

---

### Task 1: RFC-6962 Merkle math + canonical entry bytes

**Files:**
- Create: `src/polymer_claims/transparency.py`
- Test: `tests/test_transparency_merkle.py`

**Interfaces:**
- Consumes: `polymer_claims.attestation.DsseEnvelope` (fields `payload_type: str`, `payload: str`, `signatures: tuple[DsseSignature, ...]`; each `DsseSignature` has `sig: str`, `keyid: str | None`).
- Produces:
  - `canonical_entry_bytes(env: DsseEnvelope) -> bytes`
  - `leaf_hash(entry: bytes) -> bytes`
  - `node_hash(left: bytes, right: bytes) -> bytes`
  - `merkle_root(leaves: list[bytes]) -> bytes` (`leaves` = raw entry bytes, `len>=1`)
  - `inclusion_proof(leaves: list[bytes], index: int) -> list[bytes]`
  - `verify_inclusion(leaf: bytes, index: int, tree_size: int, proof: list[bytes], root: bytes) -> bool`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_transparency_merkle.py`:

```python
import base64
import hashlib

import pytest

from polymer_claims import transparency as T
from polymer_claims.attestation import DsseEnvelope, DsseSignature


def _lh(d: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + d).digest()


def _nh(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def test_leaf_and_node_hash_are_domain_separated():
    assert T.leaf_hash(b"abc") == hashlib.sha256(b"\x00abc").digest()
    assert T.node_hash(b"L" * 32, b"R" * 32) == hashlib.sha256(b"\x01" + b"L" * 32 + b"R" * 32).digest()


def test_merkle_root_n1_is_leaf_hash():
    assert T.merkle_root([b"d0"]) == _lh(b"d0")


def test_merkle_root_n2():
    assert T.merkle_root([b"d0", b"d1"]) == _nh(_lh(b"d0"), _lh(b"d1"))


def test_merkle_root_n3_splits_at_largest_power_of_two_below_n():
    # k = 2 -> left = {d0,d1}, right = {d2}
    leaves = [b"d0", b"d1", b"d2"]
    expected = _nh(_nh(_lh(b"d0"), _lh(b"d1")), _lh(b"d2"))
    assert T.merkle_root(leaves) == expected


def test_merkle_root_n5_split_structure():
    # k = 4 -> left = {d0..d3}, right = {d4}
    d = [bytes([i]) for i in range(5)]
    lh = [_lh(x) for x in d]
    left = _nh(_nh(lh[0], lh[1]), _nh(lh[2], lh[3]))
    expected = _nh(left, lh[4])
    assert T.merkle_root(d) == expected


def test_merkle_root_empty_raises():
    with pytest.raises(ValueError):
        T.merkle_root([])


@pytest.mark.parametrize("n", list(range(1, 10)))
def test_inclusion_proof_round_trip_every_leaf(n):
    leaves = [bytes([i]) for i in range(n)]
    root = T.merkle_root(leaves)
    for idx in range(n):
        proof = T.inclusion_proof(leaves, idx)
        assert T.verify_inclusion(T.leaf_hash(leaves[idx]), idx, n, proof, root) is True


def test_verify_inclusion_rejects_tampered_proof():
    leaves = [bytes([i]) for i in range(6)]
    root = T.merkle_root(leaves)
    proof = T.inclusion_proof(leaves, 2)
    bad = list(proof)
    bad[0] = bytes(32)  # flip a sibling
    assert T.verify_inclusion(T.leaf_hash(leaves[2]), 2, 6, bad, root) is False


def test_verify_inclusion_rejects_wrong_index_size_root_and_malformed():
    leaves = [bytes([i]) for i in range(6)]
    root = T.merkle_root(leaves)
    proof = T.inclusion_proof(leaves, 2)
    leaf = T.leaf_hash(leaves[2])
    assert T.verify_inclusion(leaf, 3, 6, proof, root) is False          # wrong index
    assert T.verify_inclusion(leaf, 2, 7, proof, root) is False          # wrong tree_size
    assert T.verify_inclusion(leaf, 2, 6, proof, bytes(32)) is False     # wrong root
    assert T.verify_inclusion(leaf, 2, 6, proof + [bytes(32)], root) is False  # over-long
    assert T.verify_inclusion(leaf, 2, 6, [], root) is False             # truncated
    assert T.verify_inclusion(leaf, -1, 6, proof, root) is False         # bad index, no raise


def test_canonical_entry_bytes_is_sorted_compact_json_of_signed_envelope():
    env = DsseEnvelope(
        payload_type="application/vnd.polymer.certificate+json",
        payload=base64.b64encode(b"hello").decode("ascii"),
        signatures=(DsseSignature(sig="QUJD", keyid="abcd1234"),),
    )
    out = T.canonical_entry_bytes(env)
    import json
    parsed = json.loads(out)
    assert parsed == {
        "payloadType": "application/vnd.polymer.certificate+json",
        "payload": base64.b64encode(b"hello").decode("ascii"),
        "signatures": [{"sig": "QUJD", "keyid": "abcd1234"}],
    }
    assert out == json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert T.canonical_entry_bytes(env) == out  # deterministic
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_transparency_merkle.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_claims.transparency'`.

- [ ] **Step 3: Write the minimal implementation**

Create `src/polymer_claims/transparency.py`:

```python
"""Local RFC-6962 Merkle inclusion log + C2SP signed checkpoint for Polymer bundles.

Merkle math and `canonical_entry_bytes` are pure stdlib (no crypto). The checkpoint signing/verify
and the local log reuse `signing._require_crypto()` so the base install stays crypto-free. v1 is a
Merkle *inclusion* log (no consistency proofs -> no verified append-only-ness); see
docs/superpowers/specs/2026-06-25-transparency-log-design.md.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from polymer_claims.attestation import DsseEnvelope


# --- canonical leaf bytes -------------------------------------------------------------------------
def canonical_entry_bytes(env: DsseEnvelope) -> bytes:
    """Deterministic canonical JSON of the SIGNED envelope — the bytes that become a Merkle leaf.
    Both submit and verify derive the leaf from this single function (no re-serialization drift)."""
    obj = {
        "payloadType": env.payload_type,
        "payload": env.payload,
        "signatures": [{"sig": s.sig, "keyid": s.keyid} for s in env.signatures],
    }
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


# --- RFC-6962 Merkle tree hash (SHA-256, domain-separated) ----------------------------------------
def leaf_hash(entry: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + entry).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _largest_pow2_below(n: int) -> int:
    """Largest power of two strictly less than n (n >= 2)."""
    k = 1
    while k << 1 < n:
        k <<= 1
    return k


def _root_of_hashes(hashes: list[bytes]) -> bytes:
    n = len(hashes)
    if n == 1:
        return hashes[0]
    k = _largest_pow2_below(n)
    return node_hash(_root_of_hashes(hashes[:k]), _root_of_hashes(hashes[k:]))


def merkle_root(leaves: list[bytes]) -> bytes:
    if not leaves:
        raise ValueError("merkle_root requires at least one leaf (empty tree unused in v1)")
    return _root_of_hashes([leaf_hash(d) for d in leaves])


def _proof_from_hashes(hashes: list[bytes], index: int) -> list[bytes]:
    n = len(hashes)
    if n == 1:
        return []
    k = _largest_pow2_below(n)
    if index < k:
        return _proof_from_hashes(hashes[:k], index) + [_root_of_hashes(hashes[k:])]
    return _proof_from_hashes(hashes[k:], index - k) + [_root_of_hashes(hashes[:k])]


def inclusion_proof(leaves: list[bytes], index: int) -> list[bytes]:
    if not 0 <= index < len(leaves):
        raise ValueError(f"index {index} out of range for {len(leaves)} leaves")
    return _proof_from_hashes([leaf_hash(d) for d in leaves], index)


def verify_inclusion(leaf: bytes, index: int, tree_size: int, proof: list[bytes], root: bytes) -> bool:
    """Recompute the root from (leaf, index, tree_size, proof) per RFC-6962 §2.1.1 and compare.
    Direction at each step is derived from index/size arithmetic (not stored in the proof). Never
    raises: any structural problem returns False."""
    try:
        if not 0 <= index < tree_size:
            return False
        fn = index
        sn = tree_size - 1        # canonical RFC-6962 audit-path algorithm uses tree_size - 1
        h = leaf
        for sibling in proof:
            if sn == 0:           # ran out of tree before the proof was exhausted
                return False
            if (fn & 1) or (fn == sn):
                h = node_hash(sibling, h)
                if not (fn & 1):
                    while True:
                        fn >>= 1
                        sn >>= 1
                        if (fn & 1) or fn == 0:
                            break
            else:
                h = node_hash(h, sibling)
            fn >>= 1
            sn >>= 1
        return sn == 0 and h == root
    except Exception:
        return False
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_transparency_merkle.py -q`
Expected: PASS (all, including the 9 parametrized round-trips).

- [ ] **Step 5: Lint and commit**

Run: `.venv/bin/ruff check src/polymer_claims/transparency.py tests/test_transparency_merkle.py`
Expected: no errors.

```bash
git add src/polymer_claims/transparency.py tests/test_transparency_merkle.py
git commit -m "feat(transparency): RFC-6962 Merkle math + canonical entry bytes"
```

---

### Task 2: C2SP signed checkpoint

**Files:**
- Modify: `src/polymer_claims/transparency.py` (append checkpoint functions)
- Test: `tests/test_transparency_checkpoint.py`

**Interfaces:**
- Consumes: `signing._require_crypto()` → `(ed25519, serialization, InvalidSignature)`; `signing.generate_keypair()`.
- Produces:
  - `CheckpointFields` dataclass: `origin: str`, `tree_size: int`, `root_hash: bytes`, `timestamp: str`
  - `format_checkpoint_body(origin: str, tree_size: int, root_hash: bytes, timestamp: str) -> str`
  - `sign_checkpoint(origin: str, tree_size: int, root_hash: bytes, timestamp: str, log_private_key) -> str` (full C2SP note string)
  - `verify_checkpoint(note: str, log_public_key) -> bool` (never raises)
  - `parse_checkpoint(note: str) -> CheckpointFields` (raises `ValueError` on malformed; only called inside verify-guarded paths)

**Checkpoint string format (exact):**
```
<origin>\n<tree_size>\n<base64std(root_hash)>\nTimestamp: <rfc3339>\n— <origin> <base64std(keyhint4 || ed25519_sig)>\n
```
The **signed bytes** are the body = the first four lines (through the `Timestamp:` line's `\n`), i.e. everything before the `— ` signature line. `keyhint4` = `sha256(origin.encode() + b"\n" + pubkey_DER)[:4]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_transparency_checkpoint.py`:

```python
import base64

import pytest

from polymer_claims import signing
from polymer_claims import transparency as T

pytest.importorskip("cryptography")

ORIGIN = "polymer-claims-local-log"
ROOT = bytes(range(32))
TS = "2026-06-25T00:00:00Z"


def test_body_layout_is_origin_size_b64root_timestamp_then_blank_line():
    body = T.format_checkpoint_body(ORIGIN, 3, ROOT, TS)
    lines = body.split("\n")
    assert lines[0] == ORIGIN
    assert lines[1] == "3"
    assert lines[2] == base64.b64encode(ROOT).decode("ascii")
    assert lines[3] == f"Timestamp: {TS}"
    assert body.endswith("\n\n")  # C2SP: a blank line terminates the signed body


def test_sign_then_verify_round_trip_and_parse():
    priv, pub = signing.generate_keypair()
    note = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    assert "\n— " in note  # contains an em-dash signature line
    assert T.verify_checkpoint(note, pub) is True
    fields = T.parse_checkpoint(note)
    assert fields.origin == ORIGIN
    assert fields.tree_size == 3
    assert fields.root_hash == ROOT
    assert fields.timestamp == TS


def test_verify_fails_on_body_tamper():
    priv, pub = signing.generate_keypair()
    note = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    tampered = note.replace("\n3\n", "\n4\n", 1)  # change tree_size in the signed body
    assert T.verify_checkpoint(tampered, pub) is False


def test_verify_fails_on_signature_tamper():
    priv, pub = signing.generate_keypair()
    note = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    head, sig_line = note.rsplit(" ", 1)
    forged = head + " " + base64.b64encode(b"\x00" * 68).decode("ascii") + "\n"
    assert T.verify_checkpoint(forged, pub) is False


def test_verify_fails_with_wrong_key():
    priv, _ = signing.generate_keypair()
    _, other_pub = signing.generate_keypair()
    note = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    assert T.verify_checkpoint(note, other_pub) is False


def test_verify_fails_on_keyhint_mismatch():
    # Keep the real signature bytes but corrupt the 4-byte keyhint -> must be rejected.
    priv, pub = signing.generate_keypair()
    note = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    head, blob_b64 = note.rstrip("\n").rsplit(" ", 1)
    blob = base64.b64decode(blob_b64, validate=True)
    forged = head + " " + base64.b64encode(b"\xff\xff\xff\xff" + blob[4:]).decode("ascii") + "\n"
    assert T.verify_checkpoint(forged, pub) is False


def test_verify_never_raises_on_malformed():
    _, pub = signing.generate_keypair()
    for junk in ["", "not a checkpoint", "a\nb\nc\n", "— only sig\n"]:
        assert T.verify_checkpoint(junk, pub) is False


def test_signing_is_deterministic_for_fixed_key_and_inputs():
    priv, _ = signing.generate_keypair()
    a = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    b = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    assert a == b  # ed25519 is deterministic; fixed inputs -> identical note
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_transparency_checkpoint.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'format_checkpoint_body'`.

- [ ] **Step 3: Write the minimal implementation**

Append to `src/polymer_claims/transparency.py` (add `from dataclasses import dataclass` to the imports at the top):

```python
from dataclasses import dataclass

_SIG_PREFIX = "— "  # C2SP note signature lines start with em-dash + space


@dataclass(frozen=True)
class CheckpointFields:
    origin: str
    tree_size: int
    root_hash: bytes
    timestamp: str


def format_checkpoint_body(origin: str, tree_size: int, root_hash: bytes, timestamp: str) -> str:
    """The signed C2SP note body: origin / tree_size / base64(root) / Timestamp lines, then a blank
    line that terminates the body (C2SP rule). The trailing blank line IS part of the signed bytes."""
    b64root = base64.b64encode(root_hash).decode("ascii")
    return f"{origin}\n{tree_size}\n{b64root}\nTimestamp: {timestamp}\n\n"


def _keyhint(origin: str, public_key) -> bytes:
    from polymer_claims.signing import serialize_public_der
    return hashlib.sha256(origin.encode("utf-8") + b"\n" + serialize_public_der(public_key)).digest()[:4]


def sign_checkpoint(origin: str, tree_size: int, root_hash: bytes, timestamp: str, log_private_key) -> str:
    from polymer_claims.signing import _require_crypto
    _require_crypto()  # raise the friendly [sign] error early if absent
    body = format_checkpoint_body(origin, tree_size, root_hash, timestamp)
    sig = log_private_key.sign(body.encode("utf-8"))
    hint = _keyhint(origin, log_private_key.public_key())
    blob = base64.b64encode(hint + sig).decode("ascii")
    return f"{body}{_SIG_PREFIX}{origin} {blob}\n"


def parse_checkpoint(note: str) -> CheckpointFields:
    lines = note.splitlines()
    if len(lines) < 5 or not lines[3].startswith("Timestamp: "):
        raise ValueError("malformed checkpoint note")
    return CheckpointFields(
        origin=lines[0],
        tree_size=int(lines[1]),
        root_hash=base64.b64decode(lines[2], validate=True),
        timestamp=lines[3][len("Timestamp: "):],
    )


def verify_checkpoint(note: str, log_public_key) -> bool:
    """True iff >=1 signature line verifies over the note body against log_public_key AND carries the
    expected 4-byte keyhint for that key/origin. Never raises."""
    from polymer_claims.signing import _require_crypto
    _ed, _ser, InvalidSignature = _require_crypto()
    try:
        idx = note.index("\n" + _SIG_PREFIX)
    except ValueError:
        return False
    body = note[: idx + 1].encode("utf-8")  # include the blank line that terminates the body (C2SP)
    origin = note.split("\n", 1)[0]          # origin is the first body line (itself signed)
    expected_hint = _keyhint(origin, log_public_key)
    sig_block = note[idx + 1:]
    for line in sig_block.splitlines():
        if not line.startswith(_SIG_PREFIX):
            continue
        try:
            blob = base64.b64decode(line.rsplit(" ", 1)[1], validate=True)
            if blob[:4] != expected_hint:    # keyhint must match this key/origin
                continue
            log_public_key.verify(blob[4:], body)  # remaining bytes are the ed25519 signature
            return True
        except (ValueError, IndexError, TypeError, InvalidSignature):
            continue
    return False
```

> `_keyhint` depends on `serialize_public_der`, added to `signing.py` in Step 4 below — add that helper as part of this task so Task 2 is self-contained and green (Task 4 also relies on it).

- [ ] **Step 4: Add `serialize_public_der` to signing.py**

Add this helper to `src/polymer_claims/signing.py`, right after `serialize_public_pem`:

```python
def serialize_public_der(public_key) -> bytes:
    _ed, serialization, _inv = _require_crypto()
    return public_key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_transparency_checkpoint.py -q`
Expected: PASS.

- [ ] **Step 6: Lint and commit**

Run: `.venv/bin/ruff check src/polymer_claims/transparency.py src/polymer_claims/signing.py tests/test_transparency_checkpoint.py`
Expected: no errors.

```bash
git add src/polymer_claims/transparency.py src/polymer_claims/signing.py tests/test_transparency_checkpoint.py
git commit -m "feat(transparency): C2SP signed checkpoint (sign/verify/parse) + signing.serialize_public_der"
```

---

### Task 3: `LogEntry`, `TransparencyLog` protocol, `LocalInclusionLog`

**Files:**
- Modify: `src/polymer_claims/transparency.py` (append log types)
- Test: `tests/test_transparency_log.py`

**Interfaces:**
- Consumes: `merkle_root`, `inclusion_proof`, `leaf_hash`, `sign_checkpoint`, `parse_checkpoint`, `verify_inclusion`, `verify_checkpoint`, `canonical_entry_bytes`; `signing.keyid_for`, `signing.serialize_public_pem`.
- Produces:
  - `LogEntry` dataclass: `log_index: int`, `inclusion_proof: list[str]` (hex), `checkpoint: str`, `log_id: str`, `integrated_time: str | None`, `kind_version: str`
  - `TransparencyLog` Protocol: `submit(self, entry_bytes: bytes) -> LogEntry`; property `public_key_pem -> bytes`
  - `LocalInclusionLog(log_dir: Path, log_private_key, *, origin: str = "polymer-claims-local-log", clock: Callable[[], str])` with `submit`, `public_key_pem`
  - module constant `LOCAL_KIND_VERSION = "polymer-inclusion/0.1"`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_transparency_log.py`:

```python
import base64

import pytest

from polymer_claims import signing
from polymer_claims import transparency as T

pytest.importorskip("cryptography")


def _fixed_clock():
    return "2026-06-25T00:00:00Z"


def test_submit_assigns_sequential_indices_and_verifiable_entries(tmp_path):
    priv, pub = signing.generate_keypair()
    log = T.LocalInclusionLog(tmp_path, priv, clock=_fixed_clock)
    entries = [log.submit(f"entry-{i}".encode()) for i in range(3)]
    assert [e.log_index for e in entries] == [0, 1, 2]
    for i, e in enumerate(entries):
        assert e.kind_version == T.LOCAL_KIND_VERSION
        assert e.integrated_time is None
        assert e.log_id == signing.keyid_for(pub)
        fields = T.parse_checkpoint(e.checkpoint)
        assert fields.tree_size == i + 1
        # inclusion proof for THIS entry verifies against the checkpoint root at submit time
        leaf = T.leaf_hash(f"entry-{i}".encode())
        proof = [bytes.fromhex(h) for h in e.inclusion_proof]
        assert T.verify_inclusion(leaf, i, i + 1, proof, fields.root_hash) is True
        assert T.verify_checkpoint(e.checkpoint, pub) is True


def test_reopening_continues_indices_and_grows_root(tmp_path):
    priv, _ = signing.generate_keypair()
    log1 = T.LocalInclusionLog(tmp_path, priv, clock=_fixed_clock)
    log1.submit(b"a")
    log1.submit(b"b")
    log2 = T.LocalInclusionLog(tmp_path, priv, clock=_fixed_clock)
    e = log2.submit(b"c")
    assert e.log_index == 2
    assert T.parse_checkpoint(e.checkpoint).tree_size == 3


def test_public_key_pem_matches_the_log_key(tmp_path):
    priv, pub = signing.generate_keypair()
    log = T.LocalInclusionLog(tmp_path, priv, clock=_fixed_clock)
    assert log.public_key_pem == signing.serialize_public_pem(pub)


def test_determinism_fixed_key_and_clock(tmp_path):
    priv, _ = signing.generate_keypair()
    a = T.LocalInclusionLog(tmp_path / "a", priv, clock=_fixed_clock).submit(b"x")
    b = T.LocalInclusionLog(tmp_path / "b", priv, clock=_fixed_clock).submit(b"x")
    assert a.checkpoint == b.checkpoint and a.inclusion_proof == b.inclusion_proof
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_transparency_log.py -q`
Expected: FAIL — `AttributeError: ... 'LocalInclusionLog'`.

- [ ] **Step 3: Write the minimal implementation**

Append to `src/polymer_claims/transparency.py` (add `from pathlib import Path` and `from typing import Callable, Protocol` to the imports):

```python
from pathlib import Path
from typing import Callable, Protocol

LOCAL_KIND_VERSION = "polymer-inclusion/0.1"


@dataclass(frozen=True)
class LogEntry:
    log_index: int
    inclusion_proof: list[str]      # hex sibling hashes
    checkpoint: str                 # C2SP signed-note string (state AFTER this entry)
    log_id: str
    integrated_time: str | None
    kind_version: str


class TransparencyLog(Protocol):
    def submit(self, entry_bytes: bytes) -> LogEntry: ...

    @property
    def public_key_pem(self) -> bytes: ...


class LocalInclusionLog:
    """Append-only Merkle inclusion log backed by entries.jsonl (base64 lines). Single-process,
    single-writer; no consistency proofs (not verified-append-only). The clock callable returns an
    RFC-3339 UTC string (injected for determinism)."""

    def __init__(self, log_dir, log_private_key, *, origin: str = "polymer-claims-local-log",
                 clock: Callable[[], str]):
        self._dir = Path(log_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "entries.jsonl"
        self._key = log_private_key
        self._origin = origin
        self._clock = clock

    def _load_leaves(self) -> list[bytes]:
        if not self._path.exists():
            return []
        leaves = []
        for line in self._path.read_text().splitlines():
            if line:
                leaves.append(base64.b64decode(line, validate=True))
        return leaves

    @property
    def public_key_pem(self) -> bytes:
        from polymer_claims.signing import serialize_public_pem
        return serialize_public_pem(self._key.public_key())

    def submit(self, entry_bytes: bytes) -> LogEntry:
        from polymer_claims.signing import keyid_for
        leaves = self._load_leaves()
        index = len(leaves)
        leaves.append(entry_bytes)
        with self._path.open("a") as fh:
            fh.write(base64.b64encode(entry_bytes).decode("ascii") + "\n")
        root = merkle_root(leaves)
        proof = inclusion_proof(leaves, index)
        checkpoint = sign_checkpoint(self._origin, len(leaves), root, self._clock(), self._key)
        return LogEntry(
            log_index=index,
            inclusion_proof=[h.hex() for h in proof],
            checkpoint=checkpoint,
            log_id=keyid_for(self._key.public_key()),
            integrated_time=None,
            kind_version=LOCAL_KIND_VERSION,
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_transparency_log.py -q`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

Run: `.venv/bin/ruff check src/polymer_claims/transparency.py tests/test_transparency_log.py`
Expected: no errors.

```bash
git add src/polymer_claims/transparency.py tests/test_transparency_log.py
git commit -m "feat(transparency): LogEntry + TransparencyLog protocol + LocalInclusionLog"
```

---

### Task 4: Polymer bundle — `build_bundle` (keyid-enforced) + trust-gated `verify_bundle`

**Files:**
- Create: `src/polymer_claims/bundle.py`
- Modify: `src/polymer_claims/signing.py` (add `load_public_der`)
- Test: `tests/test_bundle.py`

**Interfaces:**
- Consumes: `attestation.DsseEnvelope`/`DsseSignature`; `signing.keyid_for`, `signing.serialize_public_der`, `signing.load_public_der` (new), `signing.verify_envelope`; `transparency.canonical_entry_bytes`, `leaf_hash`, `verify_inclusion`, `verify_checkpoint`, `parse_checkpoint`, `LogEntry`.
- Produces:
  - `MEDIA_TYPE = "application/vnd.polymer.bundle.v0.1+json"`
  - `TrustStatus(str, Enum)`: `TRUSTED_VALID`, `STRUCTURALLY_VALID_UNTRUSTED`, `INVALID`
  - `BundleVerification` dataclass: `status: TrustStatus`, `envelope_signature_ok: bool`, `inclusion_ok: bool`, `checkpoint_signature_ok: bool`, `signing_key_pinned: bool`, `log_key_pinned: bool`, `reason: str`
  - `build_bundle(env: DsseEnvelope, signing_public_key, log_entry: LogEntry, log_public_key) -> dict`
  - `verify_bundle(bundle: dict, *, signing_trust_key=None, log_trust_key=None) -> BundleVerification`

- [ ] **Step 1: Add `load_public_der` to signing.py**

Add to `src/polymer_claims/signing.py` after `load_public_key`:

```python
def load_public_der(data: bytes):
    ed25519, serialization, _inv = _require_crypto()
    key = serialization.load_der_public_key(data)
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise ValueError(f"not an Ed25519 public key (got {type(key).__name__})")
    return key
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_bundle.py`:

```python
import base64
import copy

import pytest

from polymer_claims import bundle as B
from polymer_claims import signing
from polymer_claims import transparency as T
from polymer_claims.attestation import DsseEnvelope

pytest.importorskip("cryptography")


def _clock():
    return "2026-06-25T00:00:00Z"


def _make_signed_bundle(tmp_path):
    sig_priv, sig_pub = signing.generate_keypair()
    log_priv, log_pub = signing.generate_keypair()
    env = DsseEnvelope(
        payload_type="application/vnd.polymer.certificate+json",
        payload=base64.b64encode(b'{"claim":"x"}').decode("ascii"),
    )
    env = signing.sign_envelope(env, sig_priv)
    log = T.LocalInclusionLog(tmp_path, log_priv, clock=_clock)
    entry = log.submit(T.canonical_entry_bytes(env))
    b = B.build_bundle(env, sig_pub, entry, log_pub)
    return b, sig_pub, log_pub


def test_build_bundle_shape_and_media_type(tmp_path):
    b, _, _ = _make_signed_bundle(tmp_path)
    assert b["mediaType"] == "application/vnd.polymer.bundle.v0.1+json"
    assert b["mediaType"] != "application/vnd.dev.sigstore.bundle.v0.3+json"  # NOT a Sigstore type
    vm = b["verificationMaterial"]
    assert set(vm) == {"signingKey", "logKey", "inclusion"}
    assert set(vm["signingKey"]) == {"rawBytesDER", "keyHint"}
    assert set(vm["logKey"]) == {"rawBytesDER", "keyHint"}
    assert set(vm["inclusion"]) == {
        "logIndex", "logId", "kindVersion", "integratedTime", "treeSize", "rootHashHex",
        "hashesHex", "checkpoint",
    }
    assert set(b["dsseEnvelope"]) >= {"payloadType", "payload", "signatures"}


def test_build_bundle_rejects_keyid_mismatch(tmp_path):
    sig_priv, sig_pub = signing.generate_keypair()
    log_priv, log_pub = signing.generate_keypair()
    env = DsseEnvelope(payload=base64.b64encode(b"x").decode("ascii"))
    env = signing.sign_envelope(env, sig_priv, keyid="deadbeef")  # NOT keyid_for(sig_pub)
    entry = T.LocalInclusionLog(tmp_path, log_priv, clock=_clock).submit(T.canonical_entry_bytes(env))
    with pytest.raises(ValueError):
        B.build_bundle(env, sig_pub, entry, log_pub)
    assert env.signatures[0].keyid == "deadbeef"  # sanity


def test_verify_trusted_when_both_keys_pinned(tmp_path):
    b, sig_pub, log_pub = _make_signed_bundle(tmp_path)
    r = B.verify_bundle(b, signing_trust_key=sig_pub, log_trust_key=log_pub)
    assert r.status == B.TrustStatus.TRUSTED_VALID
    assert r.envelope_signature_ok and r.inclusion_ok and r.checkpoint_signature_ok
    assert r.signing_key_pinned and r.log_key_pinned and r.reason == ""


def test_verify_untrusted_without_pins(tmp_path):
    b, _, _ = _make_signed_bundle(tmp_path)
    r = B.verify_bundle(b)
    assert r.status == B.TrustStatus.STRUCTURALLY_VALID_UNTRUSTED
    assert r.envelope_signature_ok and r.inclusion_ok and r.checkpoint_signature_ok
    assert not r.signing_key_pinned and not r.log_key_pinned


def test_verify_one_pin_is_not_trusted(tmp_path):
    # Either pin alone leaves the OTHER key merely bundle-embedded -> not a trusted bundle.
    b, sig_pub, log_pub = _make_signed_bundle(tmp_path)
    r_sig_only = B.verify_bundle(b, signing_trust_key=sig_pub)
    r_log_only = B.verify_bundle(b, log_trust_key=log_pub)
    assert r_sig_only.status == B.TrustStatus.STRUCTURALLY_VALID_UNTRUSTED
    assert r_log_only.status == B.TrustStatus.STRUCTURALLY_VALID_UNTRUSTED
    assert r_sig_only.signing_key_pinned and not r_sig_only.log_key_pinned
    assert r_log_only.log_key_pinned and not r_log_only.signing_key_pinned


def test_verify_invalid_when_pinned_key_mismatches(tmp_path):
    b, _, log_pub = _make_signed_bundle(tmp_path)
    _, wrong_pub = signing.generate_keypair()
    r = B.verify_bundle(b, signing_trust_key=wrong_pub, log_trust_key=log_pub)
    assert r.status == B.TrustStatus.INVALID
    assert "signing key" in r.reason.lower()


@pytest.mark.parametrize("mutation", ["payload", "signature", "proof", "ckpt_body", "ckpt_sig",
                                      "signing_key", "log_key", "media_type", "log_id",
                                      "kind_version", "integrated_time"])
def test_verify_invalid_on_each_tamper(tmp_path, mutation):
    b, sig_pub, log_pub = _make_signed_bundle(tmp_path)
    b = copy.deepcopy(b)
    if mutation == "media_type":
        b["mediaType"] = "application/vnd.dev.sigstore.bundle.v0.3+json"
    elif mutation == "log_id":
        b["verificationMaterial"]["inclusion"]["logId"] = "deadbeefdeadbeef"
    elif mutation == "kind_version":
        b["verificationMaterial"]["inclusion"]["kindVersion"] = "dsse/0.0.1"
    elif mutation == "integrated_time":
        b["verificationMaterial"]["inclusion"]["integratedTime"] = "2026-06-25T00:00:00Z"
    elif mutation == "payload":
        b["dsseEnvelope"]["payload"] = base64.b64encode(b"tampered").decode("ascii")
    elif mutation == "signature":
        s = b["dsseEnvelope"]["signatures"][0]["sig"]
        b["dsseEnvelope"]["signatures"][0]["sig"] = base64.b64encode(bytes(64)).decode("ascii") if s else "AA=="
    elif mutation == "proof":
        inc = b["verificationMaterial"]["inclusion"]
        inc["hashesHex"] = (inc["hashesHex"] or ["00" * 32])
        inc["hashesHex"][0] = "11" * 32
    elif mutation == "ckpt_body":
        ck = b["verificationMaterial"]["inclusion"]["checkpoint"]
        b["verificationMaterial"]["inclusion"]["checkpoint"] = ck.replace("\n1\n", "\n2\n", 1)
    elif mutation == "ckpt_sig":
        ck = b["verificationMaterial"]["inclusion"]["checkpoint"]
        head, _ = ck.rsplit(" ", 1)
        b["verificationMaterial"]["inclusion"]["checkpoint"] = head + " " + base64.b64encode(bytes(68)).decode() + "\n"
    elif mutation == "signing_key":
        _, other = signing.generate_keypair()
        b["verificationMaterial"]["signingKey"]["rawBytesDER"] = base64.b64encode(
            signing.serialize_public_der(other)).decode("ascii")
    elif mutation == "log_key":
        _, other = signing.generate_keypair()
        b["verificationMaterial"]["logKey"]["rawBytesDER"] = base64.b64encode(
            signing.serialize_public_der(other)).decode("ascii")
    r = B.verify_bundle(b, signing_trust_key=sig_pub, log_trust_key=log_pub)
    assert r.status == B.TrustStatus.INVALID


def test_verify_never_raises_on_garbage():
    for junk in [{}, {"verificationMaterial": {}}, {"dsseEnvelope": 5}]:
        r = B.verify_bundle(junk)
        assert r.status == B.TrustStatus.INVALID
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_bundle.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_claims.bundle'`.

- [ ] **Step 4: Write the minimal implementation**

Create `src/polymer_claims/bundle.py`:

```python
"""Polymer bundle (Sigstore-INSPIRED, not wire-compatible — see spec §4.4): a signed DSSE envelope +
its inclusion proof + signed checkpoint, verifiable fully offline against PINNED keys.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum

from polymer_claims import signing
from polymer_claims import transparency as T
from polymer_claims.attestation import DsseEnvelope

MEDIA_TYPE = "application/vnd.polymer.bundle.v0.1+json"


class TrustStatus(str, Enum):
    TRUSTED_VALID = "trusted_valid"
    STRUCTURALLY_VALID_UNTRUSTED = "structurally_valid_untrusted"
    INVALID = "invalid"


@dataclass(frozen=True)
class BundleVerification:
    status: TrustStatus
    envelope_signature_ok: bool
    inclusion_ok: bool
    checkpoint_signature_ok: bool
    signing_key_pinned: bool
    log_key_pinned: bool
    reason: str


def build_bundle(env: DsseEnvelope, signing_public_key, log_entry: T.LogEntry, log_public_key) -> dict:
    """Assemble a Polymer bundle. Enforces (spec finding-6) that the envelope carries exactly one
    signature whose keyid == keyid_for(signing_public_key); else ValueError."""
    expected_kid = signing.keyid_for(signing_public_key)
    if len(env.signatures) != 1 or env.signatures[0].keyid != expected_kid:
        raise ValueError(
            "build_bundle: envelope must carry exactly one signature whose keyid matches the "
            f"verification key ({expected_kid!r})"
        )
    fields = T.parse_checkpoint(log_entry.checkpoint)
    return {
        "mediaType": MEDIA_TYPE,
        "$schemaNote": "Sigstore-inspired layout; not wire-compatible with dev.sigstore.bundle. See spec §4.4.",
        "verificationMaterial": {
            "signingKey": {
                "rawBytesDER": base64.b64encode(signing.serialize_public_der(signing_public_key)).decode("ascii"),
                "keyHint": expected_kid,
            },
            "logKey": {
                "rawBytesDER": base64.b64encode(signing.serialize_public_der(log_public_key)).decode("ascii"),
                "keyHint": signing.keyid_for(log_public_key),
            },
            "inclusion": {
                "logIndex": log_entry.log_index,
                "logId": log_entry.log_id,
                "kindVersion": log_entry.kind_version,
                "integratedTime": log_entry.integrated_time,
                "treeSize": fields.tree_size,
                "rootHashHex": fields.root_hash.hex(),
                "hashesHex": list(log_entry.inclusion_proof),
                "checkpoint": log_entry.checkpoint,
            },
        },
        "dsseEnvelope": {
            "payloadType": env.payload_type,
            "payload": env.payload,
            "signatures": [{"sig": s.sig, "keyid": s.keyid} for s in env.signatures],
        },
    }


def _fail(reason: str, **flags) -> BundleVerification:
    base = dict(envelope_signature_ok=False, inclusion_ok=False, checkpoint_signature_ok=False,
                signing_key_pinned=False, log_key_pinned=False)
    base.update(flags)
    return BundleVerification(status=TrustStatus.INVALID, reason=reason, **base)


def verify_bundle(bundle: dict, *, signing_trust_key=None, log_trust_key=None) -> BundleVerification:
    """Trust-gated offline verifier. Never raises. rc-mapping is the CLI's job; this returns status."""
    try:
        if not isinstance(bundle, dict) or bundle.get("mediaType") != MEDIA_TYPE:
            return _fail(f"wrong or missing mediaType (expected {MEDIA_TYPE})")
        vm = bundle["verificationMaterial"]
        inc = vm["inclusion"]
        env = DsseEnvelope.model_validate(bundle["dsseEnvelope"])
        embedded_sig_der = base64.b64decode(vm["signingKey"]["rawBytesDER"], validate=True)
        embedded_log_der = base64.b64decode(vm["logKey"]["rawBytesDER"], validate=True)
    except Exception as exc:                       # noqa: BLE001 - never raise on malformed input
        return _fail(f"malformed bundle: {exc}")

    # Trust pinning: a supplied key that does not match the embedded material is a hard INVALID.
    signing_key_pinned = False
    log_key_pinned = False
    try:
        if signing_trust_key is not None:
            if signing.serialize_public_der(signing_trust_key) != embedded_sig_der:
                return _fail("signing key mismatch: pinned key does not match bundle material")
            signing_key_pinned = True
        if log_trust_key is not None:
            if signing.serialize_public_der(log_trust_key) != embedded_log_der:
                return _fail("log key mismatch: pinned key does not match bundle material",
                             signing_key_pinned=signing_key_pinned)
            log_key_pinned = True
        signing_pub = signing.load_public_der(embedded_sig_der)
        log_pub = signing.load_public_der(embedded_log_der)
    except Exception as exc:                       # noqa: BLE001
        return _fail(f"key load failed: {exc}", signing_key_pinned=signing_key_pinned,
                     log_key_pinned=log_key_pinned)

    # (1) DSSE signature over the envelope.
    env_ok = signing.verify_envelope(env, signing_pub)
    # (2) Inclusion metadata is semantically authenticated against the log key + accepted for local.
    metadata_ok = False
    # (3) Inclusion proof recomputes to the checkpoint root at logIndex/treeSize.
    inclusion_ok = False
    # (4) Checkpoint signature vs the log key.
    ckpt_ok = False
    try:
        metadata_ok = (
            inc.get("logId") == signing.keyid_for(log_pub)         # logId binds to the actual log key
            and inc.get("kindVersion") == T.LOCAL_KIND_VERSION      # accepted kind for a local bundle
            and inc.get("integratedTime") is None                   # local v1 has no integrated time
        )
        fields = T.parse_checkpoint(inc["checkpoint"])
        leaf = T.leaf_hash(T.canonical_entry_bytes(env))
        proof = [bytes.fromhex(h) for h in inc["hashesHex"]]
        inclusion_ok = (
            fields.root_hash.hex() == inc["rootHashHex"]
            and fields.tree_size == inc["treeSize"]
            and T.verify_inclusion(leaf, inc["logIndex"], inc["treeSize"], proof, fields.root_hash)
        )
        ckpt_ok = T.verify_checkpoint(inc["checkpoint"], log_pub)
    except Exception:                              # noqa: BLE001
        inclusion_ok = False

    if not (env_ok and metadata_ok and inclusion_ok and ckpt_ok):
        if not env_ok:
            failing = "envelope signature"
        elif not metadata_ok:
            failing = "inclusion metadata (logId/kindVersion/integratedTime)"
        elif not inclusion_ok:
            failing = "inclusion proof"
        else:
            failing = "checkpoint signature"
        return BundleVerification(
            status=TrustStatus.INVALID, envelope_signature_ok=env_ok, inclusion_ok=inclusion_ok,
            checkpoint_signature_ok=ckpt_ok, signing_key_pinned=signing_key_pinned,
            log_key_pinned=log_key_pinned, reason=f"{failing} verification failed",
        )
    # TRUSTED_VALID requires BOTH the signer identity AND the log trust root to be pinned and matched;
    # one alone leaves the other merely bundle-embedded (not trusted).
    status = TrustStatus.TRUSTED_VALID if (signing_key_pinned and log_key_pinned) \
        else TrustStatus.STRUCTURALLY_VALID_UNTRUSTED
    reason = "" if status == TrustStatus.TRUSTED_VALID \
        else "both --pub-key and --log-pub-key must be pinned for trust (structurally valid only)"
    return BundleVerification(
        status=status, envelope_signature_ok=True, inclusion_ok=True, checkpoint_signature_ok=True,
        signing_key_pinned=signing_key_pinned, log_key_pinned=log_key_pinned, reason=reason,
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_bundle.py -q`
Expected: PASS (all, including the 7 parametrized tamper cases).

- [ ] **Step 6: Lint and commit**

Run: `.venv/bin/ruff check src/polymer_claims/bundle.py src/polymer_claims/signing.py tests/test_bundle.py`
Expected: no errors.

```bash
git add src/polymer_claims/bundle.py src/polymer_claims/signing.py tests/test_bundle.py
git commit -m "feat(bundle): keyid-enforced build_bundle + trust-gated verify_bundle (TrustStatus)"
```

---

### Task 5: CLI wiring — `--transparency-log`, `verify-bundle`, reserved `--rekor-url`

**Files:**
- Modify: `src/polymer_claims/cli.py`
- Test: `tests/test_cli_transparency.py`

**Interfaces:**
- Consumes: `transparency.LocalInclusionLog`, `canonical_entry_bytes`; `bundle.build_bundle`, `verify_bundle`, `TrustStatus`; `signing.load_private_key`, `load_public_key`, `generate_keypair`, `serialize_private_pem`, `keyid_for`, `load_private_key`; existing `_sign_dep_error`, `_atomic_write`, `load_corpus`, `certificate_dsse_envelope`, `dsse_envelope`, `build_attestation_statements`, `resolve_contract_index`.
- Produces: CLI flags `--transparency-log` (store_true), `--log-dir` (default `./.polymer-tlog`), `--log-key` (default None → `DIR/log.key`), `--rekor-url` (default None) on `certify` & `export-attestation`; new subcommand `verify-bundle PATH [--pub-key] [--log-pub-key]`; handler `_cmd_verify_bundle`; helper `_open_local_log(args) -> (LocalInclusionLog, sign-info) | int`.

> **Exit codes for `verify-bundle`:** `0` iff every bundle is `TRUSTED_VALID`; `1` if any is `INVALID`; `2` if none INVALID but any is `STRUCTURALLY_VALID_UNTRUSTED`. INVALID dominates UNTRUSTED.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_transparency.py`:

Run the CLI in-process via `main([...])` + `capsys` and build the corpus with the SAME fixture helper
`tests/test_cli_signing.py` uses (`_corpus_path` over `tests.attestation._fixtures`; claim id is
`"c1"`). Do NOT use a static `tests/data/*.json` file or subprocess.

```python
import base64
import json

import pytest

from polymer_claims.cli import main
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing, mc, sat

pytest.importorskip("cryptography")


def _corpus_path(tmp_path):
    corpus = corpus_with(licensed_claim("c1", licensing(sat(mc()))))
    p = tmp_path / "corpus.json"
    p.write_text(corpus.model_dump_json())
    return p


def _keys(tmp_path):
    k, p = tmp_path / "s.key", tmp_path / "s.pub"
    assert main(["keygen", "--key", str(k), "--pub-key", str(p)]) == 0
    return k, p


def _log_pub_pem(logdir, tmp_path):
    # Auto-generated private log key is at logdir/log.key; write its public PEM for pinning.
    from polymer_claims import signing
    priv = signing.load_private_key((logdir / "log.key").read_bytes())
    out = tmp_path / "auto-log.pub"
    out.write_bytes(signing.serialize_public_pem(priv.public_key()))
    return out


def _certify_bundle(tmp_path, capsys, sk, logdir, *extra):
    capsys.readouterr()  # clear prior stderr/stdout (e.g. keygen)
    rc = main(["certify", "c1", "--corpus", str(_corpus_path(tmp_path)), "--format", "dsse",
               "--key", str(sk), "--transparency-log", "--log-dir", str(logdir), *extra])
    return rc, capsys.readouterr()


def test_certify_transparency_log_emits_verifiable_bundle(tmp_path, capsys):
    sk, sp = _keys(tmp_path)
    logdir = tmp_path / "tlog"
    rc, cap = _certify_bundle(tmp_path, capsys, sk, logdir)
    assert rc == 0, cap.err
    bundle = json.loads(cap.out)
    assert bundle["mediaType"] == "application/vnd.polymer.bundle.v0.1+json"
    bpath = tmp_path / "b.json"
    bpath.write_text(cap.out)
    logpub = _log_pub_pem(logdir, tmp_path)
    assert main(["verify-bundle", str(bpath), "--pub-key", str(sp), "--log-pub-key", str(logpub)]) == 0


def test_verify_bundle_untrusted_without_both_keys_returns_2(tmp_path, capsys):
    sk, sp = _keys(tmp_path)
    logdir = tmp_path / "tlog"
    rc, cap = _certify_bundle(tmp_path, capsys, sk, logdir)
    bpath = tmp_path / "b.json"
    bpath.write_text(cap.out)
    assert main(["verify-bundle", str(bpath)]) == 2                         # no pins
    assert main(["verify-bundle", str(bpath), "--pub-key", str(sp)]) == 2   # only one pin -> still untrusted


def test_verify_bundle_tampered_returns_1(tmp_path, capsys):
    sk, sp = _keys(tmp_path)
    logdir = tmp_path / "tlog"
    rc, cap = _certify_bundle(tmp_path, capsys, sk, logdir)
    bundle = json.loads(cap.out)
    bundle["dsseEnvelope"]["payload"] = base64.b64encode(b"tampered").decode("ascii")
    bpath = tmp_path / "b.json"
    bpath.write_text(json.dumps(bundle))
    logpub = _log_pub_pem(logdir, tmp_path)
    assert main(["verify-bundle", str(bpath), "--pub-key", str(sp), "--log-pub-key", str(logpub)]) == 1


def test_rekor_url_is_reserved_not_implemented(tmp_path, capsys):
    sk, _ = _keys(tmp_path)
    rc, cap = _certify_bundle(tmp_path, capsys, sk, tmp_path / "tlog",
                              "--rekor-url", "https://rekor.sigstore.dev")
    assert rc == 1
    assert "not implemented" in cap.err.lower()


def test_certify_keyid_conflicts_with_transparency_log(tmp_path, capsys):
    sk, _ = _keys(tmp_path)
    rc, cap = _certify_bundle(tmp_path, capsys, sk, tmp_path / "tlog", "--keyid", "deadbeef")
    assert rc == 1
    assert "keyid" in cap.err.lower()


def test_certify_without_flag_still_emits_a_bare_verifiable_envelope(tmp_path, capsys):
    # No-regression: with --transparency-log OFF, certify --format dsse must still produce the SAME
    # kind of artifact as before this slice — a bare signed DSSE envelope that verify-dsse accepts,
    # NOT a bundle. (Mirrors the verify-dsse round-trip pattern in tests/test_cli_signing.py.)
    sk, sp = _keys(tmp_path)
    cp = _corpus_path(tmp_path)
    capsys.readouterr()
    assert main(["certify", "c1", "--corpus", str(cp), "--format", "dsse", "--key", str(sk)]) == 0
    out = capsys.readouterr().out
    env = json.loads(out)
    assert "mediaType" not in env                                  # NOT a bundle
    assert set(env) >= {"payloadType", "payload", "signatures"}    # a DSSE envelope
    p = tmp_path / "env.json"
    p.write_text(out)
    assert main(["verify-dsse", str(p), "--pub-key", str(sp)]) == 0  # still valid + verifiable
    # determinism is unchanged too (ed25519 + deterministic render)
    capsys.readouterr()
    assert main(["certify", "c1", "--corpus", str(cp), "--format", "dsse", "--key", str(sk)]) == 0
    assert capsys.readouterr().out == out
```

> **Fixture note:** confirm the `tests.attestation._fixtures` import names (`corpus_with`,
> `licensed_claim`, `licensing`, `mc`, `sat`) and the claim id `"c1"` against the top of
> `tests/test_cli_signing.py` before running — reuse exactly what it imports; do NOT invent a corpus.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_cli_transparency.py -q`
Expected: FAIL — `certify: unrecognized arguments: --transparency-log` (the new flags/subcommand do not exist yet).

- [ ] **Step 3: Add the `verify-bundle` parser + flags on certify/export-attestation**

In `src/polymer_claims/cli.py`, add a module-level helper (next to `_build_parser`). `p_cert` and
`p_att` are created at different points in `_build_parser`, so do NOT reference both from one loop —
call the helper immediately after each parser is created (right before its `set_defaults`):

```python
def _add_transparency_flags(parser):
    """Shared --transparency-log family for certify + export-attestation (call after each is created)."""
    parser.add_argument("--transparency-log", action="store_true",
                        help="append the signed DSSE envelope to a local Merkle inclusion log and emit a Polymer bundle (needs --key, --format dsse)")
    parser.add_argument("--log-dir", default="./.polymer-tlog",
                        help="local transparency-log directory (default ./.polymer-tlog)")
    parser.add_argument("--log-key", default=None,
                        help="ed25519 private key PEM for the log (default <log-dir>/log.key, auto-generated)")
    parser.add_argument("--rekor-url", default=None,
                        help="RESERVED: networked Rekor backend is not implemented yet (see spec §7)")
```

Then, in `_build_parser`, call `_add_transparency_flags(p_cert)` immediately after the `certify`
parser's existing `--keyid` argument (before `p_cert.set_defaults(...)`), and
`_add_transparency_flags(p_att)` immediately after the `export-attestation` parser's last argument
(before `p_att.set_defaults(...)`). This avoids referencing `p_cert` before it is assigned.

Add the new subcommand near `verify-dsse`:

```python
    p_vb = sub.add_parser("verify-bundle",
                          help="verify a Polymer bundle (or NDJSON of bundles) offline; rc 0 needs BOTH keys pinned")
    p_vb.add_argument("path", help="path to a bundle JSON or NDJSON of bundles")
    p_vb.add_argument("--pub-key", default=None, help="pin the signer's public key PEM (both --pub-key AND --log-pub-key required for rc 0)")
    p_vb.add_argument("--log-pub-key", default=None, help="pin the log's public key PEM (both --pub-key AND --log-pub-key required for rc 0)")
    p_vb.set_defaults(func=_cmd_verify_bundle)
```

- [ ] **Step 4: Add the log helper + `_cmd_verify_bundle` handler + wire signing paths**

Add a helper and handler to `src/polymer_claims/cli.py` (near `_cmd_verify_dsse`):

```python
def _open_local_log(args):
    """Return (LocalInclusionLog, log_public_key) or an int rc on error. Auto-generates DIR/log.key."""
    from datetime import datetime, timezone
    from .transparency import LocalInclusionLog
    from .signing import generate_keypair, serialize_private_pem, load_private_key
    log_dir = Path(args.log_dir)
    key_path = Path(args.log_key) if args.log_key else log_dir / "log.key"
    try:
        if key_path.exists():
            priv = load_private_key(key_path.read_bytes())
        else:
            log_dir.mkdir(parents=True, exist_ok=True)
            priv, _ = generate_keypair()
            _atomic_write(key_path, serialize_private_pem(priv), mode=0o600)
            print(f"transparency-log: generated log key {key_path}", file=sys.stderr)
    except (OSError, ValueError) as exc:
        print(f"transparency-log: cannot open log key {key_path}: {exc}", file=sys.stderr)
        return 1
    clock = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    return LocalInclusionLog(log_dir, priv, clock=clock), priv.public_key()


def _cmd_verify_bundle(args: argparse.Namespace) -> int:
    try:
        from .bundle import verify_bundle, TrustStatus
        from .signing import load_public_key, _require_crypto
        _require_crypto()   # surface the friendly [sign] hint up front (verify_bundle would otherwise
                            # swallow a missing-crypto error as INVALID via its broad except)
    except ModuleNotFoundError as exc:
        return _sign_dep_error(exc)
    sig_key = log_key = None
    try:
        if args.pub_key:
            sig_key = load_public_key(Path(args.pub_key).read_bytes())
        if args.log_pub_key:
            log_key = load_public_key(Path(args.log_pub_key).read_bytes())
    except ModuleNotFoundError as exc:
        return _sign_dep_error(exc)
    except (OSError, ValueError) as exc:
        print(f"verify-bundle: cannot load public key: {exc}", file=sys.stderr)
        return 1
    try:
        text = Path(args.path).read_text()
    except OSError as exc:
        print(f"verify-bundle: cannot read {args.path}: {exc}", file=sys.stderr)
        return 1
    bundles = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            try:
                bundles.append(json.loads(line))
            except json.JSONDecodeError:
                bundles = None
                break
    if bundles is None:                              # maybe a single multi-line JSON object
        try:
            bundles = [json.loads(text)]
        except json.JSONDecodeError:
            print("verify-bundle: input is not a bundle JSON or NDJSON of bundles", file=sys.stderr)
            return 1
    if not bundles:
        print("verify-bundle: no bundles to verify", file=sys.stderr)
        return 1
    any_invalid = any_untrusted = False
    for i, b in enumerate(bundles):
        r = verify_bundle(b, signing_trust_key=sig_key, log_trust_key=log_key)
        if r.status == TrustStatus.INVALID:
            any_invalid = True
        elif r.status == TrustStatus.STRUCTURALLY_VALID_UNTRUSTED:
            any_untrusted = True
        detail = "" if r.status == TrustStatus.TRUSTED_VALID else f" ({r.reason})"
        print(f"  bundle[{i}]: {r.status.value.upper()}{detail}", file=sys.stderr)
    if any_invalid:
        print("verify-bundle: INVALID bundle(s)", file=sys.stderr)
        return 1
    if any_untrusted:
        print("verify-bundle: structurally valid but UNTRUSTED (pin --pub-key/--log-pub-key for rc 0)", file=sys.stderr)
        return 2
    print("verify-bundle: all bundles TRUSTED_VALID", file=sys.stderr)
    return 0
```

Now wire the signing branches. In `_cmd_certify`, replace the `--format dsse` branch's tail so that after `env = sign_envelope(env, priv, keyid=args.keyid)` it optionally logs:

```python
            if args.transparency_log and args.keyid is not None:
                from .signing import keyid_for
                if args.keyid != keyid_for(priv.public_key()):
                    print("certify: --keyid conflicts with --transparency-log — a bundle requires the "
                          "derived keyid (it must equal the signing key's keyid); omit --keyid", file=sys.stderr)
                    return 1
            env = sign_envelope(env, priv, keyid=args.keyid)
            if args.rekor_url:
                print("certify: networked Rekor backend (--rekor-url) is not implemented yet; see spec §7", file=sys.stderr)
                return 1
            if args.transparency_log:
                from .transparency import canonical_entry_bytes
                from .bundle import build_bundle
                opened = _open_local_log(args)
                if isinstance(opened, int):
                    return opened
                log, log_pub = opened
                entry = log.submit(canonical_entry_bytes(env))
                bundle = build_bundle(env, priv.public_key(), entry, log_pub)
                sys.stdout.write(json.dumps(bundle, indent=2) + "\n")
                return 0
        out = env.model_dump_json(by_alias=True, exclude_none=True)
```

Add a guard at the top of `_cmd_certify` (alongside the existing `--key/--keyid` guard):

```python
    if (args.transparency_log or args.rekor_url) and not args.key:
        print("certify: --transparency-log/--rekor-url require --key (and --format dsse)", file=sys.stderr)
        return 1
```

In `_cmd_export_attestation`, after `envelopes = [sign_envelope(e, priv) for e in envelopes]`, add:

```python
            if args.rekor_url:
                print("export-attestation: networked Rekor backend (--rekor-url) is not implemented yet; see spec §7", file=sys.stderr)
                return 1
            if args.transparency_log:
                from .transparency import canonical_entry_bytes
                from .bundle import build_bundle
                opened = _open_local_log(args)
                if isinstance(opened, int):
                    return opened
                log, log_pub = opened
                bundles = []
                for e in envelopes:
                    entry = log.submit(canonical_entry_bytes(e))
                    bundles.append(build_bundle(e, priv.public_key(), entry, log_pub))
                output = "".join(json.dumps(b, separators=(",", ":")) + "\n" for b in bundles)
                if args.out:
                    Path(args.out).write_text(output)
                else:
                    sys.stdout.write(output)
                return 0
```

And the matching guard near the top of `_cmd_export_attestation`:

```python
    if (args.transparency_log or args.rekor_url) and not args.key:
        print("export-attestation: --transparency-log/--rekor-url require --key (and --format dsse)", file=sys.stderr)
        return 1
```

Ensure `import json` is present at the top of `cli.py` (it almost certainly is; if not, add it).

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_cli_transparency.py -q`
Expected: PASS (the corpus is built in-process via the shared `tests.attestation._fixtures` helper, claim id `"c1"`).

- [ ] **Step 6: Run the full suite + lint**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check src/polymer_claims tests`
Expected: all green (backward-compat test confirms no-flag output unchanged), no lint errors.

- [ ] **Step 7: Commit**

```bash
git add src/polymer_claims/cli.py tests/test_cli_transparency.py
git commit -m "feat(cli): --transparency-log on certify/export-attestation + verify-bundle + reserved --rekor-url"
```

---

### Task 6: Documentation reconciliation

**Files:**
- Modify: `docs/superpowers/specs/2026-06-25-transparency-log-design.md` (status line)
- Modify: `docs/superpowers/2026-06-23-remaining-roadmap.md` (H1.A1 entry)
- Modify: `README.md` and `ARCHITECTURE_CURRENT.md` (repo root — CLI command lists)
- Modify: `docs/superpowers/CONTINUE.md` (add a dated update block)

**Interfaces:** none (docs only). No test cycle — the deliverable is reconciled docs; verify by `grep`.

- [ ] **Step 1: Flip the spec status to shipped**

In `docs/superpowers/specs/2026-06-25-transparency-log-design.md`, change the status line from
`**Status:** Design / approved for planning. v0.3` to
`**Status:** SHIPPED (local-first). v0.3 — implemented on branch feat/transparency-log; networked Rekor backend deferred (§7).`

- [ ] **Step 2: Update the roadmap H1.A1 entry**

In `docs/superpowers/2026-06-23-remaining-roadmap.md`, in the H1.A1 bullet, append after the existing
"Still open: the Sigstore/cosign/Rekor transparency-log layer" sentence:

```
  **UPDATE (2026-06-25):** the LOCAL transparency layer shipped (feat/transparency-log) — a local
  RFC-6962 Merkle inclusion log + C2SP signed checkpoint + a trust-gated, offline-verifiable Polymer
  bundle (Sigstore-INSPIRED, not wire-compatible), behind a `TransparencyLog` seam. New CLI:
  `verify-bundle`, and `--transparency-log` on `certify`/`export-attestation`. Still open: the
  NETWORKED public-Rekor backend (`--rekor-url`, reserved+erroring today) and consistency proofs —
  what add public non-repudiation + verified append-only-ness.
```

- [ ] **Step 3: Update the README + ARCHITECTURE CLI lists**

In `README.md` and `ARCHITECTURE_CURRENT.md` (both at the repo root), find the CLI command list that
already includes `keygen` / `verify-dsse` and add one line each:

```
- `verify-bundle PATH [--pub-key] [--log-pub-key]` — verify a Polymer bundle offline (rc 0 needs BOTH --pub-key and --log-pub-key)
```
and note that `certify`/`export-attestation` gained `--transparency-log` (emits a Polymer bundle: signed DSSE + Merkle inclusion proof + signed checkpoint). Match each file's existing list style.

- [ ] **Step 4: Add a CONTINUE.md update block**

Prepend a dated block to `docs/superpowers/CONTINUE.md` summarizing: H1.A1 local transparency layer
shipped on `feat/transparency-log`; what it delivers vs. the honest boundary (no public
non-repudiation / no verified append-only-ness until the networked backend + consistency proofs);
next open slice = networked Rekor backend. Match the file's existing block format.

- [ ] **Step 5: Verify and commit**

Run: `grep -rn "verify-bundle\|transparency-log\|polymer.bundle" README.md ARCHITECTURE_CURRENT.md docs/superpowers/2026-06-23-remaining-roadmap.md`
Expected: the new lines appear in each file.

```bash
git add docs/ README.md
git commit -m "docs: reconcile for local transparency-log layer (verify-bundle, --transparency-log)"
```

---

## Self-Review

**1. Spec coverage:**
- §2 RFC-6962 math → Task 1 ✓. §3.1 canonical bytes → Task 1 ✓. §3.3 C2SP checkpoint → Task 2 ✓.
  §3.4 LogEntry/protocol + §3.5 LocalInclusionLog → Task 3 ✓. §4.1 bundle shape + §4.2 build/verify +
  §4.3 TrustStatus (TRUSTED_VALID needs BOTH pins; media-type gate; inclusion-metadata authentication
  of logId/kindVersion/integratedTime) → Task 4 `verify_bundle` + tamper tests ✓. §4.4 honesty
  (Polymer media type, not Sigstore) → Task 4 shape test ✓. §5 CLI (flags via `_add_transparency_flags`
  called per-parser, verify-bundle rc 0 needs BOTH keys / 1 / 2, `--keyid`-conflict rejection,
  reserved --rekor-url, no-regression via verify-dsse round-trip) → Task 5 ✓. Finding-6 keyid
  enforcement → Task 4 `build_bundle` + Task 5 CLI guard + tests ✓. C2SP blank-line-terminated signed
  body → Task 2 ✓. §7 seam (forward-compat LogEntry fields) → Task 3 ✓. §0.1/§11 honest-boundary
  wording → Task 6 docs ✓. §8 packaging (no new deps) → no pyproject change needed (reuses `[sign]`);
  confirmed.
**2. Placeholder scan:** No TBD/TODO. The only conditional content is Task 5 Step 1b (corpus fixture),
  which gives an explicit resolution rule (reuse the existing signing test's fixture) rather than a
  placeholder; and the Task 2 `_keyhint` note, which shows the exact clean form to use.
**3. Type consistency:** `canonical_entry_bytes`, `leaf_hash`, `verify_inclusion`, `parse_checkpoint`,
  `LogEntry` fields (`log_index`/`inclusion_proof`/`checkpoint`/`log_id`/`integrated_time`/
  `kind_version`), `TrustStatus`, `BundleVerification` fields, `build_bundle`/`verify_bundle`
  signatures, and `signing.serialize_public_der`/`load_public_der` are used identically across Tasks
  1→5. Bundle JSON keys in `build_bundle` (Task 4) match the keys asserted in the CLI tamper test
  (Task 5) and the shape test (Task 4).
