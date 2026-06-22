# Attestation DSSE (Unsigned, Signing-Ready) Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit each LICENSED claim's existing in-toto Statement as a DSSE-shaped unsigned envelope (`signatures: []`), one-per-line NDJSON, via `export-attestation --format dsse` — signing-ready, dependency-free, with the default `bundle` output byte-for-byte unchanged.

**Architecture:** Refactor `attestation.py` so the per-claim records `(statement, drs_objects, unresolved)` are reusable: `build_attestation_records` (the loop), `build_attestation_bundle` consumes it (byte-identical), `build_attestation_statements` projects the statements. Add `DsseEnvelope`/`DsseSignature` DTOs + a pure `dsse_envelope(statement)` (stdlib base64+json). The CLI gains `--format {bundle,dsse}`.

**Tech Stack:** Python 3.12, pydantic v2 (frozen `_Model`, `Field(alias=...)`), stdlib `base64`/`json`, pytest. `uv`.

**Spec:** `docs/superpowers/specs/2026-06-21-attestation-dsse-export-design.md`.

## Global Constraints

- **Additive / byte-identical default:** `export-attestation` with no `--format` (or `--format bundle`) produces exactly today's `AttestationBundle` JSON.
- **No signing / no trust claim:** `signatures` is always empty this slice. No keys/DSSE-PAE/Sigstore/Rekor/`[sigstore]` extra.
- **No new third-party dependency** beyond existing `pydantic` + stdlib; no network/clock; deterministic.
- **Statement content unchanged** — slice 1's Statement wrapped verbatim.
- **Determinism:** DSSE `payload` = standard base64 (padded) of `statement.model_dump_json(by_alias=True, exclude_none=True)`; NDJSON order = bundle order (sorted by `claim.id`); `--format dsse` to stdout vs `--out` are **byte-identical**.
- **`payloadType`** constant = `application/vnd.in-toto+json`. **`DsseSignature.keyid` optional** (`str | None = None`); `sig` required.
- **Purity:** `attestation.py` stays umbrella-side, stdlib + existing pydantic only.
- **Tests:** `uv run --project . pytest tests/attestation -q` + `uv run --project . ruff check src tests`. Full gate `bash scripts/check-all.sh`. TDD; commit per task; merge `--no-ff` at the end.

## Codebase facts (verified — use these exact names)

- Test fixtures: `tests/attestation/_fixtures.py` exports `mc(*, dimnames_hash=None, profile_hash=None, semantic_run_id=None, mid="M")`, `sat(materialization, *, credential_ids=())`, `licensing(*satisfactions, **kwargs)`, `licensed_claim(cid, lic)`, `corpus_with(*claims, fdr_ledger=None)`. There is **no** `licensed_corpus`/`contract_index` fixture; `contract_index` is passed as a plain dict (`{}` or `{h: ref}`).
- CLI tests build a corpus file via `from polymer_claims.io import dump_corpus`: `path.write_text(dump_corpus(corpus_with(claim)))`, then `main(["export-attestation", str(path), ...])`.
- `attestation.py` top-level imports (third-party = exactly `{pydantic}`): `json`, `re`, `collections.abc`, `pydantic`, `polymer_grammar*`, `polymer_claims*`, `polymer_protocol`.
- Internal builder: `_statement(claim, ledger, contract_index, registry) -> (Statement, tuple[DrsObject,...], tuple[str,...])`. `build_attestation_bundle(corpus, *, contract_index, registry=None) -> AttestationBundle`.
- There is **no committed byte-golden** for the bundle (only structural/determinism tests). This plan captures a real golden file (Task 1) as the byte-identical guard.

## File Structure

- **Modify** `src/polymer_claims/attestation.py`, `src/polymer_claims/__init__.py`, `src/polymer_claims/cli.py`.
- **Tests** in `tests/attestation/`: extend `test_build_bundle.py`, add `test_dsse.py`, extend `test_export_attestation_cli.py`; commit a captured golden `tests/attestation/_golden_bundle.json`.
- **Docs:** `docs/superpowers/CONTINUE.md`, `ARCHITECTURE_CURRENT.md`, `GLOSSARY.md`.

