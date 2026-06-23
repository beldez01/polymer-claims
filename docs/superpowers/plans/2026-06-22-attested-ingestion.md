# ATTESTED Ingestion (the credence layer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let external determinations about a LICENSED claim's standing enter the calibration ledger as the ATTESTED tier — recorded as *defeasible corpus claims*, typed by *resolvability*, feeding a `q_attested` disagreement rate that is never the headline `q`.

**Architecture:** Pure additive changes to `protocol`'s `calibration.py` (a `Resolvability` enum, an attested-only `resolvability` field, a structural prior, and resolvability counts on `TierStat`) and one additive `GenerationMode` value in `grammar`. An impure umbrella ingester (`attested_ingest.py`) parses an operator resolutions file, builds one **CONJECTURED `PropositionLeaf` attested-event claim per row** (forced non-LICENSED by construction), **appends it directly to `corpus.claims`** (no `run_cycle` — preserves the "instrument not a gate" invariant), builds an ATTESTED `ResolutionRecord` linked to it, and appends to the calibration ledger. A CLI subcommand and a certificate render line complete the slice.

**Tech Stack:** Python 3, pydantic v2 (`extra="forbid"`, `frozen=True` — via `_Model` for pure models, or an equivalent frozen `ConfigDict` on umbrella DTOs like `Resolution`), argparse CLI, pytest. No numpy in the pure layers. No network.

## Global Constraints

- **grammar/protocol stay pure + numpy-free.** The only pure additions are an enum, an enum value, a model field, additive `TierStat` fields, and a structural predicate. No filesystem, no network in `protocol/` or `grammar/`.
- **ATTESTED never feeds headline `q`.** `feeds_headline_q` (calibration.py:73-78) stays locked to DEFINITIONAL + REALIZED_FDR. Do not touch it. `q_attested` renders only under the "Warrant stability / field calibration" heading.
- **Additive / byte-identical when unused.** No resolutions file ⇒ no ATTESTED records, `Corpus` stays 4 collections. Byte identity here means the **human text render**: the certificate's zero-ATTESTED line stays exactly `  ATTESTED: 0 attested events`, and the richer `q_attested` line + disclosure appear **only** when `n_total > 0` (Task 9 honors this in the `else` branch). Note this does **not** extend to JSON serializations: the additive `TierStat.n_resolvable`/`n_unresolvable` fields default to `0` (not `None`), so `model_dump_json(exclude_none=True)` of a `CalibrationReport`/`Certificate` gains two zero fields per tier — an expected, one-time additive schema change, independent of whether any attestations exist.
- **The attested-event claim is forced non-LICENSED.** Built as `status=Status.CONJECTURED`, `licensing=None`, never passed through `verify`. A test must assert `licensing is None` / `status != LICENSED`.
- **Calibration is an instrument, not a gate.** Ingestion appends an attested-event claim to `corpus.claims` via `model_copy`; it must NOT call `run_cycle` and must NOT change any other claim's licensing/FDR state.
- **Determinism.** Attested-event claim ids are content-addressed (`canonical_sha256` over subject+verdict+ref+license_epoch). No `Date.now()`/random.
- **`stated_q` source:** `corpus.fdr_ledger.target_fdr` (the canonical per-corpus target, exactly as anchored records use at calibration.py:301).
- **Resolvability authority:** operator value if present, else `resolvability_prior(subject_claim)` (`evaluation_plan is not None` ⇒ resolvable). Read from the **subject** claim, never the attested-event claim.
- **Run commands:** pure protocol tests: `cd protocol && pytest tests/`; grammar tests: `cd grammar && pytest tests/`; umbrella tests: `pytest tests/` (from repo root). Lint: `ruff check src/ protocol/src/ grammar/src/`.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `protocol/src/polymer_protocol/calibration.py` | Modify | `Resolvability` enum, `resolvability` field + validator on `ResolutionRecord`, `resolvability_prior()`, `n_resolvable`/`n_unresolvable` on `TierStat`, populate in `_attested_stat` |
| `grammar/src/polymer_grammar/provenance.py` | Modify | Add `EXTERNAL_ATTESTATION` to `GenerationMode` |
| `src/polymer_claims/attested_ingest.py` | Create | Resolutions-file schema + parse/validate; build + append attested-event claim; build + append ATTESTED `ResolutionRecord` |
| `src/polymer_claims/calibration_store.py` | Modify | ATTESTED fold identity in `load_ledger` (include `source_claim_id` so multiple attestations per claim/epoch survive) |
| `src/polymer_claims/cli.py` | Modify | `ingest-attested` subcommand |
| `src/polymer_claims/attestation.py` | Modify | Certificate render: `q_attested` + resolvability split + disclosure |
| `protocol/tests/test_calibration_resolvability.py` | Create | Pure tests for enum, field validator, prior, `_attested_stat` counts |
| `grammar/tests/test_provenance_external_attestation.py` | Create | Pure test for the new enum value |
| `tests/test_attested_ingest.py` | Create | Umbrella: parse/validate, claim build + non-LICENSED, ledger link |
| `tests/test_cli_ingest_attested.py` | Create | CLI smoke test |
| `tests/test_attested_certificate.py` | Create | Certificate render assertions |

---

### Task 1: `Resolvability` enum + attested-only `resolvability` field on `ResolutionRecord`

**Files:**
- Modify: `protocol/src/polymer_protocol/calibration.py` (enums near lines 20-36; `ResolutionRecord` lines 53-110; its `@model_validator(mode="after")` at line 80)
- Test: `protocol/tests/test_calibration_resolvability.py`

**Interfaces:**
- Produces: `Resolvability(str, Enum)` with `RESOLVABLE = "resolvable"`, `UNRESOLVABLE = "unresolvable"`; new field `resolvability: Resolvability | None = None` on `ResolutionRecord`, valid only when `resolution_kind == ATTESTED`.

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_calibration_resolvability.py`:

```python
import pytest
from polymer_protocol.calibration import (
    ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict, Resolvability,
)


def _attested(**kw):
    base = dict(
        subject_claim_id="c1", license_epoch=0,
        resolution_kind=ResolutionKind.ATTESTED,
        calibration_target=CalibrationTarget.EXTERNAL_DISAGREEMENT,
        verdict=ResolutionVerdict.UPHELD, stated_q=0.05, observed_at_cycle=0,
        attestation_ref="doi:10.1056/x", source_claim_id="attest-abc",
    )
    base.update(kw)
    return ResolutionRecord(**base)


