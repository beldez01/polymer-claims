# Real DSSE Signing (local ed25519) — Design Spec

**Status:** Design / approved for planning. v0.1
**Date:** 2026-06-23
**Author:** Z. Belden (brainstormed with Claude)
**Roadmap:** H1.A1 (Arc-2 slice 3 — real signing) in `docs/superpowers/2026-06-23-remaining-roadmap.md`;
the first Track-A step toward a demonstrable, externally-verifiable wedge certificate.

> **One line.** Turn the existing unsigned, *signing-ready* DSSE envelopes (certificate + attestation
> Statement) into genuinely verifiable signed artifacts via **local ed25519 DSSE-PAE signing** —
> offline, deterministic, CI-testable — with a `verify-dsse` path and a `keygen` helper. The
> heavyweight Sigstore keyless story (Fulcio/Rekor transparency log) is documented and deferred.

---

## 0. Context & the fork already settled

The attestation layer already emits DSSE-shaped envelopes with an empty, signing-ready `signatures`
slot (`attestation.py`: `DsseEnvelope` has `payload_type`, base64 `payload`, and
`signatures: tuple[DsseSignature, ...]` where empty = unsigned, "NOT trust-valid"). Two producers
exist — `dsse_envelope(statement)` and `certificate_dsse_envelope(cert)` — surfaced via
`export-attestation --format dsse` (NDJSON) and `certify --format dsse`. **No signing/PAE code
exists.** DSSE signatures are computed over **PAE** (Pre-Authentication Encoding), not the raw
payload.

**Brainstorm decisions (2026-06-23):**
1. **Signing model:** local ed25519 (RFC 8032) DSSE-PAE signing via the `cryptography` lib behind a
   new `[sign]` optional-dependency extra. Deterministic, offline, CI-testable. **NOT** Sigstore
   keyless / cosign — those need OIDC interactivity + network to Fulcio/Rekor + non-deterministic
   output and oppose the project's offline/minimal-dep ethos. Deferred (§9).
2. **Integration:** opt-in `--key PATH` on the EXISTING `certify --format dsse` and
   `export-attestation --format dsse`; signs in place when given, byte-identical to today when
   absent. A standalone `verify-dsse` command and a `keygen` helper. Signs both certificates and
   attestation Statements.

## 1. Hard constraints (load-bearing)

- **Backward-compatible / additive.** With no `--key`, the DSSE output is **byte-identical** to
  today. The `DsseEnvelope` / `DsseSignature` pydantic models are unchanged (the `signatures` slot
  already exists). grammar/protocol untouched.
- **Base install stays crypto-free.** `cryptography` lives only in the new `[sign]` extra. Any code
  path that imports it is reached only when signing/verifying; a missing dep surfaces as a friendly
  "install `polymer-claims[sign]`" message (`ModuleNotFoundError`, `exc.name == "cryptography"`),
  not a traceback.
- **Sign exactly the bytes in the envelope.** The signature body is recovered by base64-decoding the
  envelope's own `payload` field, so the signature covers precisely what a verifier reads — no
  re-serialization drift.
- **Determinism.** ed25519 is deterministic (RFC 8032): a fixed key + message → a fixed signature.
  Tests round-trip (sign→verify==True; tamper/wrong-key→False) and need no committed private keys.
- **No private keys in git.** Keys are operator-supplied PEM files; tests generate ephemeral
  keypairs in-process. `keygen` writes to operator-chosen paths.

## 2. PAE — DSSE Pre-Authentication Encoding

Per the DSSE spec, the signed message is:

```
PAE(type, body) = "DSSEv1" SP LEN(type) SP type SP LEN(body) SP body
```

where `SP` is a single ASCII space, `LEN(x)` is the ASCII-decimal byte length of `x`, `type` is the
UTF-8 `payloadType`, and `body` is the **raw** payload bytes (NOT base64). Pure stdlib; no crypto
dependency. This is the one piece both signing and verification share.

## 3. New module `src/polymer_claims/signing.py`

| Function | Purity | Responsibility |
|---|---|---|
| `pae(payload_type: str, body: bytes) -> bytes` | **Pure** (stdlib) | DSSE Pre-Auth Encoding (§2) |
| `keyid_for(public_key) -> str` | needs `cryptography` | `sha256(pubkey DER SubjectPublicKeyInfo)` → first 16 hex; stable key identifier |
| `sign_envelope(env: DsseEnvelope, private_key, *, keyid: str \| None = None) -> DsseEnvelope` | needs `cryptography` | decode `env.payload` → body; `pae(env.payload_type, body)`; ed25519-sign; return a NEW envelope with `signatures=(DsseSignature(sig=b64(rawsig), keyid=keyid or keyid_for(pub)),)`. **Single-signer by design: replaces any existing signatures** (multi-signer policy deferred, §9). `keyid` is informational, not trust-bearing. |
| `verify_envelope(env: DsseEnvelope, public_key) -> bool` | needs `cryptography` | recompute PAE; True iff ≥1 signature verifies (and ≥1 present). **Malformed input (bad base64 in payload/sig) returns False, never raises.** `keyid` is ignored — verification is by the supplied `public_key` only (§9). |
| `generate_keypair() -> (private_key, public_key)` | needs `cryptography` | fresh ed25519 keypair |
| `load_private_key(path) -> private_key` / `load_public_key(path) -> public_key` | needs `cryptography` | parse PEM (PKCS8 private / SubjectPublicKeyInfo public) |
| `serialize_private_pem(k) -> bytes` / `serialize_public_pem(k) -> bytes` | needs `cryptography` | PEM bytes for `keygen` |

