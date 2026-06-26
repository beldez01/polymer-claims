# Transparency-Log Signing + Offline-Verifiable Bundle (local-first, network-ready) — Design Spec

**Status:** Design / approved for planning. v0.1
**Date:** 2026-06-25
**Author:** Z. Belden (brainstormed with Claude)
**Roadmap:** H1.A1 (Arc-2 slice 3 — real signing), the still-open half. The local ed25519 DSSE
signing of `specs/2026-06-23-dsse-signing-design.md` shipped; this is its deferred §9 successor
("H1.A1b") — the **transparency-log + Sigstore-compatible bundle** layer, scoped local-first.

> **One line.** Append each signed DSSE envelope to an **append-only RFC-6962 Merkle transparency
> log**, return a **signed inclusion proof + checkpoint**, and wrap envelope + proof + checkpoint into
> a **Sigstore-compatible bundle** that anyone can verify **fully offline**. v1 backs the log with a
> local `LocalTransparencyLog`; a networked `RekorTransparencyLog` is a later additive drop-in behind
> the same `TransparencyLog` interface. The bundle format and verifier are backend-agnostic, so the
> network upgrade changes no format and no verification code.

---

## 0. Context & the fork already settled

`signing.py` already does local ed25519 DSSE-PAE signing: `pae`, `sign_envelope(env, priv, *, keyid)`,
`verify_envelope(env, pub) -> bool`, `generate_keypair`, `keyid_for`, the PEM (de)serializers, all
crypto behind `_require_crypto()` (the `[sign]` extra; `cryptography>=42`). The CLI already has
`keygen` and `verify-dsse`, and `--key` on `certify`/`export-attestation`. **None of that changes.**
This slice adds a layer *on top of* a signed envelope.

**Brainstorm decisions (2026-06-25), locked:**
1. **Trust model — key-based + transparency log + offline-verifiable bundle.** Keep the shipped
   operator ed25519 key as the signing identity. A log entry adds tamper-evidence, an inclusion proof,
   and a signed timestamp. It is **NOT** identity-bound (no Fulcio/OIDC — deferred §9).
2. **Implementation — minimal in-house.** `urllib` + `cryptography` + stdlib `hashlib` only. RFC-6962
   Merkle math and checkpoint verification written here; no heavy deps, no `sigstore`/`cosign` binary,
   no `rekor-cli`.
3. **Scope — local-first with an explicit network seam.** v1 ships a **local append-only Merkle log**
   + bundle + offline inclusion verification, all behind a `TransparencyLog` protocol. A networked
   public-Rekor backend is the *next* slice this seam enables (§7); v1 writes no network code.

### 0.1 The honest boundary (state it in docs and CLI help)

A local log delivers **tamper-evidence** (any edit to a logged entry breaks the Merkle root),
**inclusion proofs** (cryptographic proof an envelope is in a log of a given size), **signed
timestamps** (the checkpoint is signed by the log key), and a **fully offline-verifiable bundle**.
It does **NOT** deliver **public non-repudiation** — that requires a *public, independently-operated,
append-only* log (real Rekor), because a local log's operator could rewrite history before anyone
witnessed it. v1 ships all the machinery and verification; public non-repudiation arrives with the
networked backend (§7). The CLI and bundle must not overstate this.

## 1. Hard constraints (load-bearing)

- **Additive / backward-compatible.** With no `--transparency-log` flag, `certify` /
  `export-attestation` output is **byte-identical** to today. `signing.py`, `attestation.py`'s
  `DsseEnvelope`/`DsseSignature`, grammar, and protocol are untouched.
- **Base install stays crypto-free.** All crypto stays behind the existing `[sign]` extra via the
  existing `_require_crypto()`. A missing dep surfaces the same friendly
  `pip install 'polymer-claims[sign]'` message, never a traceback.
- **Offline & deterministic in v1.** No network code path exists in v1. Merkle hashing is pure
  stdlib `hashlib`; verification is pure given the bundle bytes + the log's public key. The only
  non-determinism is the checkpoint timestamp and the per-run log key, both **injected** (a clock
  callable and an explicit key path) so tests are fully deterministic.
- **Sign/verify exactly the logged bytes.** The Merkle leaf is computed over the **canonical envelope
  bytes** (§3.1) — the same bytes a verifier reconstructs — so there is no re-serialization drift
  between submit-time and verify-time.