def _definitional(**kw):
    base = dict(
        subject_claim_id="c1", license_epoch=0,
        resolution_kind=ResolutionKind.DEFINITIONAL,
        calibration_target=CalibrationTarget.REALIZED_FDR,
        verdict=ResolutionVerdict.UPHELD, stated_q=0.05, observed_at_cycle=0,
        constructed_truth=True, model_id="m1", batch_id="b1",
    )
    base.update(kw)
    return ResolutionRecord(**base)


def test_resolvability_allowed_on_attested():
    r = _attested(resolvability=Resolvability.RESOLVABLE)
    assert r.resolvability is Resolvability.RESOLVABLE


def test_resolvability_defaults_none():
    assert _attested().resolvability is None


def test_resolvability_rejected_on_non_attested():
    with pytest.raises(ValueError, match="resolvability"):
        _definitional(resolvability=Resolvability.RESOLVABLE)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && pytest tests/test_calibration_resolvability.py -v`
Expected: FAIL — `ImportError: cannot import name 'Resolvability'`.

- [ ] **Step 3: Add the enum and field**

In `protocol/src/polymer_protocol/calibration.py`, add the enum next to the other enums (after `ResolutionVerdict`, ~line 36):

```python
class Resolvability(str, Enum):
    RESOLVABLE = "resolvable"
    UNRESOLVABLE = "unresolvable"
```

Add the field to `ResolutionRecord` alongside the other attested fields (after `source_claim_id`, ~line 71):

```python
    resolvability: Resolvability | None = None  # attested — operator-declared or structural prior
```

- [ ] **Step 4: Add the present-only-when-attested validator clause**

In the `@model_validator(mode="after")` method (the one enforcing `attestation_ref`/`source_claim_id` are attested-only, ~lines 98-101), add a sibling clause. `att` is the existing local boolean `k == ResolutionKind.ATTESTED`:

```python
        if self.resolvability is not None and not att:
            raise ValueError("resolvability is valid only when resolution_kind=attested")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd protocol && pytest tests/test_calibration_resolvability.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Run the full pure suite (no regressions)**

Run: `cd protocol && pytest tests/ -q`
Expected: PASS (existing tests unaffected — additive optional field).

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/calibration.py protocol/tests/test_calibration_resolvability.py
git commit -m "feat(calibration): add Resolvability enum + attested-only resolvability field"
```

---

### Task 2: `resolvability_prior(claim)` structural predicate

**Files:**
- Modify: `protocol/src/polymer_protocol/calibration.py` (add a module-level function; it reads `claim.evaluation_plan`)
- Test: `protocol/tests/test_calibration_resolvability.py` (extend)

**Interfaces:**
- Consumes: a `Claim` (from `polymer_grammar`) — only its `evaluation_plan` attribute.
- Produces: `resolvability_prior(claim) -> Resolvability` — `RESOLVABLE` iff `claim.evaluation_plan is not None`, else `UNRESOLVABLE`. A fallback prior only; an explicit operator value always wins (used in Task 7).

- [ ] **Step 1: Write the failing test**

Append to `protocol/tests/test_calibration_resolvability.py`:

```python
from polymer_protocol.calibration import resolvability_prior


def _claim(plan):
    # Minimal claim via the protocol test conftest builder.
    from tests.conftest import make_claim, make_plan
    return make_claim("subj", plan=plan)


def test_prior_resolvable_when_plan_present():
    from tests.conftest import make_plan
    assert resolvability_prior(_claim(make_plan(0.01, 0.05))) is Resolvability.RESOLVABLE


def test_prior_unresolvable_when_plan_absent():
    assert resolvability_prior(_claim(None)) is Resolvability.UNRESOLVABLE
```

> Note: `make_claim` and `make_plan` are the existing pure fixtures in `protocol/tests/conftest.py`. If `make_plan`'s signature differs, read the conftest and adjust the call — the only requirement is "a claim with a non-None `evaluation_plan`" vs "a claim with `evaluation_plan=None`".

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && pytest tests/test_calibration_resolvability.py -k prior -v`
Expected: FAIL — `ImportError: cannot import name 'resolvability_prior'`.

- [ ] **Step 3: Implement the prior**

Add to `protocol/src/polymer_protocol/calibration.py` (module level; no new imports needed — it only touches an attribute). Place it near the other pure helpers (e.g. before `_attested_stat`):

```python
def resolvability_prior(claim) -> Resolvability:
    """Structural fallback prior (NOT a definition of resolvability): a recomputable test
    (evaluation_plan present) means a definitive determination is at least possible. An explicit
    operator value always wins over this prior. See spec §1.1 (recomputability ≠ resolvability)."""
    return (Resolvability.RESOLVABLE if claim.evaluation_plan is not None
            else Resolvability.UNRESOLVABLE)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && pytest tests/test_calibration_resolvability.py -k prior -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/calibration.py protocol/tests/test_calibration_resolvability.py
git commit -m "feat(calibration): add resolvability_prior structural fallback"
```

---

### Task 3: `n_resolvable` / `n_unresolvable` on `TierStat`, populated by `_attested_stat`

**Files:**
- Modify: `protocol/src/polymer_protocol/calibration.py` (`TierStat` lines 133-147; `_attested_stat` lines 248-254)
- Test: `protocol/tests/test_calibration_resolvability.py` (extend)

**Interfaces:**
- Produces: two additive fields on `TierStat` — `n_resolvable: int = 0`, `n_unresolvable: int = 0`. `_attested_stat` populates them by counting the `resolvability` of the FAILED+UPHELD attested records it already selects. `q_attested` (`realized_rate`) is unchanged. ATTESTED still never `feeds_headline_q`.

- [ ] **Step 1: Write the failing test**

Append to `protocol/tests/test_calibration_resolvability.py`:

```python
from polymer_protocol.calibration import CalibrationLedger, calibration_summary


def test_attested_stat_counts_resolvability_split_and_q():
    recs = (
        _attested(subject_claim_id="a", verdict=ResolutionVerdict.FAILED,
                  resolvability=Resolvability.RESOLVABLE, source_claim_id="attest-a"),
        _attested(subject_claim_id="b", verdict=ResolutionVerdict.UPHELD,
                  resolvability=Resolvability.RESOLVABLE, source_claim_id="attest-b"),
        _attested(subject_claim_id="c", verdict=ResolutionVerdict.UPHELD,
                  resolvability=Resolvability.UNRESOLVABLE, source_claim_id="attest-c"),
        # an UNRESOLVED record must be EXCLUDED from both q_attested and the resolvability split:
        _attested(subject_claim_id="d", verdict=ResolutionVerdict.UNRESOLVED,
                  resolvability=Resolvability.RESOLVABLE, source_claim_id="attest-d"),
    )
    rep = calibration_summary(CalibrationLedger(records=recs), target_q=0.05)
    at = rep.attested
    assert at.n_total == 3 and at.n_failed == 1   # UNRESOLVED 'd' excluded from the denominator
    assert at.realized_rate == 1 / 3            # q_attested = failed/(failed+upheld), unchanged
    assert at.n_resolvable == 2                 # 'd' NOT counted despite resolvability=RESOLVABLE
    assert at.n_unresolvable == 1
    assert at.n_resolvable + at.n_unresolvable == at.n_total  # split matches the q denominator


def test_attested_never_feeds_headline_q():
    r = _attested(resolvability=Resolvability.RESOLVABLE)
    assert r.feeds_headline_q is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && pytest tests/test_calibration_resolvability.py -k "split or headline" -v`
