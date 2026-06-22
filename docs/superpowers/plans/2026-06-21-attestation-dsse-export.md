# Attestation DSSE (Unsigned, Signing-Ready) Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit each LICENSED claim's existing in-toto Statement as a DSSE-shaped unsigned envelope (`signatures: []`), one-per-line NDJSON, via `export-attestation --format dsse` — signing-ready, dependency-free, with the default `bundle` output byte-for-byte unchanged.

**Architecture:** Refactor `attestation.py` so the per-claim records `(statement, drs_objects, unresolved)` are reusable: `build_attestation_records` (the loop), `build_attestation_bundle` consumes it (byte-identical), `build_attestation_statements` projects the statements. Add `DsseEnvelope`/`DsseSignature` DTOs + a pure `dsse_envelope(statement)` (stdlib base64+json). The CLI gains `--format {bundle,dsse}`.

**Tech Stack:** Python 3.12, pydantic v2 (frozen `_Model`, `Field(alias=...)`), stdlib `base64`/`json`, pytest. `uv`.

**Spec:** `docs/superpowers/specs/2026-06-21-attestation-dsse-export-design.md` (read it; §3 envelope shape, §4 architecture, §5 CLI, §6 testing).

## Global Constraints

- **Additive / byte-identical default:** `export-attestation` with no `--format` (or `--format bundle`) produces exactly today's `AttestationBundle` JSON. The records refactor changes nothing observable.
- **No signing / no trust claim:** `signatures` is always empty this slice. No keys/DSSE-PAE/Sigstore/Rekor/`[sigstore]` extra.
- **No new third-party dependency** beyond existing `pydantic` + stdlib; no network, no clock; deterministic.
- **Statement content unchanged** — slice 1's Statement is wrapped verbatim.
- **Determinism:** DSSE `payload` = standard base64 (padded) of `statement.model_dump_json(by_alias=True, exclude_none=True)`; NDJSON envelope order matches the bundle's claim order (sorted by `claim.id`); `--format dsse` to stdout vs `--out` are **byte-identical**.
- **`payloadType`** constant = `application/vnd.in-toto+json`. **`DsseSignature.keyid` is optional** (`str | None = None`); `sig` required.
- **Purity:** `attestation.py` stays umbrella-side, stdlib + existing pydantic only; `grammar/`/`protocol/` untouched.
- **Tests:** `uv run --project . pytest tests/attestation -q` + `uv run --project . ruff check src tests`. Full gate: `bash scripts/check-all.sh`. TDD; commit per task; merge `--no-ff` at the end.

## File Structure

- **Modify** `src/polymer_claims/attestation.py` — add `AttestationRecord` DTO + `build_attestation_records`; refactor `build_attestation_bundle` to consume it; add `build_attestation_statements`; add `DsseSignature`/`DsseEnvelope` DTOs + `_INTOTO_MEDIA_TYPE` + `dsse_envelope`.
- **Modify** `src/polymer_claims/__init__.py` — export the new public names.
- **Modify** `src/polymer_claims/cli.py` — `--format {bundle,dsse}` on `export-attestation`.
- **Tests** (existing dir `tests/attestation/`): extend `test_build_bundle.py` (records + byte-identical golden), add `test_dsse.py` (envelope + dsse_envelope), extend `test_export_attestation_cli.py` (`--format dsse`, empty case, stdout==file). Reuse the LICENSED-claim fixture in `tests/attestation/_fixtures.py` (grep it).
- **Docs:** `docs/superpowers/CONTINUE.md`, `ARCHITECTURE_CURRENT.md`, `GLOSSARY.md`.

---

### Task 1: Records-based extraction (byte-identical bundle)

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Test: `tests/attestation/test_build_bundle.py`

**Interfaces:**
- Consumes: existing `_statement(claim, ledger, contract_index, registry) -> tuple[Statement, tuple[DrsObject,...], tuple[str,...]]`, `Status`, `_Model`, `Statement`, `DrsObject`, `AttestationBundle` (all in `attestation.py`).
- Produces: `AttestationRecord(_Model)` with `statement: Statement`, `drs_objects: tuple[DrsObject,...]`, `unresolved: tuple[str,...]`; `build_attestation_records(corpus, *, contract_index, registry=None) -> tuple[AttestationRecord,...]`; `build_attestation_statements(corpus, *, contract_index, registry=None) -> tuple[Statement,...]`. `build_attestation_bundle` keeps its exact signature and output.

- [ ] **Step 1: Write the failing test**

