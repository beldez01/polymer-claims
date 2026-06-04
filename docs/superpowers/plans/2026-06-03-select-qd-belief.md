# SELECT #3b Implementation Plan — QD + heterodox + Goodhart + accumulating belief

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the SELECT valve with four cross-cycle features — quality-diversity portfolio, heterodox reserve lane, surprise-Goodhart operator discount, and persisted accumulating belief — on a threaded `SelectionLedger`.

**Architecture:** All protocol-side, zero grammar changes. New cross-cycle state lives in a frozen `SelectionLedger` threaded into `run_cycle` and returned on `CycleResult` (Corpus stays grammar-IR-only / 4 collections). Belief accumulates per-claim from realized outcomes (with a settled-concentration EIG guard); a per-operator credit factor discounts fill-order density (Pareto front + EIG axis stay raw). QD uses structural cells with per-cell budget caps; a reserve lane pursues dominated candidates. `run_cycle` defaults keep the features OFF (exact #3a back-compat); the recommended values are passed explicitly.

**Tech Stack:** Python 3.14, Pydantic v2 (frozen `_Model`), `uv`, `pytest`. Stdlib only. One-way dep `polymer_protocol` → `polymer_grammar`.

**Spec:** `docs/superpowers/specs/2026-06-03-select-qd-belief-design.md`

---

## Conventions for every task

- Work in `protocol/`. Tests: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q`.
- New models subclass `_Model` from `polymer_protocol.base` (frozen, `extra="forbid"`, tuples not lists).
- Keep `ruff` clean: `uv run ruff check src tests`.
- Commit after each task with the message shown. Commits are LOCAL only.
- v1 named constants (spec §11): `SETTLED_CONCENTRATION = 200.0`, `CREDIT_A0 = 1.0`, `HIGH_EIG = 0.5`, `RESERVE_FRACTION = 0.2`, `CELL_CAP_FRACTION = 0.5`. Module-level named constants only.

---

## File Structure

| File | New/Modify | Responsibility |
|---|---|---|
| `src/polymer_protocol/ledger.py` | new | `ClaimOutcome`, `OperatorCredit`, `SelectionLedger`, `operator_of`, `credit_factor`, `ExecutedOutcome`, `update_ledger` |
| `src/polymer_protocol/belief.py` | modify | `accumulated_belief`; `SETTLED_CONCENTRATION` short-circuit in `expected_information_gain` |
| `src/polymer_protocol/corpus.py` | modify | `cell`/`lane` on `SelectionDecision`; `ledger` on `CycleResult` |
| `src/polymer_protocol/select.py` | modify | `cell_of`; accumulated-belief EIG; credit-discounted density; main-lane cell caps + reserve lane; `cell`/`lane` on decisions; `ledger`+fraction params |
| `src/polymer_protocol/cycle.py` | modify | thread `ledger`/fractions; build `ExecutedOutcome`s; `update_ledger` after verify; return `ledger` |
| `src/polymer_protocol/__init__.py` | modify | export new public symbols |

---

### Task 1: `ledger.py` — ledger types + operator_of + credit_factor

**Files:**
- Create: `src/polymer_protocol/ledger.py`
- Test: `tests/test_ledger.py`

- [ ] **Step 1: Write the failing tests** — create `tests/test_ledger.py`:

```python
import pytest
from polymer_grammar import GenerationMode, Provenance

from polymer_protocol.ledger import (
    ClaimOutcome, OperatorCredit, SelectionLedger, credit_factor, operator_of,
)
from tests.conftest import make_claim


def test_ledger_lookups():
    led = SelectionLedger(
        outcomes=(ClaimOutcome(claim_id="a", successes=2, failures=1),),
        credits=(OperatorCredit(operator_id="op", n_high_eig=3, n_grounded=1),),
    )
    assert led.outcome("a").successes == 2
    assert led.outcome("missing") is None
    assert led.credit("op").n_grounded == 1
    assert led.credit("missing") is None


def test_ledger_rejects_duplicate_ids():
    with pytest.raises(Exception):
        SelectionLedger(outcomes=(ClaimOutcome(claim_id="a"), ClaimOutcome(claim_id="a")))
    with pytest.raises(Exception):
        SelectionLedger(credits=(OperatorCredit(operator_id="x"), OperatorCredit(operator_id="x")))


def test_operator_of_uses_agent_id_for_agent_generated():
    prov = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="rival-generation",
                      search_cardinality=1)
    c = make_claim("a", provenance=prov)
    assert operator_of(c) == "rival-generation"


def test_operator_of_is_exogenous_otherwise():
    assert operator_of(make_claim("a")) == "exogenous"  # provenance None
    prov = Provenance(generated_by=GenerationMode.IMPORTED, search_cardinality=1)
    assert operator_of(make_claim("b", provenance=prov)) == "exogenous"


def test_credit_factor_optimistic_untracked_is_one():
    assert credit_factor(SelectionLedger(), "anyop") == 1.0


