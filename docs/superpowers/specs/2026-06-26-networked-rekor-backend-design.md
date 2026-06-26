# Networked Rekor Backend — Design Spec

**Status:** Design captured — **BUILD DEFERRED / TABLED** (Z. Belden, 2026-06-26). The design is
complete and build-ready; the slice is intentionally parked until there is real first-use to anchor.
Public non-repudiation only earns its cost once a claim is being shared with an external audience —
do the first-use / wedge work before this. Resume by reviewing this spec, then `writing-plans`.

**Date:** 2026-06-26
**Author:** Z. Belden (brainstormed with Claude)
**Roadmap:** H1.A1 (Arc-2 slice 3 — real signing), the networked half. Successor to the shipped local
transparency layer (`specs/2026-06-25-transparency-log-design.md`, v0.3 SHIPPED). This discharges that
spec's §7 network seam.

> **One line.** Add a networked `RekorTransparencyLog` backend behind the existing
> `TransparencyLog.submit` seam: submit a `dsse` entry to a Rekor v1 instance over `urllib`, and emit a
> `backend:"rekor"` bundle whose Rekor inclusion proof + checkpoint + Signed Entry Timestamp (SET)
> verify **fully offline** against an operator-**pinned** Rekor public key — delivering genuine public
> non-repudiation + an independent signed timestamp. Configurable target (public or self-hosted), no
> default URL, network opt-in, CI offline via recorded fixtures.

---

## 0. Locked brainstorm decisions (2026-06-26)

1. **Target & disclosure posture — configurable, no default.** `--rekor-url` is REQUIRED to opt in;
   supports both public `rekor.sigstore.dev` AND a self-hosted instance. No baked-in default, so a
   certificate is never submitted to a permanent public log by accident. Public Rekor is permanent and
   world-readable; the operator chooses public vs private consciously, per invocation.
2. **Verification fidelity — full Rekor-faithful.** `verify-bundle` verifies the real Rekor entry
   offline against a pinned Rekor key: inclusion proof against Rekor's `canonicalizedBody` leaf, the
   checkpoint note + SET against the pinned key, and that `canonicalizedBody` embeds *our* envelope.
   The only option consistent with the recomputation-trust ethos.
3. **Testing — recorded real fixtures + mocked transport.** A real Rekor response captured once and
   committed; CI verifies the full path offline against it. `submit()` POST tested against a stubbed
   transport. A separate env-gated LIVE smoke test (not in CI) actually hits a Rekor instance.
4. **API/type (recommended, not a governance call): Rekor v1 REST** (`POST /api/v1/log/entries`),
   **`dsse` entry type v0.0.1**. Rekor v2 (tile-based) deferred (§8).

### 0.1 The crypto-surface surprise (load-bearing)

**Rekor's log key is ECDSA P-256, not Ed25519.** `signing.py` is Ed25519-only (`load_public_der`
rejects non-Ed25519). Verifying Rekor's checkpoint signature and SET therefore requires **ECDSA-P256
verification** — a new capability, still via `cryptography` behind the `[sign]` extra, living in
`rekor.py`. The Ed25519 signing-key path is untouched.

## 1. Hard constraints

- **Additive / backward-compatible.** Local-log behavior, flags, and the `backend:"local"` bundle are
  100% unchanged. `transparency.py`, `signing.py`'s existing functions, `attestation.py`, grammar, and
  protocol are untouched. `bundle.py` gains a Rekor path additively.
- **Network is opt-in and isolated.** No network code runs unless `--rekor-url` is given. All HTTP
  lives in `rekor.py` behind an injected `transport`; verification is pure given response bytes + the
  pinned key. CI never touches the network (recorded fixtures + stubbed transport).
- **Base install stays crypto-free.** ECDSA verify + all crypto via the existing `[sign]` extra; a
  missing dep surfaces the friendly `pip install 'polymer-claims[sign]'` message.
- **No default trust.** No Rekor public key is shipped/auto-trusted. `TRUSTED_VALID` on a Rekor bundle
  requires the operator to pin the Rekor key (`--rekor-pub-key`) AND the signing key.
- **Verifiers never raise on malformed input** (return `INVALID`); network/HTTP failures raise a clear
  `RekorError` surfaced as rc 1 + a friendly CLI message, never a traceback.

## 2. New module `src/polymer_claims/rekor.py`

Everything Rekor-specific. Units:
- `RekorError(Exception)` — network/HTTP/parse failures.
- `RekorTransparencyLog(rekor_url, *, transport=_urllib_post)` — implements the `TransparencyLog`
  protocol. `submit(entry_bytes) -> LogEntry`. `transport(url, body_bytes) -> bytes` is injected (real
  `urllib` POST by default; a stub in tests).
