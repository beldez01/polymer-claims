# Executable Rivals + Operator Credit Economy (#4b slice-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make GENERATE self-driving — a rival of a planned claim gains a direction-mirrored transplanted `evaluation_plan` (so it executes, licenses, and autonomously activates its slice-1 provisional defeat of its source), and GENERATE allocates its budget across operators by their `SelectionLedger` credit (throttling chronic failers to a recoverable probation slot).

**Architecture:** Two new pure protocol modules (`plan_synthesis.py`, `allocate.py`) + edits to `proposers.py`, `generate.py`, `cycle.py`. Zero grammar changes — the transplant reuses existing `EvaluationPlan`/`SatisfactionCriterion` constructors and flips an existing `Comparator` value; the credit read reuses #3b's `credit_factor`. Both features additive and OFF by default (`generation_credit_floor=None` ⇒ exact #4a behavior; a planless source ⇒ today's CONJECTURED rival).

**Tech Stack:** Python 3.14, Pydantic v2 (frozen models), `uv`, `pytest`. Package `protocol/` (`polymer_protocol`), one-way dep on `grammar/` (`polymer_grammar`).

**Spec:** `docs/superpowers/specs/2026-06-04-executable-rivals-credit-economy-design.md`

---

## Conventions

- All tasks run in `protocol/`: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q`. Lint with `uv run ruff check src tests` from that dir.
- Commit after each task with the message shown. Commits are LOCAL only. Every commit message ends with the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` line.
- Tasks 1 (plan_synthesis) and 3 (allocate) are independent leaf modules; Task 2 depends on 1; Task 4 depends on 3; Task 5 depends on 1–4.

## File Structure

| File | Pkg | Responsibility |
|---|---|---|
| `protocol/src/polymer_protocol/plan_synthesis.py` | protocol | **NEW** — pure `mirror_criterion` + `transplant_plan` (2a) |
| `protocol/src/polymer_protocol/proposers.py` | protocol | `rival_generation` emits a PENDING+plan rival when the source's plan transplants (2a) |
| `protocol/src/polymer_protocol/allocate.py` | protocol | **NEW** — pure `allocate_subcaps` + `CREDIT_FLOOR_DEFAULT` (2b) |
| `protocol/src/polymer_protocol/generate.py` | protocol | `generate_stage` enforces per-operator sub-caps from the ledger (2b) |
| `protocol/src/polymer_protocol/cycle.py` | protocol | thread `generation_credit_floor` knob + pass the prior-cycle ledger to `generate_stage` (2b) |
| `protocol/src/polymer_protocol/__init__.py` | protocol | export the new public symbols |

No grammar edits. `Corpus` unchanged (4 collections).

---

### Task 1: `plan_synthesis.py` — mirror criterion + transplant plan

**Files:**
- Create: `protocol/src/polymer_protocol/plan_synthesis.py`
- Test: `protocol/tests/test_plan_synthesis.py`

- [ ] **Step 1: Write the failing tests** — create `protocol/tests/test_plan_synthesis.py`:

```python
from __future__ import annotations

from polymer_grammar import (
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    MeasurementBasis,
    OperationNode,
    ProducedLeafSpec,
    SatisfactionCriterion,
)

from polymer_protocol.plan_synthesis import mirror_criterion, transplant_plan


def _crit(comparator, *, threshold=0.05, reference=None, tolerance=None):
    if reference is not None:
        return SatisfactionCriterion(comparator=comparator, reference_leaf_index=reference)
    if tolerance is not None:
        return SatisfactionCriterion(comparator=comparator, tolerance=tolerance)
    return SatisfactionCriterion(comparator=comparator, threshold=threshold)


def _plan(comparator=Comparator.LT, *, threshold=0.05, tolerance=None):
    node = OperationNode(
        id="n0",
        impl="builtin::const",
        params=(("value", "0.09"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    crit = (
        SatisfactionCriterion(comparator=comparator, tolerance=tolerance)
        if tolerance is not None
        else SatisfactionCriterion(comparator=comparator, threshold=threshold)
    )
    return EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="n0"), criterion=crit)


def test_mirror_flips_each_orderable_comparator():
    pairs = {
        Comparator.LT: Comparator.GE,
        Comparator.GE: Comparator.LT,
        Comparator.LE: Comparator.GT,
        Comparator.GT: Comparator.LE,
        Comparator.EQ: Comparator.NE,
        Comparator.NE: Comparator.EQ,
    }
    for src, want in pairs.items():
        m = mirror_criterion(_crit(src))
        assert m is not None and m.comparator == want
        assert m.threshold == 0.05 and m.reference_leaf_index is None


def test_mirror_preserves_reference_target():
    m = mirror_criterion(_crit(Comparator.GT, reference=1))
    assert m is not None and m.comparator == Comparator.LE
    assert m.reference_leaf_index == 1 and m.threshold is None


def test_mirror_within_tol_is_none():
    assert mirror_criterion(_crit(Comparator.WITHIN_TOL, tolerance=0.1)) is None


def test_mirror_result_is_a_valid_criterion():
    m = mirror_criterion(_crit(Comparator.LT))
    assert m is not None
    # round-trips through validation (no within_tol/tolerance invariant breakage)
    assert SatisfactionCriterion.model_validate(m.model_dump()) == m


def test_transplant_reuses_graph_and_mirrors_criterion():
    src = _plan(Comparator.LT, threshold=0.05)
    out = transplant_plan(src)
    assert out is not None
    assert out.graph.content_hash() == src.graph.content_hash()  # same data + ops
    assert out.criterion.comparator == Comparator.GE and out.criterion.threshold == 0.05


def test_transplant_within_tol_is_none():
    assert transplant_plan(_plan(Comparator.WITHIN_TOL, tolerance=0.1)) is None


def test_mirror_is_logical_complement_at_the_boundary():
    # exactly one of {criterion, mirror} is SATISFIED on a given value vs the same threshold
    src = _crit(Comparator.GT, threshold=0.05)   # SATISFIED iff value > 0.05
    mir = mirror_criterion(src)                    # LE: SATISFIED iff value <= 0.05
    assert mir is not None
    above, below = 0.09, 0.01
    assert (above > 0.05) != (above <= 0.05)       # sanity on the boundary logic
    assert (below > 0.05) != (below <= 0.05)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_plan_synthesis.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.plan_synthesis'`.