---

### Task 1: Records-based extraction (byte-identical bundle, real golden)

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Create: `tests/attestation/_golden_bundle.json` (captured)
- Test: `tests/attestation/test_build_bundle.py`

**Interfaces:**
- Consumes: existing `_statement`, `Status`, `_Model`, `Statement`, `DrsObject`, `AttestationBundle`.
- Produces: `AttestationRecord(_Model)`{`statement: Statement`, `drs_objects: tuple[DrsObject,...]=()`, `unresolved: tuple[str,...]=()`}; `build_attestation_records(corpus, *, contract_index, registry=None) -> tuple[AttestationRecord,...]`; `build_attestation_statements(corpus, *, contract_index, registry=None) -> tuple[Statement,...]`. `build_attestation_bundle` keeps its exact signature + output.

- [ ] **Step 1: Capture the real byte-golden (pre-refactor) and commit it**

Run (writes the *current* bundle JSON, no trailing newline, to the golden file):

```bash
uv run --project . python -c "
import sys
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing, mc, sat
from polymer_claims.attestation import build_attestation_bundle
def L(cid): return licensed_claim(cid, licensing(sat(mc(dimnames_hash='sha256:'+'a'*64, profile_hash='sha256:'+'b'*64, semantic_run_id='r1'))))
corpus = corpus_with(L('c2'), L('c1'))
sys.stdout.write(build_attestation_bundle(corpus, contract_index={}).model_dump_json(by_alias=True, exclude_none=True))
" > tests/attestation/_golden_bundle.json
```

This golden is the byte-identical baseline; the refactor must reproduce it exactly.

- [ ] **Step 2: Write the failing tests**

Append to `tests/attestation/test_build_bundle.py`:

```python
from pathlib import Path
from polymer_claims.attestation import (
    AttestationRecord, build_attestation_records, build_attestation_statements,
)

_GOLDEN = Path(__file__).parent / "_golden_bundle.json"

def _golden_corpus():
    def L(cid):
        return licensed_claim(cid, licensing(sat(mc(
            dimnames_hash="sha256:" + "a" * 64, profile_hash="sha256:" + "b" * 64, semantic_run_id="r1"))))
    return corpus_with(L("c2"), L("c1"))

def test_bundle_matches_captured_golden():
    out = build_attestation_bundle(_golden_corpus(), contract_index={}).model_dump_json(by_alias=True, exclude_none=True)
    assert out == _GOLDEN.read_text()      # byte-identical to the pre-refactor capture

def test_records_carry_statement_drs_and_unresolved():
    records = build_attestation_records(_golden_corpus(), contract_index={})
    assert len(records) == 2
    r = records[0]
    assert isinstance(r, AttestationRecord)
    assert r.statement.subject[0].name == "c1"            # sorted by claim id
    assert isinstance(r.drs_objects, tuple) and isinstance(r.unresolved, tuple)

def test_statements_projection_equals_records_statements():
    corpus = _golden_corpus()
    assert build_attestation_statements(corpus, contract_index={}) == tuple(
        r.statement for r in build_attestation_records(corpus, contract_index={}))
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run --project . pytest tests/attestation/test_build_bundle.py -q`
Expected: `test_bundle_matches_captured_golden` PASSES (current code matches its own golden); the two new ones FAIL with `ImportError` (`AttestationRecord`/`build_attestation_records`/`build_attestation_statements` undefined) — that is the RED for the new work.

- [ ] **Step 4: Implement the records extraction**

In `src/polymer_claims/attestation.py`, add the DTO + functions and refactor the bundle body:

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
        statement, drs_objects, unresolved = _statement(claim, corpus.fdr_ledger, contract_index, registry)
        records.append(AttestationRecord(statement=statement, drs_objects=drs_objects, unresolved=unresolved))
    return tuple(records)


def build_attestation_statements(corpus, *, contract_index, registry=None) -> tuple[Statement, ...]:
    """Projection: just the in-toto Statements (the DSSE export's input)."""
    return tuple(r.statement for r in build_attestation_records(
        corpus, contract_index=contract_index, registry=registry))
