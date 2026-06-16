# #5a DRIFT daemon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pure, caller-scheduled DRIFT daemon that flags LICENSED claims whose minted materialization no longer matches the current context, plus a separate opt-in action that re-opens flagged claims to PENDING under a new `MATERIALIZATION_DRIFTED` reason.

**Architecture:** One additive grammar enum member, then a self-contained protocol module `drift.py` with two pure functions: `drift_pass` (flag-only detection — returns the corpus identity-unchanged + a `DriftRecord`) and `reopen_drifted` (the separate opt-in mutation that consumes a `DriftRecord`). No `run_cycle` wiring this slice; daemon state lives in the returned record, never in the 4-collection Corpus.

**Tech Stack:** Python 3.14, Pydantic v2 (frozen `_Model`, tuples), `uv`, pytest, ruff. Two packages: `grammar/` (`polymer_grammar`) and `protocol/` (`polymer_protocol`, one-way dep on grammar).

**Spec:** `docs/superpowers/specs/2026-06-04-drift-daemon-design.md`

---

## File Structure

- `grammar/src/polymer_grammar/status.py` — **modify**: add `PendingReason.MATERIALIZATION_DRIFTED`.
- `grammar/tests/test_status.py` — **modify**: enum count 9→10 + new-value check + claim-construction check.
- `protocol/src/polymer_protocol/drift.py` — **create**: `DriftFinding`, `DriftRecord`, `drift_pass`, `reopen_drifted`.
- `protocol/tests/test_drift.py` — **create**: detection + re-open tests.
- `protocol/src/polymer_protocol/__init__.py` — **modify**: export the four new names.

Conventions to follow (already established): all models subclass `_Model` (frozen, `extra="forbid"`, tuple fields). `model_copy(update=...)` is used deliberately for status changes (it bypasses validators — we set all interdependent fields in one call so the result is a valid state, and a test re-validates it). Tests use `protocol/tests/conftest.py` helpers `make_claim`, `make_plan` and the `empty_ledger` fixture.

---

### Task 1: Grammar — add the `MATERIALIZATION_DRIFTED` PendingReason

**Files:**
- Modify: `grammar/src/polymer_grammar/status.py`
- Test: `grammar/tests/test_status.py`

- [ ] **Step 1: Update the failing enum-count test and add the new assertions**

In `grammar/tests/test_status.py`, replace the body of `test_pending_reasons_include_governance_and_incomparable` and add a claim-construction test:

```python
def test_pending_reasons_include_governance_and_incomparable():
    vals = {r.value for r in PendingReason}
    assert "unreproducible_by_governance" in vals
    assert "strength_incomparable" in vals
    assert "duhem_underdetermined" in vals
    assert "materialization_drifted" in vals
    assert len(vals) == 10


def test_materialization_drifted_reason_carried_on_a_pending_claim():
    from polymer_grammar import CategoricalLeaf, Claim, PatternRef

    claim = Claim(
        id="c",
        title="c",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="t"),),
        status=Status.PENDING,
        pending_reason=PendingReason.MATERIALIZATION_DRIFTED,
    )
    assert claim.pending_reason is PendingReason.MATERIALIZATION_DRIFTED
    assert claim.pending_reason.value == "materialization_drifted"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd grammar && uv run pytest tests/test_status.py -q`
Expected: FAIL — `test_pending_reasons_include_governance_and_incomparable` fails the `len(vals) == 10` assertion (currently 9), and `test_materialization_drifted_reason_carried_on_a_pending_claim` fails with `AttributeError: MATERIALIZATION_DRIFTED`.

- [ ] **Step 3: Add the enum member**

In `grammar/src/polymer_grammar/status.py`, add the new member as the last entry of `PendingReason`:

```python
class PendingReason(str, Enum):
    UNTESTED = "untested"
    UNDERPOWERED = "underpowered"
    EXPLORATORY_BY_DESIGN = "exploratory_by_design"
    CONTESTED = "contested"
    DUHEM_UNDERDETERMINED = "duhem_underdetermined"
    DEFINITIONAL_COMMITMENT_CONTESTED = "definitional_commitment_contested"
    ONTOLOGY_TERM_OBSOLETE = "ontology_term_obsolete"
    STRENGTH_INCOMPARABLE = "strength_incomparable"
    UNREPRODUCIBLE_BY_GOVERNANCE = "unreproducible_by_governance"
    MATERIALIZATION_DRIFTED = "materialization_drifted"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd grammar && uv run pytest tests/test_status.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full grammar suite + ruff (no regressions)**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: all green, ruff clean. (`PendingReason` is already re-exported from `polymer_grammar`, so no `__init__` change.)

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/status.py grammar/tests/test_status.py
git commit -m "feat(grammar): add MATERIALIZATION_DRIFTED pending reason for #5a DRIFT

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Protocol — `drift.py` records + `drift_pass` (flag-only detection)

**Files:**
- Create: `protocol/src/polymer_protocol/drift.py`
- Test: `protocol/tests/test_drift.py`

- [ ] **Step 1: Write the failing detection tests**

Create `protocol/tests/test_drift.py`:

```python
from __future__ import annotations