def test_credit_factor_penalizes_failures():
    led = SelectionLedger(credits=(OperatorCredit(operator_id="bad", n_high_eig=10, n_grounded=0),))
    cf = credit_factor(led, "bad")
    assert 0.0 < cf < 0.2  # (0 + 1)/(10 + 1) ~= 0.09
    led2 = SelectionLedger(credits=(OperatorCredit(operator_id="good", n_high_eig=10, n_grounded=10),))
    assert credit_factor(led2, "good") == 1.0
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_ledger.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.ledger'`

- [ ] **Step 3: Implement** — create `src/polymer_protocol/ledger.py`:

```python
"""SelectionLedger — the threaded cross-cycle pursuit state for SELECT #3b.

Protocol pursuit-state, NOT grammar knowledge: passed into run_cycle and returned on
CycleResult (Corpus stays grammar-IR-only / 4 collections). Holds per-claim accumulated
execution outcomes (for accumulating belief) and per-operator surprise-grounding credit
(for the Goodhart guard). Pure, deterministic. Spec §2, §4.
"""
from __future__ import annotations

from pydantic import Field, model_validator

from polymer_grammar import Claim, GenerationMode

from .base import _Model

CREDIT_A0 = 1.0
HIGH_EIG = 0.5


class ClaimOutcome(_Model):
    claim_id: str
    successes: int = Field(default=0, ge=0)
    failures: int = Field(default=0, ge=0)


class OperatorCredit(_Model):
    operator_id: str
    n_high_eig: int = Field(default=0, ge=0)
    n_grounded: int = Field(default=0, ge=0)


class SelectionLedger(_Model):
    outcomes: tuple[ClaimOutcome, ...] = ()
    credits: tuple[OperatorCredit, ...] = ()

    @model_validator(mode="after")
    def _unique_ids(self) -> "SelectionLedger":
        oids = [o.claim_id for o in self.outcomes]
        if len(oids) != len(set(oids)):
            raise ValueError("SelectionLedger outcome claim_ids must be unique")
        cids = [c.operator_id for c in self.credits]
        if len(cids) != len(set(cids)):
            raise ValueError("SelectionLedger credit operator_ids must be unique")
        return self

    def outcome(self, claim_id: str) -> ClaimOutcome | None:
        return {o.claim_id: o for o in self.outcomes}.get(claim_id)

    def credit(self, operator_id: str) -> OperatorCredit | None:
        return {c.operator_id: c for c in self.credits}.get(operator_id)


def operator_of(claim: Claim) -> str:
    """The GENERATE operator that produced a claim (#4a trace), else 'exogenous'."""
    prov = claim.provenance
    if prov is not None and prov.generated_by == GenerationMode.AGENT_GENERATED and prov.agent_id:
        return prov.agent_id
    return "exogenous"


def credit_factor(ledger: SelectionLedger, operator_id: str) -> float:
    """Optimistic smoothed grounding rate (n_grounded + A0)/(n_high_eig + A0). Untracked -> 1.0;
    systematically-failing -> toward 0. Bounded (0, 1]."""
    cr = ledger.credit(operator_id)
    if cr is None:
        return 1.0
    return (cr.n_grounded + CREDIT_A0) / (cr.n_high_eig + CREDIT_A0)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_ledger.py -v`
Expected: PASS (6 tests). Also `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/ledger.py protocol/tests/test_ledger.py
git commit -m "feat(protocol): SelectionLedger + operator_of + credit_factor

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `ledger.py` — ExecutedOutcome + update_ledger

**Files:**
- Modify: `src/polymer_protocol/ledger.py`
- Test: `tests/test_ledger.py`

`update_ledger` folds a cycle's realized outcomes into the ledger: per-claim successes/failures, and per-operator high-EIG grounding credit.

- [ ] **Step 1: Append the failing tests** to `tests/test_ledger.py`:

```python
from polymer_protocol.ledger import ExecutedOutcome, update_ledger


def test_update_ledger_bumps_claim_outcomes():
    out = [
        ExecutedOutcome(claim_id="a", operator_id="op", eig=0.9, licensed=True, rejected=False),
        ExecutedOutcome(claim_id="a", operator_id="op", eig=0.9, licensed=False, rejected=True),
    ]
    led = update_ledger(SelectionLedger(), tuple(out))
    o = led.outcome("a")
    assert o.successes == 1 and o.failures == 1


def test_update_ledger_high_eig_credits_only():
    out = [
        ExecutedOutcome(claim_id="a", operator_id="op", eig=0.9, licensed=True, rejected=False),  # high
        ExecutedOutcome(claim_id="b", operator_id="op", eig=0.1, licensed=False, rejected=True),  # low
    ]
    led = update_ledger(SelectionLedger(), tuple(out))
    cr = led.credit("op")
    assert cr.n_high_eig == 1   # only the eig>=HIGH_EIG one
    assert cr.n_grounded == 1