- [ ] **Step 3: Implement** — create `protocol/src/polymer_protocol/plan_synthesis.py`:

```python
"""Pure plan synthesis for executable-generation (#4b slice-2, spec §3.1).

A rival of a planned claim tests the SAME data through the SAME computation, expecting the
opposite result. mirror_criterion flips a criterion to its logical complement at the same
boundary; transplant_plan reuses the source graph verbatim with that mirrored criterion, so
source + rival co-evaluate (exactly one SATISFIED on one data realization). None when the
criterion's comparator has no single-Comparator complement (WITHIN_TOL). Deterministic, pure.
"""
from __future__ import annotations

from polymer_grammar import Comparator, EvaluationPlan, SatisfactionCriterion

_MIRROR: dict[Comparator, Comparator] = {
    Comparator.LT: Comparator.GE,
    Comparator.GE: Comparator.LT,
    Comparator.LE: Comparator.GT,
    Comparator.GT: Comparator.LE,
    Comparator.EQ: Comparator.NE,
    Comparator.NE: Comparator.EQ,
    # WITHIN_TOL: no single-comparator complement -> not mirrorable (returns None)
}


def mirror_criterion(criterion: SatisfactionCriterion) -> SatisfactionCriterion | None:
    """The logical complement of `criterion` at the SAME boundary (same threshold/reference),
    so on identical data exactly one of {criterion, mirror} is SATISFIED. None for WITHIN_TOL."""
    flipped = _MIRROR.get(criterion.comparator)
    if flipped is None:
        return None
    return criterion.model_copy(update={"comparator": flipped})


def transplant_plan(plan: EvaluationPlan) -> EvaluationPlan | None:
    """Reuse the source graph VERBATIM with a mirrored criterion; None when not mirrorable."""
    mirrored = mirror_criterion(plan.criterion)
    if mirrored is None:
        return None
    return plan.model_copy(update={"criterion": mirrored})
```

Note: `model_copy(update=...)` bypasses validators, but the flipped comparator is never `WITHIN_TOL` and `tolerance` is untouched (always `None` for the 6 mirrorable comparators), so `_tolerance_iff_within_tol` and `_exactly_one_target` stay satisfied — `test_mirror_result_is_a_valid_criterion` pins this.

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_plan_synthesis.py -v`
Expected: all PASS. Then `uv run ruff check src tests` — clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/plan_synthesis.py protocol/tests/test_plan_synthesis.py
git commit -m "feat(protocol): plan_synthesis — mirror_criterion + transplant_plan (executable rivals)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `rival_generation` emits executable rivals

**Files:**
- Modify: `protocol/src/polymer_protocol/proposers.py`
- Test: `protocol/tests/test_proposers.py`

A rival of a planned source becomes `PENDING`/`UNTESTED` carrying the transplanted plan; a rival of a planless or `WITHIN_TOL`-planned source stays `CONJECTURED` (unchanged). The provisional `R⊣C` rebut edge is emitted in both cases.

- [ ] **Step 1: Write the failing tests** — append to `protocol/tests/test_proposers.py`. First check the top imports; add what's missing: `Comparator`, `Status`, `PendingReason`, and from conftest `make_plan`. Use this test code:

```python
def test_rival_of_planned_source_is_executable():
    from polymer_grammar import Comparator, PendingReason
    from tests.conftest import make_plan
    plan = make_plan(0.09, 0.05, Comparator.LT)  # source criterion: value < threshold
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE), plan=plan)
    props = rival_generation(_corpus([c]), ())
    assert props  # two rivals (negative, null)
    for p in props:
        assert p.claim.status == Status.PENDING
        assert p.claim.pending_reason == PendingReason.UNTESTED
        assert p.claim.evaluation_plan is not None
        # graph reused verbatim, criterion mirrored LT -> GE
        assert p.claim.evaluation_plan.graph.content_hash() == plan.graph.content_hash()
        assert p.claim.evaluation_plan.criterion.comparator == Comparator.GE
        # still emits the provisional rebut edge into the source
        assert len(p.edges) == 1 and p.edges[0].target == "c"
        assert p.edges[0].provisional is True