In `tests/attestation/test_build_bundle.py` (reuse the module's LICENSED-claim corpus + `contract_index` fixtures — grep `tests/attestation/_fixtures.py` and the existing bundle test for their names; below they're shown as `licensed_corpus()` and `contract_index()`):

```python
from polymer_claims.attestation import (
    build_attestation_bundle, build_attestation_records, build_attestation_statements,
)

def test_records_carry_statement_drs_and_unresolved():
    corpus = licensed_corpus()
    idx = contract_index()
    records = build_attestation_records(corpus, contract_index=idx)
    assert len(records) == sum(1 for c in corpus.claims
                               if c.status.value == "licensed" and c.licensing is not None)
    r = records[0]
    assert hasattr(r, "statement") and hasattr(r, "drs_objects") and hasattr(r, "unresolved")

def test_statements_projection_matches_records():
    corpus = licensed_corpus(); idx = contract_index()
    stmts = build_attestation_statements(corpus, contract_index=idx)
    assert stmts == tuple(r.statement for r in build_attestation_records(corpus, contract_index=idx))

def test_bundle_byte_identical_after_records_refactor():
    # GOLDEN: the bundle JSON must be unchanged by the extraction.
    corpus = licensed_corpus(); idx = contract_index()
    out = build_attestation_bundle(corpus, contract_index=idx).model_dump_json(by_alias=True, exclude_none=True)
    # Compare to the committed golden from slice 1 (reuse the existing golden const/file in this test
    # module — grep for the slice-1 bundle golden assertion and assert `out` equals that same golden).
    assert out == EXPECTED_BUNDLE_JSON   # the existing slice-1 golden
```

> Find the slice-1 bundle golden in `test_build_bundle.py` (grep `model_dump_json`/`golden`/an expected-JSON constant or file) and assert the refactored output equals that exact value — that is the byte-identical guard.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project . pytest tests/attestation/test_build_bundle.py -q`
Expected: FAIL — `build_attestation_records` / `build_attestation_statements` are not defined (ImportError).

- [ ] **Step 3: Implement the records extraction**

In `src/polymer_claims/attestation.py`, add the DTO (near the other DTOs) and the two functions, and refactor `build_attestation_bundle`:

```python
class AttestationRecord(_Model):
    statement: Statement
    drs_objects: tuple[DrsObject, ...] = ()
    unresolved: tuple[str, ...] = ()


def build_attestation_records(corpus, *, contract_index, registry=None) -> tuple[AttestationRecord, ...]:
    """One record (statement + its DRS objects + unresolved dimnames hashes) per LICENSED claim,
    sorted by claim id. Pure; contract_index + registry injected."""
    licensed = sorted(
        (c for c in corpus.claims if c.status == Status.LICENSED and c.licensing is not None),
        key=lambda c: c.id,
    )
    records: list[AttestationRecord] = []
    for claim in licensed:
        statement, drs_objects, unresolved = _statement(
            claim, corpus.fdr_ledger, contract_index, registry
        )
        records.append(AttestationRecord(statement=statement, drs_objects=drs_objects, unresolved=unresolved))
    return tuple(records)


def build_attestation_statements(corpus, *, contract_index, registry=None) -> tuple[Statement, ...]:
    """Projection: just the in-toto Statements (the DSSE export's input)."""
    return tuple(r.statement for r in build_attestation_records(corpus, contract_index=contract_index, registry=registry))
