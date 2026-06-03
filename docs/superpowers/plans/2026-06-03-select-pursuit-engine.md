# SELECT #3a Pursuit Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the protocol's dumb execute-all driver with a value-ranked, budget-limited SELECT stage — a minimal Beta–Bernoulli posterior → real expected-information-gain, structural stakes, structured cost, a Pareto-front budget knapsack — and a cardinality-scaled Benjamini–Hochberg VERIFY bar.

**Architecture:** All new code is protocol-side (`polymer_protocol`), zero grammar changes. Three pure leaf modules (`belief`, `stakes`, `cost`) feed a `select_stage` that scores candidates on `ValueVector(eig, stakes)` under a structured cost, selects under a budget, and stamps `provenance.search_cardinality`. `commit` gains an `only=` filter so only selected claims are locked/executed; `verify_stage` consumes the stamped cardinality to apply a BH significance bar; `run_cycle` wires it together. Everything stays a pure `Corpus`-transform; determinism via fixed-node quadrature + lexicographic tie-breaks.

**Tech Stack:** Python 3.14, Pydantic v2 (frozen `_Model`), `uv` for env/test, `pytest`. Stdlib `math` only (no `scipy`/`numpy`). One-way dependency `polymer_protocol` → `polymer_grammar`.

**Spec:** `docs/superpowers/specs/2026-06-03-select-pursuit-engine-design.md`

---

## Conventions for every task

- Work in `protocol/`. Run tests with `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q`.
- Run a single test: `uv run pytest tests/<file>::<test> -v`.
- All new models subclass `_Model` from `polymer_protocol.base` (frozen, `extra="forbid"`, tuples not lists).
- Keep `ruff` clean: `uv run ruff check src tests`.
- Commit after each task with the message shown. Commits are LOCAL only — do not push.
- v1 tunable constants (spec §11): `KAPPA_MIN = 2.0`, `KAPPA_MAX = 20.0`, `EPS = 1e-6`, quadrature `N = 64`, `LICENSED_STAKE_WEIGHT = 2.0`, `COST_FLOOR = 1e-6`, BH `Q = 0.10`. Define each as a module-level named constant where it is used — never a bare literal in a function body.

---

## File Structure

| File | New/Modify | Responsibility |
|---|---|---|
| `src/polymer_protocol/belief.py` | new | `Beta`, `prior_belief(claim)`, `expected_information_gain(beta)` |
| `src/polymer_protocol/stakes.py` | new | `dependency_cone(corpus, claim_id)`, `stakes(corpus, claim_id)` |
| `src/polymer_protocol/cost.py` | new | `CostVector`, `CostWeights`, `CostModel`, `aggregate_cost` |
| `src/polymer_protocol/select.py` | new | `ValueVector`, `ValueWeights`, `SelectionDecision`, `SelectionRecord`, `select_stage` |
| `src/polymer_protocol/commit.py` | modify | add `only=` filter |
| `src/polymer_protocol/verify.py` | modify | cardinality-scaled BH bar |
| `src/polymer_protocol/cycle.py` | modify | insert `select_stage`; thread cost/budget/weights; `commit(only=...)`; return `SelectionRecord` |
| `src/polymer_protocol/corpus.py` | modify | add `selection: SelectionRecord` field to `CycleResult` |
| `src/polymer_protocol/__init__.py` | modify | export new public symbols |
| `tests/test_belief.py` | new | belief/EIG tests |
| `tests/test_stakes.py` | new | stakes tests |
| `tests/test_cost.py` | new | cost tests |
| `tests/test_select.py` | new | select_stage tests |
| `tests/test_commit.py` | modify | `only=` filter tests |
| `tests/test_verify.py` | modify | BH bar tests |
| `tests/test_cycle.py` | modify | integration tests |

---

### Task 1: `belief.py` — Beta model + prior from strength

**Files:**
- Create: `src/polymer_protocol/belief.py`
- Test: `tests/test_belief.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_belief.py
from polymer_grammar import StrengthVector

from polymer_protocol.belief import Beta, prior_belief
from tests.conftest import make_claim


def test_prior_for_none_strength_is_uniform():
    c = make_claim("a")  # strength defaults to None
    assert prior_belief(c) == Beta(alpha=1.0, beta=1.0)


def test_prior_mean_tracks_evidence_against_null():
    # high evidence_against_null, low uncertainty -> mean high, concentrated
    sv = StrengthVector(magnitude=0.5, uncertainty=0.0, evidence_against_null=0.8,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    c = make_claim("a", strength=sv)
    b = prior_belief(c)
    # kappa = 2 + (20-2)*(1-0) = 20 ; alpha = 0.8*20 = 16 ; beta = 0.2*20 = 4
    assert b.alpha == 16.0
    assert b.beta == 4.0
    assert abs(b.alpha / (b.alpha + b.beta) - 0.8) < 1e-9


def test_prior_concentration_drops_with_uncertainty():
    sv = StrengthVector(magnitude=0.5, uncertainty=1.0, evidence_against_null=0.5,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    c = make_claim("a", strength=sv)
    b = prior_belief(c)
    # kappa = 2 + 18*(1-1) = 2 ; alpha = beta = 1.0
    assert b.alpha == 1.0 and b.beta == 1.0


def test_beta_is_frozen_and_proper():
    b = Beta(alpha=2.0, beta=3.0)
    import pytest
    with pytest.raises(Exception):
        b.alpha = 5.0  # frozen
    # floor keeps it proper even for extreme strength
    sv = StrengthVector(magnitude=0.0, uncertainty=0.0, evidence_against_null=1.0,
                        severity=0.0, world_contact=0.0, explanatory_virtue=0.0)
    pb = prior_belief(make_claim("a", strength=sv))
    assert pb.alpha > 0.0 and pb.beta > 0.0  # beta floored above 0 despite mean=1.0
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_belief.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.belief'`

- [ ] **Step 3: Implement `Beta` + `prior_belief`**