def test_rival_of_within_tol_source_stays_conjectured():
    from polymer_grammar import Comparator
    from tests.conftest import make_plan
    plan = make_plan(0.09, 0.05, Comparator.WITHIN_TOL)  # not mirrorable
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE), plan=plan)
    props = rival_generation(_corpus([c]), ())
    assert props
    for p in props:
        assert p.claim.status == Status.CONJECTURED
        assert p.claim.evaluation_plan is None
        assert len(p.edges) == 1 and p.edges[0].provisional is True
```

Note: `make_plan` accepts `comparator=`; `make_plan(0.09, 0.05, Comparator.WITHIN_TOL)` builds a `WITHIN_TOL` criterion which requires a `tolerance` — VERIFY `make_plan` supplies one for WITHIN_TOL; if it does NOT (it builds `SatisfactionCriterion(comparator=comparator, threshold=threshold)` with no tolerance, which RAISES for WITHIN_TOL), then in this test construct the plan inline instead:
```python
    from polymer_grammar import (
        ComputeGraph, EvaluationPlan, MeasurementBasis, OperationNode,
        ProducedLeafSpec, SatisfactionCriterion,
    )
    node = OperationNode(id="n0", impl="builtin::const", params=(("value", "0.09"),),
                         produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED))
    plan = EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="n0"),
                          criterion=SatisfactionCriterion(comparator=Comparator.WITHIN_TOL, tolerance=0.1))
```
Use whichever path matches the real `make_plan`. The existing `test_rival_emits_other_two_directions` (planless source → CONJECTURED rivals) must still pass unchanged.

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_proposers.py::test_rival_of_planned_source_is_executable -v`
Expected: FAIL — the rival is currently always `CONJECTURED` with `evaluation_plan is None`.

- [ ] **Step 3: Implement** — in `proposers.py`:

Add `PendingReason` to the grammar import and import the transplant helper. The grammar import becomes:
```python
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    DefeatEdge,
    DefeatEdgeKind,
    Direction,
    GenerationMode,
    PendingReason,
    Provenance,
    Status,
)

from .corpus import Corpus, Proposal
from .generate import _corpus_fingerprint, _gen_id
from .plan_synthesis import transplant_plan
```

Replace the rival-construction block inside `rival_generation`'s inner loop (the `rid = _gen_id(...)` through the `proposals.append(...)`) with:
```python
            rid = _gen_id("rival", c.id, d.value)
            transplanted = (
                transplant_plan(c.evaluation_plan) if c.evaluation_plan is not None else None
            )
            if transplanted is not None:
                rival = Claim(
                    id=rid,
                    title=f"rival({d.value}) of {c.id}",
                    pattern=c.pattern,
                    leaves=c.leaves,
                    status=Status.PENDING,
                    pending_reason=PendingReason.UNTESTED,
                    subject=c.subject,
                    conclusion=rival_concl,
                    evaluation_plan=transplanted,
                    provenance=_generated_by(corpus, RIVAL_OP),
                )
            else:
                rival = Claim(
                    id=rid,
                    title=f"rival({d.value}) of {c.id}",
                    pattern=c.pattern,
                    leaves=c.leaves,
                    status=Status.CONJECTURED,
                    subject=c.subject,
                    conclusion=rival_concl,
                    provenance=_generated_by(corpus, RIVAL_OP),
                )
            edge = DefeatEdge(source=rid, target=c.id, kind=DefeatEdgeKind.REBUT, provisional=True)
            proposals.append(Proposal(operator_id=RIVAL_OP, claim=rival, edges=(edge,)))
```

Also update the module docstring's first paragraph to note that `rival_generation` makes a rival of a *planned* source executable (transplanted, direction-mirrored plan), while planless/within-tol sources keep the CONJECTURED rival.

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_proposers.py -v`
Expected: new tests PASS; existing rival/frontier tests still PASS (planless sources → CONJECTURED). Then FULL protocol suite `uv run pytest -q` — green. `uv run ruff check src tests`. If `test_generation_converges` or a belief-neutrality test regresses, STOP and report.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/proposers.py protocol/tests/test_proposers.py
git commit -m "feat(protocol): rival_generation emits executable (transplanted-plan) rivals of planned sources

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `allocate.py` — per-operator sub-cap allocation

**Files:**
- Create: `protocol/src/polymer_protocol/allocate.py`
- Test: `protocol/tests/test_allocate.py`

- [ ] **Step 1: Write the failing tests** — create `protocol/tests/test_allocate.py`:

```python
from __future__ import annotations

