# Attestation DSSE + Verifier Export — Design

**Date:** 2026-06-21 · **Status:** Design (approved in brainstorm; pre-plan)
**Builds on:** `docs/superpowers/specs/2026-06-21-standards-skin-attestation-design.md` (slice 1, merged —
the `AttestationBundle` of in-toto Statement v1 / SLSA Provenance v1 per LICENSED claim + DRS objects).
This is **North-Star arc 2, slice 2**: make those Statements verifier-ingestible and signing-ready.

> **One line.** Emit each LICENSED claim's existing in-toto Statement as a **DSSE envelope**
> (`signatures: []` — unsigned but structurally complete) in **NDJSON**, so a standard in-toto/SLSA
> verifier can ingest the bare Statement and a future slice can sign the envelope. Dependency-free,
> deterministic, additive — the default `bundle` output is byte-for-byte unchanged.

---

## 1. Goal & non-goals

**Goal.** Bridge the Polymer-specific `AttestationBundle` to the standard trust fabric: per-claim DSSE
envelopes wrapping the **unchanged** in-toto Statements, in a one-per-line NDJSON stream a verifier or
(later) a signer consumes. This is the dependency-free prerequisite to real signing.

**Non-goals (this slice).**
- **No signing.** No cryptographic signatures, keys, Sigstore/cosign, Rekor, or `[sigstore]` extra.
  `signatures` is always `[]`. Actual signing + transparency log is slice 3.
- **No new dependencies / no network / no clock.** Stdlib `base64` + `json` only; deterministic.
- **No change to the Statement content** or the SLSA predicate — slice 1's Statement is wrapped verbatim.
- **No other seams** (WES/TRS/RO-Crate, FAIR Signposting, Refget) — separate later slices.

## 2. Constraints / invariants

- **Additive / byte-identical default:** `export-attestation` without `--format` (or `--format bundle`)
  produces exactly today's `AttestationBundle` JSON. The DTO refactor (§4) changes nothing observable.
- **Determinism:** the DSSE `payload` is base64 of the Statement's stable serialization; envelope order
  in the NDJSON matches the bundle's existing claim order. Same corpus → byte-identical output.
- **Purity:** the builder is pure/umbrella-side (`attestation.py`), stdlib-only, no IO beyond the
  existing `resolve_contract_index`. `grammar/`/`protocol/` untouched.
- **Frozen models:** new DTO subclasses `_Model` (frozen, `extra="forbid"`); tuple fields.

## 3. DSSE envelope shape

[DSSE](https://github.com/secure-systems-lab/dsse) is the standard signing envelope in-toto/SLSA use:

```json
{
  "payloadType": "application/vnd.in-toto+json",
  "payload": "<base64( Statement JSON bytes )>",
  "signatures": []
}
```

- `payloadType` = the in-toto media type `application/vnd.in-toto+json` (constant).
- `payload` = **standard base64** (with padding) of the bytes a consumer parses as the bare in-toto
  Statement. Those bytes are `statement.model_dump_json(by_alias=True, exclude_none=True)` (the exact
  serialization slice 1 already uses for Statements inside the bundle) — deterministic for a frozen
  model. `base64-decode(payload)` round-trips to that Statement verbatim.
- `signatures` = **always `[]`** this slice — the explicit "signing-ready, not yet signed" marker. A
  DSSE *signature* verifier will (correctly) treat it as unsigned; the **bare Statement** obtained by
  decoding `payload` is what a standard in-toto/SLSA *statement* consumer ingests now. Slice 3 populates
  `signatures` (and adds the DSSE PAE + keys/Rekor) without changing this shape.

## 4. Architecture (reuse, don't duplicate)

Refactor `src/polymer_claims/attestation.py` so the per-claim Statement list is reusable, then add the
DSSE wrapper:

- **Extract** `build_attestation_statements(corpus, *, contract_index, registry=None) -> tuple[Statement, ...]`
  — the Statement-building logic currently inside `build_attestation_bundle`. `build_attestation_bundle`
  now calls it and wraps the result into the `AttestationBundle` (+ DRS objects) exactly as before —
  **byte-identical** output (verified by a golden test, §6).
- **Add DTO** `DsseEnvelope(_Model)`: `payload_type: str` (alias `payloadType`, default the in-toto
  media type), `payload: str`, `signatures: tuple[DsseSignature, ...] = ()`. (Define a minimal
  `DsseSignature(_Model)` with `keyid: str` + `sig: str` for forward-compat, even though no signatures
  are produced this slice — keeps the shape stable for slice 3.)
- **Add** `dsse_envelope(statement) -> DsseEnvelope` — pure: `base64.b64encode(statement.model_dump_json(by_alias=True, exclude_none=True).encode())`,
  wrapped with the constant `payloadType` and empty `signatures`.
- Export `build_attestation_statements`, `dsse_envelope`, `DsseEnvelope` (and `DsseSignature`) from
  `polymer_claims/__init__.py` alongside the existing attestation names.

## 5. CLI

Extend `export-attestation` in `src/polymer_claims/cli.py`:

- Add `--format {bundle,dsse}` (default `bundle`).
- `bundle` → unchanged: `build_attestation_bundle(...).model_dump_json(by_alias=True, exclude_none=True)`.
- `dsse` → build statements via `build_attestation_statements(corpus, contract_index=resolve_contract_index(corpus))`,
  map `dsse_envelope` over them, and emit **NDJSON**: each envelope
  `.model_dump_json(by_alias=True, exclude_none=True)` joined by `\n` (one DSSE envelope per LICENSED
  claim, in the same deterministic order the bundle uses). Written via the existing `_write_or_print`.
- `--out` behaves as today (write to file or stdout).

## 6. Testing

- **Refactor safety (golden):** `build_attestation_bundle` output on a fixture corpus is **byte-identical**
  before/after the `build_attestation_statements` extraction (reuse / extend slice 1's bundle golden).
- **DSSE shape:** for a LICENSED-claim corpus, `dsse_envelope(stmt)` has `payloadType ==
  "application/vnd.in-toto+json"`, `signatures == ()`, and `json.loads(base64.b64decode(payload))`
  equals `json.loads(stmt.model_dump_json(by_alias=True, exclude_none=True))` (round-trip to the exact
  Statement).
- **CLI `--format dsse`:** NDJSON line count == number of LICENSED claims; each line parses as a DSSE
  envelope; order matches the bundle's `subject`/claim order; `--format bundle` (and no `--format`)
  is byte-identical to current output.
- **Determinism:** same corpus → identical NDJSON across runs.
- **No-deps guard:** `attestation.py` imports only stdlib + existing internal modules (no new
  third-party import); base import stays as today.

## 7. Out of scope (YAGNI — later slices)

- **Slice 3 — real signing:** DSSE PAE, key management, Sigstore/cosign, Rekor transparency log, a
  `[sigstore]` extra, populating `signatures`. ("Trust lives in the Merkle log, not us.")
- A bare-`statements` NDJSON format (without the DSSE wrapper) — the DSSE `payload` already carries the
  bare Statement; add a `statements` format only if a consumer needs it.
- One-file-per-claim directory output — NDJSON is the single-artifact default; revisit if a verifier
  workflow needs discrete files.
- WES / TRS / RO-Crate / FAIR Signposting / Refget SeqCol.

## 8. Sequencing

Single cohesive slice: (1) extract `build_attestation_statements` (golden-guarded) → (2) `DsseEnvelope`/
`DsseSignature` DTOs + `dsse_envelope` → (3) `--format dsse` NDJSON CLI + tests → (4) docs. Ordinary
TDD; no frontend.