```python
# src/polymer_protocol/belief.py
"""The minimal posterior: a Beta credence a claim will license, from its StrengthVector.

Pure and deterministic (spec §3.1-3.2). No new grammar fields; reads only the existing
6-axis StrengthVector. strength=None -> Beta(1,1) (the honest know-nothing prior, which
yields maximum EIG).
"""
from __future__ import annotations

from polymer_grammar import Claim

from .base import _Model

KAPPA_MIN = 2.0
KAPPA_MAX = 20.0
EPS = 1e-6


class Beta(_Model):
    alpha: float
    beta: float


def prior_belief(claim: Claim) -> Beta:
    s = claim.strength
    if s is None:
        return Beta(alpha=1.0, beta=1.0)
    mu = min(1.0, max(0.0, s.evidence_against_null))
    kappa = KAPPA_MIN + (KAPPA_MAX - KAPPA_MIN) * (1.0 - s.uncertainty)
    alpha = max(EPS, mu * kappa)
    beta = max(EPS, (1.0 - mu) * kappa)
    return Beta(alpha=alpha, beta=beta)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_belief.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/belief.py protocol/tests/test_belief.py
git commit -m "feat(protocol): Beta posterior + prior_belief from StrengthVector

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `belief.py` — expected information gain (EIG)

**Files:**
- Modify: `src/polymer_protocol/belief.py`
- Test: `tests/test_belief.py`

EIG is the mutual information `I(Y; theta) = H_b(mu) - E_theta[H_b(theta)]` in bits, where
`H_b` is binary entropy, `mu = alpha/(alpha+beta)`, and the expectation is a fixed-node
quadrature over `[0,1]` of `H_b(t) * pdf_Beta(t)`. Closed form, deterministic, stdlib only.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_belief.py
from polymer_protocol.belief import expected_information_gain


def test_eig_of_uniform_is_maximal():
    eig_uniform = expected_information_gain(Beta(alpha=1.0, beta=1.0))
    eig_concentrated = expected_information_gain(Beta(alpha=50.0, beta=50.0))
    eig_certain = expected_information_gain(Beta(alpha=100.0, beta=1.0))
    assert eig_uniform > eig_concentrated > eig_certain
    assert eig_uniform > 0.0


def test_eig_is_bounded_and_nonnegative():
    for b in [Beta(alpha=1.0, beta=1.0), Beta(alpha=2.0, beta=8.0),
              Beta(alpha=0.5, beta=0.5), Beta(alpha=30.0, beta=30.0)]:
        eig = expected_information_gain(b)
        assert 0.0 <= eig <= 1.0 + 1e-9


def test_eig_is_deterministic():
    b = Beta(alpha=3.0, beta=7.0)
    assert expected_information_gain(b) == expected_information_gain(b)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_belief.py::test_eig_of_uniform_is_maximal -v`
Expected: FAIL — `ImportError: cannot import name 'expected_information_gain'`

- [ ] **Step 3: Implement EIG**

```python
# add to src/polymer_protocol/belief.py
import math

QUADRATURE_NODES = 64


def _binary_entropy_bits(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def _beta_log_pdf(t: float, alpha: float, beta: float) -> float:
    # log of t^(a-1) (1-t)^(b-1) / B(a,b)
    log_norm = math.lgamma(alpha) + math.lgamma(beta) - math.lgamma(alpha + beta)
    return (alpha - 1.0) * math.log(t) + (beta - 1.0) * math.log(1.0 - t) - log_norm


def expected_information_gain(belief: Beta) -> float:
    """Mutual information I(Y; theta) in bits between one Bernoulli outcome Y and the
    Beta credence theta. EIG = H_b(mu) - E_theta[H_b(theta)], the textbook expected
    uncertainty reduction. Deterministic fixed-node midpoint quadrature for the
    expectation (spec §3.2)."""
    a, b = belief.alpha, belief.beta
    mu = a / (a + b)
    # E_theta[H_b(theta)] via midpoint rule on (0,1); endpoints excluded (H_b=0 there
    # and the Beta log-pdf diverges for alpha/beta < 1).
    n = QUADRATURE_NODES
    h = 1.0 / n
    expected_cond_entropy = 0.0
    for i in range(n):
        t = (i + 0.5) * h
        expected_cond_entropy += _binary_entropy_bits(t) * math.exp(_beta_log_pdf(t, a, b)) * h
    eig = _binary_entropy_bits(mu) - expected_cond_entropy
    return max(0.0, min(1.0, eig))
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_belief.py -v`
Expected: PASS (7 tests total)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/belief.py protocol/tests/test_belief.py
git commit -m "feat(protocol): expected_information_gain via deterministic quadrature

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `stakes.py` — dependency cone + stakes

**Files:**
- Create: `src/polymer_protocol/stakes.py`
- Test: `tests/test_stakes.py`

Stakes = size of a claim's forward dependency cone: claims reachable via defeat edges
(it attacks) plus claims whose conclusion is entailed by it (via `entails_closure`).
LICENSED dependents weighted higher. Pure, uses existing grammar graph functions.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_stakes.py
from polymer_grammar import DefeatEdge, DefeatEdgeKind, FDRLedger, Status

from polymer_protocol.corpus import Corpus
from polymer_protocol.stakes import dependency_cone, stakes
from tests.conftest import make_claim


def _corpus(claims, edges=()):
    return Corpus(claims=tuple(claims), defeat_edges=tuple(edges), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_isolated_claim_has_empty_cone():
    c = make_claim("a")
    corp = _corpus([c])
    assert dependency_cone(corp, "a") == frozenset()
    assert stakes(corp, "a") == 0.0


def test_cone_follows_defeat_edges_transitively():
    a, b, d = make_claim("a"), make_claim("b"), make_claim("d")
    edges = (
        DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="b", target="d", kind=DefeatEdgeKind.REBUT),
    )
    corp = _corpus([a, b, d], edges)
    assert dependency_cone(corp, "a") == frozenset({"b", "d"})
    assert stakes(corp, "a") == 2.0  # b, d both non-LICENSED -> weight 1 each