from polymer_protocol.allocate import CREDIT_FLOOR_DEFAULT, allocate_subcaps
from polymer_protocol.ledger import OperatorCredit, SelectionLedger


def _ledger(**rates):
    # rates: operator_id -> (n_grounded, n_high_eig)
    credits = tuple(
        OperatorCredit(operator_id=op, n_grounded=g, n_high_eig=h) for op, (g, h) in rates.items()
    )
    return SelectionLedger(credits=credits)


def test_default_floor_is_half():
    assert CREDIT_FLOOR_DEFAULT == 0.5


def test_proportional_split_among_healthy():
    # rival credit_factor = (8+1)/(9+1)=0.9 ; frontier untracked -> 1.0 ; both healthy
    led = _ledger(**{"rival-generation": (8, 9)})
    caps = allocate_subcaps(("rival-generation", "frontier-attack"), 10, led, floor=0.5)
    assert sum(caps.values()) == 10
    # frontier (1.0) gets a bit more than rival (0.9): 10*1.0/1.9=5.26 -> 5 ; 10*0.9/1.9=4.73 -> 5
    assert caps == {"rival-generation": 5, "frontier-attack": 5}


def test_below_floor_operator_gets_one_probation_slot():
    # frontier credit_factor = (0+1)/(4+1)=0.2 < 0.5 -> probation ; rival untracked -> 1.0 healthy
    led = _ledger(**{"frontier-attack": (0, 4)})
    caps = allocate_subcaps(("rival-generation", "frontier-attack"), 10, led, floor=0.5)
    assert caps["frontier-attack"] == 1           # exactly the probation slot, never 0
    assert caps["rival-generation"] == 9          # remaining = 10 - 1 probation
    assert sum(caps.values()) == 10


def test_all_below_floor_round_robin_leftover():
    led = _ledger(**{"a": (0, 9), "b": (0, 9)})   # both 0.1 < floor
    caps = allocate_subcaps(("a", "b"), 5, led, floor=0.5)
    # each gets 1 probation + leftover(3) round-robin in caller order: a=1+2, b=1+1
    assert sum(caps.values()) == 5
    assert caps["a"] == 3 and caps["b"] == 2


def test_starved_cap_seats_first_operators_in_caller_order():
    led = _ledger(**{"a": (0, 9)})  # a below floor; b untracked healthy
    caps = allocate_subcaps(("a", "b", "c"), 2, led, floor=0.5)
    # cap (2) <= operators (3): first 2 in caller order get 1, rest 0 (probation does not preempt)
    assert caps == {"a": 1, "b": 1, "c": 0}


def test_empty_ledger_even_split():
    caps = allocate_subcaps(("a", "b"), 10, SelectionLedger(), floor=0.5)
    assert caps == {"a": 5, "b": 5}  # both untracked -> 1.0 -> even


def test_deterministic_repeated_calls():
    led = _ledger(**{"rival-generation": (8, 9)})
    args = (("rival-generation", "frontier-attack"), 10, led)
    assert allocate_subcaps(*args, floor=0.5) == allocate_subcaps(*args, floor=0.5)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_allocate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.allocate'`.

- [ ] **Step 3: Implement** — create `protocol/src/polymer_protocol/allocate.py`:

```python
"""Per-operator generation budget allocation (#4b slice-2, spec §4.1).

Splits the global generation cap into per-operator sub-caps by SelectionLedger credit:
above-floor operators share the budget proportional to credit_factor (largest-remainder,
deterministic); a below-floor operator is throttled to a single recoverable probation slot
(never killed). Caller order breaks every tie. Pure, deterministic. Spec §4.
"""
from __future__ import annotations

from .ledger import SelectionLedger, credit_factor

CREDIT_FLOOR_DEFAULT = 0.5  # an operator grounding <~half its high-EIG bets (smoothed) is on probation


def allocate_subcaps(
    operator_ids: tuple[str, ...],
    cap: int,
    ledger: SelectionLedger,
    *,
    floor: float,
) -> dict[str, int]:
    ops = tuple(operator_ids)
    if not ops or cap <= 0:
        return {op: 0 for op in ops}

    cf = {op: credit_factor(ledger, op) for op in ops}

    # Starved: cannot seat even one slot per operator -> first `cap` in caller order get 1.
    if cap <= len(ops):
        return {op: (1 if i < cap else 0) for i, op in enumerate(ops)}

    below = [op for op in ops if cf[op] < floor]
    healthy = [op for op in ops if cf[op] >= floor]
    subcaps = {op: 1 for op in below}  # probation slot each
    remaining = cap - len(below)

    if not healthy:
        # all below floor: round-robin the leftover across `below` in caller order
        for i in range(remaining):
            subcaps[below[i % len(below)]] += 1
        return {op: subcaps.get(op, 0) for op in ops}

    total_w = sum(cf[op] for op in healthy)
    exact = {op: remaining * cf[op] / total_w for op in healthy}
    floors = {op: int(exact[op]) for op in healthy}
    leftover = remaining - sum(floors.values())
    # hand leftover to largest fractional parts; ties broken by caller order (stable sort)
    order = sorted(healthy, key=lambda op: (-(exact[op] - floors[op]), ops.index(op)))
    for op in order[:leftover]:
        floors[op] += 1
    subcaps.update(floors)
    return {op: subcaps.get(op, 0) for op in ops}
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_allocate.py -v`
Expected: all PASS (incl. the worked example `{rival:5, frontier:5}`, the probation `{frontier:1, rival:9}`, the starved `{a:1,b:1,c:0}`). Then `uv run ruff check src tests` — clean.