Expected: FAIL — `AttributeError: 'TierStat' object has no attribute 'n_resolvable'`.

- [ ] **Step 3: Add the `TierStat` fields**

In `TierStat` (calibration.py:133-147), add after `n_superseded`:

```python
    n_resolvable: int = 0       # attested only — resolvability split
    n_unresolvable: int = 0     # attested only
```

- [ ] **Step 4: Populate them in `_attested_stat`**

Replace the `return` in `_attested_stat` (lines 252-254) so the counts are computed from the selected records (`recs` already filters ATTESTED + `stated_q == target_q`):

```python
def _attested_stat(records: tuple[ResolutionRecord, ...], target_q: float) -> TierStat:
    recs = [r for r in records
            if r.resolution_kind == ResolutionKind.ATTESTED and r.stated_q == target_q]
    n_failed = sum(1 for r in recs if r.verdict == ResolutionVerdict.FAILED)
    denom = sum(1 for r in recs if r.verdict in (ResolutionVerdict.FAILED, ResolutionVerdict.UPHELD))
    # resolvability split is counted over the SAME resolved denominator as q_attested
    # (FAILED+UPHELD only) so the two numbers are reconcilable.
    resolved = [r for r in recs
                if r.verdict in (ResolutionVerdict.FAILED, ResolutionVerdict.UPHELD)]
    n_resolvable = sum(1 for r in resolved if r.resolvability == Resolvability.RESOLVABLE)
    n_unresolvable = sum(1 for r in resolved if r.resolvability == Resolvability.UNRESOLVABLE)
    return TierStat(n_total=denom, n_failed=n_failed,
                    realized_rate=(n_failed / denom if denom else None),
                    n_resolvable=n_resolvable, n_unresolvable=n_unresolvable)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd protocol && pytest tests/test_calibration_resolvability.py -v`
Expected: PASS (all in file).

- [ ] **Step 6: Full pure suite + lint**

Run: `cd protocol && pytest tests/ -q && cd .. && ruff check protocol/src/`
Expected: PASS, no lint errors.

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/calibration.py protocol/tests/test_calibration_resolvability.py
git commit -m "feat(calibration): resolvability split counts on attested TierStat"
```

---

### Task 4: Add `EXTERNAL_ATTESTATION` to `GenerationMode`

**Files:**
- Modify: `grammar/src/polymer_grammar/provenance.py` (`GenerationMode` enum, lines 18-23)
- Test: `grammar/tests/test_provenance_external_attestation.py`

**Interfaces:**
- Produces: `GenerationMode.EXTERNAL_ATTESTATION = "external_attestation"` — used by the umbrella ingester (Task 6) to stamp attested-event claims.

- [ ] **Step 1: Write the failing test**

Create `grammar/tests/test_provenance_external_attestation.py`:

```python
from polymer_grammar.provenance import GenerationMode, Provenance


def test_external_attestation_member_exists():
    assert GenerationMode.EXTERNAL_ATTESTATION.value == "external_attestation"


def test_provenance_accepts_external_attestation():
    p = Provenance(generated_by=GenerationMode.EXTERNAL_ATTESTATION,
                   search_cardinality=1, method="doi:10.1056/x")
    assert p.generated_by is GenerationMode.EXTERNAL_ATTESTATION
    assert p.method == "doi:10.1056/x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && pytest tests/test_provenance_external_attestation.py -v`
Expected: FAIL — `AttributeError: EXTERNAL_ATTESTATION`.

- [ ] **Step 3: Add the enum value**

In `grammar/src/polymer_grammar/provenance.py`, add to `GenerationMode` (after `IMPORTED`):

```python
    EXTERNAL_ATTESTATION = "external_attestation"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && pytest tests/test_provenance_external_attestation.py -v`
Expected: PASS.

- [ ] **Step 5: Full grammar suite + commit**

Run: `cd grammar && pytest tests/ -q`
Expected: PASS (additive enum value, no regressions).

```bash
git add grammar/src/polymer_grammar/provenance.py grammar/tests/test_provenance_external_attestation.py
git commit -m "feat(grammar): add EXTERNAL_ATTESTATION GenerationMode"
```

---

### Task 5: Resolutions-file schema + parse/validate

**Files:**
- Create: `src/polymer_claims/attested_ingest.py`
- Test: `tests/test_attested_ingest.py`

**Interfaces:**
- Produces:
  - `class Resolution(BaseModel)` — `extra="forbid"`; fields `subject_claim_id: str`, `verdict: Literal["upheld", "failed"]`, `attestation_ref: str`, `resolvability: Literal["resolvable", "unresolvable"] | None = None`, `observed_at_cycle: int | None = None`, `license_epoch: int = 0`.
  - `parse_resolutions(text: str) -> list[Resolution]` — parse a JSON array; raises `ValueError` on malformed/unknown fields.
  - `validate_against_corpus(res: Resolution, corpus) -> None` — raises `ValueError` if `subject_claim_id` is absent or carries no licensing record (`licensing is None` ⇒ never earned standing). Note: this is a *licensing-record-present* check, the available proxy for earned standing in the current grammar; distinguishing current `Status.LICENSED` from a historical "was licensed at this epoch" check requires the epoch ledger and is deferred (§11).

- [ ] **Step 1: Write the failing test**

Create `tests/test_attested_ingest.py`:

```python
import pytest
from polymer_claims.attested_ingest import (
    Resolution, parse_resolutions, validate_against_corpus,
)


def test_parse_minimal_row():
    text = '[{"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "doi:x"}]'
    rows = parse_resolutions(text)
    assert len(rows) == 1
    r = rows[0]
    assert r.subject_claim_id == "c1" and r.verdict == "failed"
    assert r.resolvability is None and r.license_epoch == 0


def test_parse_rejects_unknown_field():
    text = '[{"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "x", "bogus": 1}]'
    with pytest.raises(ValueError):
        parse_resolutions(text)


def test_parse_rejects_bad_verdict():
    text = '[{"subject_claim_id": "c1", "verdict": "maybe", "attestation_ref": "x"}]'
    with pytest.raises(ValueError):
        parse_resolutions(text)


def test_parse_rejects_negative_epoch():
    text = ('[{"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "x",'
            ' "license_epoch": -1}]')
    with pytest.raises(ValueError):
        parse_resolutions(text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_attested_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError: polymer_claims.attested_ingest`.