```

Replace the body of `build_attestation_bundle` (keep its signature/docstring) so it consumes records and assembles the bundle with the **same** dedupe/sort:

```python
def build_attestation_bundle(corpus, *, contract_index, registry=None) -> AttestationBundle:
    """Deterministic in-toto/SLSA attestation bundle + DRS object docs for a corpus's LICENSED claims.
    Pure: contract_index + registry injected; no IO/clock/random."""
    records = build_attestation_records(corpus, contract_index=contract_index, registry=registry)
    drs: dict = {}
    unresolved: set[str] = set()
    for rec in records:
        for obj in rec.drs_objects:
            drs[obj.id] = obj
        unresolved.update(rec.unresolved)
    return AttestationBundle(
        attestations=tuple(r.statement for r in records),
        drs_objects=tuple(drs[k] for k in sorted(drs)),
        unresolved_datasets=tuple(sorted(unresolved)),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project . pytest tests/attestation/test_build_bundle.py -q`
Expected: PASS — including the byte-identical golden (the refactor is behavior-preserving).

- [ ] **Step 5: Lint + commit**

```bash
uv run --project . ruff check src tests
git add src/polymer_claims/attestation.py tests/attestation/test_build_bundle.py
git commit -m "refactor(attestation): records-based extraction (build_attestation_records/_statements); bundle byte-identical"
```

---

### Task 2: DSSE DTOs + `dsse_envelope`

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Test: `tests/attestation/test_dsse.py` (new)

**Interfaces:**
- Consumes: `_Model`, `Statement`, `Field` (already imported from pydantic), `build_attestation_statements` (Task 1).
- Produces: `_INTOTO_MEDIA_TYPE = "application/vnd.in-toto+json"`; `DsseSignature(_Model)` (`sig: str`, `keyid: str | None = None`); `DsseEnvelope(_Model)` (`payload_type: str` alias `payloadType` default `_INTOTO_MEDIA_TYPE`, `payload: str`, `signatures: tuple[DsseSignature,...] = ()`); `dsse_envelope(statement: Statement) -> DsseEnvelope`.

- [ ] **Step 1: Write the failing test**

Create `tests/attestation/test_dsse.py`:

```python
import base64, json
from polymer_claims.attestation import dsse_envelope, build_attestation_statements, DsseEnvelope
# reuse the module fixtures (grep tests/attestation/_fixtures.py for the real names)
from tests.attestation._fixtures import licensed_corpus, contract_index   # adjust import to actual

def test_dsse_envelope_shape_and_roundtrip():
    stmt = build_attestation_statements(licensed_corpus(), contract_index=contract_index())[0]
    env = dsse_envelope(stmt)
    assert isinstance(env, DsseEnvelope)
    assert env.payload_type == "application/vnd.in-toto+json"
    assert env.signatures == ()
    decoded = json.loads(base64.b64decode(env.payload))
    assert decoded == json.loads(stmt.model_dump_json(by_alias=True, exclude_none=True))

def test_dsse_envelope_serializes_with_intoto_aliases_and_empty_sigs():
    stmt = build_attestation_statements(licensed_corpus(), contract_index=contract_index())[0]
    obj = json.loads(dsse_envelope(stmt).model_dump_json(by_alias=True, exclude_none=True))
    assert obj["payloadType"] == "application/vnd.in-toto+json"
    assert obj["signatures"] == []
    assert isinstance(obj["payload"], str)

def test_dsse_signature_keyid_optional():
    from polymer_claims.attestation import DsseSignature
    assert DsseSignature(sig="x").keyid is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project . pytest tests/attestation/test_dsse.py -q`
Expected: FAIL — `dsse_envelope` / `DsseEnvelope` / `DsseSignature` not defined.

- [ ] **Step 3: Implement the DTOs + builder**

Add to `src/polymer_claims/attestation.py` (near the top with the other DTOs; `Field` is already imported, `base64` needs adding to the stdlib imports):

```python
import base64   # add alongside the existing `import json`

_INTOTO_MEDIA_TYPE = "application/vnd.in-toto+json"


class DsseSignature(_Model):
    sig: str
    keyid: str | None = None          # DSSE: keyid is OPTIONAL


class DsseEnvelope(_Model):
    payload_type: str = Field(default=_INTOTO_MEDIA_TYPE, alias="payloadType")
    payload: str                      # standard base64 of the Statement JSON
    signatures: tuple[DsseSignature, ...] = ()   # empty = unsigned, signing-ready (NOT trust-valid)


def dsse_envelope(statement: Statement) -> DsseEnvelope:
    """Wrap one in-toto Statement in an unsigned DSSE-shaped envelope. Pure; stdlib base64+json.
    payload = standard base64 of the standalone Statement serialization (round-trips to the Statement)."""
    raw = statement.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
    return DsseEnvelope(payload=base64.b64encode(raw).decode("ascii"))
```

> Confirm `_Model` allows construction by field name with an aliased field (slice-1 DTOs like `Builder(builder_dependencies=...)` already do, so `populate_by_name` is on). `DsseEnvelope(payload=...)` uses the default `payload_type`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project . pytest tests/attestation/test_dsse.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Lint + commit**

```bash
uv run --project . ruff check src tests
git add src/polymer_claims/attestation.py tests/attestation/test_dsse.py
git commit -m "feat(attestation): DsseEnvelope/DsseSignature DTOs + dsse_envelope (unsigned, signing-ready)"
```

---

### Task 3: CLI `export-attestation --format dsse` (NDJSON)

**Files:**
- Modify: `src/polymer_claims/cli.py`
- Test: `tests/attestation/test_export_attestation_cli.py`

**Interfaces:**
- Consumes: `load_corpus`, `_write_or_print`, `main`/parser plumbing (existing in `cli.py`); `build_attestation_bundle`, `build_attestation_statements`, `dsse_envelope`, `resolve_contract_index` (attestation). `sys` + `pathlib.Path` (confirm imported at top of `cli.py`; add if missing).
- Produces: `export-attestation` accepts `--format {bundle,dsse}` (default `bundle`); `dsse` emits NDJSON written byte-identically to stdout/`--out`.

- [ ] **Step 1: Write the failing tests**

In `tests/attestation/test_export_attestation_cli.py` (mirror the existing slice-1 CLI test's invocation — it builds a corpus JSON in `tmp_path` and calls `main([...])` capturing stdout via `capsys`):

```python
import json, base64
from polymer_claims.cli import main

def test_export_attestation_dsse_ndjson(tmp_path, capsys, licensed_corpus_path):  # reuse the existing corpus-file fixture
    rc = main(["export-attestation", str(licensed_corpus_path), "--format", "dsse"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.split("\n") if ln]               # drop the trailing-newline empty tail
    assert len(lines) >= 1
    for ln in lines:
        env = json.loads(ln)
        assert env["payloadType"] == "application/vnd.in-toto+json"
        assert env["signatures"] == []
        json.loads(base64.b64decode(env["payload"]))            # payload decodes to a Statement

def test_export_attestation_default_is_bundle(tmp_path, capsys, licensed_corpus_path):
    rc = main(["export-attestation", str(licensed_corpus_path)])
    assert rc == 0
    obj = json.loads(capsys.readouterr().out)
    assert "attestations" in obj                                # the bundle, unchanged

def test_export_attestation_dsse_stdout_equals_file(tmp_path, capsys, licensed_corpus_path):
    out_file = tmp_path / "att.ndjson"
    assert main(["export-attestation", str(licensed_corpus_path), "--format", "dsse", "--out", str(out_file)]) == 0
    assert main(["export-attestation", str(licensed_corpus_path), "--format", "dsse"]) == 0
    stdout = capsys.readouterr().out
    assert out_file.read_text() == stdout                       # byte-identical, no print() divergence

def test_export_attestation_dsse_empty_corpus_emits_nothing(tmp_path, capsys, empty_corpus_path):
    # a corpus with zero LICENSED claims
    assert main(["export-attestation", str(empty_corpus_path), "--format", "dsse"]) == 0
    assert capsys.readouterr().out == ""                        # no blank line
```

> If there's no ready `licensed_corpus_path`/`empty_corpus_path` file fixture, build one in `tmp_path` exactly as the slice-1 CLI test does (it writes a corpus's `model_dump_json` to a file). An empty corpus = `Corpus(claims=(), fdr_ledger=FDRLedger(target_fdr=0.05))`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project . pytest tests/attestation/test_export_attestation_cli.py -q -k dsse`
Expected: FAIL — `--format` is an unrecognized argument (SystemExit 2).

- [ ] **Step 3: Implement the CLI option**

In `src/polymer_claims/cli.py`: add the argument to the `export-attestation` subparser (find `p_att = sub.add_parser("export-attestation", ...)`):

```python
    p_att.add_argument("--format", choices=("bundle", "dsse"), default="bundle",
                       help="bundle (default Polymer AttestationBundle) or dsse (NDJSON of unsigned DSSE envelopes)")
```

Rewrite `_cmd_export_attestation` to branch on the format and write the dsse output byte-identically (ensure `import sys` and `from pathlib import Path` exist at the top of `cli.py`; add if missing):

```python
def _cmd_export_attestation(args: argparse.Namespace) -> int:
    from .attestation import (
        build_attestation_bundle, build_attestation_statements, dsse_envelope, resolve_contract_index,
    )
    corpus = load_corpus(args.corpus)
    index = resolve_contract_index(corpus)
    if args.format == "dsse":
        envelopes = [dsse_envelope(s) for s in build_attestation_statements(corpus, contract_index=index)]
        output = "".join(e.model_dump_json(by_alias=True, exclude_none=True) + "\n" for e in envelopes)
        if args.out:
            Path(args.out).write_text(output)
        else:
            sys.stdout.write(output)        # exact string — NOT print() (no extra newline; empty => nothing)
        return 0
    bundle = build_attestation_bundle(corpus, contract_index=index)
    _write_or_print(bundle.model_dump_json(by_alias=True, exclude_none=True), args.out)
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project . pytest tests/attestation/test_export_attestation_cli.py -q`
Expected: PASS (dsse ndjson, default bundle, stdout==file, empty-corpus).

- [ ] **Step 5: Lint + commit**

```bash
uv run --project . ruff check src tests
git add src/polymer_claims/cli.py tests/attestation/test_export_attestation_cli.py
git commit -m "feat(cli): export-attestation --format dsse (NDJSON, byte-identical stdout/file, empty-safe)"
```

---

### Task 4: Public exports + docs + full gate

**Files:**
- Modify: `src/polymer_claims/__init__.py`, `docs/superpowers/CONTINUE.md`, `ARCHITECTURE_CURRENT.md`, `GLOSSARY.md`

- [ ] **Step 1: Export the new names**

In `src/polymer_claims/__init__.py`, extend the existing `from polymer_claims.attestation import (...)` block and `__all__` to add: `AttestationRecord`, `build_attestation_records`, `build_attestation_statements`, `DsseEnvelope`, `DsseSignature`, `dsse_envelope`.

- [ ] **Step 2: Quick import sanity**

Run: `uv run --project . python -c "import polymer_claims as p; [getattr(p,n) for n in ['dsse_envelope','DsseEnvelope','DsseSignature','build_attestation_records','build_attestation_statements','AttestationRecord']]; print('exports ok')"`
Expected: `exports ok`.

- [ ] **Step 3: Update docs**

- `GLOSSARY.md`: extend the **attestation / standards skin** entry — note `export-attestation --format dsse` emits per-claim **unsigned DSSE-shaped envelopes** (`signatures: []`) in NDJSON: signing-ready, not trust-valid (decode `payload` for the bare Statement; signing is slice 3).
- `ARCHITECTURE_CURRENT.md`: append to the standards-skin paragraph that slice 2 added `--format dsse` (unsigned DSSE NDJSON; reuses the Statements via `build_attestation_statements`; signing/Rekor = slice 3).
- `CONTINUE.md`: a Done entry — "Attestation DSSE export (arc 2, slice 2)" — `--format dsse` NDJSON of unsigned DSSE envelopes; records-based refactor (bundle byte-identical); stdlib-only/deterministic/additive; spec+plan `docs/superpowers/{specs,plans}/2026-06-21-attestation-dsse-export*`; deferred: real signing (Sigstore/Rekor/DSSE PAE) = slice 3. Update the umbrella test count by the number of new tests added (run `uv run --project . pytest tests/attestation -q | tail -2` and `... pytest tests/ -q | tail -2`, set the count to the observed total).

- [ ] **Step 4: Full gate**

Run: `bash scripts/check-all.sh`
Expected: ALL GREEN (Python + ruff + isolation + viewer tsc/build). `next build` may fail only on the known Google-Fonts network block — if it stops there, confirm everything before it passed and report that.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/__init__.py docs/superpowers/CONTINUE.md ARCHITECTURE_CURRENT.md GLOSSARY.md
git commit -m "docs+exports(attestation): DSSE export public API + docs (arc 2, slice 2)"
```

---

## Self-Review

**Spec coverage:** §3 envelope shape → Task 2 (`dsse_envelope`, `_INTOTO_MEDIA_TYPE`, base64 payload, empty signatures). §4 records extraction → Task 1 (`AttestationRecord`/`build_attestation_records`/`build_attestation_statements`, bundle byte-identical) + DTOs in Task 2 (keyid optional). §5 CLI `--format dsse` + NDJSON + byte-identical write + empty case → Task 3. §6 tests: golden byte-identical (T1), shape+round-trip (T2), CLI/empty/stdout==file (T3), dependency guard (stdlib base64+json — no new import, asserted by the no-new-dep nature of T2's code). §7 out-of-scope (signing/Rekor) not built. §2 sequencing → Tasks 1→2→3→4. All spec sections map to a task.

**Placeholder scan:** Every code step shows complete code; every test step shows real assertions (base64 round-trip, `signatures == []`, line counts, stdout==file bytes, empty→`""`). The "grep the fixture/golden names" notes are verification instructions against unseen local fixture names in `tests/attestation/`, not deferred logic — the surrounding code is complete.

**Type consistency:** `AttestationRecord{statement,drs_objects,unresolved}`, `build_attestation_records(corpus,*,contract_index,registry=None)->tuple[AttestationRecord,...]`, `build_attestation_statements(...)->tuple[Statement,...]`, `DsseSignature{sig:str, keyid:str|None=None}`, `DsseEnvelope{payload_type(alias payloadType), payload, signatures:tuple=()}`, `dsse_envelope(statement)->DsseEnvelope`, `_INTOTO_MEDIA_TYPE` — names/signatures are identical across tasks and match the CLI's calls. `build_attestation_bundle` keeps its exact signature and (golden-verified) output.