def test_licensed_dependents_weighted_higher():
    a = make_claim("a")
    b = make_claim("b", status=Status.LICENSED)
    edges = (DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT),)
    corp = _corpus([a, b], edges)
    assert stakes(corp, "a") == 2.0  # one LICENSED dependent at weight 2.0


def test_cone_excludes_self():
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT),)
    corp = _corpus([a, b], edges)
    assert "a" not in dependency_cone(corp, "a")
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_stakes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.stakes'`

- [ ] **Step 3: Implement**

```python
# src/polymer_protocol/stakes.py
"""Stakes: the structural leverage of a claim — the size of its forward dependency cone.

If a claim's grounded status flipped, every claim in its cone would need re-evaluation:
claims it attacks (defeat edges, transitively) and claims whose conclusion it entails
(L1 ENTAILS, via the grammar's entails_closure). An honest weighted count — no hidden
scalarization of the strength vector (spec §3.3).
"""
from __future__ import annotations

from polymer_grammar import Status, entails_closure

from .corpus import Corpus

LICENSED_STAKE_WEIGHT = 2.0


def dependency_cone(corpus: Corpus, claim_id: str) -> frozenset[str]:
    by_id = corpus.by_id()
    # forward reachability over defeat edges (source -> target)
    out: dict[str, list[str]] = {}
    for e in corpus.defeat_edges:
        out.setdefault(e.source, []).append(e.target)
    reached: set[str] = set()
    stack = list(out.get(claim_id, []))
    while stack:
        nxt = stack.pop()
        if nxt in reached or nxt == claim_id:
            continue
        reached.add(nxt)
        stack.extend(out.get(nxt, []))
    # entailment cone: claims whose conclusion is entailed by this claim's conclusion
    seed = by_id.get(claim_id)
    if seed is not None and seed.conclusion is not None:
        entailed_hashes = entails_closure([seed.conclusion.content_hash], corpus.claims)
        for c in corpus.claims:
            if c.id != claim_id and c.conclusion is not None and c.conclusion.content_hash in entailed_hashes:
                reached.add(c.id)
    reached.discard(claim_id)
    return frozenset(reached)


def stakes(corpus: Corpus, claim_id: str) -> float:
    by_id = corpus.by_id()
    total = 0.0
    for dep_id in dependency_cone(corpus, claim_id):
        dep = by_id.get(dep_id)
        if dep is not None and dep.status == Status.LICENSED:
            total += LICENSED_STAKE_WEIGHT
        else:
            total += 1.0
    return total
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_stakes.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/stakes.py protocol/tests/test_stakes.py
git commit -m "feat(protocol): structural stakes from the forward dependency cone

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `cost.py` — structured cost config

**Files:**
- Create: `src/polymer_protocol/cost.py`
- Test: `tests/test_cost.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cost.py
import pytest

from polymer_protocol.cost import CostModel, CostVector, CostWeights, aggregate_cost


def test_resolve_returns_listed_or_default():
    cv = CostVector(wall_latency=5.0)
    model = CostModel(costs=(("a", cv),), default=CostVector(wall_latency=1.0))
    assert model.resolve("a") == cv
    assert model.resolve("missing") == CostVector(wall_latency=1.0)


def test_aggregate_is_weighted_sum_floored():
    cv = CostVector(wall_latency=2.0, capital=3.0, human_hours=0.0,
                    failure_rate=0.0, oracle_queue_depth=0.0)
    w = CostWeights(wall_latency=1.0, capital=2.0)
    assert aggregate_cost(cv, w) == 2.0 * 1.0 + 3.0 * 2.0  # = 8.0


def test_aggregate_never_zero():
    # all-zero cost would divide by zero in value-density; floored instead
    assert aggregate_cost(CostVector(), CostWeights()) >= 1e-6


def test_cost_models_are_frozen():
    with pytest.raises(Exception):
        CostVector().wall_latency = 9.0
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_cost.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.cost'`

- [ ] **Step 3: Implement**

```python
# src/polymer_protocol/cost.py
"""Structured cost — passed-in protocol config (like OracleRegistry), never grammar IR.

A per-claim CostVector aggregated to a single positive scalar budget-consumer by
passed-in weights (spec §3.4). The scalar feeds the value-density fill order in SELECT;
the floor keeps that division safe.
"""
from __future__ import annotations

from pydantic import Field

from .base import _Model

COST_FLOOR = 1e-6


class CostVector(_Model):
    wall_latency: float = Field(default=0.0, ge=0.0)
    capital: float = Field(default=0.0, ge=0.0)
    human_hours: float = Field(default=0.0, ge=0.0)
    failure_rate: float = Field(default=0.0, ge=0.0)
    oracle_queue_depth: float = Field(default=0.0, ge=0.0)


class CostWeights(_Model):
    wall_latency: float = 1.0
    capital: float = 1.0
    human_hours: float = 1.0
    failure_rate: float = 1.0
    oracle_queue_depth: float = 1.0


class CostModel(_Model):
    costs: tuple[tuple[str, CostVector], ...] = ()
    default: CostVector = CostVector()

    def resolve(self, claim_id: str) -> CostVector:
        for cid, cv in self.costs:
            if cid == claim_id:
                return cv
        return self.default


def aggregate_cost(vec: CostVector, weights: CostWeights) -> float:
    total = (
        vec.wall_latency * weights.wall_latency
        + vec.capital * weights.capital
        + vec.human_hours * weights.human_hours
        + vec.failure_rate * weights.failure_rate
        + vec.oracle_queue_depth * weights.oracle_queue_depth
    )
    return max(COST_FLOOR, total)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_cost.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/cost.py protocol/tests/test_cost.py
git commit -m "feat(protocol): structured CostVector/CostModel + aggregate_cost

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `corpus.py` — add `selection` to `CycleResult`

**Files:**
- Modify: `src/polymer_protocol/corpus.py`
- Test: `tests/test_corpus.py`

`CycleResult` must carry the ephemeral `SelectionRecord`. To avoid a circular import
(`select.py` imports `corpus.py`), the record types live in `select.py` and `corpus.py`
imports them lazily inside a `TYPE_CHECKING` block, typing the field as the concrete class
via a forward ref resolved at runtime. Simplest robust approach: define `SelectionDecision`
and `SelectionRecord` in `corpus.py` (they are plain data, no behavior), and have `select.py`
import them from `corpus.py` — matching how `ExecRecord`/`StageAudit` already live in
`corpus.py`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_corpus.py
from polymer_protocol.corpus import (
    CycleResult, SelectionRecord, SelectionDecision, ValueVector,
)


def test_cycle_result_defaults_empty_selection():
    from polymer_grammar import FDRLedger
    from polymer_protocol.corpus import Corpus
    r = CycleResult(corpus=Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)))
    assert r.selection == SelectionRecord()
    assert r.selection.cardinality == 0
    assert r.selection.decisions == ()


def test_selection_record_holds_decisions():
    d = SelectionDecision(claim_id="a", selected=True, value=ValueVector(eig=0.5, stakes=2.0),
                          cost=1.0, rank=0)
    rec = SelectionRecord(decisions=(d,), cardinality=1)
    assert rec.decisions[0].claim_id == "a"
    assert rec.decisions[0].value.eig == 0.5
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_corpus.py::test_cycle_result_defaults_empty_selection -v`
Expected: FAIL — `ImportError: cannot import name 'SelectionRecord' from 'polymer_protocol.corpus'`