- [ ] **Step 3: Create the module with the schema + parser**

Create `src/polymer_claims/attested_ingest.py`:

```python
"""ATTESTED ingestion (the credence layer) — impure umbrella.

Parses an operator/authority resolutions file, builds one defeasible attested-event claim per
row (forced non-LICENSED), and appends an ATTESTED ResolutionRecord linked to it. Calibration is
an instrument, not a gate: this NEVER runs a cycle and NEVER changes any other claim's status.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)  # match the repo's immutable-DTO convention

    subject_claim_id: str
    verdict: Literal["upheld", "failed"]
    attestation_ref: str
    resolvability: Literal["resolvable", "unresolvable"] | None = None
    observed_at_cycle: int | None = Field(default=None, ge=0)  # reject negative operator input
    # license_epoch is RECORDED on the ResolutionRecord, not verified against actual epoch state in
    # this slice (epoch-state validation is deferred — §11). The operator declares which licensing
    # episode they assessed; the ingester trusts the value (but rejects negatives).
    license_epoch: int = Field(default=0, ge=0)


def parse_resolutions(text: str) -> list[Resolution]:
    """Parse a JSON array of resolution objects. Raises ValueError on malformed input."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"resolutions file is not valid JSON: {exc}") from exc
    if not isinstance(raw, list):
        raise ValueError("resolutions file must be a JSON array")
    try:
        return [Resolution.model_validate(row) for row in raw]
    except ValidationError as exc:
        raise ValueError(f"invalid resolution row: {exc}") from exc


def validate_against_corpus(res: Resolution, corpus) -> None:
    """The subject must exist and carry a licensing record (earned standing). Distinguishing a
    *historical* license at this epoch from the current one is deferred (needs the epoch ledger)."""
    claim = corpus.by_id().get(res.subject_claim_id)
    if claim is None:
        raise ValueError(f"subject_claim_id {res.subject_claim_id!r} not in corpus")
    if claim.licensing is None:
        raise ValueError(
            f"subject_claim_id {res.subject_claim_id!r} carries no licensing record "
            "(calibration is about earned standing)"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_attested_ingest.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/attested_ingest.py tests/test_attested_ingest.py
git commit -m "feat(ingest): resolutions-file schema + parse/validate"
```

---

### Task 6: Build the attested-event claim and append it (forced non-LICENSED)

**Files:**
- Modify: `src/polymer_claims/attested_ingest.py`
- Test: `tests/test_attested_ingest.py` (extend)

**Interfaces:**
- Consumes: `Resolution` (Task 5); `canonical_sha256` from `polymer_claims._hashing`; grammar `Claim`, `PropositionLeaf`, `PatternRef`, `Provenance`, `GenerationMode`, `Status`.
- Produces:
  - `attested_event_claim(res: Resolution) -> Claim` — a deterministic, content-addressed CONJECTURED `PropositionLeaf` claim, `licensing=None`, provenance `EXTERNAL_ATTESTATION` with `method=res.attestation_ref`.
  - `inject_attested_event(corpus, claim) -> Corpus` — returns a new corpus with `claim` appended to `claims` via `model_copy` (no cycle run). Idempotent on id collision (skips if id already present).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_attested_ingest.py`:

```python
from polymer_grammar import GenerationMode
from polymer_grammar.claim import Status
from polymer_claims.attested_ingest import attested_event_claim, inject_attested_event


def _res(**kw):
    base = dict(subject_claim_id="c1", verdict="failed", attestation_ref="doi:10.1056/x")
    base.update(kw)
    return Resolution(**base)


def test_attested_event_claim_is_conjectured_and_unlicensed():
    c = attested_event_claim(_res())
    assert c.status == Status.CONJECTURED
    assert c.licensing is None
    assert c.provenance.generated_by is GenerationMode.EXTERNAL_ATTESTATION
    assert c.provenance.method == "doi:10.1056/x"
    assert "c1" in c.leaves[0].data and "failed" in c.leaves[0].data


def test_attested_event_claim_id_is_deterministic():
    assert attested_event_claim(_res()).id == attested_event_claim(_res()).id
    assert attested_event_claim(_res()).id != attested_event_claim(_res(verdict="upheld")).id


def test_inject_appends_without_relicensing(licensing_corpus_fixture):
    corpus = licensing_corpus_fixture            # a corpus with >=1 LICENSED claim
    before = {c.id: c.status for c in corpus.claims}
    c = attested_event_claim(_res())
    out = inject_attested_event(corpus, c)
    assert c.id in out.by_id()
    assert out.by_id()[c.id].licensing is None        # forced non-LICENSED
    # no other claim's status changed (instrument, not a gate)
    assert {k: out.by_id()[k].status for k in before} == before
    assert len(out.claims) == len(corpus.claims) + 1
```

Add a fixture at the top of `tests/test_attested_ingest.py` that builds a corpus with one LICENSED claim. Reuse the umbrella attestation fixtures confirmed to exist:

```python
import pytest
from tests.attestation._fixtures import licensed_claim, licensing, corpus_with


@pytest.fixture
def licensing_corpus_fixture():
    return corpus_with(licensed_claim("c1", licensing()))
```

> If `tests/attestation/_fixtures.py` import path differs at execution time, read it and adjust — the only requirement is "a `Corpus` containing a claim with id `c1` whose `licensing is not None`."

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_attested_ingest.py -k "event_claim or inject" -v`
Expected: FAIL — `ImportError: cannot import name 'attested_event_claim'`.

- [ ] **Step 3: Implement claim build + inject**

Add to `src/polymer_claims/attested_ingest.py`. Add imports at top:

```python
from polymer_grammar import GenerationMode, Provenance
from polymer_grammar.claim import Claim, Status
from polymer_grammar.leaf import PropositionLeaf
from polymer_grammar.pattern import PatternRef

from ._hashing import canonical_sha256

_ATTEST_PATTERN = PatternRef(id="external-attestation", version="v1")
```

Then the functions:

```python
def attested_event_claim(res: Resolution) -> Claim:
    """A defeasible-CAPABLE corpus claim asserting an external authority's determination. CONJECTURED
    and licensing=None => non-LICENSED by construction (the gate never licenses a conjecture, and we
    never call verify on it). It is corpus content that CAN be attacked through the defeat graph, but
    this slice does NOT auto-wire defeat edges between contradictory attestations (deferred — §11).
    Content-addressed id for determinism + idempotency."""
    digest = canonical_sha256({
        "subject": res.subject_claim_id,
        "verdict": res.verdict,
        "ref": res.attestation_ref,
        "epoch": res.license_epoch,
    }).split(":", 1)[1][:16]
    cid = f"attest-{digest}"
    data = (f"external authority {res.attestation_ref} determined that LICENSED claim "
            f"{res.subject_claim_id} is {res.verdict}")
    return Claim(
        id=cid,
        title=f"Attestation: {res.subject_claim_id} {res.verdict}",
        pattern=_ATTEST_PATTERN,
        leaves=(PropositionLeaf(
            data=data,
            warrant="external authority testimony (defeasible, not an oracle)",
            warrant_type="expert_judgment",
        ),),
        status=Status.CONJECTURED,
        provenance=Provenance(
            generated_by=GenerationMode.EXTERNAL_ATTESTATION,
            method=res.attestation_ref,
            search_cardinality=1,
        ),
    )


def inject_attested_event(corpus, claim: Claim):
    """Append the attested-event claim to corpus.claims (no cycle run; no other claim touched).
    Idempotent: if the content-addressed id is already present, return the corpus unchanged."""
    if claim.id in corpus.by_id():
        return corpus
    return corpus.model_copy(update={"claims": (*corpus.claims, claim)})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_attested_ingest.py -v`
Expected: PASS.

> If `Claim` construction raises a validation error (e.g. `PropositionLeaf` needs another required field, or `Status.CONJECTURED` has a coupled constraint), read the error and the grammar file it points at, then satisfy the minimal requirement. The shape above matches the confirmed `PropositionLeaf(data, warrant, warrant_type)` and `Claim(id, title, pattern, leaves, status, provenance)` signatures; `_referential_integrity` does NOT validate `PatternRef` against a registry, so the sentinel pattern is safe.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/attested_ingest.py tests/test_attested_ingest.py
git commit -m "feat(ingest): build + inject defeasible attested-event claim (non-LICENSED)"
```

---

### Task 7: Build the ATTESTED `ResolutionRecord`, fix the ledger fold identity, and append

**Files:**
- Modify: `src/polymer_claims/attested_ingest.py`
- Modify: `src/polymer_claims/calibration_store.py` (`load_ledger` fold key — see Steps 6-7)
- Test: `tests/test_attested_ingest.py` (extend)

**Interfaces:**
- Consumes: `Resolution`; `attested_event_claim`; protocol `ResolutionRecord`, `ResolutionKind`, `CalibrationTarget`, `ResolutionVerdict`, `Resolvability`, `resolvability_prior`; umbrella `append_records` from `calibration_store`.
- Produces:
  - `build_attested_record(res, subject_claim, event_claim, *, stated_q) -> ResolutionRecord` — ATTESTED record; `calibration_target=EXTERNAL_DISAGREEMENT`; `verdict` mapped from `res.verdict`; `source_claim_id=event_claim.id`; `resolvability` = operator value if present, else `resolvability_prior(subject_claim)`; `observed_at_cycle = res.observed_at_cycle or 0`.
  - `ingest(corpus, resolutions: list[Resolution], ledger_path) -> Corpus` — orchestrates per row: validate, build+inject event claim, build record, append to ledger; returns the updated corpus.
  - A revised `load_ledger` fold key: ATTESTED records key on `(subject_claim_id, license_epoch, "attested", source_claim_id)`; DEFINITIONAL/ANCHORED keep `(subject_claim_id, license_epoch)` exactly as before.

**Why the fold-key change (audit High #1):** today `load_ledger` folds *all* records on `(subject_claim_id, license_epoch)` with latest-line-wins. Two sources attesting the **same** claim/epoch would collapse to one record, silently breaking `q_attested` as an event-level disagreement rate. Keying ATTESTED on its content-addressed `source_claim_id` lets distinct determinations coexist, while re-ingesting the *same* determination (same `source_claim_id`) folds to one — making ingestion idempotent at the folded-count level (audit Medium #7). DEFINITIONAL/ANCHORED behavior is untouched.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_attested_ingest.py`:

```python
from polymer_protocol.calibration import (
    ResolutionKind, CalibrationTarget, ResolutionVerdict, Resolvability,
)
from polymer_claims.calibration_store import load_ledger   # load_ledger lives in the umbrella store
from polymer_claims.attested_ingest import build_attested_record, ingest


def test_record_links_event_claim_and_maps_verdict(licensing_corpus_fixture):
    corpus = licensing_corpus_fixture
    subject = corpus.by_id()["c1"]
    res = _res(verdict="failed")
    event = attested_event_claim(res)
    rec = build_attested_record(res, subject, event, stated_q=corpus.fdr_ledger.target_fdr)
    assert rec.resolution_kind == ResolutionKind.ATTESTED
    assert rec.calibration_target == CalibrationTarget.EXTERNAL_DISAGREEMENT
    assert rec.verdict == ResolutionVerdict.FAILED
    assert rec.source_claim_id == event.id
    assert rec.attestation_ref == "doi:10.1056/x"
    assert rec.feeds_headline_q is False


def test_resolvability_override_beats_prior(licensing_corpus_fixture):
    corpus = licensing_corpus_fixture
    subject = corpus.by_id()["c1"]                       # LICENSED claim, plan may be None
    res = _res(resolvability="resolvable")
    rec = build_attested_record(res, subject, attested_event_claim(res),
                                stated_q=corpus.fdr_ledger.target_fdr)
    assert rec.resolvability is Resolvability.RESOLVABLE  # operator wins regardless of prior


def test_ingest_appends_to_ledger_and_corpus(licensing_corpus_fixture, tmp_path):
    corpus = licensing_corpus_fixture
    ledger_path = tmp_path / "calib.jsonl"
    out = ingest(corpus, [_res()], ledger_path)
    # event claim now in corpus
    assert any(c.id.startswith("attest-") for c in out.claims)
    # one ATTESTED record in the ledger, linked to the event claim
    led = load_ledger(ledger_path)
    assert len(led.records) == 1
    rec = led.records[0]
    assert rec.resolution_kind == ResolutionKind.ATTESTED
    assert rec.source_claim_id in out.by_id()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_attested_ingest.py -k "record or ingest or override" -v`
Expected: FAIL — `ImportError: cannot import name 'build_attested_record'`.

- [ ] **Step 3: Implement record build + orchestration**

Add imports to `src/polymer_claims/attested_ingest.py`:

```python
from polymer_protocol.calibration import (
    CalibrationTarget, Resolvability, ResolutionKind, ResolutionRecord, ResolutionVerdict,
    resolvability_prior,
)

from .calibration_store import append_records

_VERDICT = {"upheld": ResolutionVerdict.UPHELD, "failed": ResolutionVerdict.FAILED}
```

