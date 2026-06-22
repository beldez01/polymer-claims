# Attestation DSSE (Unsigned, Signing-Ready) Export — Design

**Date:** 2026-06-21 · **Status:** Design (approved in brainstorm; revised after spec audit; pre-plan)
**Builds on:** `docs/superpowers/specs/2026-06-21-standards-skin-attestation-design.md` (slice 1, merged —
the `AttestationBundle` of in-toto Statement v1 / SLSA Provenance v1 per LICENSED claim + DRS objects).
This is **North-Star arc 2, slice 2**: re-emit those Statements as DSSE-shaped, signing-ready envelopes.

> **One line.** Wrap each LICENSED claim's existing in-toto Statement in a **DSSE-shaped envelope with
> empty signatures** and emit them as **NDJSON** (`export-attestation --format dsse`). The envelopes are
> **signing-ready, not yet trust-valid**: a consumer can base64-decode `payload` and inspect the bare
> in-toto Statement now, but DSSE *signature verification is expected to fail until slice 3 signs them*.
> Dependency-free, deterministic, additive — the default `bundle` output is byte-for-byte unchanged.

---

## 1. Goal & non-goals

**Goal.** Produce a **DSSE-shaped unsigned envelope** (the standard `payloadType`/`payload`/`signatures`
field layout) wrapping slice 1's **unchanged** Statements, in a one-per-line NDJSON stream. This is the
dependency-free plumbing that makes the Statements (a) decodable/inspectable as bare in-toto Statements
and (b) ready for slice 3 to sign — *without* claiming any cryptographic trust this slice.

