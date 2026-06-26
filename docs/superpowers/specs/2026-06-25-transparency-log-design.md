# Transparency-Log Signing + Offline-Verifiable Bundle (local-first, network-ready) — Design Spec

**Status:** SHIPPED (local-first). v0.3 — implemented on branch feat/transparency-log; networked Rekor backend deferred (§7).
**Date:** 2026-06-25
**Author:** Z. Belden (brainstormed with Claude)
**Roadmap:** H1.A1 (Arc-2 slice 3 — real signing), the still-open half. The local ed25519 DSSE
signing of `specs/2026-06-23-dsse-signing-design.md` shipped; this is its deferred §9 successor
("H1.A1b") — the **transparency-log + offline-verifiable bundle** layer, scoped local-first.

> **Revision note (v0.2).** Hardened after external review against the RFC-6962 and Sigstore/Rekor
> specs. Key corrections: this is a **Polymer bundle (Sigstore-*inspired*), not Sigstore-wire-compatible**
> (§4.4); the checkpoint uses the **C2SP signed-note format** (§3.3); `verify_bundle` reports a **trust
> status**; v1 is a **Merkle *inclusion* log** (append-only-ness needs consistency proofs, deferred)
> (§0.1, §11); and §7's seam guarantee is the **`submit` interface**, with the bundle/verifier extending
> *additively* for Rekor's richer entry fields — not "zero change" (§7).
>
> **Revision note (v0.3).** Second review pass hardened the verifier's trust model: `TRUSTED_VALID`
> now requires **both** trust roots pinned (`--pub-key` AND `--log-pub-key`) — one alone leaves the
> other key merely bundle-embedded (§4.3, §5); `verify_bundle` adds a **media-type gate** and
> **semantic authentication of inclusion metadata** (`logId == keyid_for(log key)`, accepted
> `kindVersion`, `integratedTime is None` for local) (§4.2). With `--transparency-log`, a conflicting
> custom `--keyid` is rejected up front (§5).

> **One line.** Append each signed DSSE envelope to a local **RFC-6962 Merkle inclusion log**, return a
> **C2SP-format signed checkpoint + inclusion proof**, and wrap envelope + proof + checkpoint into a
> **Polymer bundle** (Sigstore-inspired in shape, not Sigstore-wire-compatible — §4.4) that verifies
> **fully offline against pinned keys**. v1 backs the log with a local `LocalInclusionLog`; a networked
> `RekorTransparencyLog` is a later additive backend behind the same `TransparencyLog` interface. The
> `TransparencyLog.submit` *interface* is the stable seam; `bundle.py`/`verify_bundle` extend
> *additively* to carry Rekor's richer entry fields when that backend lands (§7).

---

## 0. Context & the fork already settled

`signing.py` already does local ed25519 DSSE-PAE signing: `pae`, `sign_envelope(env, priv, *, keyid)`,
`verify_envelope(env, pub) -> bool`, `generate_keypair`, `keyid_for`, the PEM (de)serializers, all
crypto behind `_require_crypto()` (the `[sign]` extra; `cryptography>=42`). The CLI already has
`keygen` and `verify-dsse` (which correctly **requires** `--pub-key`), and `--key` on
`certify`/`export-attestation`. **None of that changes.** This slice adds a layer *on top of* a signed
envelope.

**Brainstorm decisions (2026-06-25), locked:**
1. **Trust model — key-based + inclusion log + offline-verifiable bundle.** Keep the shipped operator
   ed25519 key as the signing identity. A log entry adds tamper-evidence, an inclusion proof, and a
   signed timestamp. It is **NOT** identity-bound (no Fulcio/OIDC — deferred §11).
2. **Implementation — minimal in-house.** `urllib` (network slice only) + `cryptography` + stdlib
   `hashlib` only. RFC-6962 Merkle math, the C2SP checkpoint, and verification are written here; no
   heavy deps, no `sigstore`/`cosign`/`rekor-cli` binary.
3. **Scope — local-first with an explicit network seam.** v1 ships a **local Merkle inclusion log** +
   bundle + offline verification, all behind a `TransparencyLog` protocol. A networked public-Rekor
   backend is the *next* slice this seam enables (§7); v1 writes no network code.