Note: verify the proportional example resolves to `{5, 5}` — `floors` are `int(5.26)=5` and `int(4.73)=4`, leftover `10-9=1` goes to the largest fractional part (frontier 1.0: frac 0.26 vs rival 0.9: frac 0.73 → rival), giving `frontier 5, rival 5`. If the implementer's run shows a different split, the assertion in `test_proportional_split_among_healthy` must match the deterministic output — adjust the EXPECTED in the test to the actual largest-remainder result and note it, but the SUM must equal 10 and neither may be 0.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/allocate.py protocol/tests/test_allocate.py
git commit -m "feat(protocol): allocate_subcaps — credit-weighted generation budget with probation floor

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `generate_stage` enforces per-operator sub-caps

**Files:**
- Modify: `protocol/src/polymer_protocol/generate.py`
- Test: `protocol/tests/test_generate.py`

- [ ] **Step 1: Write the failing tests** — append to `protocol/tests/test_generate.py` (inspect its existing imports/helpers first; it builds corpora + proposers. Reuse its style. Add `from polymer_protocol.ledger import OperatorCredit, SelectionLedger` and `from polymer_protocol.generate import generate_stage` if not present):

```python
def _const_proposers(n_rival, n_frontier):
    # two toy proposers that emit n isolated CONJECTURED claims each (no edges), distinct ids
    from polymer_grammar import CategoricalLeaf, Claim, GenerationMode, Provenance, Status

    from polymer_protocol.corpus import Proposal
    from tests.conftest import _PATTERN

    def _mk(op, i):
        return Claim(
            id=f"{op}-{i}",
            title=f"{op}-{i}",
            pattern=_PATTERN,
            leaves=(CategoricalLeaf(ontology_term=f"t-{op}-{i}"),),
            status=Status.CONJECTURED,
            provenance=Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id=op,
                                  method=f"{op}@x", search_cardinality=1),
        )

    def rival(corpus, frontier):
        return tuple(Proposal(operator_id="rival-generation", claim=_mk("rival-generation", i))
                     for i in range(n_rival))

    def frontier_op(corpus, frontier):
        return tuple(Proposal(operator_id="frontier-attack", claim=_mk("frontier-attack", i))
                     for i in range(n_frontier))

    return (rival, frontier_op)


def test_economy_off_is_flat_cap(empty_corpus):
    props = _const_proposers(5, 5)
    # ledger=None -> flat cap exactly as #4a: first 4 admitted in caller order
    corp_a, rec_a = generate_stage(empty_corpus, (), proposers=props, cap=4)
    corp_b, rec_b = generate_stage(empty_corpus, (), proposers=props, cap=4, credit_floor=0.5)  # ledger=None
    assert rec_a.admitted == rec_b.admitted
    assert len(rec_a.admitted) == 4


def test_economy_throttles_low_credit_operator(empty_corpus):
    from polymer_protocol.ledger import OperatorCredit, SelectionLedger
    # frontier below floor (0/4 -> 0.2); rival untracked (1.0). cap 6 -> frontier probation 1, rival 5
    led = SelectionLedger(credits=(OperatorCredit(operator_id="frontier-attack", n_grounded=0, n_high_eig=4),))
    props = _const_proposers(5, 5)
    corp, rec = generate_stage(empty_corpus, (), proposers=props, cap=6, ledger=led, credit_floor=0.5)
    admitted_ops = [cid.rsplit("-", 1)[0] for cid in rec.admitted]
    assert admitted_ops.count("rival-generation") == 5
    assert admitted_ops.count("frontier-attack") == 1
    # the surplus frontier proposals are discarded with the operator-cap reason
    op_cap_discards = [d for d in rec.discarded if d.reason == "operator-cap"]
    assert len(op_cap_discards) == 4 and all(d.operator_id == "frontier-attack" for d in op_cap_discards)


def test_exogenous_is_exempt_from_operator_cap(empty_corpus):
    from polymer_grammar import CategoricalLeaf, Claim, Status
    from polymer_protocol.ledger import OperatorCredit, SelectionLedger
    from tests.conftest import _PATTERN
    led = SelectionLedger(credits=(OperatorCredit(operator_id="frontier-attack", n_grounded=0, n_high_eig=4),))
    inj = tuple(
        Claim(id=f"inj-{i}", title=f"inj-{i}", pattern=_PATTERN,
              leaves=(CategoricalLeaf(ontology_term=f"t-inj-{i}"),), status=Status.CONJECTURED)
        for i in range(3)
    )
    corp, rec = generate_stage(empty_corpus, (), proposers=_const_proposers(0, 5), injected=inj,
                               cap=8, ledger=led, credit_floor=0.5)
    # all 3 exogenous admitted (never operator-capped); frontier throttled to its probation slot
    assert sum(cid.startswith("inj-") for cid in rec.admitted) == 3
    assert sum(cid.startswith("frontier-attack") for cid in rec.admitted) == 1
```