**Honest scope of the artifact (per the [DSSE spec](https://github.com/secure-systems-lab/dsse/blob/master/envelope.md)):**
DSSE defines the envelope *around signatures* (the formal protobuf requires `signatures` length ≥ 1).
An envelope with `signatures: []` is **structurally useful** — it carries the exact
`payloadType`/`payload` pair that slice 3 will sign via the DSSE **PAE** (Pre-Authentication Encoding;
DSSE signs the PAE over those two fields, **not** the serialized JSON envelope) — but it is **not a
trust-valid attestation**: a DSSE signature verifier treats it as unsigned, and a strict signed-DSSE
loader may reject empty `signatures` at schema level. What a consumer can do today: base64-decode
`payload` to recover the bare in-toto Statement and inspect it. This artifact targets inspection +
slice-3 signing, not ingestion by a strict signed-DSSE verifier.

**Non-goals (this slice).**
- **No signing / no trust claim.** No signatures, keys, DSSE PAE, Sigstore/cosign, Rekor, or `[sigstore]`
  extra. `signatures` is always empty. Real signing + transparency log is slice 3.
- **No new third-party dependency** beyond the project's existing `pydantic`/stdlib usage; no network, no
  clock; deterministic.
- **No change to Statement content** or the SLSA predicate — slice 1's Statement is wrapped verbatim.
- **No other seams** (WES/TRS/RO-Crate, FAIR Signposting, Refget) — separate later slices.

## 2. Constraints / invariants

- **Additive / byte-identical default:** `export-attestation` without `--format` (or `--format bundle`)
  produces exactly today's `AttestationBundle` JSON. The records refactor (§4) changes nothing observable.
- **Determinism:** the DSSE `payload` is base64 of a standalone Statement serialization; envelope order in
  the NDJSON matches the bundle's existing claim/`subject` order. Same corpus → byte-identical output.
- **Purity:** the builders are pure/umbrella-side (`attestation.py`), stdlib + existing `pydantic` only,
  no IO beyond the existing `resolve_contract_index`. `grammar/`/`protocol/` untouched.
- **Frozen models:** new DTOs subclass `_Model` (frozen, `extra="forbid"`); tuple fields.

## 3. DSSE envelope shape

```json
{
  "payloadType": "application/vnd.in-toto+json",
  "payload": "<base64( standalone Statement JSON )>",
  "signatures": []
}
```

- `payloadType` = the in-toto media type `application/vnd.in-toto+json` (constant).
- `payload` = **standard base64 (padded)** of the bytes
  `statement.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")` — a **standalone**
  serialization of that one Statement (the same per-Statement serialization the model produces;
  *not* claimed to be a byte-substring of the bundle's serialization). It is deterministic for a frozen
  model, and `json.loads(base64-decode(payload))` round-trips to the same Statement object (asserted by
  test, §6).
- `signatures` = **always empty** this slice. This is the explicit "signing-ready, not yet signed"
  state, per §1: structurally useful, not trust-valid. Slice 3 populates it (and adds the DSSE PAE +
  keys/Rekor) without changing this envelope shape.

## 4. Architecture (records-based extraction — preserves bundle behavior)

The current internal `_statement(claim, …)` returns a **triple** `(Statement, drs_objects, unresolved)`,
and `build_attestation_bundle` needs all three to assemble the bundle (Statements + deduped DRS objects +
the unresolved-dataset accounting). So the public extraction must be at the **record** level, not
statements-only:

- **Add** `build_attestation_records(corpus, *, contract_index, registry=None) -> tuple[AttestationRecord, ...]`
  — loops the LICENSED claims (same selection/order as today) and returns one record per claim. Define a
  frozen `AttestationRecord(_Model)` with `statement: Statement`, `drs_objects: tuple[DrsObject, ...]`,
  `unresolved: tuple[str, ...]` (or reuse the existing triple internally and wrap at the boundary —
  implementer's call, but the public return must carry all three).
- **`build_attestation_bundle`** is refactored to consume `build_attestation_records(...)` and assemble
  the `AttestationBundle` (dedupe/sort DRS objects + unresolved exactly as today). **Byte-identical**
  output, proven by a golden test (§6).
- **Add** `build_attestation_statements(corpus, *, contract_index, registry=None) -> tuple[Statement, ...]`
  as a thin **projection**: `tuple(r.statement for r in build_attestation_records(...))`.
- **Add DTOs:** `DsseSignature(_Model)` with `sig: str` (required) and `keyid: str | None = None`
  (DSSE treats `keyid` as **optional** — must not be required, for forward-compat with slice-3 / external
  signatures that omit it); `DsseEnvelope(_Model)` with `payload_type: str` (alias `payloadType`, default
  the in-toto media type), `payload: str`, `signatures: tuple[DsseSignature, ...] = ()`.
- **Add** `dsse_envelope(statement) -> DsseEnvelope` — pure:
  `base64.b64encode(statement.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")).decode("ascii")`,
  with the constant `payloadType` and empty `signatures`.
- Export `build_attestation_records`, `build_attestation_statements`, `dsse_envelope`, `DsseEnvelope`,
  `DsseSignature` (and `AttestationRecord`) from `polymer_claims/__init__.py` alongside the existing names.

## 5. CLI

Extend `export-attestation` in `src/polymer_claims/cli.py`:

- Add `--format {bundle,dsse}` (default `bundle`).
- `bundle` → unchanged: `build_attestation_bundle(...).model_dump_json(by_alias=True, exclude_none=True)`.
- `dsse` → `build_attestation_statements(corpus, contract_index=resolve_contract_index(corpus))`, map
  `dsse_envelope` over them, and build **NDJSON**:
  `output = "".join(env.model_dump_json(by_alias=True, exclude_none=True) + "\n" for env in envelopes)`
  — one DSSE envelope per LICENSED claim, each line newline-terminated (including the last), in the same
  deterministic order the bundle uses.
- **Write `output` byte-identically to stdout and `--out`** — the `dsse` path writes the exact string
  (`sys.stdout.write(output)` / `Path.write_text(output)`), **not** via `print()` (which appends an extra
  newline and would make stdout differ from the file). This makes determinism mode-independent.
- **Zero LICENSED claims → `output == ""`:** emit nothing — no blank line to stdout, an empty `--out`
  file. (Do not `print("")`.)

## 6. Testing

- **Refactor safety (golden):** `build_attestation_bundle` output on a fixture corpus is **byte-identical**
  before/after the records refactor (reuse / extend slice 1's bundle golden). Confirms DRS objects +
  unresolved accounting survive the extraction.
- **DSSE shape + round-trip:** for a LICENSED-claim corpus, `dsse_envelope(stmt)` has
  `payloadType == "application/vnd.in-toto+json"`, `signatures == ()`, and
  `json.loads(base64.b64decode(payload))` **equals** `json.loads(stmt.model_dump_json(by_alias=True, exclude_none=True))`
  (round-trips to the same Statement object — not asserting any byte-relationship to the bundle).
- **Projection parity:** `build_attestation_statements(...)` equals
  `tuple(r.statement for r in build_attestation_records(...))` and matches the Statements the bundle uses.
- **CLI `--format dsse`:** NDJSON line count == number of LICENSED claims; each line parses as a DSSE
  envelope; order matches the bundle's `subject`/claim order; `--format bundle` (and no `--format`) is
  byte-identical to current output.
- **Determinism:** same corpus → identical NDJSON across runs, and `--format dsse` to stdout vs `--out`
  are **byte-identical** (no `print()`-added trailing-newline divergence).
- **Empty case:** a corpus with zero LICENSED claims → `--format dsse` emits **nothing** (no blank line
  to stdout; an empty `--out` file).
- **Dependency guard:** `attestation.py` introduces **no new third-party import** beyond the existing
  `pydantic` + stdlib (the new code uses stdlib `base64`/`json` only).

## 7. Out of scope (YAGNI — later slices)

- **Slice 3 — real signing / trust:** DSSE PAE, key management, Sigstore/cosign, Rekor transparency log,
  a `[sigstore]` extra, populating `signatures`. ("Trust lives in the Merkle log, not us.")
- A bare-`statements` NDJSON format (without the DSSE wrapper) — the DSSE `payload` already carries the
  bare Statement; add only if a consumer needs it.
- One-file-per-claim directory output — NDJSON is the single-artifact default; revisit if a verifier
  workflow needs discrete files.
- WES / TRS / RO-Crate / FAIR Signposting / Refget SeqCol.

## 8. Sequencing

Single cohesive slice: (1) records refactor — `build_attestation_records` + `AttestationRecord`,
`build_attestation_bundle` consumes it (golden-guarded byte-identical) → (2) `build_attestation_statements`
projection → (3) `DsseEnvelope`/`DsseSignature` DTOs + `dsse_envelope` → (4) `--format dsse` NDJSON CLI +
tests → (5) docs. Ordinary TDD; no frontend.