- **`verify_bundle` never raises on malformed input.** Mirroring `verify_envelope`: any structural
  defect, bad base64, short proof, or signature failure returns a negative structured result, not an
  exception.
- **No private keys in git.** The log key is an operator-supplied/`keygen`-generated PEM, same policy
  as the signing key; tests generate ephemeral keys in-process.

## 2. RFC-6962 Merkle mechanics (the math, pinned)

Hashing follows RFC 6962 §2.1 exactly (domain-separated, SHA-256):

```
leaf hash   MTH({d})        = SHA256(0x00 || d)
node hash   MTH(D[0:n])     = SHA256(0x01 || MTH(left) || MTH(right))
empty tree  MTH({})         = SHA256("")          # not used in v1 (we never log an empty tree)
```

where for a list of `n>1` leaves the split point `k` is **the largest power of two strictly less than
`n`** (left subtree = first `k` leaves, right = the rest). `||` is byte concatenation; `d` is the raw
leaf entry bytes (§3.1).

**Inclusion proof** for leaf index `m` in a tree of size `n` (RFC 6962 §2.1.1): the ordered list of
sibling hashes from leaf to root. **Verification** (`verify_inclusion`) recomputes the root from
`(leaf_bytes, index, tree_size, proof)` and compares to the expected root — pure, no crypto-lib
dependency (only `hashlib`). Direction at each step is determined by the index/size arithmetic, not
stored in the proof (RFC-6962 algorithm), so a forged direction cannot be smuggled in.

> These are exactly the test vectors RFC 6962 publishes (roots for the 8-leaf reference tree, and the
> inclusion proofs for each leaf). The plan pins them as conformance tests (§6).

## 3. New module `src/polymer_claims/transparency.py`

Pure-stdlib Merkle math + a log-key-signed checkpoint + the log interface and its local backend.

### 3.1 Canonical entry bytes

`canonical_entry_bytes(env: DsseEnvelope) -> bytes` — the exact bytes that become a Merkle leaf.
Defined as `json.dumps({"payloadType":…, "payload":…, "signatures":[{"sig":…,"keyid":…}, …]},
sort_keys=True, separators=(",",":")).encode("utf-8")` — a deterministic canonical JSON of the
**signed** envelope (signatures included; an envelope must be signed before it is logged). Both
submit and verify derive the leaf from this single function. (Rationale: stable, re-derivable from the
bundle's embedded envelope; independent of pydantic's field order / alias rendering.)

### 3.2 Merkle functions (pure)

| Function | Responsibility |
|---|---|
| `leaf_hash(entry: bytes) -> bytes` | `sha256(b"\x00" + entry)` |
| `node_hash(left: bytes, right: bytes) -> bytes` | `sha256(b"\x01" + left + right)` |
| `merkle_root(leaves: list[bytes]) -> bytes` | RFC-6962 root over leaf-hashes (`n>=1`) |
| `inclusion_proof(leaves: list[bytes], index: int) -> list[bytes]` | sibling hashes leaf→root |
| `verify_inclusion(leaf: bytes, index: int, tree_size: int, proof: list[bytes], root: bytes) -> bool` | recompute root, compare; **never raises** |

### 3.3 Checkpoint (signed log state)

```python
@dataclass(frozen=True)
class Checkpoint:
    origin: str          # log identifier, e.g. "polymer-claims-local-log"
    tree_size: int
    root_hash: str       # hex sha256
    timestamp: str       # RFC-3339 UTC, injected clock
    signature: str       # b64 ed25519 over canonical_checkpoint_bytes (excl. signature)
    key_hint: str        # keyid_for(log_pubkey) — informational
```

- `canonical_checkpoint_bytes(cp_without_sig) -> bytes` — deterministic JSON of the unsigned fields
  (a note-style text body would also work; canonical JSON keeps it consistent with §3.1).
- `sign_checkpoint(unsigned, log_private_key) -> Checkpoint` and
  `verify_checkpoint(cp, log_public_key) -> bool` reuse `signing.pae`-style ed25519 directly via
  `signing._require_crypto()` (the checkpoint is signed over `canonical_checkpoint_bytes`, no PAE
  wrapper needed — it is not a DSSE envelope). `verify_checkpoint` never raises.