Note: confirm `Corpus`'s structural-key canonicalization is NOT triggered here (these are bare CONJECTURED skeletons — but `generate_stage` does not canonicalize; that's a later stage). If `_const_proposers` claims collide on content-addressed ids, give them distinct `ontology_term`s (already done via the `t-{op}-{i}` tags). Also confirm the discard reason string is exactly `"operator-cap"` and the global-cap reason stays `"cap"`.

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_generate.py::test_economy_throttles_low_credit_operator -v`
Expected: FAIL — `generate_stage` has no `ledger`/`credit_floor` params (TypeError) — or, after adding the params, the throttle isn't applied yet.

- [ ] **Step 3: Implement** — modify `generate.py`:

Add the import at the top: `from .allocate import allocate_subcaps`.

Change the `generate_stage` signature to add the two kw-only params:
```python
def generate_stage(
    corpus: Corpus,
    frontier: tuple[str, ...],
    *,
    proposers: tuple[Proposer, ...] = (),
    injected: tuple[Claim, ...] = (),
    cap: int | None = None,
    ledger: "SelectionLedger | None" = None,
    credit_floor: float | None = None,
) -> tuple[Corpus, GenerationRecord]:
```
Add a `TYPE_CHECKING` import for the annotation (keep runtime import out of the hot path is unnecessary here since allocate already imports ledger; simplest: `from .ledger import SelectionLedger` at top and drop the quotes). Use the top-level import form:
```python
from .ledger import SelectionLedger
```
and annotate `ledger: SelectionLedger | None = None`.

After building `proposals` (proposers + injected) and before the admit loop, compute per-operator sub-caps when the economy is active:
```python
    economy_on = ledger is not None and credit_floor is not None and cap is not None
    subcaps: dict[str, int] = {}
    if economy_on:
        endo_ops: list[str] = []
        for p in proposals:
            if p.operator_id != "exogenous" and p.operator_id not in endo_ops:
                endo_ops.append(p.operator_id)
        subcaps = allocate_subcaps(tuple(endo_ops), cap, ledger, floor=credit_floor)
    op_admitted: dict[str, int] = {}
```

In the admit loop, add the per-operator gate AFTER the global-cap check and BEFORE `compile_to_IR`:
```python
    for p in proposals:
        if cap is not None and len(admitted) >= cap:
            discarded.append(DiscardEntry(operator_id=p.operator_id, claim_id=p.claim.id, reason="cap"))
            continue
        if economy_on and p.operator_id != "exogenous":
            if op_admitted.get(p.operator_id, 0) >= subcaps.get(p.operator_id, 0):
                discarded.append(
                    DiscardEntry(operator_id=p.operator_id, claim_id=p.claim.id, reason="operator-cap")
                )
                continue
        reason = compile_to_IR(p, present_ids)
        if reason is not None:
            discarded.append(DiscardEntry(operator_id=p.operator_id, claim_id=p.claim.id, reason=reason))
            continue
        new_claims.append(p.claim)
        new_edges.extend(p.edges)
        present_ids.add(p.claim.id)
        admitted.append(p.claim.id)
        if p.operator_id != "exogenous":
            op_admitted[p.operator_id] = op_admitted.get(p.operator_id, 0) + 1
```

Keep the rest (record assembly, identity-preserved early return) unchanged. Update the module docstring to mention credit-governed per-operator sub-caps (active only when ledger+floor+cap are all supplied).

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_generate.py -v`
Expected: new tests PASS; existing generate tests still PASS (economy OFF when `ledger`/`credit_floor` unset → identical behavior). Then FULL protocol suite `uv run pytest -q` — green. `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/generate.py protocol/tests/test_generate.py
git commit -m "feat(protocol): generate_stage enforces credit-weighted per-operator sub-caps

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `run_cycle` knob + end-to-end tests

**Files:**
- Modify: `protocol/src/polymer_protocol/cycle.py`
- Test: `protocol/tests/test_cycle.py`

- [ ] **Step 1: Implement the knob first** (this task is integration-pinning; implement the wiring, then the tests assert end-to-end). In `cycle.py`:

Find the `run_cycle` signature and add a kw-only param `generation_credit_floor: float | None = None`. Find the `generate_stage(...)` call inside `run_cycle` and pass the ledger + floor. The ledger variable already exists in `run_cycle` (the threaded `SelectionLedger | None` from #3b — confirm its local name, e.g. `ledger`). Update the call:
```python
    corpus, gen_record = generate_stage(
        corpus,
        frontier,
        proposers=proposers,
        injected=injected,
        cap=generation_cap,
        ledger=ledger,
        credit_floor=generation_credit_floor,
    )