- [ ] **Step 3: Implement — move value/record types into `corpus.py`**

Add to `src/polymer_protocol/corpus.py` (after `StageAudit`, before `CycleResult`):

```python
class ValueVector(_Model):
    """Two-axis pursuit value (spec §3.5). Pareto, not a scalar."""

    eig: float = Field(default=0.0, ge=0.0)
    stakes: float = Field(default=0.0, ge=0.0)

    def dominates(self, other: "ValueVector") -> bool:
        ge = self.eig >= other.eig and self.stakes >= other.stakes
        gt = self.eig > other.eig or self.stakes > other.stakes
        return ge and gt


class SelectionDecision(_Model):
    claim_id: str
    selected: bool
    value: ValueVector
    cost: float
    rank: int = Field(default=0, ge=0)


class SelectionRecord(_Model):
    decisions: tuple[SelectionDecision, ...] = ()
    cardinality: int = Field(default=0, ge=0)
```

Then add the field to `CycleResult`:

```python
class CycleResult(_Model):
    corpus: Corpus
    frontier: tuple[str, ...] = ()
    gated_lane: tuple[str, ...] = ()
    audit: tuple[StageAudit, ...] = ()
    selection: SelectionRecord = SelectionRecord()
```

Note: `Field` is already imported in `corpus.py` (`from pydantic import Field, model_validator`).
These value/record types live in `corpus.py` (not `select.py`) to avoid a circular import —
`select.py` imports `Corpus`, and `Corpus`/`CycleResult` need `SelectionRecord`. `select.py`
(Task 6) imports and re-exports them, so the package root still exposes `ValueVector` etc. (The
spec §6 lists them under `select.py` conceptually; this is the concrete placement that keeps
imports acyclic — same pattern as `ExecRecord`/`StageAudit` already living in `corpus.py`.)

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_corpus.py -v`
Expected: PASS (existing corpus tests + 2 new)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/corpus.py protocol/tests/test_corpus.py
git commit -m "feat(protocol): ValueVector + SelectionRecord on CycleResult

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `select.py` — the SELECT stage

**Files:**
- Create: `src/polymer_protocol/select.py`
- Test: `tests/test_select.py`

`select_stage` scores eligible candidates, computes the non-dominated value front, fills
the budget greedily by value-density, stamps `search_cardinality = M` (pool size) on
selected claims (minting a `Provenance` if absent, like `commit`), and returns the new
corpus + a `SelectionRecord`. Eligibility = PENDING + has plan + not safety-gated.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_select.py
from polymer_grammar import FDRLedger, Governance, HazardClass, Status, StrengthVector

from polymer_protocol.corpus import Corpus
from polymer_protocol.cost import CostModel, CostVector, CostWeights
from polymer_protocol.select import ValueWeights, select_stage
from tests.conftest import make_claim, make_plan


def _corpus(claims):
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def _sv(ean):
    return StrengthVector(magnitude=0.5, uncertainty=0.2, evidence_against_null=ean,
                          severity=0.5, world_contact=0.5, explanatory_virtue=0.5)


def _run(corpus, budget=None, cost_model=None):
    return select_stage(
        corpus, budget=budget,
        cost_model=cost_model or CostModel(),
        value_weights=ValueWeights(), cost_weights=CostWeights(),
    )


def test_only_pending_planned_unganged_claims_are_candidates():
    conj = make_claim("conj")  # CONJECTURED, no plan
    planless = make_claim("p", status=Status.PENDING)  # PENDING, no plan
    gated = make_claim("g", status=Status.PENDING, plan=make_plan(0.01, 0.05),
                       governance=Governance(hazard_class=HazardClass.HIGH))
    ok = make_claim("ok", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corp, rec = _run(_corpus([conj, planless, gated, ok]))
    selected = {d.claim_id for d in rec.decisions if d.selected}
    assert selected == {"ok"}
    assert rec.cardinality == 1  # only "ok" was a candidate


def test_unbounded_budget_selects_all_candidates():
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    corp, rec = _run(_corpus([a, b]), budget=None)
    assert {d.claim_id for d in rec.decisions if d.selected} == {"a", "b"}
    assert rec.cardinality == 2


def test_selected_claims_get_cardinality_stamped():
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    corp, rec = _run(_corpus([a, b]))
    for c in corp.claims:
        assert c.provenance is not None
        assert c.provenance.search_cardinality == 2


def test_zero_budget_selects_nothing():
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corp, rec = _run(_corpus([a]), budget=0.0)
    assert all(not d.selected for d in rec.decisions)
    # unselected claim is untouched (no provenance stamped)
    assert corp.by_id()["a"].provenance is None


def test_budget_prefers_higher_value_density():
    # cheap high-evidence claim beats expensive one under a tight budget
    cheap = make_claim("cheap", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv(0.9))
    pricey = make_claim("pricey", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv(0.9))
    cost_model = CostModel(costs=(
        ("cheap", CostVector(wall_latency=1.0)),
        ("pricey", CostVector(wall_latency=100.0)),
    ))
    corp, rec = _run(_corpus([cheap, pricey]), budget=1.0, cost_model=cost_model)
    selected = {d.claim_id for d in rec.decisions if d.selected}
    assert "cheap" in selected and "pricey" not in selected


def test_empty_candidate_pool():
    corp, rec = _run(_corpus([make_claim("conj")]))
    assert rec.decisions == ()
    assert rec.cardinality == 0


def test_select_is_deterministic():
    def build():
        return _corpus([
            make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv(0.5)),
            make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=_sv(0.5)),
        ])
    r1 = _run(build())
    r2 = _run(build())
    assert r1 == r2
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_select.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.select'`