```

Replace the body of `build_attestation_bundle` (keep signature + docstring) to consume records:

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

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --project . pytest tests/attestation/test_build_bundle.py -q`
Expected: PASS — all, including `test_bundle_matches_captured_golden` (byte-identical) **and the pre-existing structural tests unchanged** (`test_golden_statement_shape_for_resolved_corpus`, `test_one_statement_per_licensed_claim_sorted_by_id`, etc. — do NOT modify those; their continued passing is the behavior-preservation guard).

- [ ] **Step 6: Lint + commit**

```bash
uv run --project . ruff check src tests
git add src/polymer_claims/attestation.py tests/attestation/test_build_bundle.py tests/attestation/_golden_bundle.json
git commit -m "refactor(attestation): records-based extraction; bundle byte-identical (captured golden)"
```

---

### Task 2: DSSE DTOs + `dsse_envelope` (+ dependency guard)

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Test: `tests/attestation/test_dsse.py` (new)

**Interfaces:**
- Consumes: `_Model`, `Statement`, `Field` (pydantic, already imported), `build_attestation_statements` (Task 1).
- Produces: `_INTOTO_MEDIA_TYPE="application/vnd.in-toto+json"`; `DsseSignature(_Model)`{`sig: str`, `keyid: str|None=None`}; `DsseEnvelope(_Model)`{`payload_type` (alias `payloadType`, default `_INTOTO_MEDIA_TYPE`), `payload: str`, `signatures: tuple[DsseSignature,...]=()`}; `dsse_envelope(statement: Statement) -> DsseEnvelope`.

- [ ] **Step 1: Write the failing tests**

Create `tests/attestation/test_dsse.py`:

```python
from __future__ import annotations
import ast, base64, json, sys
from pathlib import Path

from polymer_claims.attestation import (
    DsseEnvelope, DsseSignature, dsse_envelope, build_attestation_statements,
)
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing, mc, sat


def _stmt():
    claim = licensed_claim("c1", licensing(sat(mc(dimnames_hash="sha256:" + "a" * 64))))
    return build_attestation_statements(corpus_with(claim), contract_index={})[0]


def test_dsse_envelope_shape_and_roundtrip():
    env = dsse_envelope(_stmt())
    assert isinstance(env, DsseEnvelope)
    assert env.payload_type == "application/vnd.in-toto+json"
    assert env.signatures == ()
    assert json.loads(base64.b64decode(env.payload)) == json.loads(
        _stmt().model_dump_json(by_alias=True, exclude_none=True))


def test_dsse_envelope_serializes_with_intoto_aliases_and_empty_sigs():
    obj = json.loads(dsse_envelope(_stmt()).model_dump_json(by_alias=True, exclude_none=True))
    assert obj["payloadType"] == "application/vnd.in-toto+json"
    assert obj["signatures"] == []
    assert isinstance(obj["payload"], str)


def test_dsse_signature_keyid_optional():
    assert DsseSignature(sig="x").keyid is None


def test_attestation_no_new_thirdparty_imports():
    """Dependency guard: attestation.py may import only stdlib + pydantic + internal packages."""
    src = (Path(__file__).parents[2] / "src" / "polymer_claims" / "attestation.py").read_text()
    mods: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    thirdparty = mods - set(sys.stdlib_module_names) - {"polymer_grammar", "polymer_protocol", "polymer_claims"}
    assert thirdparty <= {"pydantic"}, f"unexpected third-party imports: {thirdparty}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project . pytest tests/attestation/test_dsse.py -q`
Expected: FAIL — `dsse_envelope`/`DsseEnvelope`/`DsseSignature` undefined (ImportError). (The import-guard test would pass, but the module-level import of the new names blocks the file from loading until they exist.)

- [ ] **Step 3: Implement the DTOs + builder**

In `src/polymer_claims/attestation.py`: add `import base64` to the stdlib imports (next to `import json`), and add near the other DTOs:

```python
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project . pytest tests/attestation/test_dsse.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Lint + commit**

```bash
uv run --project . ruff check src tests
git add src/polymer_claims/attestation.py tests/attestation/test_dsse.py
git commit -m "feat(attestation): DsseEnvelope/DsseSignature + dsse_envelope (unsigned, signing-ready) + dep guard"
```

---

### Task 3: CLI `export-attestation --format dsse` (NDJSON)

**Files:**
- Modify: `src/polymer_claims/cli.py`
- Test: `tests/attestation/test_export_attestation_cli.py`

**Interfaces:**
- Consumes: `load_corpus`, `_write_or_print`, the `export-attestation` subparser (`p_att`) and `_cmd_export_attestation` in `cli.py`; `build_attestation_bundle`, `build_attestation_statements`, `dsse_envelope`, `resolve_contract_index`. `sys` + `pathlib.Path` (confirm imported at top of `cli.py`; add if missing).
- Produces: `--format {bundle,dsse}` (default `bundle`); `dsse` emits NDJSON written byte-identically to stdout/`--out`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/attestation/test_export_attestation_cli.py` (it already imports `json`, `main`, `dump_corpus`, and the fixtures):

```python
import base64
from tests.attestation._fixtures import corpus_with  # already importing licensed_claim/licensing/mc/sat

def _write_empty_corpus(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(dump_corpus(corpus_with()))        # zero LICENSED claims
    return path

def test_export_attestation_dsse_ndjson(tmp_path, capsys):
    corpus_path = _write_corpus(tmp_path)
    assert main(["export-attestation", str(corpus_path), "--format", "dsse"]) == 0
    lines = [ln for ln in capsys.readouterr().out.split("\n") if ln]
    assert len(lines) == 1
    env = json.loads(lines[0])
    assert env["payloadType"] == "application/vnd.in-toto+json"
    assert env["signatures"] == []
    json.loads(base64.b64decode(env["payload"]))        # payload decodes to a Statement

def test_export_attestation_default_equals_format_bundle_bytes(tmp_path):
    corpus_path = _write_corpus(tmp_path)
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    assert main(["export-attestation", str(corpus_path), "--out", str(a)]) == 0
    assert main(["export-attestation", str(corpus_path), "--format", "bundle", "--out", str(b)]) == 0
    assert a.read_text() == b.read_text()               # default == explicit bundle, byte-for-byte

def test_export_attestation_dsse_stdout_equals_file(tmp_path, capsys):
    corpus_path = _write_corpus(tmp_path)
    out_file = tmp_path / "att.ndjson"
    assert main(["export-attestation", str(corpus_path), "--format", "dsse", "--out", str(out_file)]) == 0
    assert main(["export-attestation", str(corpus_path), "--format", "dsse"]) == 0
    assert out_file.read_text() == capsys.readouterr().out     # byte-identical, no print() divergence

def test_export_attestation_dsse_empty_emits_nothing(tmp_path, capsys):
    empty_path = _write_empty_corpus(tmp_path)
    assert main(["export-attestation", str(empty_path), "--format", "dsse"]) == 0
    assert capsys.readouterr().out == ""                # no blank line
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project . pytest tests/attestation/test_export_attestation_cli.py -q -k "dsse or bundle_bytes"`
Expected: FAIL — `--format` is an unrecognized argument (SystemExit 2).

- [ ] **Step 3: Implement the CLI option**

In `src/polymer_claims/cli.py`, ensure `import sys` and `from pathlib import Path` exist at the top (add if missing). Add the argument to the `export-attestation` subparser (find `p_att = sub.add_parser("export-attestation", ...)`):

```python
    p_att.add_argument("--format", choices=("bundle", "dsse"), default="bundle",
                       help="bundle (default Polymer AttestationBundle) or dsse (NDJSON of unsigned DSSE envelopes)")
```

Rewrite `_cmd_export_attestation`:

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
Expected: PASS (existing `test_export_attestation_writes_bundle` + the 4 new).

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

- [ ] **Step 1: Export the new names + test**