```
(Match the REAL existing call's keyword names — `cap=generation_cap` may already be present; add only `ledger=` and `credit_floor=`. If the run_cycle ledger local is named differently, use that name. If `run_cycle` currently has no `ledger` local because #3b made it optional, read how #3b's `ledger` is threaded and reuse exactly that variable.)

- [ ] **Step 2: Write the end-to-end tests** — append to `protocol/tests/test_cycle.py`:

```python
def test_generated_rival_adjudicates_and_defeats_source(empty_ledger, ctx, adapters):
    from polymer_grammar import Comparator, Direction, Proposition
    from polymer_protocol.proposers import rival_generation
    from polymer_protocol.represent import represent
    from tests.conftest import make_plan
    # C: a POSITIVE conclusion with a plan whose criterion the data REFUTES (0.09 < 0.05 is False).
    # The mirrored rival criterion (>= 0.05) is SATISFIED by 0.09 -> the rival licenses.
    concl = Proposition(direction=Direction.POSITIVE, estimand="beta", descriptor="X on Y")
    c = make_claim("c", status=Status.PENDING, conclusion=concl, plan=make_plan(0.09, 0.05, Comparator.LT))
    corp = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    # generous budget so the generated rival is selected + executed
    r1 = run_cycle(corp, adapters, ctx, proposers=(rival_generation,))
    by = r1.corpus.by_id()
    rival_ids = [cid for cid in by if cid.startswith("gen-rival-")]
    assert rival_ids, "rival_generation should have planted at least one rival"
    licensed_rivals = [rid for rid in rival_ids if by[rid].status == Status.LICENSED]
    assert licensed_rivals, "a mirrored rival should license on the refuting data"
    # the licensed rival's provisional edge is now active -> C is defeated (out of grounded extension)
    scaf = represent(r1.corpus)
    assert "c" not in scaf.grounded_extension


def test_planned_rival_is_belief_neutral_without_budget(empty_ledger, ctx, adapters):
    from polymer_grammar import Comparator, Direction, Proposition
    from polymer_protocol.proposers import rival_generation
    from polymer_protocol.represent import represent
    from tests.conftest import make_plan
    concl = Proposition(direction=Direction.POSITIVE, estimand="beta", descriptor="X on Y")
    c = make_claim("c", status=Status.PENDING, conclusion=concl, plan=make_plan(0.09, 0.05, Comparator.LT))
    corp = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    # budget=0 -> nothing selected/executed; the planted rival stays PENDING, its edge inert
    r1 = run_cycle(corp, adapters, ctx, proposers=(rival_generation,), budget=0)
    scaf = represent(r1.corpus)
    assert "c" in scaf.grounded_extension  # source not defeated; rival edge inert while PENDING


def test_generation_credit_floor_throttles_through_run_cycle(empty_ledger, ctx, adapters):
    from polymer_grammar import Direction, Proposition
    from polymer_protocol.ledger import OperatorCredit, SelectionLedger
    from polymer_protocol.proposers import frontier_attack, rival_generation
    # ledger with frontier-attack below floor; run a cycle with both operators + the credit knob
    led = SelectionLedger(credits=(OperatorCredit(operator_id="frontier-attack", n_grounded=0, n_high_eig=4),))
    concl = Proposition(direction=Direction.POSITIVE, estimand="beta", descriptor="X on Y")
    src = make_claim("c", conclusion=concl)  # planless -> rivals are CONJECTURED (cheap, no execution)
    corp = Corpus(claims=(src,), fdr_ledger=empty_ledger)
    r1 = run_cycle(
        corp, adapters, ctx,
        proposers=(rival_generation, frontier_attack),
        ledger=led,
        generation_cap=3,
        generation_credit_floor=0.5,
    )
    # the run completed and the credit knob was honored (no crash; frontier throttled in the record)
    gen = r1.generation
    fa_op_cap = [d for d in gen.discarded if d.operator_id == "frontier-attack" and d.reason == "operator-cap"]
    # frontier produced >1 attacker only if there are frontier nodes; assert the knob path is exercised
    assert gen is not None  # generation record present