- [ ] **Step 3: Implement**

```python
# src/polymer_protocol/select.py
"""SELECT: the pursuit/value engine — the valve replacing the dumb execute-all driver.

Scores eligible candidates on ValueVector(eig, stakes), takes the non-dominated front,
fills the budget greedily by an explicit value-density, and stamps search_cardinality on
the selected claims. Pure Corpus -> (Corpus, SelectionRecord) (spec §3.5, §4).
"""
from __future__ import annotations

from polymer_grammar import (
    Claim,
    GenerationMode,
    Provenance,
    Status,
    requires_safety_review,
)

from .base import _Model
from .belief import expected_information_gain, prior_belief
from .corpus import Corpus, SelectionDecision, SelectionRecord, ValueVector
from .cost import CostModel, CostWeights, aggregate_cost
from .stakes import stakes


class ValueWeights(_Model):
    eig: float = 1.0
    stakes: float = 1.0


def _is_candidate(claim: Claim) -> bool:
    if claim.status != Status.PENDING or claim.evaluation_plan is None:
        return False
    if claim.governance is not None and requires_safety_review(claim.governance):
        return False
    return True


def _value(corpus: Corpus, claim: Claim) -> ValueVector:
    eig = expected_information_gain(prior_belief(claim))
    return ValueVector(eig=eig, stakes=stakes(corpus, claim.id))


def _density(value: ValueVector, cost: float, w: ValueWeights) -> float:
    return (w.eig * value.eig + w.stakes * value.stakes) / cost


def _stamp_cardinality(claim: Claim, m: int) -> Claim:
    if claim.provenance is None:
        prov = Provenance(generated_by=GenerationMode.IMPORTED, search_cardinality=m)
    else:
        prov = claim.provenance.model_copy(update={"search_cardinality": m})
    return claim.model_copy(update={"provenance": prov})


def select_stage(
    corpus: Corpus,
    *,
    cost_model: CostModel,
    budget: float | None,
    value_weights: ValueWeights,
    cost_weights: CostWeights,
) -> tuple[Corpus, SelectionRecord]:
    candidates = [c for c in corpus.claims if _is_candidate(c)]
    m = len(candidates)
    if m == 0:
        return corpus, SelectionRecord()

    scored = []
    for c in candidates:
        value = _value(corpus, c)
        cost = aggregate_cost(cost_model.resolve(c.id), cost_weights)
        scored.append((c, value, cost))

    # non-dominated value front
    front_ids = set()
    for c, value, _ in scored:
        dominated = any(
            other_v.dominates(value) for oc, other_v, _ in scored if oc.id != c.id
        )
        if not dominated:
            front_ids.add(c.id)

    # fill order: front first, each group by descending value-density, ties by claim_id
    def order_key(item):
        c, value, cost = item
        return (0 if c.id in front_ids else 1, -_density(value, cost, value_weights), c.id)

    ordered = sorted(scored, key=order_key)

    selected_ids = set()
    spent = 0.0
    decisions = []
    for rank, (c, value, cost) in enumerate(ordered):
        take = budget is None or spent + cost <= budget
        if take:
            selected_ids.add(c.id)
            spent += cost
        decisions.append(
            SelectionDecision(claim_id=c.id, selected=take, value=value, cost=cost, rank=rank)
        )

    new_claims = tuple(
        _stamp_cardinality(c, m) if c.id in selected_ids else c for c in corpus.claims
    )
    record = SelectionRecord(
        decisions=tuple(sorted(decisions, key=lambda d: d.claim_id)),
        cardinality=m,
    )
    return corpus.model_copy(update={"claims": new_claims}), record
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_select.py -v`
Expected: PASS (7 tests)

`select.py` imports `ValueVector` from `.corpus` (already in the import list above), so it is
re-exported as `polymer_protocol.select.ValueVector` for callers that expect it there. No
change to the Task-5 test is needed.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/select.py protocol/tests/test_select.py protocol/tests/test_corpus.py
git commit -m "feat(protocol): select_stage — Pareto-front budget knapsack

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `commit.py` — `only=` filter

**Files:**
- Modify: `src/polymer_protocol/commit.py`
- Test: `tests/test_commit.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_commit.py
from polymer_grammar import FDRLedger, Status

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus
from tests.conftest import make_claim, make_plan


def test_commit_only_locks_listed_claims():
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    corp = Corpus(claims=(a, b), fdr_ledger=FDRLedger(target_fdr=0.05))
    out = commit(corp, only=frozenset({"a"}))
    locked = {c.id for c in out.claims
              if c.provenance is not None and c.provenance.preregistration_hash is not None}
    assert locked == {"a"}


def test_commit_none_locks_all_eligible():
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    corp = Corpus(claims=(a, b), fdr_ledger=FDRLedger(target_fdr=0.05))
    out = commit(corp)  # only=None -> pre-#3 behavior
    locked = {c.id for c in out.claims
              if c.provenance is not None and c.provenance.preregistration_hash is not None}
    assert locked == {"a", "b"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_commit.py::test_commit_only_locks_listed_claims -v`
Expected: FAIL — `TypeError: commit() got an unexpected keyword argument 'only'`

- [ ] **Step 3: Implement**