Then:

```python
def build_attested_record(res: Resolution, subject_claim, event_claim, *, stated_q: float
                          ) -> ResolutionRecord:
    """ATTESTED record. Resolvability is operator value if declared, else the structural prior
    over the SUBJECT claim (never the event claim). observed_at_cycle defaults to 0 (richer
    cycle resolution is deferred — spec §11)."""
    if res.resolvability is not None:
        resolvability = Resolvability(res.resolvability)
    else:
        resolvability = resolvability_prior(subject_claim)
    return ResolutionRecord(
        subject_claim_id=res.subject_claim_id,
        license_epoch=res.license_epoch,
        resolution_kind=ResolutionKind.ATTESTED,
        calibration_target=CalibrationTarget.EXTERNAL_DISAGREEMENT,
        verdict=_VERDICT[res.verdict],
        stated_q=stated_q,
        observed_at_cycle=res.observed_at_cycle or 0,
        attestation_ref=res.attestation_ref,
        source_claim_id=event_claim.id,
        resolvability=resolvability,
    )


def ingest(corpus, resolutions: list[Resolution], ledger_path):
    """Per row: validate, build + inject the event claim, build the ATTESTED record, append to the
    ledger. Returns the updated corpus. Deterministic; no cycle run; no network."""
    stated_q = corpus.fdr_ledger.target_fdr
    records = []
    for res in resolutions:
        validate_against_corpus(res, corpus)
        subject = corpus.by_id()[res.subject_claim_id]
        event = attested_event_claim(res)
        corpus = inject_attested_event(corpus, event)
        records.append(build_attested_record(res, subject, event, stated_q=stated_q))
    if records:
        append_records(ledger_path, records)
    return corpus
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_attested_ingest.py -v`
Expected: PASS (all in file — single-attestation path works).

- [ ] **Step 5: Write the failing multi-source + idempotency tests (the fold-key bug)**

Append to `tests/test_attested_ingest.py`:

```python
def test_two_sources_same_claim_both_survive(licensing_corpus_fixture, tmp_path):
    corpus = licensing_corpus_fixture
    ledger_path = tmp_path / "calib.jsonl"
    # two DIFFERENT external sources assess the same claim/epoch -> two distinct events
    rows = [
        _res(attestation_ref="doi:source-A", verdict="failed"),
        _res(attestation_ref="doi:source-B", verdict="upheld"),
    ]
    ingest(corpus, rows, ledger_path)
    led = load_ledger(ledger_path)
    assert len(led.records) == 2                       # neither folds away
    assert len({r.source_claim_id for r in led.records}) == 2


def test_reingest_same_resolution_is_idempotent(licensing_corpus_fixture, tmp_path):
    corpus = licensing_corpus_fixture
    ledger_path = tmp_path / "calib.jsonl"
    out1 = ingest(corpus, [_res()], ledger_path)
    ingest(out1, [_res()], ledger_path)                # run again, same determination
    led = load_ledger(ledger_path)
    assert len(led.records) == 1                       # content-addressed id folds to one
```

- [ ] **Step 6: Run to verify the multi-source test fails**

Run: `pytest tests/test_attested_ingest.py -k "two_sources or idempotent" -v`
Expected: `test_two_sources_same_claim_both_survive` FAILS (`len == 1`, not 2) — the current `(subject_claim_id, license_epoch)` fold collapses both attestations.

- [ ] **Step 7: Fix the ATTESTED fold identity in `load_ledger`**

In `src/polymer_claims/calibration_store.py`, add a small key helper above `load_ledger` and use it. Import `ResolutionKind` (the module already imports `ResolutionRecord` from the same place):

```python
from polymer_protocol.calibration import ResolutionKind  # add to the existing import


def _fold_key(r: ResolutionRecord):
    # ATTESTED is an event-level tier: distinct external determinations on the same claim/epoch
    # must coexist, keyed by a per-event discriminator. This ingester always sets source_claim_id,
    # but the pure model keeps it optional (set iff the event is a corpus claim), so fall back to
    # attestation_ref for source-less records. DEFINITIONAL/ANCHORED keep the original
    # (subject_claim_id, license_epoch) identity (latest verdict wins).
    if r.resolution_kind == ResolutionKind.ATTESTED:
        discriminator = r.source_claim_id or r.attestation_ref
        return (r.subject_claim_id, r.license_epoch, "attested", discriminator)
    return (r.subject_claim_id, r.license_epoch)
```

> Edge case: if a manually-authored ATTESTED record has **both** `source_claim_id` and `attestation_ref` as `None`, its discriminator is `None` and such records still fold together for that claim/epoch — acceptable, since source-less attestations carry no event identity to tell them apart. This ingester always sets both, so it never hits that path.

Then in `load_ledger`, change the fold to use it. The `latest`/`order` dicts become keyed by the helper's return value (a tuple of varying arity — fine as a dict key):

```python
    latest: dict[tuple, ResolutionRecord] = {}
    order: list[tuple] = []
    if path.is_file():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = ResolutionRecord.model_validate_json(line)
            key = _fold_key(r)
            if key not in latest:
                order.append(key)
            latest[key] = r  # latest event wins
```

- [ ] **Step 8: Run to verify all ingest tests pass**

Run: `pytest tests/test_attested_ingest.py -v`
Expected: PASS (multi-source → 2 records; re-ingest → 1 record).

- [ ] **Step 9: Guard existing ledger behavior (no regression)**

Run: `cd protocol && pytest tests/ -q && cd .. && pytest tests/ -q -k calibration`
Expected: PASS — DEFINITIONAL/ANCHORED folding unchanged (their key is still the 2-tuple).

- [ ] **Step 10: Lint + commit**

Run: `ruff check src/polymer_claims/attested_ingest.py src/polymer_claims/calibration_store.py`

```bash
git add src/polymer_claims/attested_ingest.py src/polymer_claims/calibration_store.py tests/test_attested_ingest.py
git commit -m "feat(ingest): ATTESTED record + event-level ledger fold identity (idempotent)"
```

---

### Task 8: `ingest-attested` CLI subcommand

**Files:**
- Modify: `src/polymer_claims/cli.py` (`_build_parser` ~lines 482-621; add a handler near the other `_cmd_*` functions)
- Test: `tests/test_cli_ingest_attested.py`

**Interfaces:**
- Consumes: `parse_resolutions`, `ingest` (Task 5/7); the module's existing `load_corpus` / `dump_corpus` / `_write_or_print` IO helpers.
- Produces: CLI `polymer-claims ingest-attested --corpus PATH --resolutions FILE --calibration LEDGER [--out CORPUS]`. Writes the updated corpus to `--out` (else stdout). Returns 0 on success, 1 on validation error.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli_ingest_attested.py`:

```python
import json
from polymer_claims.cli import main
from tests.attestation._fixtures import licensed_claim, licensing, corpus_with