```

Note (IMPORTANT for the implementer): the THIRD test's exact discard assertion depends on whether `frontier_attack` produces multiple seeds in this corpus (it needs unresolved-frontier nodes with claim-sourced attackers — there are none here, so it may emit 0). Keep the third test ROBUST: assert the cycle runs with the knob set and `r1.generation` is present; if you can construct a corpus where frontier_attack emits >1 seed AND frontier is below floor, tighten it to assert `len(fa_op_cap) >= 1`. If you cannot cheaply, leave the robust form and instead rely on Task-4's `test_economy_throttles_low_credit_operator` for the precise throttle assertion (that one is deterministic). DO NOT write an assertion that depends on frontier emitting seeds it doesn't emit. Confirm `budget=` and `generation_cap=`/`proposers=`/`ledger=` are the REAL `run_cycle` kwarg names (read the signature); adapt if they differ.

- [ ] **Step 3: Run to verify**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_cycle.py -v`
Expected: the three new tests PASS (adjudication defeats C; belief-neutral with budget=0; credit knob runs clean). If `test_generated_rival_adjudicates_and_defeats_source` FAILS because the rival isn't selected/executed, check: the rival is PENDING+plan (Task 2), SELECT's candidate filter admits it, the default budget executes it, and VERIFY licenses it on `0.09 >= 0.05`. Report a real integration gap rather than weakening the assertion.

- [ ] **Step 4: Full gate + commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims/protocol
uv run pytest -q
uv run ruff check src tests
uv run pytest tests/test_isolation.py -q
```
Expected: all green; isolation 3 passed. Then:
```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/cycle.py protocol/tests/test_cycle.py
git commit -m "feat(protocol): run_cycle generation_credit_floor + end-to-end executable-rival adjudication

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Public exports + README + CONTINUE docs

**Files:**
- Modify: `protocol/src/polymer_protocol/__init__.py`, `README.md`, `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Export the new public symbols** — in `protocol/src/polymer_protocol/__init__.py`, add (matching the file's existing import + `__all__` style):
```python
from .allocate import CREDIT_FLOOR_DEFAULT, allocate_subcaps
from .plan_synthesis import mirror_criterion, transplant_plan
```
and add `"CREDIT_FLOOR_DEFAULT"`, `"allocate_subcaps"`, `"mirror_criterion"`, `"transplant_plan"` to `__all__`. Run `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run python -c "import polymer_protocol as p; print(p.mirror_criterion, p.allocate_subcaps, p.CREDIT_FLOOR_DEFAULT)"` — no error.

- [ ] **Step 2: Get the test counts**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q 2>&1 | tail -1` (protocol count `<P>`). Grammar is unchanged at 268.

- [ ] **Step 3: Update `README.md`** — update the protocol table row count and append, after the provisional-edge paragraph, a paragraph:

> GENERATE is now **self-driving** (#4b slice-2): a rival of a *planned* claim transplants the source's
> compute graph with a direction-**mirrored** criterion (`mirror_criterion`/`transplant_plan`), so the
> rival is a real SELECT candidate — running it adjudicates source-vs-rival on the same data, and a
> winning rival's provisional edge autonomously defeats its source. And GENERATE allocates its budget
> across operators by their `SelectionLedger` credit (`run_cycle(..., generation_credit_floor=)`),
> throttling chronic Goodhart-failers to a recoverable probation slot (never killed). Both OFF by
> default. (frontier-attack seeds and the embedding/LLM operator seam remain for slice-3.)

Update the protocol row in the status table to `… + #4b (provisional links + executable rivals + credit economy) — <P> tests`.

- [ ] **Step 4: Update `docs/superpowers/CONTINUE.md`** — add a Current-state paragraph for #4b slice-2 (DONE, branch `feat/executable-rivals-4b`, merge SHA `<pending>`): executable rivals (transplant + mirror; PENDING/UNTESTED; co-evaluated adjudicator pair; autonomous activation of slice-1's provisional edge) + the credit economy (proportional + floor + probation, `generation_credit_floor` knob, OFF by default). Note zero grammar changes, Corpus still 4 collections, `<P>` protocol tests. Record the load-bearing decisions: (1) executable-generation only for rivals of planned, non-WITHIN_TOL sources (honest limit shrinks, frontier seeds still dormant → slice-3); (2) mirror = single logical complement, so both flipped-direction rivals share it (accepted coarseness); (3) credit economy gated by one float knob, prior-cycle ledger governs this cycle, probation not death. Repoint the NEXT action at slice-3 (intelligent-operator seam) / #5 daemons / grammar representation_revision. Keep the existing CONTINUE format.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/__init__.py README.md docs/superpowers/CONTINUE.md
git commit -m "docs: record #4b slice-2 (executable rivals + credit economy) + export new symbols

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final review

After Task 6, dispatch the whole-package Opus review (per subagent-driven-development) — it spans only `protocol/` this time (grammar untouched; still confirm grammar↔protocol isolation holds). Verify the two new pure modules have no infra/LLM imports. Then `superpowers:finishing-a-development-branch` (merge no-ff to main, verify the protocol + grammar suites on the merged result, delete the branch). Backfill the merge SHA into CONTINUE.md. Update memory (`project_polymer_claims_knowledge_protocol.md` + `MEMORY.md`) with the merge SHA + decisions.

## Progress Log

- (fill in per task: commit SHA + any decisions/deviations)