def test_update_ledger_undetermined_is_neither():
    out = (ExecutedOutcome(claim_id="a", operator_id="op", eig=0.9, licensed=False, rejected=False),)
    led = update_ledger(SelectionLedger(), out)
    o = led.outcome("a")
    assert o.successes == 0 and o.failures == 0  # undetermined: no outcome bump
    assert led.credit("op").n_high_eig == 1 and led.credit("op").n_grounded == 0  # but credit counts the miss


def test_update_ledger_merges_existing():
    led0 = SelectionLedger(outcomes=(ClaimOutcome(claim_id="a", successes=1),))
    out = (ExecutedOutcome(claim_id="a", operator_id="op", eig=0.1, licensed=True, rejected=False),)
    led = update_ledger(led0, out)
    assert led.outcome("a").successes == 2  # merged, not replaced


def test_update_ledger_deterministic():
    out = (ExecutedOutcome(claim_id="b", operator_id="op", eig=0.9, licensed=True, rejected=False),
           ExecutedOutcome(claim_id="a", operator_id="op2", eig=0.9, licensed=True, rejected=False))
    assert update_ledger(SelectionLedger(), out) == update_ledger(SelectionLedger(), out)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_ledger.py::test_update_ledger_bumps_claim_outcomes -v`
Expected: FAIL — `ImportError: cannot import name 'ExecutedOutcome'`

- [ ] **Step 3: Implement** — append to `src/polymer_protocol/ledger.py`:

```python
class ExecutedOutcome(_Model):
    """One claim's realized outcome this cycle, fed to update_ledger."""

    claim_id: str
    operator_id: str
    eig: float            # the raw belief-EIG at selection (for the HIGH_EIG test)
    licensed: bool
    rejected: bool


def update_ledger(ledger: SelectionLedger, outcomes: tuple[ExecutedOutcome, ...]) -> SelectionLedger:
    succ: dict[str, int] = {o.claim_id: o.successes for o in ledger.outcomes}
    fail: dict[str, int] = {o.claim_id: o.failures for o in ledger.outcomes}
    he: dict[str, int] = {c.operator_id: c.n_high_eig for c in ledger.credits}
    gr: dict[str, int] = {c.operator_id: c.n_grounded for c in ledger.credits}
    for o in outcomes:
        succ[o.claim_id] = succ.get(o.claim_id, 0) + (1 if o.licensed else 0)
        fail[o.claim_id] = fail.get(o.claim_id, 0) + (1 if o.rejected else 0)
        if o.eig >= HIGH_EIG:
            he[o.operator_id] = he.get(o.operator_id, 0) + 1
            gr[o.operator_id] = gr.get(o.operator_id, 0) + (1 if o.licensed else 0)
    new_outcomes = tuple(
        ClaimOutcome(claim_id=cid, successes=succ[cid], failures=fail.get(cid, 0))
        for cid in sorted(succ)
    )
    new_credits = tuple(
        OperatorCredit(operator_id=oid, n_high_eig=he[oid], n_grounded=gr.get(oid, 0))
        for oid in sorted(he)
    )
    return ledger.model_copy(update={"outcomes": new_outcomes, "credits": new_credits})
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_ledger.py -v`
Expected: PASS (11 tests total). Also `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/ledger.py protocol/tests/test_ledger.py
git commit -m "feat(protocol): ExecutedOutcome + update_ledger

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `belief.py` — accumulated_belief + settled-concentration guard

**Files:**
- Modify: `src/polymer_protocol/belief.py`
- Test: `tests/test_belief.py`

- [ ] **Step 1: Append the failing tests** to `tests/test_belief.py`:

```python
from polymer_protocol.belief import accumulated_belief, SETTLED_CONCENTRATION
from polymer_protocol.ledger import ClaimOutcome, SelectionLedger
from tests.conftest import make_claim


def test_accumulated_belief_is_prior_for_fresh_claim():
    c = make_claim("a")  # strength None -> prior Beta(1,1)
    assert accumulated_belief(c, SelectionLedger()) == Beta(alpha=1.0, beta=1.0)


def test_accumulated_belief_adds_outcomes():
    c = make_claim("a")  # prior Beta(1,1)
    led = SelectionLedger(outcomes=(ClaimOutcome(claim_id="a", successes=3, failures=2),))
    b = accumulated_belief(c, led)
    assert b.alpha == 4.0 and b.beta == 3.0  # 1+3, 1+2


def test_eig_settled_concentration_returns_zero():
    # a very concentrated Beta -> settled -> EIG 0 (analytic + avoids quadrature degradation)
    assert expected_information_gain(Beta(alpha=150.0, beta=150.0)) == 0.0  # alpha+beta=300 >= 200
    # just below threshold the quadrature still runs (non-settled), value may be tiny but computed
    assert expected_information_gain(Beta(alpha=50.0, beta=50.0)) >= 0.0  # alpha+beta=100 < 200
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_belief.py::test_accumulated_belief_adds_outcomes -v`
Expected: FAIL — `ImportError: cannot import name 'accumulated_belief'`