### 3.4 `LogEntry` and the `TransparencyLog` protocol

```python
@dataclass(frozen=True)
class LogEntry:
    log_index: int
    inclusion_proof: list[str]   # hex sibling hashes
    checkpoint: Checkpoint       # signed state AFTER this entry was appended

class TransparencyLog(Protocol):
    def submit(self, entry_bytes: bytes) -> LogEntry: ...
    @property
    def public_key_pem(self) -> bytes: ...   # the key a verifier pins to check checkpoints
```

`submit` is the **only** method that differs between local and networked backends.

### 3.5 `LocalTransparencyLog`

- Constructed with `(log_dir: Path, log_private_key, *, origin="polymer-claims-local-log",
  clock: Callable[[], str])`. The clock returns an RFC-3339 UTC string; production passes a real-UTC
  lambda, tests pass a fixed stub.
- Storage: append-only `log_dir/entries.jsonl`, one canonical-entry-bytes record per line (base64),
  index = line number. The tree is the full set of leaves; `submit` appends, recomputes the root over
  all leaves, builds the inclusion proof for the new index, signs a fresh `Checkpoint`, returns
  `LogEntry`. (v1 recomputes from all leaves on each submit — simple and correct; the log is small.
  Incremental/cached tree state is a YAGNI optimization, not in scope.)
- Concurrency: single-process, single-writer assumption (documented). No file locking in v1.

## 4. New module `src/polymer_claims/bundle.py`

The Sigstore-compatible bundle and its offline verifier.

### 4.1 `SigstoreBundle` shape

A JSON object shaped after the Sigstore bundle (`dev.sigstore.bundle`) so the future Rekor backend
populates the *same* fields:

```jsonc
{
  "mediaType": "application/vnd.dev.sigstore.bundle+json;version=0.3",
  "verificationMaterial": {
    "publicKey": { "rawBytes": "<b64 DER SubjectPublicKeyInfo of the SIGNING key>",
                   "keyid": "<keyid_for(signing pub)>" },
    "tlogEntries": [ {
        "logIndex": <int>,
        "logId": "<keyid_for(log pubkey)>",
        "inclusionProof": { "logIndex": <int>, "rootHash": "<hex>", "treeSize": <int>,
                            "hashes": ["<hex>", …], "checkpoint": { …Checkpoint… } }
    } ],
    "logPublicKey": { "rawBytes": "<b64 DER of the LOG key>" }   // pinned trust root for v1's local log
  },
  "dsseEnvelope": { "payloadType": …, "payload": …, "signatures": [ {"sig":…, "keyid":…} ] }
}
```