def _write_corpus(tmp_path):
    corpus = corpus_with(licensed_claim("c1", licensing()))
    p = tmp_path / "corpus.json"
    p.write_text(corpus.model_dump_json())
    return p


def test_ingest_attested_smoke(tmp_path, capsys):
    corpus_path = _write_corpus(tmp_path)
    res_path = tmp_path / "res.json"
    res_path.write_text(json.dumps([
        {"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "doi:10.1056/x"}
    ]))
    ledger = tmp_path / "calib.jsonl"
    out = tmp_path / "out.json"
    rc = main(["ingest-attested", "--corpus", str(corpus_path),
               "--resolutions", str(res_path), "--calibration", str(ledger),
               "--out", str(out)])
    assert rc == 0
    assert ledger.exists() and out.exists()
    data = json.loads(out.read_text())
    assert any(c["id"].startswith("attest-") for c in data["claims"])


def test_ingest_attested_unknown_subject_errors(tmp_path, capsys):
    corpus_path = _write_corpus(tmp_path)
    res_path = tmp_path / "res.json"
    res_path.write_text(json.dumps([
        {"subject_claim_id": "nope", "verdict": "failed", "attestation_ref": "x"}
    ]))
    rc = main(["ingest-attested", "--corpus", str(corpus_path),
               "--resolutions", str(res_path), "--calibration", str(tmp_path / "c.jsonl")])
    assert rc == 1
    assert "nope" in capsys.readouterr().err
```

> The fixture only needs the corpus to round-trip through `model_dump_json` (written to disk) and back via the handler's `load_corpus`; the test itself never references `Corpus` directly.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_ingest_attested.py -v`
Expected: FAIL — argparse error: invalid choice `ingest-attested`.

- [ ] **Step 3: Add the handler**

In `src/polymer_claims/cli.py`, add near the other `_cmd_*` functions:

```python
def _cmd_ingest_attested(args: argparse.Namespace) -> int:
    from .attested_ingest import ingest, parse_resolutions

    corpus = load_corpus(args.corpus)               # reuse the module's IO helpers (cli.py:42)
    try:
        resolutions = parse_resolutions(Path(args.resolutions).read_text())
        out_corpus = ingest(corpus, resolutions, args.calibration)
    except ValueError as exc:
        print(f"ingest-attested failed: {exc}", file=sys.stderr)
        return 1
    _write_or_print(dump_corpus(out_corpus), args.out)
    print(f"ingested {len(resolutions)} attestation(s)", file=sys.stderr)
    return 0
```

> `load_corpus`, `dump_corpus`, and `_write_or_print` are already imported/defined in `cli.py` (see `_cmd_run_cycle`). The resolutions file is read directly with `Path(...).read_text()` since it is not a corpus.

- [ ] **Step 4: Register the subcommand**

In `_build_parser`, after an existing `sub.add_parser(...)` block:

```python
    p_ing = sub.add_parser("ingest-attested",
                           help="ingest external determinations as ATTESTED calibration records")
    p_ing.add_argument("--corpus", required=True, help="path to the corpus JSON")
    p_ing.add_argument("--resolutions", required=True, help="path to the resolutions JSON array")
    p_ing.add_argument("--calibration", required=True, help="path to the calibration JSONL ledger")
    p_ing.add_argument("--out", help="write updated corpus here (default: stdout)")
    p_ing.set_defaults(func=_cmd_ingest_attested)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_cli_ingest_attested.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/cli.py tests/test_cli_ingest_attested.py
git commit -m "feat(cli): ingest-attested subcommand"
```

---

### Task 9: Certificate render — `q_attested` + resolvability split + disclosure

**Files:**
- Modify: `src/polymer_claims/attestation.py` (`render_certificate_text`, the ATTESTED line ~579)
- Test: `tests/test_attested_certificate.py`

**Interfaces:**
- Consumes: a `CalibrationReport` with a populated `attested` `TierStat` (Task 3).
- Produces: the ATTESTED certificate line now shows `q_attested` (`realized_rate`), the `N resolvable / N unresolvable` split, and a disclosure that ATTESTED is external testimony recorded as defeasible claims — never truth, never headline. Headline `q` untouched.

- [ ] **Step 1: Write the failing test**

Create `tests/test_attested_certificate.py`:

```python
from polymer_protocol.calibration import (
    ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict, Resolvability,
    CalibrationLedger,
)
from polymer_claims.attestation import build_certificate, render_certificate_text
from tests.attestation._fixtures import licensed_claim, licensing, corpus_with


def _attested(cid, verdict, resolvability):
    return ResolutionRecord(
        subject_claim_id=cid, license_epoch=0, resolution_kind=ResolutionKind.ATTESTED,
        calibration_target=CalibrationTarget.EXTERNAL_DISAGREEMENT, verdict=verdict,
        stated_q=0.05, observed_at_cycle=0, attestation_ref=f"doi:{cid}",
        source_claim_id=f"attest-{cid}", resolvability=resolvability,
    )


def test_certificate_shows_q_attested_and_resolvability_split():
    # render_certificate_text takes a Certificate; build one via build_certificate, which attaches
    # calibration_summary(ledger, target_q). Attested tier is corpus-level field calibration, so the
    # records' subjects need not be the certified claim.
    corpus = corpus_with(licensed_claim("c1", licensing()))
    led = CalibrationLedger(records=(
        _attested("a", ResolutionVerdict.FAILED, Resolvability.RESOLVABLE),
        _attested("b", ResolutionVerdict.UPHELD, Resolvability.UNRESOLVABLE),
    ))
    cert = build_certificate(corpus, "c1", ledger=led, target_q=0.05)
    text = render_certificate_text(cert)
    assert "q_attested" in text
    assert "0.500" in text                      # 1 failed / 2 (failed+upheld)
    assert "1 resolvable" in text and "1 unresolvable" in text
    assert "never" in text.lower()              # disclosure present


def test_certificate_zero_attested_is_byte_identical():
    corpus = corpus_with(licensed_claim("c1", licensing()))
    cert = build_certificate(corpus, "c1", ledger=CalibrationLedger(records=()), target_q=0.05)
    text = render_certificate_text(cert)
    assert "  ATTESTED: 0 attested events" in text   # unchanged from the pre-slice render
    assert "q_attested" not in text                  # richer line only appears when n_total > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_attested_certificate.py -v`
Expected: `test_certificate_shows_q_attested_and_resolvability_split` FAILS — the current line prints only `ATTESTED: N attested events` (no `q_attested`, no split). `test_certificate_zero_attested_is_byte_identical` already PASSES (it's a regression guard for the unchanged zero output).

- [ ] **Step 3: Replace the ATTESTED render line**

In `src/polymer_claims/attestation.py`, replace the single line `lines.append(f"  ATTESTED: {rep.attested.n_total} attested events")` (~line 579) with:

```python
    at = rep.attested
    if at.n_total:
        lines.append(
            f"  ATTESTED: {at.n_total} external determinations; {at.n_failed} disagreed"
            f" -> q_attested {at.realized_rate:.3f}"
            f" ({at.n_resolvable} resolvable / {at.n_unresolvable} unresolvable)"
        )
        lines.append(
            "            (external testimony recorded as defeasible corpus claims —"
            " never truth, never the headline q)"
        )
    else:
        # byte-identical to the pre-slice zero output (honors the "additive when unused" invariant)
        lines.append(f"  ATTESTED: {at.n_total} attested events")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_attested_certificate.py -v`
Expected: PASS.

- [ ] **Step 5: Full umbrella suite + lint**

Run: `pytest tests/ -q && ruff check src/`
Expected: PASS, no lint errors.

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/attestation.py tests/test_attested_certificate.py
git commit -m "feat(certificate): render q_attested + resolvability split + disclosure"
```

---

## Final Verification

- [ ] **Full suite, all three packages:**

```bash
cd protocol && pytest tests/ -q && cd ../grammar && pytest tests/ -q && cd .. && pytest tests/ -q
```
Expected: all green.

- [ ] **Lint:** `ruff check src/ protocol/src/ grammar/src/` → clean.

- [ ] **Byte-identical-when-unused invariant:** render a certificate for a ledger with **no** ATTESTED records and confirm the ATTESTED line reads exactly `  ATTESTED: 0 attested events` (byte-identical to the pre-slice render — covered by `test_certificate_zero_attested_is_byte_identical`) and the headline `q` is unchanged from before this slice.

- [ ] **Anti-laundering spot check:** confirm no ATTESTED record returns `feeds_headline_q is True` (covered by Task 3 test) and the certificate's headline `q` line draws only from `rep.definitional`.

---

## Self-Review Notes (planner)

- **Spec coverage:** §1.1 resolvability prior → Task 2; §6 pure model changes → Tasks 1-3; §5 attested-as-corpus-claim (non-LICENSED) → Tasks 4, 6; §4 resolutions file → Task 5; §7 CLI → Task 8; §8 certificate → Task 9. §10 invariants → Final Verification.
- **Resolved open detail (§5):** the attested-event claim is a CONJECTURED `PropositionLeaf` appended directly to `corpus.claims` (no `run_cycle`), non-LICENSED by construction. This honors "forced non-LICENSED" and the §10 "instrument not a gate" invariant more faithfully than routing through `compile_untrusted` (which re-stamps provenance to `AGENT_GENERATED` and whose forged-licensing guard is moot since the claim is built from a licensing-free resolution row). Origin recorded via new `GenerationMode.EXTERNAL_ATTESTATION` (Task 4). **Both decisions confirmed with the operator.**
- **Deferred (not in this slice, per §11):** proper scoring (resolvable), surrogate/peer-prediction (unresolvable), live feeds, markets, TSV adapter, richer `observed_at_cycle`/epoch resolution (this slice defaults `observed_at_cycle` to 0), auto-wiring defeat edges between contradictory attestations, and the current-vs-historical "was-ever-LICENSED" distinction.

## Audit Resolutions (applied 2026-06-23)

An itemized review surfaced 10 issues; all verified against the real code and applied here:

- **High #1 — ledger fold erases multi-source attestations:** fixed in Task 7 (Steps 5-9) — `load_ledger` now keys ATTESTED on `(subject_claim_id, license_epoch, "attested", source_claim_id)`; DEFINITIONAL/ANCHORED unchanged.
- **High #2 — byte-identical contradiction:** Task 9 `else` branch preserves `  ATTESTED: 0 attested events` exactly; the invariant text now states this and a guard test (`test_certificate_zero_attested_is_byte_identical`) enforces it.
- **High #3 — `load_ledger` import:** Task 7 test imports it from `polymer_claims.calibration_store` (verified location).
- **High #4 — wrong certificate API:** Task 9 test builds a real `Certificate` via `build_certificate(corpus, "c1", ledger=..., target_q=...)` and renders that.
- **Medium #5 — "defeasible" overstated:** reworded to "defeasible-CAPABLE corpus content"; auto-wiring defeat edges is deferred.
- **Medium #6 — "was ever LICENSED" unvalidated:** prose now matches the actual `licensing is None` check (licensing-record-present proxy); historical-epoch check deferred.
- **Medium #7 — ledger idempotency:** content-addressed `source_claim_id` in the fold key makes re-ingest fold to one record (Task 7 Step 5 test).
- **Medium #8 — resolvability denominator mismatch:** Task 3 counts the split over the FAILED+UPHELD `resolved` subset; test asserts `n_resolvable + n_unresolvable == n_total` and excludes an UNRESOLVED record.
- **Low #9 — `_Model`/frozen convention:** `Resolution` now sets `ConfigDict(extra="forbid", frozen=True)`.
- **Low #10 — bad `Corpus` import in CLI test:** fixed to `polymer_protocol.corpus`.

**Second pass (cleanup):**

- **Med #1 — fold key vs optional `source_claim_id`:** `_fold_key` now falls back to `attestation_ref` when `source_claim_id` is `None` (umbrella-only; the pure model keeps the field optional per spec §0).
- **Med #2 — `license_epoch` recorded not verified:** documented in the `Resolution` schema; epoch-state validation deferred (§11).
- **Low #3 — id determinism prose:** global constraint now reads `subject+verdict+ref+license_epoch` to match the implementation.
- **Low #4 — `_Model` convention vs `Resolution(BaseModel)`:** tech-stack sentence now allows "an equivalent frozen `ConfigDict` on umbrella DTOs."
- **Low #5 — CLI IO helpers:** handler now uses `load_corpus` / `dump_corpus` / `_write_or_print` like the other subcommands.

**Third pass (polish):**

- **Low #1 — stale Task 8 interface line:** now states the CLI consumes the existing `load_corpus`/`dump_corpus`/`_write_or_print` helpers.
- **Low #2 — unused `Corpus` import in CLI test:** removed.
- **Low #3 — byte-identity scope:** invariant now clarifies it covers the human **text** zero-ATTESTED render, not JSON dumps (the additive `TierStat` count fields default to `0`, a one-time additive schema change).
- **Low #4 — unconstrained numeric input:** `observed_at_cycle` and `license_epoch` now use `Field(ge=0)`; a parse test rejects a negative epoch.