### 0.1 The honest boundary (state it in docs and CLI help)

A local inclusion log delivers **tamper-evidence** (any edit to a logged entry breaks the signed
Merkle root), **inclusion proofs** (cryptographic proof an envelope is a member of a tree of a given
size whose root the log operator signed), **signed timestamps** (the C2SP checkpoint is signed by the
log key), and a **fully offline-verifiable bundle**.

It does **NOT** deliver:
- **Append-only-ness.** An inclusion proof proves membership in *one* signed root; it does not prove a
  later root *extends* an earlier one. RFC-6962's append-only property requires **consistency proofs**
  between observed checkpoints (deferred, §11). v1 is therefore precisely a *Merkle inclusion log*, not
  a verified-append-only transparency log.
- **Public non-repudiation.** That requires a *public, independently-operated, witnessed* log (real
  Rekor) — a local operator could rewrite history before anyone witnessed a checkpoint.
- **Sigstore wire-compatibility.** The bundle is Sigstore-*inspired*, not byte-compatible with upstream
  Sigstore/`cosign` tooling (§4.4).

v1 ships all the local machinery + offline verification; the three properties above arrive with the
networked backend + consistency proofs + witnessing (§7, §11). The CLI and bundle must not overstate.

## 1. Hard constraints (load-bearing)

- **Additive / backward-compatible.** With no `--transparency-log` flag, `certify` /
  `export-attestation` output is **byte-identical** to today. `signing.py`, `attestation.py`'s
  `DsseEnvelope`/`DsseSignature`, grammar, and protocol are untouched.
- **Base install stays crypto-free.** All crypto stays behind the existing `[sign]` extra via the
  existing `_require_crypto()`. A missing dep surfaces the same friendly
  `pip install 'polymer-claims[sign]'` message, never a traceback.
- **Offline & deterministic in v1.** No network code path exists in v1. Merkle hashing is pure stdlib
  `hashlib`; verification is pure given the bundle bytes + pinned keys. The only non-determinism is the
  checkpoint timestamp and the per-run log key, both **injected** (a clock callable and an explicit key
  path) so tests are fully deterministic.
- **Sign/verify exactly the logged bytes.** The Merkle leaf is computed over the **canonical envelope
  bytes** (§3.1) — the same bytes a verifier reconstructs — so there is no re-serialization drift
  between submit-time and verify-time.
- **Verification is trust-gated and never raises on malformed input.** Mirroring `verify_envelope` and
  the `verify-dsse --pub-key` requirement: any structural defect, bad base64, short proof, or signature
  failure yields a negative/`INVALID` structured result (never an exception); and a bundle that is only
  internally consistent against its *own* embedded keys is reported `STRUCTURALLY_VALID_UNTRUSTED`, not
  trusted (§4.3).
- **No private keys in git.** The log key is operator-supplied/`keygen`-generated PEM, same policy as
  the signing key; tests generate ephemeral keys in-process.

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

Pure-stdlib Merkle math + a C2SP signed checkpoint + the log interface and its local backend.

### 3.1 Canonical entry bytes