- Wire helpers: `build_proposed_entry(envelope_json, signing_pub_der) -> dict`;
  `parse_log_entry(response_json) -> RekorEntry` (the single-key `{uuid: {...}}` response).
- Canonicalization/verify helpers (pure): `rekor_leaf(canonicalized_body_b64) -> bytes`;
  `verify_set(rekor_entry, rekor_pub) -> bool`; `verify_rekor_checkpoint(checkpoint_note, rekor_pub) ->
  bool`; `envelope_matches_body(env, canonicalized_body_b64) -> bool`; `_ecdsa_verify(pub, sig, msg) ->
  bool` (P-256 / SHA-256, never raises).
- `load_rekor_public_key(pem_or_der_bytes)` — ECDSA P-256 loader (separate from the Ed25519 loaders).

## 3. Submit — Rekor v1 `dsse` flow

Proposed entry POSTed to `{rekor_url}/api/v1/log/entries`:

```jsonc
{ "apiVersion": "0.0.1", "kind": "dsse",
  "spec": { "proposedContent": {
    "envelope": "<our DSSE envelope JSON, as a string>",
    "verifiers": ["<base64 DER SubjectPublicKeyInfo of our SIGNING pubkey>"] } } }
```

Rekor responds with `{ "<uuid>": { body, integratedTime, logID, logIndex,
verification:{ inclusionProof:{ checkpoint, hashes[], logIndex, rootHash, treeSize },
signedEntryTimestamp } } }`. `submit()` parses this into a `LogEntry` with the forward-compat fields
populated (`log_id=logID`, `integrated_time=<RFC3339 of integratedTime>`, `kind_version="dsse/0.0.1"`)
plus a `RekorEntry` carrying `canonicalizedBody (=body)`, the inclusion proof, checkpoint, and SET.

## 4. The Rekor-backed bundle (`bundle.py`, additive)