- [ ] **Step 3: Implement** — in `src/polymer_protocol/belief.py`:

(a) Add the constant near the top (after `EPS`):

```python
SETTLED_CONCENTRATION = 200.0
```

(b) Add the settled-belief short-circuit as the FIRST line of `expected_information_gain`'s body (before `a, b = belief.alpha, belief.beta` — actually compute a,b first):

```python
def expected_information_gain(belief: Beta) -> float:
    """... (existing docstring) ..."""
    a, b = belief.alpha, belief.beta
    if a + b >= SETTLED_CONCENTRATION:
        # a settled (sharply peaked) belief yields negligible expected information; return 0
        # analytically AND sidestep the fixed-node quadrature's high-concentration degradation.
        return 0.0
    mu = a / (a + b)
    # ... rest unchanged ...
```

(c) Add `accumulated_belief` at the end of the file. It imports `SelectionLedger` from `.ledger`:

```python
from .ledger import SelectionLedger  # at top with the other imports


def accumulated_belief(claim: Claim, ledger: SelectionLedger) -> Beta:
    """The #3a prior updated by the claim's accumulated execution outcomes (spec §3).
    Fresh claim (no ledger entry) -> the #3a prior unchanged."""
    prior = prior_belief(claim)
    o = ledger.outcome(claim.id)
    if o is None:
        return prior
    return Beta(alpha=prior.alpha + o.successes, beta=prior.beta + o.failures)
```

**Import-cycle note:** `belief.py` importing `.ledger`, and `.ledger` imports only `.base` + grammar — NO import of `.belief`. So `belief → ledger` is one-way, no cycle. Verify `ledger.py` does not import `belief`.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_belief.py -v`
Expected: PASS (existing belief tests + 3 new). Also `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/belief.py protocol/tests/test_belief.py
git commit -m "feat(protocol): accumulated_belief + settled-concentration EIG guard

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `corpus.py` — cell/lane on SelectionDecision; ledger on CycleResult

**Files:**
- Modify: `src/polymer_protocol/corpus.py`
- Test: `tests/test_corpus.py`