`canonical_entry_bytes(env: DsseEnvelope) -> bytes` — the exact bytes that become a Merkle leaf.
Defined as `json.dumps({"payloadType":…, "payload":…, "signatures":[{"sig":…,"keyid":…}, …]},
sort_keys=True, separators=(",",":")).encode("utf-8")` — deterministic canonical JSON of the **signed**
envelope (signatures included; an envelope must be signed before it is logged). Both submit and verify
derive the leaf from this single function. (Rationale: stable, re-derivable from the bundle's embedded
envelope; independent of pydantic's field order / alias rendering.)

### 3.2 Merkle functions (pure)

| Function | Responsibility |
|---|---|
| `leaf_hash(entry: bytes) -> bytes` | `sha256(b"\x00" + entry)` |
| `node_hash(left: bytes, right: bytes) -> bytes` | `sha256(b"\x01" + left + right)` |
| `merkle_root(leaves: list[bytes]) -> bytes` | RFC-6962 root over leaf-hashes (`n>=1`) |
| `inclusion_proof(leaves: list[bytes], index: int) -> list[bytes]` | sibling hashes leaf→root |
| `verify_inclusion(leaf: bytes, index: int, tree_size: int, proof: list[bytes], root: bytes) -> bool` | recompute root, compare; **never raises** |

### 3.3 Checkpoint — C2SP signed-note format

The checkpoint is the C2SP/`transparency-dev` **signed note** that Rekor's `InclusionProof.Checkpoint`
uses, so the local checkpoint is the *same artifact shape* a networked log produces. It is a text
envelope: a body (the signed bytes) and one or more signature lines.

```
<origin>                       # e.g. "polymer-claims-local-log"
<tree_size>                    # decimal
<base64(root_hash bytes)>      # standard base64 of the 32-byte SHA-256 root
                               # (blank line terminates the note body)
— <key-name> <base64( keyhint[4] || ed25519_sig )>
```

- The **signed bytes** are the note body: the three lines + trailing newline, up to and including the
  blank line (C2SP rule). `key-name` is the origin; `keyhint` is the first 4 bytes of
  `sha256(key-name "\n" || pubkey-DER)` (C2SP Ed25519 note-key hint).
- Functions (signed via `signing._require_crypto()` ed25519 directly — a checkpoint note is **not** a
  DSSE envelope, so no PAE wrapper):
  - `format_checkpoint_body(origin, tree_size, root_hash: bytes) -> str`
  - `sign_checkpoint(origin, tree_size, root_hash, log_private_key) -> str` → full note string.
  - `verify_checkpoint(note: str, log_public_key) -> bool` → parse, verify ≥1 signature line over the
    body against the key; **never raises**.
  - `parse_checkpoint(note: str) -> CheckpointFields(origin, tree_size, root_hash: bytes)` for the
    inclusion check; raises only inside `verify_*`-guarded callers, which catch and return False.
- The injected clock (§3.5) supplies the timestamp; v1 records it as an additional note body line
  (`Timestamp: <RFC-3339>`) below the root, per C2SP's "extension lines" allowance, kept inside the
  signed body so the timestamp is signed.

### 3.4 `LogEntry` and the `TransparencyLog` protocol

```python
@dataclass(frozen=True)
class LogEntry:
    log_index: int
    inclusion_proof: list[str]   # hex sibling hashes
    checkpoint: str              # C2SP signed-note string, state AFTER this entry was appended
    # Forward-compat fields (populated by the networked backend; local backend sets defaults):
    log_id: str                  # keyid of the log key (local) / Rekor logId (networked)
    integrated_time: str | None  # None for local v1; Rekor integratedTime when networked
    kind_version: str            # "polymer-inclusion/0.1" (local) / "dsse/0.0.1" etc. (Rekor)

class TransparencyLog(Protocol):
    def submit(self, entry_bytes: bytes) -> LogEntry: ...
    @property
    def public_key_pem(self) -> bytes: ...   # the key a verifier pins to check checkpoints
```

`submit` is the **only** method that differs between local and networked backends. The forward-compat
fields are present from v1 (local defaults) so the bundle shape does not change when Rekor populates
them; the heavier Rekor-only field `canonicalized_body` is named as an extension point in §7, not
modeled in v1.

### 3.5 `LocalInclusionLog`

- Constructed with `(log_dir: Path, log_private_key, *, origin="polymer-claims-local-log",
  clock: Callable[[], str])`. The clock returns an RFC-3339 UTC string; production passes a real-UTC
  lambda, tests pass a fixed stub.
- Storage: append-only `log_dir/entries.jsonl`, one canonical-entry-bytes record per line (base64),
  index = line number. The tree is the full set of leaves; `submit` appends, recomputes the root over
  all leaves, builds the inclusion proof for the new index, signs a fresh checkpoint note, returns
  `LogEntry` (`log_id=keyid_for(log pub)`, `integrated_time=None`, `kind_version="polymer-inclusion/0.1"`).
  (v1 recomputes from all leaves on each submit — simple and correct; the log is small. Incremental
  tree state is a YAGNI optimization, not in scope.)
- Concurrency: single-process, single-writer assumption (documented). No file locking in v1.
- **Not** a verified-append-only log: it emits no consistency proofs (§11). The name says *inclusion*.

## 4. New module `src/polymer_claims/bundle.py`

The Polymer bundle and its trust-gated offline verifier.

### 4.1 `PolymerBundle` shape (Sigstore-inspired)

```jsonc
{
  "mediaType": "application/vnd.polymer.bundle.v0.1+json",   // Polymer type — NOT a Sigstore type (§4.4)
  "$schemaNote": "Sigstore-inspired layout; not wire-compatible with dev.sigstore.bundle. See spec §4.4.",
  "verificationMaterial": {
    "signingKey": { "rawBytesDER": "<b64 DER SubjectPublicKeyInfo of the SIGNING key>",
                    "keyHint": "<keyid_for(signing pub) — equals the DSSE signature keyid (§4.2)>" },
    "logKey":     { "rawBytesDER": "<b64 DER of the LOG key>",
                    "keyHint": "<keyid_for(log pub)>" },          // local log's pinned trust root
    "inclusion": {
        "logIndex": <int>,
        "logId": "<keyHint of the log key>",
        "kindVersion": "polymer-inclusion/0.1",
        "integratedTime": null,                                  // populated by the networked backend
        "treeSize": <int>,
        "rootHashHex": "<hex>",
        "hashesHex": ["<hex>", …],
        "checkpoint": "<C2SP signed-note string (§3.3)>"
    }
  },
  "dsseEnvelope": { "payloadType": …, "payload": …, "signatures": [ {"sig":…, "keyid":…} ] }
}
```

> The shape is deliberately Sigstore-*adjacent* (a `verificationMaterial` block, an inclusion entry
> with `logIndex`/`logId`/`kindVersion`/`integratedTime`, a checkpoint note, a `dsseEnvelope`) so the
> mental model and the future migration are clean. It is **not** the `dev.sigstore.bundle` protobuf
> JSON (§4.4). The local bundle embeds `logKey` because the local log *is* the trust root the operator
> distributes; a networked bundle drops it (Rekor's key is pinned out-of-band) — `verify_bundle` takes
> the log trust key as a parameter, so that drop is not a verifier change.

### 4.2 Functions

| Function | Responsibility |
|---|---|
| `build_bundle(env, signing_public_key, log_entry: LogEntry, log_public_key) -> dict` | assemble §4.1. **Enforces (§ finding-6):** the envelope must carry exactly one signature whose `keyid == keyid_for(signing_public_key)`; otherwise raise `ValueError` (refuse to build a bundle whose DSSE key hint disagrees with its verification material). Sets `signingKey.keyHint` to that matching keyid. |
| `verify_bundle(bundle, *, signing_trust_key=None, log_trust_key=None) -> BundleVerification` | the trust-gated offline verifier (§4.3); **never raises** |

`verify_bundle` performs, in order: (0) **media-type gate** — reject unless `bundle["mediaType"] ==
MEDIA_TYPE` (do not validate a structurally-similar object carrying another format label); (1) DSSE
signature over the envelope; (2) **inclusion-metadata authentication** — `inclusion.logId ==
keyid_for(log key)`, `kindVersion` is an accepted local value (`polymer-inclusion/0.1`), and
`integratedTime is None` for a local bundle (these fields are unsigned, so the verifier authenticates
them semantically rather than trusting them blindly); (3) inclusion proof recomputes to the checkpoint
root at `logIndex`/`treeSize`; (4) checkpoint signature vs the log key.

`signing_trust_key` / `log_trust_key` are the **pinned** trust roots. When omitted, verification still
runs against the bundle's *embedded* keys but the result is capped at `STRUCTURALLY_VALID_UNTRUSTED`
(§4.3) — internal consistency is proven, trust is not.

### 4.3 `BundleVerification` result — trust status, not a bare bool

```python
class TrustStatus(str, Enum):
    TRUSTED_VALID = "trusted_valid"                          # all checks pass AND BOTH trust roots pinned + matched
    STRUCTURALLY_VALID_UNTRUSTED = "structurally_valid_untrusted"  # all checks pass vs embedded keys, not both pinned
    INVALID = "invalid"                                      # a check failed

@dataclass(frozen=True)
class BundleVerification:
    status: TrustStatus
    envelope_signature_ok: bool   # DSSE sig verifies against the signing key used
    inclusion_ok: bool            # leaf+proof recompute to the checkpoint root at logIndex/treeSize
    checkpoint_signature_ok: bool # checkpoint note signed by the log key used
    signing_key_pinned: bool      # a signing_trust_key was supplied AND matched the embedded/used key
    log_key_pinned: bool          # a log_trust_key was supplied AND matched the embedded/used key
    reason: str                   # first failing/limiting condition, human-readable; "" when TRUSTED_VALID
```

Rules: if the media-type gate, any `*_ok`, or the inclusion-metadata check fails → `INVALID`. Else if
**both** `signing_key_pinned` AND `log_key_pinned` are true → `TRUSTED_VALID`. Else →
`STRUCTURALLY_VALID_UNTRUSTED`. **Both** trust roots are required for trust: one pin alone leaves the
*other* key merely bundle-embedded, so the bundle is not fully trustworthy (only `STRUCTURALLY_VALID_
UNTRUSTED`). A supplied trust key that does **not** match the bundle's key → `INVALID` (key mismatch),
never silently downgraded. Each sub-check is independently reported so a tampered field names *which*
check failed.

### 4.4 Relationship to Sigstore (honesty section)

This bundle is **inspired by** the Sigstore bundle / Rekor `TransparencyLogEntry` mental model but is
**not** wire-compatible, and the spec does not claim it is:

- The media type is a **Polymer** type (`application/vnd.polymer.bundle.v0.1+json`), not
  `application/vnd.dev.sigstore.bundle.v0.3+json`.
- Sigstore's `verificationMaterial.publicKey` is a `PublicKeyIdentifier` *hint*; raw key material uses a
  different proto shape with `keyDetails`. We carry raw DER under a Polymer field name on purpose.
- A real Rekor `TransparencyLogEntry` additionally carries `kindVersion`, `integratedTime`, `logId` as
  key-id bytes, and a `canonicalizedBody`. v1 adopts the cheap, stable subset
  (`kindVersion`/`integratedTime`/`logId`/checkpoint-note) and names `canonicalizedBody` as an
  extension point (§7). The C2SP checkpoint note (§3.3) *is* the Rekor checkpoint shape.

Upstream `cosign`/`sigstore` interop is explicitly deferred (§11). Calling this "Sigstore-compatible"
would be false; we call it "Sigstore-inspired."

## 5. CLI changes (`src/polymer_claims/cli.py`)

- **`certify CLAIM --format dsse --key K [--keyid ID] --transparency-log [--log-dir DIR]
  [--log-key LK]`** — when `--transparency-log` is given (requires `--key`), after signing: open/create
  the `LocalInclusionLog` at `--log-dir` (default `./.polymer-tlog`) with `--log-key` (default
  `DIR/log.key`, auto-`keygen`'d on first use and its path + pubkey keyHint reported to stderr), submit
  the canonical envelope bytes, build the bundle, and emit the **bundle** JSON instead of the bare
  envelope. Without the flag: unchanged.
- **`export-attestation … --format dsse --key K --transparency-log [--log-dir DIR] [--log-key LK]`** —
  same, logging EACH envelope and emitting one bundle per NDJSON line.
- **`verify-bundle PATH [--pub-key SIGNING.pub] [--log-pub-key LOG.pub]`** (new subcommand) — read a
  bundle JSON *or* NDJSON of bundles; run `verify_bundle` pinning whichever keys are supplied. **Exit
  codes:** `0` iff every bundle is `TRUSTED_VALID`; `1` if any is `INVALID`; `2` if none INVALID but any
  is `STRUCTURALLY_VALID_UNTRUSTED` (not both keys pinned — structurally fine but **not** trusted;
  INVALID dominates). Print a one-line per-bundle verdict naming the status and any failing check to
  stderr. This mirrors `verify-dsse`'s "you must supply the key you trust" stance: **rc 0 requires BOTH
  `--pub-key` AND `--log-pub-key` pinned** (the signer identity *and* the log trust root).
- **`--rekor-url URL`** is **reserved/parsed but documented as not-implemented in v1** (errors with a
  clear "networked Rekor backend is not implemented yet; see spec §7" message). It exists so the flag
  surface is stable for the network slice.

All new paths guard the `cryptography` import with the existing friendly `[sign]` message.

## 6. Testing (TDD, all offline / CI-green, no committed keys)

- **RFC-6962 conformance (pure):** `merkle_root` over the published 8-leaf reference vectors;
  `leaf_hash`/`node_hash` against hand-computed `SHA256(0x00||·)` / `SHA256(0x01||·||·)`;
  `inclusion_proof` + `verify_inclusion` round-trip for **every** leaf index in trees of size 1..9
  (covers the odd-split edge cases).
- **Inclusion adversarial:** flip one proof hash → False; wrong index → False; wrong tree_size → False;
  wrong root → False; truncated/over-long proof → False (never raises).
- **C2SP checkpoint:** `sign_checkpoint` → `verify_checkpoint` True; the signed body matches the C2SP
  layout (origin/size/b64-root/timestamp lines + blank line); one-byte tamper of any body line → False;
  a corrupted signature line → False; verification with a different log key → False; malformed note →
  False (never raises). `parse_checkpoint` recovers `(origin, tree_size, root_hash)`.
- **Local log:** `submit` thrice → indices 0,1,2; each `LogEntry` verifies (`verify_inclusion` against
  its checkpoint's parsed root) and the checkpoint verifies against the log pubkey; reopening the log
  dir and submitting again continues the indices and grows the root; `log_id`/`kind_version` set,
  `integrated_time is None`.
- **Determinism:** fixed log key + fixed clock stub → identical checkpoint note/signature across runs.
- **`build_bundle` keyid enforcement (finding 6):** an envelope whose signature `keyid` ≠
  `keyid_for(signing pub)` → `build_bundle` raises `ValueError`; a matching one → `signingKey.keyHint`
  equals that keyid.
- **Bundle round-trip + trust status (finding 2):**
  - `build_bundle` → `verify_bundle(signing_trust_key=sig_pub, log_trust_key=log_pub)` →
    `TRUSTED_VALID`, all sub-flags true, both `*_pinned` true.
  - `verify_bundle` with **no** pins → `STRUCTURALLY_VALID_UNTRUSTED` (not trusted), all `*_ok` true.
  - a supplied trust key that does **not** match → `INVALID` (key mismatch), not a silent downgrade.
  - mutate each of {a payload byte, a signature byte, a proof hash, a checkpoint body byte, the
    checkpoint signature, the embedded signing key, the embedded log key} → `INVALID` with the correct
    sub-flag false and a matching `reason`.
- **CLI:** `certify --format dsse --key --transparency-log` emits a bundle; `verify-bundle --pub-key
  --log-pub-key` returns `0`; `verify-bundle` with **no** key returns `2` (untrusted); flipping a byte
  of the saved bundle → `verify-bundle` returns `1` and names the check; `export-attestation …
  --transparency-log` emits one verifiable bundle per line; `--rekor-url` errors with the documented
  not-implemented message; **backward-compat:** without `--transparency-log`, `certify`/
  `export-attestation` output is byte-identical to today.
- **Bundle shape golden:** assert the built bundle JSON contains exactly the Polymer-shaped keys §4.1
  lists (structural golden) — so the network slice can populate the same shape and the §4.4 honesty
  boundary is enforced (asserts the media type is the Polymer type, **not** a Sigstore one).
- **Missing-dep:** the friendly `[sign]` path (forcing the guarded import to raise
  `ModuleNotFoundError(name="cryptography")`).

## 7. The network seam (the "expand later" guarantee — scoped honestly)

`TransparencyLog.submit` is the single **interface** boundary, and it is the stable seam. A later,
additive slice adds `RekorTransparencyLog(rekor_url, *, pinned_log_key)`:

- `submit(entry_bytes)` POSTs a `dsse`/`intoto`-type entry to Rekor v1 over `urllib`, and parses
  Rekor's `logIndex`, inclusion proof, `integratedTime`, `logId`, `kindVersion`, the C2SP checkpoint,
  and `canonicalizedBody` into a `LogEntry`. The forward-compat fields (§3.4) are already in `LogEntry`;
  `canonicalizedBody` is added then as a new optional field (additive).
- The pinned Rekor public key replaces the local log key as `log_trust_key`; `logKey` is dropped from
  the bundle (pinned out-of-band).

**What is guaranteed vs. not:** the `submit` interface and the three verification checks (DSSE sig /
inclusion / checkpoint-sig) are stable; `verify_bundle`'s *logic* does not change. The bundle JSON and
`verify_bundle` will gain *additive* fields (`canonicalizedBody`, populated `integratedTime`) — this is
deliberately **not** claimed as "zero change to bundle.py," only "no change to the verification model
and no breaking change to the format." What the networked slice buys that local cannot: append-only
verification (consistency proofs), witnessing, and public non-repudiation.

**In scope for v1: only the seam** (the `TransparencyLog` protocol + `LocalInclusionLog` + the
forward-compat `LogEntry` fields), **not** the Rekor backend.

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
                                  canonical_entry_bytes ──▶ LocalInclusionLog.submit
                                                  │            (append leaf, recompute root,
                                                  │             inclusion_proof, sign C2SP checkpoint)
                                                  ▼
                                            LogEntry ──▶ build_bundle (keyid-enforced) ──▶ PolymerBundle JSON

verify-bundle bundle.json --pub-key S.pub --log-pub-key L.pub ──▶ verify_bundle:
   (1) DSSE sig vs signing key   (2) leaf+proof ⇒ checkpoint root   (3) checkpoint sig vs log key
   + trust gate (pinned key matched?) ──▶ rc 0 TRUSTED_VALID / 2 UNTRUSTED / 1 INVALID
```

## 10. Invariants

Additive; no-flag output byte-identical; `signing.py`/`attestation.py`/grammar/protocol untouched; base
install crypto-free; leaf computed over the same canonical bytes submit and verify both derive; Merkle
math is RFC-6962-exact and pure-stdlib; checkpoint is a C2SP signed note; verification never raises and
is **trust-gated** (rc 0 needs a pinned root); `build_bundle` enforces DSSE-keyid ↔ verification-material
agreement; clock + keys injected for determinism; no private keys committed; the `submit` interface and
three-check model are the stable seam, with the bundle extending additively for the networked backend.

## 11. Deferred (documented, → later slices)

- **Consistency proofs** (RFC-6962 §2.1.2) + **witnessed/gossiped checkpoints** — what turns the v1
  *inclusion* log into a verified *append-only* transparency log. Required before any "append-only"
  claim.
- **Networked public Rekor backend** (`RekorTransparencyLog`, `--rekor-url` wired, pinned-key trust
  root, `canonicalizedBody`) — the *next* slice this seam enables; delivers public non-repudiation.
- **Sigstore wire-compatibility & `cosign`/`rekor-cli` interop** — emitting/consuming the real
  `dev.sigstore.bundle` protobuf JSON (correct media type, `PublicKey` proto with `keyDetails`, full
  `TransparencyLogEntry`) and round-tripping with upstream tools.
- **Fulcio / OIDC keyless identity binding** — identity-bound signing (no long-lived key). Needs
  interactive auth + network; opposes offline ethos for v1.
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
- RFC 6962 §2.1 (Merkle Tree Hash, inclusion + consistency proofs, test vectors).
- C2SP / `transparency-dev` checkpoint (signed-note) format — the checkpoint shape §3.3 adopts.
- Sigstore bundle (`dev.sigstore.bundle` v0.3) and Rekor `TransparencyLogEntry` / `InclusionProof` —
  the mental model §4.1 is *inspired by* and the §4.4 honesty boundary measures against.