from polymer_grammar import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
    Status,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.drift import drift_pass
from tests.conftest import make_claim, make_plan


def _mat(mid: str, api: str, data: str) -> MaterializationContext:
    return MaterializationContext(id=mid, api_version=api, data_version=data)


def _lic(*mats: MaterializationContext) -> Licensing:
    """A valid Licensing record over the given materializations (all SATISFIED)."""
    sats = tuple(
        Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=m) for m in mats
    )
    route = LicenseRoute.REPLICATION if len({m.id for m in mats}) >= 2 else LicenseRoute.SEVERE_TEST
    return Licensing(
        route=route,
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
        rivals_considered=(),
        satisfactions=sats,
    )


def _corpus(empty_ledger, *claims) -> Corpus:
    return Corpus(claims=tuple(claims), fdr_ledger=empty_ledger)


_CURRENT = _mat("now", "v1", "d1")


def test_stale_licensed_claim_is_flagged(empty_ledger):
    c = make_claim("c", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    corpus = _corpus(empty_ledger, c)
    out, rec = drift_pass(corpus, current=_CURRENT)
    assert [f.claim_id for f in rec.drifted] == ["c"]
    assert rec.examined == 1
    assert rec.drifted[0].licensed_versions == (("v0", "d0"),)


def test_fresh_licensed_claim_is_not_flagged(empty_ledger):
    c = make_claim("c", Status.LICENSED, licensing=_lic(_mat("M1", "v1", "d1")))
    out, rec = drift_pass(_corpus(empty_ledger, c), current=_CURRENT)
    assert rec.drifted == ()
    assert rec.examined == 1


def test_replication_fresh_if_any_satisfaction_matches(empty_ledger):
    # M_old is stale but M_now matches current -> fresh (any-match rule)
    c = make_claim(
        "c", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0"), _mat("M1", "v1", "d1"))
    )
    out, rec = drift_pass(_corpus(empty_ledger, c), current=_CURRENT)
    assert rec.drifted == ()


def test_replication_drifted_if_no_satisfaction_matches(empty_ledger):
    c = make_claim(
        "c", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0"), _mat("M9", "v9", "d9"))
    )
    out, rec = drift_pass(_corpus(empty_ledger, c), current=_CURRENT)
    assert [f.claim_id for f in rec.drifted] == ["c"]
    assert rec.drifted[0].licensed_versions == (("v0", "d0"), ("v9", "d9"))


def test_non_licensed_claims_are_never_scanned(empty_ledger):
    a = make_claim("a", Status.CONJECTURED)
    b = make_claim("b", Status.PENDING)
    c = make_claim("c", Status.REJECTED)
    out, rec = drift_pass(_corpus(empty_ledger, a, b, c), current=_CURRENT)
    assert rec.examined == 0
    assert rec.drifted == ()


def test_re_executable_reflects_evaluation_plan(empty_ledger):
    planned = make_claim(
        "p", Status.LICENSED, plan=make_plan(0.01, 0.05), licensing=_lic(_mat("M0", "v0", "d0"))
    )
    planless = make_claim("q", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    out, rec = drift_pass(_corpus(empty_ledger, planned, planless), current=_CURRENT)
    by_id = {f.claim_id: f.re_executable for f in rec.drifted}
    assert by_id == {"p": True, "q": False}


def test_returned_corpus_is_the_same_object(empty_ledger):
    c = make_claim("c", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    corpus = _corpus(empty_ledger, c)
    out, rec = drift_pass(corpus, current=_CURRENT)
    assert out is corpus  # flag-only: never mutates the corpus


def test_licensed_without_licensing_block_is_counted_but_not_flagged(empty_ledger):
    # A LICENSED claim may carry licensing=None (the validator only forbids licensing on
    # non-LICENSED, it does not require it). Drift can't be assessed -> examined but not drifted.
    c = make_claim("c", Status.LICENSED)
    out, rec = drift_pass(_corpus(empty_ledger, c), current=_CURRENT)
    assert rec.examined == 1
    assert rec.drifted == ()


def test_drift_pass_is_deterministic(empty_ledger):
    c2 = make_claim("c2", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    c1 = make_claim("c1", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    corpus = _corpus(empty_ledger, c2, c1)
    _, r1 = drift_pass(corpus, current=_CURRENT)
    _, r2 = drift_pass(corpus, current=_CURRENT)
    assert r1 == r2
    assert [f.claim_id for f in r1.drifted] == ["c1", "c2"]  # sorted by claim_id
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd protocol && uv run pytest tests/test_drift.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.drift'`.

- [ ] **Step 3: Create `drift.py` with the records and `drift_pass`**

Create `protocol/src/polymer_protocol/drift.py`:

```python
"""DRIFT daemon (#5a) — flag LICENSED claims whose minted materialization no longer matches
the world's current context.

Pure / deterministic / caller-scheduled (the standing #5 invariant): no clock, no randomness,
no environment read — the `current` context is an argument. `drift_pass` is FLAG-ONLY: it
returns the corpus identity-unchanged plus a `DriftRecord`. Re-opening drifted claims is the
separate opt-in `reopen_drifted` action. Daemon state lives in the record, never in the Corpus.
"""
from __future__ import annotations

from polymer_grammar import Claim, MaterializationContext, Status

from .base import _Model
from .corpus import Corpus


class DriftFinding(_Model):
    """One LICENSED claim whose materialization(s) all fail to match the current context."""

    claim_id: str
    re_executable: bool  # claim.evaluation_plan is not None -> SELECT could re-pursue it
    # the (api_version, data_version) pairs it was licensed under (the only audit trail that
    # survives a re-open, since the grammar forbids a `licensing` block on a non-LICENSED claim)
    licensed_versions: tuple[tuple[str, str], ...]


class DriftRecord(_Model):
    current: MaterializationContext  # echoed for audit
    examined: int  # number of LICENSED claims scanned
    drifted: tuple[DriftFinding, ...] = ()


def _is_fresh(claim: Claim, current: MaterializationContext) -> bool:
    """A LICENSED claim is fresh if ANY of its satisfaction materializations matches `current`
    on BOTH api_version and data_version (id/note ignored). Equality match (no semver)."""
    for sat in claim.licensing.satisfactions:
        m = sat.materialization
        if m.api_version == current.api_version and m.data_version == current.data_version:
            return True
    return False


def drift_pass(
    corpus: Corpus, *, current: MaterializationContext
) -> tuple[Corpus, DriftRecord]:
    """Scan LICENSED claims; flag those whose materialization no longer matches `current`.
    FLAG-ONLY: the returned Corpus IS the input object (never mutated)."""
    examined = 0
    findings: list[DriftFinding] = []
    for c in corpus.claims:
        if c.status != Status.LICENSED:
            continue
        examined += 1
        if c.licensing is None:  # LICENSED may carry no licensing block -> can't assess drift
            continue
        if _is_fresh(c, current):
            continue
        versions = tuple(
            sorted({(s.materialization.api_version, s.materialization.data_version)
                    for s in c.licensing.satisfactions})
        )
        findings.append(
            DriftFinding(
                claim_id=c.id,
                re_executable=c.evaluation_plan is not None,
                licensed_versions=versions,
            )
        )
    findings.sort(key=lambda f: f.claim_id)
    return corpus, DriftRecord(current=current, examined=examined, drifted=tuple(findings))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd protocol && uv run pytest tests/test_drift.py -q`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/drift.py protocol/tests/test_drift.py
git commit -m "feat(protocol): drift_pass — flag-only DRIFT detection (#5a)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Protocol — `reopen_drifted` (the opt-in re-open action)

**Files:**
- Modify: `protocol/src/polymer_protocol/drift.py`
- Test: `protocol/tests/test_drift.py`

- [ ] **Step 1: Write the failing re-open tests**

Append to `protocol/tests/test_drift.py`:

```python
def test_reopen_sets_pending_drops_licensing_sets_reason(empty_ledger):
    from polymer_grammar import PendingReason
    from polymer_protocol.drift import reopen_drifted

    c = make_claim(
        "c", Status.LICENSED, plan=make_plan(0.01, 0.05), licensing=_lic(_mat("M0", "v0", "d0"))
    )
    corpus = _corpus(empty_ledger, c)
    _, rec = drift_pass(corpus, current=_CURRENT)
    out = reopen_drifted(corpus, rec)
    reopened = out.by_id()["c"]
    assert reopened.status is Status.PENDING
    assert reopened.licensing is None
    assert reopened.pending_reason is PendingReason.MATERIALIZATION_DRIFTED


def test_reopened_claim_round_trips_as_a_valid_claim(empty_ledger):
    from polymer_grammar import Claim
    from polymer_protocol.drift import reopen_drifted

    c = make_claim(
        "c", Status.LICENSED, plan=make_plan(0.01, 0.05), licensing=_lic(_mat("M0", "v0", "d0"))
    )
    corpus = _corpus(empty_ledger, c)
    _, rec = drift_pass(corpus, current=_CURRENT)
    out = reopen_drifted(corpus, rec)
    reopened = out.by_id()["c"]
    # model_copy bypassed validators when re-opening; re-validate to pin a VALID state.
    Claim.model_validate(reopened.model_dump())


def test_reopen_require_plan_skips_planless(empty_ledger):
    from polymer_protocol.drift import reopen_drifted

    planless = make_claim("q", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    corpus = _corpus(empty_ledger, planless)
    _, rec = drift_pass(corpus, current=_CURRENT)
    out = reopen_drifted(corpus, rec)  # require_plan=True default
    assert out.by_id()["q"].status is Status.LICENSED  # left untouched


def test_reopen_require_plan_false_reopens_planless(empty_ledger):
    from polymer_grammar import PendingReason
    from polymer_protocol.drift import reopen_drifted

    planless = make_claim("q", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    corpus = _corpus(empty_ledger, planless)
    _, rec = drift_pass(corpus, current=_CURRENT)
    out = reopen_drifted(corpus, rec, require_plan=False)
    reopened = out.by_id()["q"]
    assert reopened.status is Status.PENDING
    assert reopened.pending_reason is PendingReason.MATERIALIZATION_DRIFTED


def test_reopen_leaves_non_drifted_and_other_collections_untouched(empty_ledger):
    from polymer_protocol.drift import reopen_drifted

    fresh = make_claim("fresh", Status.LICENSED, licensing=_lic(_mat("M1", "v1", "d1")))
    stale = make_claim(
        "stale", Status.LICENSED, plan=make_plan(0.01, 0.05), licensing=_lic(_mat("M0", "v0", "d0"))
    )
    corpus = _corpus(empty_ledger, fresh, stale)
    _, rec = drift_pass(corpus, current=_CURRENT)
    out = reopen_drifted(corpus, rec)
    assert out.by_id()["fresh"].status is Status.LICENSED  # not drifted -> unchanged
    assert out.by_id()["stale"].status is Status.PENDING
    assert out.equivalences == corpus.equivalences
    assert out.defeat_edges == corpus.defeat_edges
    assert out.fdr_ledger == corpus.fdr_ledger


def test_reopen_skips_findings_for_absent_claims(empty_ledger):
    from polymer_protocol.drift import DriftFinding, DriftRecord, reopen_drifted

    corpus = _corpus(empty_ledger, make_claim("a", Status.CONJECTURED))
    rec = DriftRecord(
        current=_CURRENT,
        examined=0,
        drifted=(DriftFinding(claim_id="ghost", re_executable=True, licensed_versions=(("v0", "d0"),)),),
    )
    out = reopen_drifted(corpus, rec)  # ghost not in corpus -> silently skipped, no raise
    assert out is corpus


def test_reopen_is_pure(empty_ledger):
    from polymer_protocol.drift import reopen_drifted

    c = make_claim(
        "c", Status.LICENSED, plan=make_plan(0.01, 0.05), licensing=_lic(_mat("M0", "v0", "d0"))
    )
    corpus = _corpus(empty_ledger, c)
    _, rec = drift_pass(corpus, current=_CURRENT)
    out1 = reopen_drifted(corpus, rec)
    out2 = reopen_drifted(corpus, rec)
    assert out1 == out2
    assert corpus.by_id()["c"].status is Status.LICENSED  # input corpus unchanged
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd protocol && uv run pytest tests/test_drift.py -q`
Expected: FAIL — `ImportError: cannot import name 'reopen_drifted' from 'polymer_protocol.drift'`.

- [ ] **Step 3: Add `reopen_drifted` to `drift.py`**

Add to the imports at the top of `protocol/src/polymer_protocol/drift.py`:

```python
from polymer_grammar import Claim, MaterializationContext, PendingReason, Status
```

(Replace the existing `from polymer_grammar import Claim, MaterializationContext, Status` line — adds `PendingReason`.)

Append this function to `protocol/src/polymer_protocol/drift.py`:

```python
def reopen_drifted(
    corpus: Corpus, record: DriftRecord, *, require_plan: bool = True
) -> Corpus:
    """Re-open the drifted claims named in `record` to PENDING (the opt-in action `drift_pass`
    never performs itself). With `require_plan=True` (default) only re-executable findings are
    re-opened — a planless claim re-opened to PENDING could never self-relicense, so it would
    strand. Pure: returns a new Corpus; findings for absent claim ids are silently skipped."""
    targets = {f.claim_id for f in record.drifted if (f.re_executable or not require_plan)}
    if not targets:
        return corpus
    new_claims = tuple(
        c.model_copy(
            update={
                "status": Status.PENDING,
                "licensing": None,
                "pending_reason": PendingReason.MATERIALIZATION_DRIFTED,
            }
        )
        if c.id in targets
        else c
        for c in corpus.claims
    )
    if new_claims == corpus.claims:
        return corpus
    return corpus.model_copy(update={"claims": new_claims})
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd protocol && uv run pytest tests/test_drift.py -q`
Expected: PASS (16 tests total).

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/drift.py protocol/tests/test_drift.py
git commit -m "feat(protocol): reopen_drifted — opt-in re-PENDING of drifted claims (#5a)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Protocol — exports + full-suite green

**Files:**
- Modify: `protocol/src/polymer_protocol/__init__.py`

- [ ] **Step 1: Write the failing export test**

Append to `protocol/tests/test_drift.py`:

```python
def test_drift_symbols_are_exported_from_package():
    import polymer_protocol as pp

    assert hasattr(pp, "drift_pass")
    assert hasattr(pp, "reopen_drifted")
    assert hasattr(pp, "DriftRecord")
    assert hasattr(pp, "DriftFinding")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_drift.py::test_drift_symbols_are_exported_from_package -q`
Expected: FAIL — `AttributeError: module 'polymer_protocol' has no attribute 'drift_pass'`.

- [ ] **Step 3: Add the imports and `__all__` entries**

In `protocol/src/polymer_protocol/__init__.py`, add an import line next to the other module imports (e.g. after the `from .oracle import ...` line):

```python
from .drift import DriftFinding, DriftRecord, drift_pass, reopen_drifted
```

And add these four names to the `__all__` list (anywhere in it):

```python
    "DriftFinding",
    "DriftRecord",
    "drift_pass",
    "reopen_drifted",
```

- [ ] **Step 4: Run the export test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_drift.py::test_drift_symbols_are_exported_from_package -q`
Expected: PASS.

- [ ] **Step 5: Run the full protocol suite + ruff + isolation**

Run: `cd protocol && uv run pytest -q && uv run ruff check src tests`
Expected: all green (existing protocol tests + 17 drift tests), ruff clean. `tests/test_isolation.py` still passes (grammar never imports protocol).

- [ ] **Step 6: Run the full grammar suite (confirm Task 1 still green)**

Run: `cd grammar && uv run pytest -q`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/__init__.py protocol/tests/test_drift.py
git commit -m "feat(protocol): export DRIFT daemon symbols (#5a)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Progress Log

(Update after each task.)

- [ ] Task 1 — grammar `MATERIALIZATION_DRIFTED` reason
- [ ] Task 2 — `drift_pass` flag-only detection
- [ ] Task 3 — `reopen_drifted` opt-in action
- [ ] Task 4 — exports + full-suite green

## Self-review notes

- **Spec coverage:** Component 1 (enum) → Task 1; Component 2 (`DriftFinding`/`DriftRecord`/`drift_pass`, flag-only, any-match freshness, identity-unchanged corpus, determinism) → Task 2; Component 3 (`reopen_drifted`, plan-gate, atomic mutation, re-validate, absent-id skip, purity) → Task 3; exports → Task 4. All spec test bullets map to a named test.
- **Fences honored:** equality match (no semver); no oracle tier; no `run_cycle` wiring; prior-licensing versions survive only in `DriftRecord.licensed_versions`.
- **Type consistency:** `DriftFinding(claim_id, re_executable, licensed_versions)`, `DriftRecord(current, examined, drifted)`, `drift_pass(corpus, *, current) -> (Corpus, DriftRecord)`, `reopen_drifted(corpus, record, *, require_plan=True) -> Corpus` — identical across plan, spec, and tests.
- **Edge added beyond spec:** a LICENSED claim with `licensing=None` is counted in `examined` but never flagged (the grammar permits LICENSED without a licensing block); covered by `test_licensed_without_licensing_block_is_counted_but_not_flagged`.