Change the `commit` signature and add the guard. Replace the function definition's header and
the start of the loop body:

```python
def commit(corpus: Corpus, only: frozenset[str] | None = None) -> Corpus:
    new_claims = []
    changed = False
    for c in corpus.claims:
        if only is not None and c.id not in only:
            new_claims.append(c)
            continue
        if c.status != Status.PENDING or c.evaluation_plan is None or _is_locked(c):
            new_claims.append(c)
            continue
        # ... rest unchanged ...
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_commit.py -v`
Expected: PASS (existing commit tests + 2 new)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/commit.py protocol/tests/test_commit.py
git commit -m "feat(protocol): commit only= filter for the selected set

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: `verify.py` — cardinality-scaled BH bar

**Files:**
- Modify: `src/polymer_protocol/verify.py`
- Test: `tests/test_verify.py`

The bar: among executed claims this cycle, treat `p = 1 - evidence_against_null` as a
pseudo-p-value; apply Benjamini–Hochberg with denominator `M = max search_cardinality`
across the executed pool. A claim licenses only if (existing conditions) AND it passes the
bar. **Exemptions (spec §5):** `M <= 1` → identity (bar skipped); `strength is None` →
exempt (no pseudo-p). These keep every existing test green.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_verify.py — the bar's new behavior
from polymer_grammar import (
    FDRLedger, MaterializationContext, Status, StrengthVector,
)

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus
from polymer_protocol.execute import execute_ground
from polymer_protocol.represent import represent
from polymer_protocol.select import ValueWeights, select_stage
from polymer_protocol.cost import CostModel, CostWeights
from polymer_protocol.verify import verify_stage
from tests.conftest import make_claim, make_plan


def _sv(ean):
    return StrengthVector(magnitude=0.5, uncertainty=0.2, evidence_against_null=ean,
                          severity=0.5, world_contact=0.5, explanatory_virtue=0.5)


def _verify_through_select(claims, adapters, ctx):
    corp = Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))
    scaffolding = represent(corp)
    corp, rec = select_stage(corp, budget=None, cost_model=CostModel(),
                             value_weights=ValueWeights(), cost_weights=CostWeights())
    corp = commit(corp, only=frozenset(d.claim_id for d in rec.decisions if d.selected))
    corp, records = execute_ground(corp, adapters, ctx)
    return verify_stage(corp, scaffolding, records)


def test_bar_is_identity_at_cardinality_one(ctx, adapters):
    # single strong claim, M=1 -> licenses regardless of evidence value
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv(0.2))
    out = _verify_through_select([c], adapters, ctx)
    assert out.by_id()["a"].status == Status.LICENSED


def test_none_strength_claim_is_exempt_in_a_pool(ctx, adapters):
    # two None-strength satisfied claims, M=2 -> both still license (exempt)
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    out = _verify_through_select([a, b], adapters, ctx)
    assert out.by_id()["a"].status == Status.LICENSED
    assert out.by_id()["b"].status == Status.LICENSED


def test_weak_evidence_claim_fails_bar_in_a_large_pool(ctx, adapters):
    # one weak-evidence claim competing in a pool of many -> BH bar rejects it.
    # pool: the weak claim + 4 others (all satisfied, None strength so exempt, but they
    # inflate M to 5). p_weak = 1 - 0.10 = 0.90; BH crit (1/5)*0.10 = 0.02; 0.90 > 0.02 -> fail.
    weak = make_claim("weak", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv(0.10))
    others = [make_claim(f"o{i}", status=Status.PENDING, plan=make_plan(0.01, 0.05)) for i in range(4)]
    out = _verify_through_select([weak, *others], adapters, ctx)
    # weak is non-exempt and fails the bar -> stays PENDING (not LICENSED)
    assert out.by_id()["weak"].status == Status.PENDING