In `src/polymer_claims/__init__.py`, extend the existing `from polymer_claims.attestation import (...)` block and `__all__` with: `AttestationRecord`, `build_attestation_records`, `build_attestation_statements`, `DsseEnvelope`, `DsseSignature`, `dsse_envelope`. Then append to `tests/attestation/test_build_bundle.py::test_public_api_exports` (or add a sibling test) assertions that these six names are attributes of `polymer_claims` and in `pc.__all__`.

Run: `uv run --project . pytest tests/attestation -q`
Expected: PASS (all attestation tests, including the exports assertions).

- [ ] **Step 2: Update docs**

- `GLOSSARY.md`: extend the **attestation / standards skin** entry — `export-attestation --format dsse` emits per-claim **unsigned DSSE-shaped envelopes** (`signatures: []`) in NDJSON: signing-ready, **not trust-valid** (decode `payload` for the bare Statement; real signing is slice 3).
- `ARCHITECTURE_CURRENT.md`: append to the standards-skin paragraph that slice 2 added `--format dsse` (unsigned DSSE NDJSON; reuses Statements via `build_attestation_statements`; signing/Rekor = slice 3).
- `CONTINUE.md`: a Done entry — "Attestation DSSE export (arc 2, slice 2)" — `--format dsse` NDJSON of unsigned DSSE envelopes; records-based refactor (bundle byte-identical, captured golden); stdlib-only/deterministic/additive; spec+plan `docs/superpowers/{specs,plans}/2026-06-21-attestation-dsse-export*`; deferred: real signing (Sigstore/Rekor/DSSE PAE) = slice 3. Update the current-state umbrella test count to the observed total (`uv run --project . pytest tests/ -q | tail -2`) — CONTINUE.md is this repo's live status ledger, so keep the count accurate.

- [ ] **Step 3: Full gate**

Run: `bash scripts/check-all.sh`
Expected: ALL GREEN (Python + ruff + isolation + viewer tsc/build). `next build` may fail only on the known Google-Fonts network block — if it stops there, confirm everything before it passed and report that.

- [ ] **Step 4: Commit**

```bash
git add src/polymer_claims/__init__.py tests/attestation/test_build_bundle.py docs/superpowers/CONTINUE.md ARCHITECTURE_CURRENT.md GLOSSARY.md
git commit -m "docs+exports(attestation): DSSE export public API + docs (arc 2, slice 2)"
```

---

## Self-Review

**Spec coverage:** §3 envelope shape → Task 2. §4 records extraction + statements projection + keyid-optional → Tasks 1–2. §5 CLI `--format dsse` + byte-identical write + empty case → Task 3. §6 tests: captured byte-golden (T1), shape+round-trip+dep-guard (T2), CLI dsse/default-bytes/stdout==file/empty (T3), exports (T4). §2 byte-identical default → T1 golden + T3 `test_export_attestation_default_equals_format_bundle_bytes`. §7 out-of-scope (signing) not built. All spec sections map to a task.

**Placeholder scan:** No fabricated fixtures or golden — all test code uses the verified `_fixtures.py` helpers (`corpus_with`/`licensed_claim`/`licensing`/`mc`/`sat`), `contract_index={}`, `dump_corpus` + `_write_corpus`, and a **captured** golden file (real current output, not invented). The dependency guard is a concrete AST import-scan test (third-party ⊆ `{pydantic}`), not a prose claim. No "grep/adjust" left for the new code.

**Type consistency:** `AttestationRecord{statement,drs_objects,unresolved}`, `build_attestation_records(corpus,*,contract_index,registry=None)->tuple[AttestationRecord,...]`, `build_attestation_statements(...)->tuple[Statement,...]`, `DsseSignature{sig, keyid:str|None=None}`, `DsseEnvelope{payload_type(alias payloadType), payload, signatures:tuple=()}`, `dsse_envelope(statement)->DsseEnvelope`, `_INTOTO_MEDIA_TYPE` — identical across tasks and the CLI calls. `build_attestation_bundle` keeps its exact signature and golden-verified output.