A Rekor bundle adds `"backend": "rekor"` and replaces the local `inclusion`/`logKey` block with a
`rekorEntry` block; `dsseEnvelope` + `signingKey` are identical to the local bundle. **No embedded
`logKey`** (Rekor's key is pinned out-of-band).

```jsonc
{ "mediaType": "application/vnd.polymer.bundle.v0.1+json",
  "backend": "rekor",
  "verificationMaterial": {
    "signingKey": { "rawBytesDER": "...", "keyHint": "..." },
    "rekorEntry": {
      "logIndex": <int>, "logId": "<hex>", "integratedTime": "<rfc3339>",
      "kindVersion": "dsse/0.0.1",
      "canonicalizedBody": "<base64 of Rekor's canonical dsse entry>",
      "inclusionProof": { "logIndex": <int>, "rootHashHex": "<hex>", "treeSize": <int>,
                          "hashesHex": ["<hex>", ...], "checkpoint": "<C2SP note>" },
      "signedEntryTimestamp": "<base64 SET>" } },
  "dsseEnvelope": { "payloadType": ..., "payload": ..., "signatures": [ ... ] } }
```

`build_rekor_bundle(env, signing_public_key, log_entry)`; the local `build_bundle` is unchanged.
`verify_bundle` becomes a dispatcher on `backend` (`"local"` → existing C2SP path; `"rekor"` → §5;
absent → treat as `"local"` for back-compat).

## 5. Verification path (five checks, offline, against the pinned Rekor key)

`verify_bundle(bundle, *, signing_trust_key=None, rekor_trust_key=None)` for `backend:"rekor"`:

1. **DSSE signature** vs the signing key (as today).
2. **Envelope binding** — decode `canonicalizedBody` (Rekor's canonical `dsse` JSON: `spec.payloadHash`,
   `spec.signatures[].signature`/`.verifier`); confirm `payloadHash == sha256(our payload bytes)`, the
   signature equals our envelope's signature, and the verifier equals our signing pubkey DER. Proves
   Rekor logged *this* artifact, not a substitute.
3. **Inclusion proof** — `leaf = sha256(0x00 ‖ base64decode(canonicalizedBody))` recomputes to
   `rootHashHex` at `logIndex`/`treeSize` via the existing `transparency.verify_inclusion`.
4. **SET (primary non-repudiation proof)** — `signedEntryTimestamp` is ECDSA-P256-SHA256 over the
   canonical JSON `{"body":…,"integratedTime":…,"logID":…,"logIndex":…}` (sorted keys, no spaces);
   verify against the pinned Rekor key.
5. **Checkpoint** — the C2SP note commits to `(treeSize, rootHash)`; verify its signature against the
   pinned Rekor key.

**Trust status** mirrors local: `TRUSTED_VALID` iff the signing key AND the Rekor key are pinned and
matched and all five checks pass; only one pinned (others valid) → `STRUCTURALLY_VALID_UNTRUSTED`; any
failed check or a mismatched pin → `INVALID`. Never raises on malformed input.

> **Implementation risk (flagged):** the C2SP checkpoint-note **signature encoding for ECDSA** (the
> 4-byte key hint + signature-bytes layout) is the fiddliest piece. Check 4 (the SET) is well-specified
> and is the load-bearing non-repudiation proof; if the note-sig encoding fights the implementation,
> the SET + inclusion-to-`rootHash` + the checkpoint *body* binding `(treeSize, rootHash)` still hold.
> The recorded fixture pins the exact bytes during implementation.

## 6. CLI (`cli.py`)

- `certify`/`export-attestation`: `--rekor-url URL` (currently reserved + erroring) goes live. With
  `--transparency-log --key K --rekor-url URL`, submit to Rekor instead of the local log and emit a
  `backend:"rekor"` bundle. Without `--rekor-url`, local-log behavior is exactly as today.
- `verify-bundle`: add `--rekor-pub-key PATH` to pin the Rekor key. For a `backend:"rekor"` bundle,
  `TRUSTED_VALID` (rc 0) requires both `--pub-key` and `--rekor-pub-key`; absent the Rekor pin →
  `STRUCTURALLY_VALID_UNTRUSTED` (rc 2). No Rekor key is shipped or defaulted.
- Network/HTTP errors → rc 1 with a clear message (`RekorError`), never a traceback.

## 7. Testing (TDD; CI fully offline + deterministic)

- **Recorded fixture:** one real Rekor response + the matching pinned Rekor pubkey, committed (public
  data). CI verifies the full five-check path offline against it.
- **Per-check tamper cases:** flip the payload, a signature byte, a proof hash, the rootHash, the SET,
  the checkpoint → each forces `INVALID` with the right reason.
- **Trust gate:** both pins → `TRUSTED_VALID`; one pin → `STRUCTURALLY_VALID_UNTRUSTED`; mismatched pin
  → `INVALID`.
- **`submit()`:** stubbed transport returns the recorded Rekor JSON → assert the parsed `LogEntry` +
  bundle; transport raising / non-200 / malformed JSON → `RekorError`.
- **ECDSA verify:** known-answer P-256 verify; tamper → False; never raises.
- **Live smoke (env-gated `POLYMER_REKOR_LIVE=1`, NOT in CI):** real POST to a Rekor instance, then
  verify the returned bundle.
- **Back-compat:** a `backend:"local"` (or backend-absent) bundle still verifies via the local path
  unchanged; no-`--rekor-url` certify/export output unchanged.

## 8. Scope / YAGNI

**In:** Rekor v1 REST + `dsse` type, `submit` over injected transport, the five-check offline verify,
ECDSA-P256 verify, the `backend:"rekor"` bundle variant, CLI wiring, recorded fixtures.
**Out (deferred):** Rekor **v2** (tlog-tiles); **consistency-proof** verification between two
checkpoints (we verify one signed root, not that later roots extend earlier ones — inclusion + SET ≠
consistency); witness/gossip cross-checks; Fulcio/OIDC keyless identity; `cosign`/`rekor-cli` interop;
auto-trusting a bundled public-Rekor key; full Sigstore-bundle wire compatibility.

## 9. Honest boundary

A public-Rekor-backed, fully-verified bundle delivers **public non-repudiation + an independent signed
timestamp + membership in a public witnessed log** — the properties the local inclusion log could not.
Still NOT delivered (deferred §8): verified **append-only-ness** (needs consistency proofs between
checkpoints) and witness/gossip corroboration. The CLI/docs must not overstate.

## 10. References

- `docs/superpowers/specs/2026-06-25-transparency-log-design.md` (v0.3 SHIPPED) — §7 seam this discharges.
- `src/polymer_claims/transparency.py` — `TransparencyLog` protocol, `LogEntry`, `verify_inclusion`, C2SP note helpers.
- `src/polymer_claims/bundle.py` — `build_bundle`, `verify_bundle`, `TrustStatus`, `BundleVerification`.
- `src/polymer_claims/signing.py` — Ed25519 sign/verify, DER (de)serializers (the Rekor path adds ECDSA-P256 verify alongside).
- Rekor v1 REST `dsse` type v0.0.1; C2SP `tlog-checkpoint` (signed note); Sigstore SET (`signedEntryTimestamp`).