> Forward-compat note recorded in the spec: the only field a real-Rekor bundle drops is
> `logPublicKey` (a public Rekor's key is pinned out-of-band, not embedded). v1 embeds the local log
> key because the local log *is* the trust root the operator distributes. `verify_bundle` takes the
> trust-root key as a parameter (defaulting to the embedded `logPublicKey` for the local case), so the
> networked case supplies a pinned key instead with no format change. This is captured as a golden
> shape test (§6) so the drop-in is verified now.

### 4.2 Functions

| Function | Responsibility |
|---|---|
| `build_bundle(env: DsseEnvelope, signing_public_key, log_entry: LogEntry, log_public_key) -> dict` | assemble the bundle dict above |
| `verify_bundle(bundle: dict, *, signing_public_key=None, log_trust_key=None) -> BundleVerification` | the offline 3-check verifier (§4.3); **never raises** |

`signing_public_key` defaults to the embedded `verificationMaterial.publicKey` (verify against the
key the bundle claims); callers may pass an expected key to pin it. `log_trust_key` defaults to the
embedded `logPublicKey`; the networked case passes a pinned Rekor key.

### 4.3 `BundleVerification` result

```python
@dataclass(frozen=True)
class BundleVerification:
    ok: bool
    envelope_signature_ok: bool   # DSSE sig verifies against signing key
    inclusion_ok: bool            # leaf+proof recompute to checkpoint root_hash, at logIndex/treeSize
    checkpoint_signature_ok: bool # checkpoint signed by log_trust_key
    reason: str                   # first failing check, human-readable; "" when ok
```

`ok == (envelope_signature_ok and inclusion_ok and checkpoint_signature_ok)`. Each sub-check is
independently reported so a tampered field names *which* check failed.

## 5. CLI changes (`src/polymer_claims/cli.py`)

- **`certify CLAIM --format dsse --key K [--keyid ID] --transparency-log [--log-dir DIR]
  [--log-key LK]`** — when `--transparency-log` is given (requires `--key`), after signing: open/create
  the `LocalTransparencyLog` at `--log-dir` (default `./.polymer-tlog`) with `--log-key` (default
  `DIR/log.key`, auto-`keygen`'d on first use and reported), submit the canonical envelope bytes, build
  the bundle, and emit the **bundle** JSON instead of the bare envelope. Without the flag: unchanged.
- **`export-attestation … --format dsse --key K --transparency-log [--log-dir DIR] [--log-key LK]`** —
  same, logging EACH envelope and emitting one bundle per NDJSON line.
- **`verify-bundle PATH [--pub-key SIGNING.pub] [--log-pub-key LOG.pub]`** (new subcommand) — read a
  bundle JSON *or* NDJSON of bundles; run `verify_bundle` on each (pinning the signing/log keys if
  provided, else using the embedded keys); print a one-line per-bundle verdict naming the failing
  check to stderr; return `0` iff every bundle's `ok` is true, else `1`.
- **`--rekor-url URL`** is **reserved/parsed but documented as not-yet-implemented in v1** (errors with
  a clear "networked Rekor backend is not implemented yet; see spec §7" message). It exists so the flag
  surface is stable for the network slice.

All new paths guard the `cryptography` import with the existing friendly `[sign]` message.

## 6. Testing (TDD, all offline / CI-green, no committed keys)

- **RFC-6962 conformance (pure):** `merkle_root` over the published 8-leaf reference vectors;
  `leaf_hash`/`node_hash` against hand-computed `SHA256(0x00||·)` / `SHA256(0x01||·||·)`;
  `inclusion_proof` + `verify_inclusion` round-trip for **every** leaf index in trees of size 1..9
  (covers the odd-split edge cases).
- **Inclusion adversarial:** flip one proof hash → False; wrong index → False; wrong tree_size →
  False; wrong root → False; truncated/over-long proof → False (never raises).
- **Checkpoint:** `sign_checkpoint` → `verify_checkpoint` True; one-byte tamper of any signed field →
  False; verification with a different log key → False; malformed checkpoint → False (never raises).
- **Local log:** `submit` thrice → indices 0,1,2; each returned `LogEntry` verifies
  (`verify_inclusion` against its checkpoint root) and the checkpoint verifies against the log pubkey;
  reopening the log dir and submitting again continues the indices and grows the root.
- **Determinism:** fixed log key + fixed clock stub → identical checkpoint bytes/signature across runs.
- **Bundle round-trip:** `build_bundle` → `verify_bundle` `ok=True` with all three sub-flags true;
  then mutate each of {a payload byte, a signature byte, a proof hash, the checkpoint signature, the
  embedded signing key, the embedded log key} → `ok=False` with the *correct* sub-flag false and a
  matching `reason`.
- **Bundle key-pinning:** `verify_bundle` with an explicit wrong `signing_public_key` → False; with
  the right one → True; same for `log_trust_key` (proves the networked drop-in: trust key supplied
  externally, format unchanged).
- **Forward-compat golden:** assert the built bundle JSON contains exactly the Sigstore-shaped keys
  §4.1 lists (a structural golden), so the network slice can populate the same shape without a format
  change.
- **CLI:** `certify --format dsse --key --transparency-log` emits a bundle whose `verify-bundle`
  returns 0; flipping a byte of the saved bundle → `verify-bundle` returns 1 and names the check;
  `export-attestation … --transparency-log` emits one verifiable bundle per line; `--rekor-url`
  errors with the documented not-implemented message; **backward-compat:** without
  `--transparency-log`, `certify`/`export-attestation` output is byte-identical to today.
- **Missing-dep:** the friendly `[sign]` path (forcing the guarded import to raise
  `ModuleNotFoundError(name="cryptography")`).

## 7. The network seam (the "expand later" guarantee)

`TransparencyLog.submit` is the single abstraction boundary. A later, additive slice adds
`RekorTransparencyLog(rekor_url, *, pinned_log_key)`:

- `submit(entry_bytes)` POSTs a `dsse`/`intoto`-type entry to Rekor v1 over `urllib`, parses Rekor's
  returned `logIndex`, inclusion proof, and signed entry timestamp / checkpoint into the **same**
  `LogEntry`.
- The pinned Rekor public key replaces the local log key as `log_trust_key`; `logPublicKey` is dropped
  from the bundle (pinned out-of-band).
- **`bundle.py` and `verify_bundle` do not change** — same fields, same three checks, key supplied
  externally. CLI wires `--rekor-url` to select this backend.

What this buys that local cannot: public non-repudiation (an independent, witnessed, append-only log).
Recorded so the boundary is honest and the upgrade path is concrete. **In scope for v1: only the seam
(the `TransparencyLog` protocol + `LocalTransparencyLog`), not the Rekor backend.**

## 8. Packaging

No new dependencies. Reuses the existing `[sign]` extra (`cryptography>=42`) and stdlib `hashlib` /
`urllib` (urllib only when the network backend lands). `transparency.py` and `bundle.py` are pure
package modules (Hatchling already ships `src/polymer_claims/**`).

## 9. Components & flow

```
keygen ──▶ signing key (operator identity)        keygen ──▶ log key (local-log trust root)

certify --format dsse --key K --transparency-log ─┐
                                                  │ sign_envelope (existing)
                                                  ▼
                                  canonical_entry_bytes ──▶ LocalTransparencyLog.submit
                                                  │            (append leaf, recompute root,
                                                  │             inclusion_proof, sign Checkpoint)
                                                  ▼
                                            LogEntry ──▶ build_bundle ──▶ SigstoreBundle JSON

verify-bundle bundle.json ──▶ verify_bundle:
   (1) DSSE sig vs signing key   (2) leaf+proof ⇒ checkpoint root   (3) checkpoint sig vs log key
   ──▶ rc 0 (all ok) / 1 (names failing check)
```

## 10. Invariants

Additive; no-flag output byte-identical; `signing.py`/`attestation.py`/grammar/protocol untouched;
base install crypto-free; leaf computed over the same canonical bytes submit and verify both derive;
Merkle math is RFC-6962-exact and pure-stdlib; `verify_inclusion`/`verify_checkpoint`/`verify_bundle`
never raise; clock + keys injected for determinism; no private keys committed; the bundle format and
verifier are backend-agnostic so the networked-Rekor slice is purely additive.

## 11. Deferred (documented, → later slices)

- **Networked public Rekor backend** (`RekorTransparencyLog`, `--rekor-url` wired, pinned-key trust
  root) — the *next* slice this seam enables; delivers public non-repudiation.
- **Fulcio / OIDC keyless identity binding** — identity-bound signing (no long-lived key). Needs
  interactive auth + network; opposes offline ethos for v1.
- **`cosign`/`rekor-cli` binary interop** — verifying our bundles with the upstream tools and vice
  versa.
- **Consistency proofs** (RFC-6962 §2.1.2, proving log append-only-ness between two checkpoints) and
  **witness/gossip** — strengthen a networked log; not needed for v1's single-operator local log.
- **Incremental/cached Merkle tree state**, file locking / multi-writer concurrency — perf/robustness,
  YAGNI for v1's small single-process log.
- **Multi-signer envelopes / key rotation / trust policy** — inherited from the signing spec §9.

## 12. References

- `src/polymer_claims/signing.py` — `pae`, `sign_envelope`, `verify_envelope`, `keyid_for`,
  `generate_keypair`, `_require_crypto`, PEM (de)serializers.
- `src/polymer_claims/attestation.py` — `DsseEnvelope`, `DsseSignature`, `dsse_envelope`,
  `certificate_dsse_envelope`, the media types.
- `src/polymer_claims/cli.py` — `_cmd_certify`, `_cmd_export_attestation`, `_cmd_keygen`,
  `_cmd_verify_dsse`, `_build_parser`.
- `docs/superpowers/specs/2026-06-23-dsse-signing-design.md` — the shipped local-signing predecessor
  and its §9 deferral that this spec discharges (local-first).
- RFC 6962 §2.1 (Merkle Tree Hash, inclusion proofs, test vectors).
- Sigstore bundle format `dev.sigstore.bundle` (the JSON shape §4.1 targets for forward-compat).