`SelectionLedger` lives in `ledger.py` which imports `.corpus` (for nothing currently) — actually `ledger.py` imports only `.base` + grammar, and `corpus.py` must reference `SelectionLedger` for the `CycleResult.ledger` field. To avoid a cycle (`corpus → ledger` while `ledger`'s helpers are independent), `ledger.py` must NOT import `corpus.py`. Confirm `ledger.py` imports only `.base` + `polymer_grammar`. Then `corpus.py` importing `SelectionLedger` from `.ledger` is a clean one-way edge.

- [ ] **Step 1: Append the failing tests** to `tests/test_corpus.py`:

```python
from polymer_protocol.ledger import SelectionLedger
from polymer_protocol.corpus import SelectionDecision, ValueVector


def test_selection_decision_has_cell_and_lane():
    d = SelectionDecision(claim_id="a", selected=True, value=ValueVector(eig=0.5, stakes=1.0),
                          cost=1.0, rank=0, cell="pat|none", lane="reserve")
    assert d.cell == "pat|none"
    assert d.lane == "reserve"


def test_selection_decision_lane_defaults_main():
    d = SelectionDecision(claim_id="a", selected=False, value=ValueVector(), cost=1.0, rank=0)
    assert d.cell == "" and d.lane == "main"


def test_cycle_result_defaults_empty_ledger():
    from polymer_grammar import FDRLedger
    from polymer_protocol.corpus import Corpus, CycleResult
    r = CycleResult(corpus=Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)))
    assert r.ledger == SelectionLedger()
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_corpus.py::test_selection_decision_has_cell_and_lane -v`
Expected: FAIL — `SelectionDecision` has no `cell`.

- [ ] **Step 3: Implement** — in `src/polymer_protocol/corpus.py`:

(a) Add the import at the top (with the other `from .` imports):

```python
from .ledger import SelectionLedger
```

(b) Add two fields to the existing `SelectionDecision` class (after `rank`):

```python
    cell: str = ""
    lane: str = "main"
```

(c) Add a field at the end of `CycleResult`'s field list:

```python
    ledger: SelectionLedger = SelectionLedger()
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_corpus.py -v`
Expected: PASS (existing + 3 new). Also `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/corpus.py protocol/tests/test_corpus.py
git commit -m "feat(protocol): cell/lane on SelectionDecision; ledger on CycleResult

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `select.py` — accumulated belief, credit discount, QD cells, reserve lane

**Files:**
- Modify: `src/polymer_protocol/select.py`
- Test: `tests/test_select.py`

This rewrites `select_stage`'s scoring + fill. New params `ledger`, `reserve_fraction`, `cell_cap_fraction`. EIG now from `accumulated_belief`; fill-order density scaled by `credit_factor`; main lane has per-cell caps; a reserve lane pursues dominated candidates; decisions record `cell`/`lane`.

- [ ] **Step 1: Append the failing tests** to `tests/test_select.py`:

```python
from polymer_grammar import GenerationMode, Provenance, StrengthVector
from polymer_protocol.ledger import OperatorCredit, SelectionLedger
from polymer_protocol.select import cell_of


def _run_b(corpus, budget=None, cost_model=None, ledger=None, reserve=0.0, cell_cap=1.0):
    return select_stage(
        corpus, budget=budget, cost_model=cost_model or CostModel(),
        value_weights=ValueWeights(), cost_weights=CostWeights(),
        ledger=ledger or SelectionLedger(), reserve_fraction=reserve, cell_cap_fraction=cell_cap,
    )


def test_cell_of_is_pattern_and_subject_kind():
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    # default conftest pattern id is "adjusted_effect"; subject None -> "none"
    assert cell_of(c) == "adjusted_effect|none"


def test_defaults_reproduce_3a_selection():
    # ledger empty + reserve 0 + cell_cap 1.0 -> identical selection to #3a (everything selected unbudgeted)
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    corp = Corpus(claims=(a, b), fdr_ledger=FDRLedger(target_fdr=0.05))
    _, rec = _run_b(corp)
    assert {d.claim_id for d in rec.decisions if d.selected} == {"a", "b"}
    assert all(d.lane == "main" for d in rec.decisions if d.selected)


def test_reserve_lane_pursues_a_dominated_candidate():
    # strong claim dominates a weak one; tight budget; reserve lane picks the dominated weak one
    sv_strong = StrengthVector(magnitude=0.9, uncertainty=0.1, evidence_against_null=0.9,
                               severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    sv_weak = StrengthVector(magnitude=0.1, uncertainty=0.9, evidence_against_null=0.1,
                             severity=0.1, world_contact=0.1, explanatory_virtue=0.1)
    strong = make_claim("strong", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=sv_strong)
    weak = make_claim("weak", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=sv_weak)
    corp = Corpus(claims=(strong, weak), fdr_ledger=FDRLedger(target_fdr=0.05))
    cm = CostModel(costs=(("strong", CostVector(wall_latency=1.0)), ("weak", CostVector(wall_latency=1.0))))
    # budget 2.0, reserve 0.5 -> main_budget 1.0 (fits only strong), reserve_budget 1.0 (picks up weak).
    # The reserve lane only sees what the main lane could NOT afford; with the main budget exhausted
    # by the front claim, the dominated weak claim falls to the reserve lane.
    _, rec = _run_b(corp, budget=2.0, cost_model=cm, reserve=0.5)
    lanes = {d.claim_id: d.lane for d in rec.decisions if d.selected}
    assert lanes.get("strong") == "main"
    assert lanes.get("weak") == "reserve"  # dominated + main exhausted -> only the reserve lane pursues it


def test_cell_cap_spreads_budget_across_cells():
    # three claims in cell A, one in cell B (different pattern); a tight cell cap forces B to be served
    from polymer_grammar import PatternRef
    patB = PatternRef(id="other_pattern", version="v1")
    a1 = make_claim("a1", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    a2 = make_claim("a2", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    a3 = make_claim("a3", status=Status.PENDING, plan=make_plan(0.03, 0.05))
    b1 = make_claim("b1", status=Status.PENDING, plan=make_plan(0.01, 0.05), pattern=patB)
    corp = Corpus(claims=(a1, a2, a3, b1), fdr_ledger=FDRLedger(target_fdr=0.05))
    cm = CostModel(default=CostVector(wall_latency=1.0))
    # budget 3.0, cell_cap 0.34 -> each cell may spend <= ~1.0 (1 claim). B's cell must get served.
    _, rec = _run_b(corp, budget=3.0, cost_model=cm, cell_cap=0.34)
    selected = {d.claim_id for d in rec.decisions if d.selected}
    assert "b1" in selected  # the lone B-cell claim is served despite 3 cheaper A-cell claims


def test_operator_discount_changes_fill_priority():
    # an operator with a bad track record gets its claims pursued later under a tight budget
    sv = StrengthVector(magnitude=0.5, uncertainty=0.2, evidence_against_null=0.5,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    good_prov = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="good", search_cardinality=1)
    bad_prov = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="bad", search_cardinality=1)
    g = make_claim("g", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=sv, provenance=good_prov)
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=sv, provenance=bad_prov)
    corp = Corpus(claims=(g, b), fdr_ledger=FDRLedger(target_fdr=0.05))
    cm = CostModel(default=CostVector(wall_latency=1.0))
    led = SelectionLedger(credits=(OperatorCredit(operator_id="bad", n_high_eig=20, n_grounded=0),))
    # budget for exactly one claim -> the trusted operator's claim wins
    _, rec = _run_b(corp, budget=1.0, cost_model=cm, ledger=led)
    selected = {d.claim_id for d in rec.decisions if d.selected}
    assert selected == {"g"}
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_select.py::test_cell_of_is_pattern_and_subject_kind -v`
Expected: FAIL — `ImportError: cannot import name 'cell_of'` (and `select_stage` has no `ledger` kwarg).

- [ ] **Step 3: Implement** — rewrite `src/polymer_protocol/select.py`:

Update imports:

```python
from .belief import accumulated_belief, expected_information_gain
from .ledger import SelectionLedger, credit_factor, operator_of
```
(remove the now-unused `prior_belief` import; keep `expected_information_gain`.)

Add the constants + `cell_of`:

```python
RESERVE_FRACTION = 0.2
CELL_CAP_FRACTION = 0.5


def cell_of(claim: Claim) -> str:
    """A structural QD niche key: (pattern id, subject kind). No embeddings (spec §5)."""
    kind = claim.subject.kind if claim.subject is not None else "none"
    return f"{claim.pattern.id}|{kind}"
```

Change `_value` to take the ledger:

```python
def _value(corpus: Corpus, claim: Claim, ledger: SelectionLedger) -> ValueVector:
    eig = expected_information_gain(accumulated_belief(claim, ledger))
    return ValueVector(eig=eig, stakes=stakes(corpus, claim.id))
```

Replace `select_stage` with:

```python
def select_stage(
    corpus: Corpus,
    *,
    cost_model: CostModel,
    budget: float | None,
    value_weights: ValueWeights,
    cost_weights: CostWeights,
    ledger: SelectionLedger = SelectionLedger(),
    reserve_fraction: float = 0.0,
    cell_cap_fraction: float = 1.0,
) -> tuple[Corpus, SelectionRecord]:
    candidates = [c for c in corpus.claims if _is_candidate(c)]
    m = len(candidates)
    if m == 0:
        return corpus, SelectionRecord()

    scored = []  # (claim, value, cost, cell, credit)
    for c in candidates:
        value = _value(corpus, c, ledger)
        cost = aggregate_cost(cost_model.resolve(c.id), cost_weights)
        cell = cell_of(c)
        credit = credit_factor(ledger, operator_of(c))
        scored.append((c, value, cost, cell, credit))

    front_ids = set()
    for c, value, _, _, _ in scored:
        dominated = any(ov.dominates(value) for oc, ov, _, _, _ in scored if oc.id != c.id)
        if not dominated:
            front_ids.add(c.id)

    def density(item) -> float:
        c, value, cost, cell, credit = item
        return _density(value, cost, value_weights) * credit

    def order_key(item):
        c, value, cost, cell, credit = item
        return (0 if c.id in front_ids else 1, -density(item), c.id)

    ordered = sorted(scored, key=order_key)

    if budget is None:
        main_budget = None
        reserve_budget = 0.0
    else:
        reserve_budget = budget * reserve_fraction
        main_budget = budget - reserve_budget
    cell_cap = None if main_budget is None else main_budget * cell_cap_fraction

    selected_ids: set[str] = set()
    lane_of: dict[str, str] = {}
    cell_spend: dict[str, float] = {}
    main_spent = 0.0
    for item in ordered:
        c, value, cost, cell, credit = item
        if main_budget is not None:
            if main_spent + cost > main_budget:
                continue
            if cell_cap is not None and cell_spend.get(cell, 0.0) + cost > cell_cap:
                continue
        selected_ids.add(c.id)
        lane_of[c.id] = "main"
        main_spent += cost
        cell_spend[cell] = cell_spend.get(cell, 0.0) + cost

    # reserve lane: dominated (off-front) candidates the main lane didn't take
    reserve_spent = 0.0
    for item in ordered:
        c, value, cost, cell, credit = item
        if c.id in selected_ids or c.id in front_ids:
            continue
        if reserve_spent + cost > reserve_budget:
            continue
        selected_ids.add(c.id)
        lane_of[c.id] = "reserve"
        reserve_spent += cost

    decisions = []
    for rank, item in enumerate(ordered):
        c, value, cost, cell, credit = item
        decisions.append(SelectionDecision(
            claim_id=c.id, selected=c.id in selected_ids, value=value, cost=cost,
            rank=rank, cell=cell, lane=lane_of.get(c.id, "main"),
        ))

    new_claims = tuple(
        _stamp_cardinality(c, m) if c.id in selected_ids else c for c in corpus.claims
    )
    record = SelectionRecord(
        decisions=tuple(sorted(decisions, key=lambda d: d.claim_id)),
        cardinality=m,
    )
    return corpus.model_copy(update={"claims": new_claims}), record
```

Note: when `budget is None`, `main_budget is None` ⇒ main lane admits everything (no checks), `reserve_budget = 0.0` ⇒ reserve lane admits nothing — so everything is selected via the main lane (exact #3a unbounded behavior).

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_select.py -v`
Expected: existing #3a select tests + 5 new all PASS. Then FULL suite `uv run pytest -q` — green. `uv run ruff check src tests`.

**Back-compat note:** `select_stage`'s three new params (`ledger`/`reserve_fraction`/`cell_cap_fraction`) have defaults (`SelectionLedger()`/`0.0`/`1.0`), so existing direct callers — the `_run` helper in `test_select.py` AND `_verify_through_select` in `test_verify.py` — keep working unchanged (they don't pass the new kwargs; the defaults reproduce #3a). Do NOT edit those helpers. Only the NEW `_run_b` helper (above) passes the new kwargs explicitly to exercise #3b features.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/select.py protocol/tests/test_select.py
git commit -m "feat(protocol): SELECT #3b — accumulated belief, credit discount, QD cells, reserve lane

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `cycle.py` — thread ledger; update after verify

**Files:**
- Modify: `src/polymer_protocol/cycle.py`
- Test: `tests/test_cycle.py`

- [ ] **Step 1: Append the failing tests** to `tests/test_cycle.py`:

```python
def test_ledger_threads_and_accumulates(empty_ledger, ctx, adapters):
    # a satisfied claim licenses -> its ClaimOutcome accrues a success in the returned ledger
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    o = result.ledger.outcome("a")
    assert o is not None and o.successes == 1


def test_ledger_default_is_empty_and_backcompat(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    # default reserve/cell-cap are OFF -> claim still licenses exactly as #3a
    assert result.corpus.by_id()["a"].status == Status.LICENSED


def test_surprise_goodhart_downweights_failing_operator(empty_ledger, ctx, adapters):
    from polymer_grammar import GenerationMode, Provenance, StrengthVector
    # operator "bad" proposes a high-EIG claim that gets REJECTED -> next cycle its credit drops
    sv = StrengthVector(magnitude=0.5, uncertainty=0.2, evidence_against_null=0.5,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    bad_prov = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="bad", search_cardinality=1)
    # value 0.99 vs threshold 0.05 with LT -> NOT satisfied -> REFUTED -> REJECTED
    miss = make_claim("miss", status=Status.PENDING, plan=make_plan(0.99, 0.05), strength=sv, provenance=bad_prov)
    r1 = run_cycle(Corpus(claims=(miss,), fdr_ledger=empty_ledger), adapters, ctx)
    cr = r1.ledger.credit("bad")
    # the high-EIG (strength-None prior would be 1.0; with sv eig may be < HIGH_EIG) — assert credit recorded only if high-eig
    # robust assertion: the claim was executed and rejected -> its outcome recorded a failure
    assert r1.ledger.outcome("miss").failures == 1
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_cycle.py::test_ledger_threads_and_accumulates -v`
Expected: FAIL — `CycleResult` has no `ledger` populated / `run_cycle` doesn't update it.

- [ ] **Step 3: Implement** — modify `src/polymer_protocol/cycle.py`:

(a) Add imports:

```python
from .ledger import ExecutedOutcome, SelectionLedger, operator_of, update_ledger
```

(b) Add keyword-only params after `generation_cap`:

```python
    ledger: SelectionLedger | None = None,
    reserve_fraction: float = 0.0,
    cell_cap_fraction: float = 1.0,
```

(c) Normalize the ledger at the top of the body (after `audit: list... = []`):

```python
    led = ledger if ledger is not None else SelectionLedger()
```

(d) Pass the ledger + fractions into `select_stage`:

```python
    corpus, selection = select_stage(
        corpus, cost_model=cost_model or CostModel(), budget=budget,
        value_weights=value_weights, cost_weights=cost_weights,
        ledger=led, reserve_fraction=reserve_fraction, cell_cap_fraction=cell_cap_fraction,
    )
```

(e) After `verify_stage` (after `n_licensed = ...`), build outcomes + update the ledger:

```python
    after = corpus.by_id()
    eig_by_id = {d.claim_id: d.value.eig for d in selection.decisions}
    outcomes = tuple(
        ExecutedOutcome(
            claim_id=cid,
            operator_id=operator_of(after[cid]),
            eig=eig_by_id.get(cid, 0.0),
            licensed=after[cid].status == Status.LICENSED,
            rejected=after[cid].status == Status.REJECTED,
        )
        for cid in sorted(executed_ids) if cid in after
    )
    led = update_ledger(led, outcomes)
```

(f) Add `ledger=led` to the returned `CycleResult(...)`.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_cycle.py -v`
Expected: new + existing cycle tests PASS. Then FULL suite `uv run pytest -q` — green. `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/cycle.py protocol/tests/test_cycle.py
git commit -m "feat(protocol): thread SelectionLedger through run_cycle + update after verify

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `__init__.py` — exports + full-suite green

**Files:**
- Modify: `src/polymer_protocol/__init__.py`
- Test: whole suite

- [ ] **Step 1: Append this test** to `tests/test_ledger.py`:

```python
def test_public_exports():
    import polymer_protocol as p
    for name in ["SelectionLedger", "ClaimOutcome", "OperatorCredit", "ExecutedOutcome",
                 "operator_of", "credit_factor", "update_ledger", "accumulated_belief", "cell_of"]:
        assert hasattr(p, name), name
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_ledger.py::test_public_exports -v`
Expected: FAIL — `assert hasattr(p, 'SelectionLedger')` is False.

- [ ] **Step 3: Add the exports** — in `src/polymer_protocol/__init__.py`:

Add imports (with the other `from .` imports):

```python
from .belief import accumulated_belief
from .ledger import (
    ClaimOutcome, ExecutedOutcome, OperatorCredit, SelectionLedger,
    credit_factor, operator_of, update_ledger,
)
from .select import cell_of
```

(If `belief`/`select` symbols are already partially imported in `__init__`, merge rather than duplicate.) Append these names to `__all__`:

```python
    "SelectionLedger", "ClaimOutcome", "OperatorCredit", "ExecutedOutcome",
    "operator_of", "credit_factor", "update_ledger", "accumulated_belief", "cell_of",
```

- [ ] **Step 4: Run the FULL gate**

```bash
cd /Users/zbb2/Desktop/polymer-claims/protocol
uv run pytest -q
uv run ruff check src tests
uv run pytest tests/test_isolation.py -q
```
Expected: ALL tests pass; ruff clean; isolation guard (3 tests) passes — no new grammar import of protocol. STOP and report if any fail.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/__init__.py protocol/tests/test_ledger.py
git commit -m "feat(protocol): export SELECT #3b public surface

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: README + CONTINUE docs

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Get the protocol test count**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q 2>&1 | tail -1` — note "N passed"; call it `<N>`.

- [ ] **Step 2: Update `README.md`** — update the protocol table row to:

```markdown
| `protocol/` | `polymer_protocol` | ✅ Sub-projects #1 + #2 + #3a + #3b + #4a (assessment spine + oracle dossier + SELECT [value engine + QD/heterodox/Goodhart/accumulating belief] + GENERATE proposer bus) — <N> tests |
```

Add this paragraph after the GENERATE paragraph:

> **SELECT #3b** hardens the valve against monoculture and reward-hacking on a threaded
> `SelectionLedger` (`run_cycle(..., ledger=)` in/out — `Corpus` stays grammar-IR-only). Belief now
> *accumulates* per claim across cycles from realized outcomes (with a settled-concentration EIG
> guard); a per-operator **surprise-Goodhart** credit discounts the fill-order priority of proposers
> whose high-EIG claims fail to ground (Pareto front + belief stay undistorted); a **quality-diversity**
> portfolio spreads the budget across structural cells `(pattern, subject-kind)` with per-cell caps;
> and a **heterodox reserve lane** pursues dominated/contrarian candidates the main lane would never
> pick. The hardening is OFF by default (`reserve_fraction=0.0`, `cell_cap_fraction=1.0` → exact #3a
> back-compat); a deployment turns it on with the recommended `0.2`/`0.5`.

- [ ] **Step 3: Update `docs/superpowers/CONTINUE.md`**

Mark #3b DONE on branch `feat/select-qd-belief-3b` (merge SHA `<merge-sha pending>`). Repoint the IMMEDIATE NEXT ACTION toward the open fronts: **#4b GENERATE** (embedding/LLM operators + credit ledger + provisional-link mechanism), **#5 daemons** (DRIFT / ORACLE-VALIDATION / REPRESENTATION RED-TEAM + loop-economics — note the surprise-Goodhart ledger + tail-coverage now have a home), or the grammar **`representation_revision` meta-tier**. List the load-bearing #3b decisions: (1) cross-cycle state in a threaded `SelectionLedger`, NOT a 5th Corpus collection (Corpus stays grammar-IR-only); (2) accumulating belief (prior + outcomes) + settled-concentration EIG guard (closes the #3a quadrature follow-up); (3) surprise-Goodhart credit discounts *fill-order density* (optimistic smoothing → exact #3a back-compat; Pareto front + high-EIG signal stay raw); (4) QD structural cells + per-cell caps; (5) heterodox reserve lane for dominated candidates; (6) features OFF by default for back-compat (recommended 0.2/0.5 passed explicitly); (7) zero grammar changes. Keep the existing CONTINUE format.

- [ ] **Step 4: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add README.md docs/superpowers/CONTINUE.md
git commit -m "docs: record SELECT #3b in README + CONTINUE primer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final review

After Task 8, dispatch the whole-package Opus review (per subagent-driven-development), then `superpowers:finishing-a-development-branch` (merge no-ff to main, verify the full suite on the merged result, delete the branch). Update the memory file `project_polymer_claims_knowledge_protocol.md` + `MEMORY.md` with the #3b merge SHA and the load-bearing decisions.

## Progress Log

- (fill in per task: commit SHA + any decisions/deviations)