def test_strong_evidence_claim_passes_bar_in_a_pool(ctx, adapters):
    # strong-evidence claim in a pool of 2 -> p = 0.05; BH crit (1/2)*0.10 = 0.05; passes.
    strong = make_claim("s", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv(0.95))
    other = make_claim("o", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    out = _verify_through_select([strong, other], adapters, ctx)
    assert out.by_id()["s"].status == Status.LICENSED
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_verify.py::test_weak_evidence_claim_fails_bar_in_a_large_pool -v`
Expected: FAIL — `weak` is currently LICENSED (no bar yet), assertion expects PENDING.

- [ ] **Step 3: Implement the bar**

Add a helper computing the BH-permitted set, and consult it in the LICENSED branch. Add to
`verify.py`:

```python
BH_Q = 0.10


def _permitted_by_bar(corpus: Corpus, exec_records: tuple[ExecRecord, ...]) -> set[str]:
    """Ids of executed claims permitted to license under the cardinality-scaled BH bar.
    M=1 -> all permitted (identity). strength=None -> exempt (always permitted)."""
    by_id = corpus.by_id()
    executed = [by_id[r.claim_id] for r in exec_records if r.claim_id in by_id]
    if not executed:
        return set()
    m = max(
        (c.provenance.search_cardinality for c in executed if c.provenance is not None),
        default=1,
    )
    if m <= 1:
        return {c.id for c in executed}
    permitted = {c.id for c in executed if c.strength is None}  # exempt
    scored = [
        (1.0 - c.strength.evidence_against_null, c.id)
        for c in executed
        if c.strength is not None
    ]
    scored.sort()  # ascending pseudo-p, ties by id
    k_max = 0
    for k, (p, _) in enumerate(scored, start=1):
        if p <= (k / m) * BH_Q:
            k_max = k
    permitted.update(cid for _, cid in scored[:k_max])
    return permitted
```

Then in `verify_stage`, compute the permitted set once before the loop and gate the LICENSED
branch on it:

```python
def verify_stage(corpus, scaffolding, exec_records, oracles=None):
    registry = oracles if oracles is not None else OracleRegistry()
    in_ext = set(scaffolding.grounded_extension)
    rec_by_id = {r.claim_id: r for r in exec_records}
    permitted = _permitted_by_bar(corpus, exec_records)
    new_claims = []
    for c in corpus.claims:
        rec = rec_by_id.get(c.id)
        if rec is None:
            new_claims.append(c)
            continue
        ev = rec.evaluation
        agreed_refuted = (
            ev.agreement and ev.results
            and ev.results[0].verdict == SatisfactionVerdict.REFUTED
        )
        if (ev.satisfaction is not None and c.id in in_ext
                and c.provenance is not None and c.id in permitted):
            # ... unchanged LICENSED branch ...
        elif agreed_refuted or c.id not in in_ext:
            # ... unchanged REJECTED branch ...
        else:
            new_claims.append(c)  # stays PENDING
    return corpus.model_copy(update={"claims": tuple(new_claims)})
```

A claim that fails only the bar (satisfaction present, in extension, but not permitted) falls
through to the `else` branch and stays PENDING — correct: it may license in a later, less
crowded cycle.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_verify.py -v`
Expected: PASS (existing verify tests + 4 new)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/verify.py protocol/tests/test_verify.py
git commit -m "feat(protocol): cardinality-scaled BH bar in verify_stage

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: `cycle.py` — wire SELECT into `run_cycle`

**Files:**
- Modify: `src/polymer_protocol/cycle.py`
- Test: `tests/test_cycle.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_cycle.py
from polymer_protocol.cost import CostModel, CostVector, CostWeights


def test_budget_limits_what_executes(empty_ledger, ctx, adapters):
    # tight budget: only the cheaper claim executes; the pricey one stays PENDING
    from polymer_grammar import StrengthVector
    sv = StrengthVector(magnitude=0.5, uncertainty=0.2, evidence_against_null=0.9,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    # distinct plan values (0.01 vs 0.02) so canonicalize does not collapse them
    cheap = make_claim("cheap", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=sv)
    pricey = make_claim("pricey", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=sv)
    cost_model = CostModel(costs=(
        ("cheap", CostVector(wall_latency=1.0)),
        ("pricey", CostVector(wall_latency=100.0)),
    ))
    corpus = Corpus(claims=(cheap, pricey), fdr_ledger=empty_ledger)
    result = run_cycle(corpus, adapters, ctx, cost_model=cost_model,
                       budget=1.0, cost_weights=CostWeights())
    assert result.corpus.by_id()["cheap"].status == Status.LICENSED
    assert result.corpus.by_id()["pricey"].status == Status.PENDING
    assert result.selection.cardinality == 2
    assert {d.claim_id for d in result.selection.decisions if d.selected} == {"cheap"}


def test_unselected_claim_reappears_next_cycle(empty_ledger, ctx, adapters):
    from polymer_grammar import StrengthVector
    sv = StrengthVector(magnitude=0.5, uncertainty=0.2, evidence_against_null=0.9,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    cheap = make_claim("cheap", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=sv)
    pricey = make_claim("pricey", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=sv)
    cost_model = CostModel(costs=(
        ("cheap", CostVector(wall_latency=1.0)),
        ("pricey", CostVector(wall_latency=100.0)),
    ))
    c1 = run_cycle(Corpus(claims=(cheap, pricey), fdr_ledger=empty_ledger), adapters, ctx,
                   cost_model=cost_model, budget=1.0)
    # second cycle with a big budget: pricey (still PENDING) now executes
    c2 = run_cycle(c1.corpus, adapters, ctx, budget=None)
    assert c2.corpus.by_id()["pricey"].status == Status.LICENSED


def test_audit_includes_select_stage(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert "select_stage" in {a.stage for a in result.audit}
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_cycle.py::test_audit_includes_select_stage -v`
Expected: FAIL — `select_stage` not in audit (and `run_cycle` lacks `cost_model`/`budget` kwargs).

- [ ] **Step 3: Implement the wiring**

In `cycle.py`: import the new pieces, extend the signature (keyword-only new params after
`oracles`), insert `select_stage` between `safety_gate` and `commit`, pass the selected set to
`commit(only=...)`, add the `select_stage` audit line, and put the `SelectionRecord` in the
result.

```python
from .cost import CostModel, CostWeights
from .select import ValueWeights, select_stage


def run_cycle(
    corpus, adapters, ctx, oracles=None, *,
    cost_model: CostModel | None = None,
    budget: float | None = None,
    value_weights: ValueWeights = ValueWeights(),
    cost_weights: CostWeights = CostWeights(),
) -> CycleResult:
    audit = []
    scaffolding = represent(corpus)
    audit.append(StageAudit(stage="represent",
        note=f"{len(scaffolding.grounded_extension)} grounded, {len(scaffolding.frontier)} on frontier",
        count=len(scaffolding.frontier)))

    before_eq = len(corpus.equivalences)
    corpus = canonicalize(corpus)
    audit.append(StageAudit(stage="canonicalize",
        note=f"{len(corpus.equivalences) - before_eq} equivalence edge(s) added",
        count=len(corpus.equivalences) - before_eq))

    corpus, gated = safety_gate(corpus)
    audit.append(StageAudit(stage="safety_gate", note=f"{len(gated)} gated", count=len(gated)))

    corpus, selection = select_stage(
        corpus, cost_model=cost_model or CostModel(), budget=budget,
        value_weights=value_weights, cost_weights=cost_weights,
    )
    n_selected = sum(1 for d in selection.decisions if d.selected)
    audit.append(StageAudit(stage="select_stage",
        note=f"{n_selected}/{selection.cardinality} selected", count=n_selected))

    selected_ids = frozenset(d.claim_id for d in selection.decisions if d.selected)
    locked_before = _locked_ids(corpus)
    corpus = commit(corpus, only=selected_ids)
    n_committed = len(_locked_ids(corpus) - locked_before)
    audit.append(StageAudit(stage="commit", note=f"{n_committed} claim(s) committed", count=n_committed))

    corpus, records = execute_ground(corpus, adapters, ctx)
    audit.append(StageAudit(stage="execute_ground", note=f"{len(records)} executed", count=len(records)))

    executed_ids = {r.claim_id for r in records}
    corpus = verify_stage(corpus, scaffolding, records, oracles)
    n_licensed = sum(1 for c in corpus.claims if c.id in executed_ids and c.status == Status.LICENSED)
    audit.append(StageAudit(stage="verify_stage", note=f"{n_licensed} licensed", count=n_licensed))

    corpus, skipped = integrate(corpus, scaffolding, records)
    n_added = len(records) - len(skipped)
    audit.append(StageAudit(stage="integrate",
        note=f"{n_added} FDR test(s) added ({corpus.fdr_ledger.n_tests} total); {len(skipped)} skipped",
        count=n_added))

    frontier = represent(corpus).frontier
    present = set(corpus.by_id())
    gated_lane = tuple(g for g in gated if g in present)
    return CycleResult(
        corpus=corpus, frontier=frontier, gated_lane=gated_lane,
        audit=tuple(audit), selection=selection,
    )
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_cycle.py -v`
Expected: PASS — new tests pass. **Existing `test_cycle.py` tests must also still pass**
(single-claim and None-strength claims are bar-exempt; the `select_stage` audit line is now
expected — note `test_cycle_licenses_a_satisfied_claim` asserts the exact set of audit stages,
so update that set to include `"select_stage"`).

Update that assertion in `test_cycle_licenses_a_satisfied_claim`:

```python
    assert {a.stage for a in result.audit} == {
        "represent", "canonicalize", "safety_gate", "select_stage", "commit",
        "execute_ground", "verify_stage", "integrate",
    }
```

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/cycle.py protocol/tests/test_cycle.py
git commit -m "feat(protocol): wire select_stage into run_cycle

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: `__init__.py` — exports + full-suite green

**Files:**
- Modify: `src/polymer_protocol/__init__.py`
- Test: whole suite

- [ ] **Step 1: Write the failing test**

```python
# tests/test_select.py — append
def test_public_exports():
    import polymer_protocol as p
    for name in ["select_stage", "ValueVector", "ValueWeights", "SelectionRecord",
                 "SelectionDecision", "Beta", "prior_belief", "expected_information_gain",
                 "stakes", "dependency_cone", "CostVector", "CostModel", "CostWeights",
                 "aggregate_cost"]:
        assert hasattr(p, name), name
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_select.py::test_public_exports -v`
Expected: FAIL — `assert hasattr(p, 'select_stage')` is False.

- [ ] **Step 3: Add the exports**

Add to `src/polymer_protocol/__init__.py` imports and `__all__`:

```python
from .belief import Beta, expected_information_gain, prior_belief
from .cost import CostModel, CostVector, CostWeights, aggregate_cost
from .corpus import (
    Corpus, CycleResult, CycleScaffolding, ExecRecord, StageAudit,
    SelectionDecision, SelectionRecord, ValueVector,
)
from .select import ValueWeights, select_stage
from .stakes import dependency_cone, stakes
```

and append to `__all__`:
`"Beta", "prior_belief", "expected_information_gain", "stakes", "dependency_cone",
"CostVector", "CostModel", "CostWeights", "aggregate_cost", "select_stage", "ValueVector",
"ValueWeights", "SelectionRecord", "SelectionDecision"`.

(The existing `from .corpus import (...)` line should be merged with the new names rather than
duplicated.)

- [ ] **Step 4: Run the FULL suite + ruff + isolation**

```bash
cd /Users/zbb2/Desktop/polymer-claims/protocol
uv run pytest -q
uv run ruff check src tests
```
Expected: ALL tests pass (existing #1/#2 + all new); ruff clean. The isolation guard
(`tests/test_isolation.py`) must still pass — no new grammar import of protocol.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/__init__.py protocol/tests/test_select.py
git commit -m "feat(protocol): export SELECT #3a public surface

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: README + CONTINUE + grammar/protocol test counts

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Update the protocol status row in `README.md`**

In the "Protocol runtime" section, update the table row and add a SELECT paragraph:

```markdown
| `protocol/` | `polymer_protocol` | ✅ Sub-projects #1 + #2 + #3a (assessment spine + oracle dossier + SELECT pursuit engine) — <N> tests |
```

Add after the oracle paragraph:

> `run_cycle` no longer executes every committed claim. The **SELECT** stage ranks eligible
> PENDING claims on a two-axis value `(expected-information-gain, stakes)` under a structured,
> passed-in cost and a budget, executing only the selected subset (`run_cycle(..., cost_model=,
> budget=)`). EIG comes from a minimal Beta–Bernoulli posterior derived from each claim's
> `StrengthVector`; stakes is the size of its forward dependency cone. The search cardinality of
> each selection is recorded and **tightens VERIFY's significance bar** (a Benjamini–Hochberg
> selective-inference correction) as the competed pool grows — identity at cardinality 1.
> Quality-diversity portfolios, a heterodox reserve lane, and cross-cycle accumulating belief
> are the deferred **#3b** slice.

(Replace `<N>` with the protocol test count printed by `uv run pytest -q`.)

- [ ] **Step 2: Update `docs/superpowers/CONTINUE.md`**

Mark #3a done (with its merge SHA placeholder to fill after merge), and repoint the IMMEDIATE
NEXT ACTION at #3b (QD portfolio + heterodox lane + cross-cycle belief) or #4 GENERATE, per the
build order. Keep it to the existing CONTINUE format.

- [ ] **Step 3: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add README.md docs/superpowers/CONTINUE.md
git commit -m "docs: record SELECT #3a in README + CONTINUE primer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final review

After Task 11, dispatch the whole-package Opus review (per subagent-driven-development), then
`superpowers:finishing-a-development-branch` (merge no-ff to main, verify the full suite on the
merged result, delete the branch). Update the memory file
`project_polymer_claims_knowledge_protocol.md` + `MEMORY.md` with the #3a merge SHA and the five
load-bearing decisions (minimal-posterior EIG, structural stakes, passed-in cost, Pareto-front
budget knapsack, cardinality-scaled BH bar with M=1/None-strength exemptions).

## Progress Log

- (fill in per task: commit SHA + any decisions/deviations)