The `cryptography` import is module-local-guarded so importing `signing` for `pae` alone (or in a
base install) does not hard-fail — pattern: a thin `_require_crypto()` helper that imports inside the
signing/verify/key functions and raises a friendly error, while `pae` stays import-free at module top.

> Build-time detail to pin in the plan: exact `cryptography` API
> (`ed25519.Ed25519PrivateKey.generate()`, `.sign(msg)`, `.public_key()`,
> `serialization.load_pem_private_key`, `Encoding.PEM`, `PrivateFormat.PKCS8`,
> `PublicFormat.SubjectPublicKeyInfo`, `NoEncryption`). `verify` raises `InvalidSignature` → caught
> and returned as `False`.

## 4. CLI changes (`src/polymer_claims/cli.py`)

- **`certify CLAIM --format dsse [--key PATH] [--keyid ID]`** — when `--key` is given, load the
  private key and `sign_envelope` the certificate DSSE before dumping; else unchanged. `--keyid`
  overrides the derived keyid (optional).
- **`export-attestation … --format dsse [--key PATH]`** — when `--key` given, sign EACH envelope
  (one per NDJSON line); else unchanged.
- **`verify-dsse PATH --pub-key PATH`** (new) — read a DSSE envelope JSON *or* NDJSON of envelopes;
  load the public key; return `0` iff every envelope has a valid signature, else `1`. Prints a
  one-line per-envelope verdict to stderr and a summary.
- **`keygen --key OUT.key --pub-key OUT.pub`** (new) — generate an ed25519 keypair, write PEM files
  (private `0600` where supported). Refuse to overwrite existing files unless `--force`.

All four guard the `cryptography` import with the friendly `[sign]`-extra message.

## 5. Packaging

`pyproject.toml` → `[project.optional-dependencies]` gains `sign = ["cryptography>=42"]`. `dev` gains
`cryptography>=42` so the test suite can exercise signing. No change to base `dependencies`.

## 6. Testing (TDD)

- **Pure (`pae`):** matches a hand-computed DSSE PAE vector for a known (type, body).
- **Round-trip:** `generate_keypair` → `sign_envelope` → `verify_envelope` is True; a one-byte
  payload tamper → False; verification with a *different* public key → False; an unsigned envelope
  (`signatures=()`) → False.
- **keyid:** `keyid_for` is deterministic for a fixed public key and changes for a different key;
  the signed envelope's `signatures[0].keyid` equals `keyid_for(pub)` unless `--keyid` overrides.
- **PEM round-trip:** `serialize_private_pem`/`load_private_key` (and public) round-trip to a key
  that still verifies.
- **CLI smoke:** `keygen` → `certify --format dsse --key` produces an envelope with a non-empty
  `signatures`; `verify-dsse --pub-key` returns 0; flipping a byte of the saved envelope → `verify-dsse`
  returns 1. `export-attestation --format dsse --key` signs every NDJSON line.
- **Backward-compat:** `certify --format dsse` and `export-attestation --format dsse` WITHOUT `--key`
  produce output byte-identical to the pre-slice render (a committed golden or a direct compare).
- **Missing-dep:** the friendly `[sign]` message path (simulated by forcing the guarded import to
  raise `ModuleNotFoundError(name="cryptography")`).

## 7. Components & flow

```
keygen ──▶ key.pem / pub.pem  (operator holds the private key; distributes pub.pem)

certify --format dsse --key key.pem ─┐
                                     ├─▶ build (un)signed envelope ──▶ sign_envelope(pae+ed25519) ──▶ signed DSSE JSON
export-attestation --format dsse --key key.pem ─┘ (per NDJSON line)

verify-dsse signed.json --pub-key pub.pem ──▶ verify_envelope (recompute PAE, ed25519 verify) ──▶ rc 0/1
```

## 8. Invariants

Additive; unsigned output byte-identical; models unchanged; base install crypto-free; signatures
cover exactly the envelope's payload bytes; ed25519 determinism makes signing reproducible;
grammar/protocol untouched; no private keys committed.

## 9. Deferred (documented, → H1.A1b)

- **Sigstore keyless:** OIDC identity → Fulcio short-lived cert → Rekor transparency log; the full
  industry-standard external-trust story (no key management, public log). Needs network + interactive
  auth + a heavy dep/external `cosign` binary; non-deterministic; can't run offline/CI.
- **cosign interop:** verifying our DSSE envelopes with the `cosign` binary, and vice-versa.
- **Key/trust policy:** rotation, multiple signers, a trust root / allowed-keys policy, keyid→key
  resolution, and **keyid-match enforcement** (a present `keyid` is informational this slice — a
  signature still verifies against an explicitly-supplied `--pub-key` regardless of its keyid).
  Multi-signature envelopes (append-rather-than-replace) also land here; this slice is single-signer.
  This slice verifies against an explicitly-supplied `--pub-key` only.
- **Encrypted private keys / keyrings / env-var key material.**

## 10. References

- `src/polymer_claims/attestation.py` — `DsseEnvelope`, `DsseSignature`, `dsse_envelope`,
  `certificate_dsse_envelope`, the media types.
- `src/polymer_claims/cli.py` — `_cmd_certify`, `_cmd_export_attestation`, `_build_parser`.
- `docs/superpowers/specs/2026-06-21-standards-skin-attestation-design.md`,
  `docs/superpowers/specs/2026-06-21-attestation-dsse-export-design.md` (the unsigned DSSE substrate).
- DSSE spec (PAE): secure-systems-lab/dsse `protocol.md`.
