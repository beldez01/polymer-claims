# Earned Strength (the full 2c reconciliation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apparatus-grounded empirical claims (`strength=None` + `oracle_ref`) earn a `StrengthVector` from the actual verify result; the raw earned `evidence_against_null` feeds the selective-inference bar and the oracle tier caps the recorded strength afterward.

**Architecture:** A new pure protocol helper `earn_strength` derives a strength vector from the agreed terminal value + the criterion's margin. `verify_stage` builds an `earned` map for in-scope executed claims, scores that raw evidence in `_permitted_by_bar` (the #3a bar), and writes `cap_earned(...)` for licensed earned claims. A small `oracle.py` refactor extracts the tier resolution so the earned path reuses it. Zero grammar changes; Corpus stays at 4.

**Tech Stack:** Python 3.14, pydantic v2, pytest. Packages: `polymer_grammar` (frozen IR), `polymer_protocol` (runtime), umbrella `polymer_claims`.

**Spec:** `docs/superpowers/archive/specs/2026-06-08-earned-strength-design.md`

---

### Task 1: `earn_strength` pure helper

**Files:**
- Create: `protocol/src/polymer_protocol/earned_strength.py`
- Test: `protocol/tests/test_earned_strength.py`

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_earned_strength.py`:

```python
import math

from polymer_grammar import Comparator, SatisfactionCriterion

from polymer_protocol.earned_strength import earn_strength


def _crit(comparator, threshold):
    return SatisfactionCriterion(comparator=comparator, threshold=threshold)


def test_gt_margin_drives_evidence_monotonically():
    crit = _crit(Comparator.GT, 10.0)
    weak = earn_strength(11.0, crit, has_real_data=True, agreement=True)   # rel 0.1
    strong = earn_strength(14.0, crit, has_real_data=True, agreement=True)  # rel 0.4
    assert 0.0 < weak.evidence_against_null < strong.evidence_against_null < 1.0


def test_strong_gt_margin_clears_a_two_way_bar():
    # rel_margin 0.4 must earn evidence >= 0.95 so it survives a 2-way BH bar (crit (1/2)*0.1=0.05).
    s = earn_strength(14.0, _crit(Comparator.GT, 10.0), has_real_data=True, agreement=True)
    assert s.evidence_against_null >= 0.95


def test_lt_comparator_is_mirrored():
    crit = _crit(Comparator.LT, 0.05)
    s = earn_strength(0.01, crit, has_real_data=True, agreement=True)  # clears by 0.04/0.05 = 0.8
    assert s.evidence_against_null > 0.99


def test_zero_or_negative_margin_floors_evidence():
    # value does not clear the threshold -> no earned evidence (defensive; caller earns only SATISFIED)
    s = earn_strength(10.0, _crit(Comparator.GT, 10.0), has_real_data=True, agreement=True)
    assert s.evidence_against_null == 0.0


def test_non_ordering_comparator_floors_evidence():
    s = earn_strength(1.0, _crit(Comparator.EQ, 1.0), has_real_data=True, agreement=True)
    assert s.evidence_against_null == 0.0


def test_magnitude_scales_with_value():
    crit = _crit(Comparator.GT, 10.0)
    small = earn_strength(11.0, crit, has_real_data=True, agreement=True)
    big = earn_strength(40.0, crit, has_real_data=True, agreement=True)
    assert small.magnitude < big.magnitude


def test_provenance_and_agreement_toggle_their_axes():
    crit = _crit(Comparator.GT, 10.0)
    real_agreed = earn_strength(14.0, crit, has_real_data=True, agreement=True)
    synth_disagreed = earn_strength(14.0, crit, has_real_data=False, agreement=False)
    assert real_agreed.world_contact == 0.9 and synth_disagreed.world_contact == 0.3
    assert real_agreed.certainty == 0.8 and synth_disagreed.certainty == 0.4


def test_theory_axes_are_fixed_defaults():
    s = earn_strength(14.0, _crit(Comparator.GT, 10.0), has_real_data=True, agreement=True)
    assert s.severity == 0.7
    assert s.explanatory_virtue == 0.5


def test_none_threshold_floors_evidence():
    s = earn_strength(14.0, _crit(Comparator.GT, None), has_real_data=True, agreement=True)
    assert s.evidence_against_null == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && python -m pytest tests/test_earned_strength.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.earned_strength'`

- [ ] **Step 3: Write minimal implementation**

Create `protocol/src/polymer_protocol/earned_strength.py`:

```python
"""earned_strength.py — derive a StrengthVector from a verify result (the 2c reconciliation).

An apparatus-grounded claim EARNS its empirical strength from the computed result instead of
asserting it: evidence_against_null / magnitude scale with the margin by which the agreed
terminal value clears the criterion threshold. The earned evidence then feeds the
selective-inference bar (so a strong real effect legitimately clears the cardinality penalty),
and the oracle tier caps the recorded strength afterward (see protocol/verify.py). Pure: no I/O.
"""
from __future__ import annotations

import math

from polymer_grammar import Comparator, SatisfactionCriterion, StrengthVector

# v1 evidence-curve shape. sat(x)=1-exp(-K*x) maps a non-negative margin ratio into [0,1).
# Calibrated so a true effect that clears the threshold by ~40% of the threshold scale
# (rel_margin 0.4) earns ~0.96 evidence — enough to clear a 2-way BH bar — while a ~10% margin
# earns ~0.55. Tunable; recalibrate against real test statistics (with n) in the 2d arc.
_EVIDENCE_SHAPE_K = 8.0
_EPS = 1e-9

# Theory axes — not earned from data (set by argument); recorded uncapped (v1 fixed defaults).
_SEVERITY = 0.7             # a pre-registered threshold met by real computation is a severe test
_EXPLANATORY_VIRTUE = 0.5   # neutral — no theory argument supplied


def _sat(x: float) -> float:
    """Saturating squash of a non-negative ratio into [0, 1)."""
    if x <= 0.0:
        return 0.0
    return 1.0 - math.exp(-_EVIDENCE_SHAPE_K * x)


def _scale(criterion: SatisfactionCriterion) -> float:
    thr = criterion.threshold
    return max(abs(thr), _EPS) if thr is not None else _EPS


def _rel_margin(value: float, criterion: SatisfactionCriterion) -> float:
    """How far `value` clears the criterion, in threshold units (>=0 when satisfied). EQ/NE/
    WITHIN_TOL and a None threshold have no monotone margin -> 0.0 (floor)."""
    thr = criterion.threshold
    if thr is None:
        return 0.0
    if criterion.comparator in (Comparator.GT, Comparator.GE):
        margin = value - thr
    elif criterion.comparator in (Comparator.LT, Comparator.LE):
        margin = thr - value
    else:
        return 0.0
    return max(margin / _scale(criterion), 0.0)


def earn_strength(
    value: float,
    criterion: SatisfactionCriterion,
    *,
    has_real_data: bool,
    agreement: bool,
) -> StrengthVector:
    """Earn a StrengthVector from a verify result. Goodness empirical axes derive from the margin
    by which `value` clears `criterion` (+ provenance/agreement); theory axes are fixed v1
    defaults. The oracle tier caps the empirical axes downstream (verify.py)."""
    return StrengthVector(
        magnitude=_sat(abs(value) / _scale(criterion)),
        evidence_against_null=_sat(_rel_margin(value, criterion)),
        world_contact=0.9 if has_real_data else 0.3,
        certainty=0.8 if agreement else 0.4,
        severity=_SEVERITY,
        explanatory_virtue=_EXPLANATORY_VIRTUE,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && python -m pytest tests/test_earned_strength.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/earned_strength.py protocol/tests/test_earned_strength.py
git commit -m "feat(protocol): earn_strength — derive StrengthVector from a verify result

Pure helper: evidence_against_null/magnitude scale with the margin by which the
agreed terminal clears the criterion; theory axes fixed. Part of the 2c reconciliation.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `cap_earned` — apply the oracle tier to an external (earned) strength

**Files:**
- Modify: `protocol/src/polymer_protocol/oracle.py`
- Test: `protocol/tests/test_oracle.py` (append)

This refactors `oracle_cap` to share its tier resolution with a new `cap_earned(strength, claim, registry)` that caps an EARNED vector (not `claim.strength`). Behavior of `oracle_cap` is preserved exactly.

- [ ] **Step 1: Write the failing test**

Append to `protocol/tests/test_oracle.py`:

```python
def test_cap_earned_caps_external_strength_by_tier():
    from polymer_protocol.oracle import cap_earned
    earned = StrengthVector(magnitude=0.95, certainty=0.9, evidence_against_null=0.96,
                            severity=0.7, world_contact=0.9, explanatory_virtue=0.5)
    c = make_claim("a", plan=make_plan(0.01, 0.05, oracle_ref="g"))  # strength None — irrelevant here
    reg = OracleRegistry(dossiers=(_dossier("g", ValidationTier.BENCHMARKED),))
    capped = cap_earned(earned, c, reg)
    assert capped.magnitude == 0.6              # goodness axis capped to BENCHMARKED ceiling
    assert capped.evidence_against_null == 0.6
    assert capped.certainty == 0.6
    assert capped.world_contact == 0.6
    assert capped.severity == 0.7               # theory axis untouched
    assert capped.explanatory_virtue == 0.5


def test_cap_earned_unvalidated_without_registry():
    from polymer_protocol.oracle import cap_earned
    earned = StrengthVector(magnitude=0.95, certainty=0.9, evidence_against_null=0.96,
                            severity=0.7, world_contact=0.9, explanatory_virtue=0.5)
    c = make_claim("a", plan=make_plan(0.01, 0.05, oracle_ref="g"))
    capped = cap_earned(earned, c, OracleRegistry())  # unresolved -> UNVALIDATED -> 0.0
    assert capped.magnitude == 0.0
    assert capped.severity == 0.7
```

Note: `test_oracle.py` already imports `StrengthVector`, `make_claim`, `make_plan`, `OracleRegistry`, `ValidationTier`, `_dossier`. If a name is missing at the top of the file, add it to the existing imports.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && python -m pytest tests/test_oracle.py -q`
Expected: FAIL — `ImportError: cannot import name 'cap_earned'`

- [ ] **Step 3: Write minimal implementation**

In `protocol/src/polymer_protocol/oracle.py`, replace the `oracle_cap` function (the block from `def oracle_cap(` to its `return`) with:

```python
def _tier_for_claim(claim: Claim, registry: OracleRegistry) -> ValidationTier:
    """The weakest effective tier of the oracles the claim's plan references. No plan / no refs
    -> GOLD (the no-constraint identity: GOLD's ceiling is all-1.0, so capping by it is a no-op)."""
    if claim.evaluation_plan is None:
        return ValidationTier.GOLD
    refs = referenced_oracle_ids(claim.evaluation_plan)
    if not refs:
        return ValidationTier.GOLD
    return weakest_tier([_effective_tier(registry, r, claim.subject) for r in refs])


def oracle_cap(claim: Claim, registry: OracleRegistry) -> StrengthVector | None:
    """The strength to write for `claim` after its weakest oracle's ceiling. Returns the
    (possibly unchanged) strength; None only when the claim has no strength to cap."""
    if claim.strength is None:
        return None
    return cap_strength(claim.strength, _tier_for_claim(claim, registry))


def cap_earned(
    strength: StrengthVector, claim: Claim, registry: OracleRegistry
) -> StrengthVector:
    """Cap an EARNED strength (derived in verify_stage, not `claim.strength`) by the claim's
    weakest oracle tier — the recorded-strength step of the earned path (the 2c reconciliation)."""
    return cap_strength(strength, _tier_for_claim(claim, registry))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd protocol && python -m pytest tests/test_oracle.py tests/test_verify.py -q`
Expected: PASS (all existing oracle/verify tests + the 2 new cap_earned tests)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/oracle.py protocol/tests/test_oracle.py
git commit -m "feat(protocol): cap_earned — apply oracle tier to an external earned strength

Extract _tier_for_claim from oracle_cap (behavior preserved); add cap_earned so the
earned path caps a derived StrengthVector by the apparatus tier.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: wire the earned path into `verify_stage`

**Files:**
- Modify: `protocol/src/polymer_protocol/verify.py`
- Test: `protocol/tests/test_verify.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `protocol/tests/test_verify.py`:

```python
def test_earned_strength_licenses_and_is_tier_capped(empty_ledger, ctx, adapters):
    # None-strength + oracle_ref claim that clears the threshold strongly -> earns strength,
    # licenses (single claim, M small), and the recorded goodness axes are tier-capped (BENCHMARKED).
    from polymer_grammar import OracleDossier, ValidationTier
    from polymer_protocol import OracleRegistry
    # make_plan default comparator LT: value 0.01 clears threshold 0.05 by 0.04/0.05 = 0.8 -> strong.
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"))
    assert c.strength is None
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    reg = OracleRegistry(dossiers=(OracleDossier(oracle_id="api",
                                                 validation_tier=ValidationTier.BENCHMARKED),))
    out = verify_stage(corpus, scaffolding, records, reg)
    graded = out.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.strength is not None                       # earned (was None)
    assert graded.strength.evidence_against_null <= 0.6      # capped by BENCHMARKED
    assert graded.strength.magnitude <= 0.6
    assert graded.strength.severity == 0.7                   # theory axis uncapped


def test_earned_path_leaves_const_none_strength_claim_exempt(empty_ledger, ctx, adapters):
    # No oracle_ref -> NOT earned -> stays exempt, strength stays None (byte-unchanged behavior).
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    graded = out.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.strength is None


def test_earned_evidence_prices_the_search(ctx, adapters):
    # Reconciliation: among competing None-strength + oracle_ref claims, the strongly-supported
    # one licenses while a thin-margin rival is held PENDING by the selective-inference bar.
    # strong: LT value 0.01 vs threshold 0.05 -> rel 0.8 -> evidence ~1.0
    # thin:   LT value 0.049 vs threshold 0.05 -> rel 0.02 -> evidence ~0.15
    strong = make_claim("strong", status=Status.PENDING,
                        plan=make_plan(0.01, 0.05, oracle_ref="api"))
    thin = make_claim("thin", status=Status.PENDING,
                      plan=make_plan(0.049, 0.05, oracle_ref="api"))
    out = _verify_through_select([strong, thin], adapters, ctx)
    assert out.by_id()["strong"].status == Status.LICENSED
    assert out.by_id()["thin"].status == Status.PENDING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && python -m pytest tests/test_verify.py -k earned -q`
Expected: FAIL — `test_earned_strength_licenses_and_is_tier_capped` asserts a non-None strength but the current code writes `oracle_cap(c, registry)` which is `None` for a None-strength claim (status LICENSED but `strength is None`).

- [ ] **Step 3: Write minimal implementation**

In `protocol/src/polymer_protocol/verify.py`:

(a) Extend the `polymer_grammar` import block — add `DataHandle`, `StrengthVector`, and `referenced_oracle_ids` to the existing `from polymer_grammar import (...)`:

```python
from polymer_grammar import (
    Claim,
    DataHandle,
    LicenseRoute,
    Licensing,
    PendingReason,
    RivalSetClosure,
    SatisfactionVerdict,
    Status,
    StrengthVector,
    clears_mdl_bar,
    corpus_implied_schema,
    is_representation_revision,
    mdl_delta,
    meets_meta_tier_bar,
    referenced_oracle_ids,
)
```

(b) Update the oracle import line to add `cap_earned`:

```python
from .oracle import OracleRegistry, cap_earned, oracle_cap
```

(c) Add the import for `earn_strength` (next to the `.oracle` import):

```python
from .earned_strength import earn_strength
```

(d) Add `_build_earned` above `_permitted_by_bar`:

```python
def _build_earned(
    corpus: Corpus, exec_records: tuple[ExecRecord, ...]
) -> dict[str, StrengthVector]:
    """Earned strengths for executed None-strength + oracle_ref claims with a numeric, agreed,
    SATISFIED result (the spec's D2 scope). Empty for every other claim, which preserves today's
    behavior (None-strength -> exempt; asserted strength -> scored as before)."""
    by_id = corpus.by_id()
    earned: dict[str, StrengthVector] = {}
    for r in exec_records:
        c = by_id.get(r.claim_id)
        if c is None or c.strength is not None or c.evaluation_plan is None:
            continue
        if not referenced_oracle_ids(c.evaluation_plan):
            continue
        ev = r.evaluation
        # ev.satisfaction is non-None only for an agreed SATISFIED result (the air-gap mint).
        if ev.satisfaction is None or not ev.results:
            continue
        val = ev.results[0].terminal.value
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            continue
        has_real_data = any(
            isinstance(i, DataHandle)
            for n in c.evaluation_plan.graph.nodes
            for i in n.inputs
        )
        earned[c.id] = earn_strength(
            float(val), c.evaluation_plan.criterion,
            has_real_data=has_real_data, agreement=ev.agreement,
        )
    return earned
```

(e) Change `_permitted_by_bar` to take and use `earned` (replace the whole function):

```python
def _permitted_by_bar(
    corpus: Corpus,
    exec_records: tuple[ExecRecord, ...],
    earned: dict[str, StrengthVector],
) -> set[str]:
    """Ids of executed claims permitted to license under the cardinality-scaled BH bar.
    M<=1 -> all permitted (identity). strength=None AND not earned -> exempt (always permitted).
    An earned claim is scored by its RAW earned evidence (the 2c reconciliation: data-evidence
    survives selection on its own merit; the oracle cap is applied to the recorded strength later)."""
    by_id = corpus.by_id()
    executed = [by_id[r.claim_id] for r in exec_records if r.claim_id in by_id]
    if not executed:
        return set()
    permitted = {c.id for c in executed if c.strength is None and c.id not in earned}  # exempt
    scored = []
    for c in executed:
        if c.id in earned:
            scored.append((1.0 - earned[c.id].evidence_against_null, c.id))
        elif c.strength is not None:
            scored.append((1.0 - c.strength.evidence_against_null, c.id))
    m = max(
        (c.provenance.search_cardinality for c in executed if c.provenance is not None),
        default=1,
    )
    # defense-in-depth: the BH denominator must cover EVERY scored claim, else a too-small
    # hand-stamped search_cardinality would let claims ranked beyond M pass on a >1 bar.
    m = max(m, len(scored))
    if m <= 1:
        return {c.id for c in executed}
    scored.sort()  # ascending pseudo-p, ties by id
    k_max = 0
    for k, (p, _) in enumerate(scored, start=1):
        if p <= (k / m) * BH_Q + _BH_EPS:
            k_max = k
    permitted.update(cid for _, cid in scored[:k_max])
    return permitted
```

(f) In `verify_stage`, after `registry = ...`, build the earned map and pass it to the bar; add a recorded-strength resolver. Replace the lines:

```python
    registry = oracles if oracles is not None else OracleRegistry()
    in_ext = set(scaffolding.grounded_extension)
    rec_by_id = {r.claim_id: r for r in exec_records}
    permitted = _permitted_by_bar(corpus, exec_records)
```

with:

```python
    registry = oracles if oracles is not None else OracleRegistry()
    in_ext = set(scaffolding.grounded_extension)
    rec_by_id = {r.claim_id: r for r in exec_records}
    earned = _build_earned(corpus, exec_records)
    permitted = _permitted_by_bar(corpus, exec_records, earned)

    def _recorded_strength(claim: Claim) -> StrengthVector | None:
        """Earned claims record cap_earned(earned, tier); everything else keeps oracle_cap."""
        if claim.id in earned:
            return cap_earned(earned[claim.id], claim, registry)
        return oracle_cap(claim, registry)
```

(g) Replace BOTH `strength=oracle_cap(c, registry)` occurrences (the MDL route and the ordinary route) with `strength=_recorded_strength(c)`. The MDL-route line keeps its comment; the ordinary line drops its inline comment. After the change both read:

```python
                            strength=_recorded_strength(c),
```

and

```python
                    strength=_recorded_strength(c),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd protocol && python -m pytest tests/test_verify.py -q`
Expected: PASS — the 3 new earned tests plus all pre-existing verify tests (the asserted-strength and exempt-bar tests are untouched by the earned path).

- [ ] **Step 5: Run the full protocol + grammar suites (no regressions)**

Run: `cd protocol && python -m pytest -q && cd ../grammar && python -m pytest -q`
Expected: PASS for both. If a pre-existing test that builds a None-strength + oracle_ref claim through `verify_stage` flipped, reconcile against the spec's D2 scope before changing the test.

- [ ] **Step 6: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/verify.py protocol/tests/test_verify.py
git commit -m "feat(protocol): earned strength in verify_stage (the 2c reconciliation)

Build an earned-strength map for None-strength + oracle_ref claims; the raw earned
evidence feeds the selective-inference bar; record cap_earned(earned, tier) on license.
Const/asserted-strength paths unchanged.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: export the new protocol API

**Files:**
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_earned_strength.py` (append an import-surface check)

- [ ] **Step 1: Write the failing test**

Append to `protocol/tests/test_earned_strength.py`:

```python
def test_public_api_exports():
    import polymer_protocol as pp
    assert hasattr(pp, "earn_strength")
    assert hasattr(pp, "cap_earned")
    from polymer_protocol import cap_earned, earn_strength  # noqa: F401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && python -m pytest tests/test_earned_strength.py::test_public_api_exports -q`
Expected: FAIL — `AttributeError: module 'polymer_protocol' has no attribute 'earn_strength'`

- [ ] **Step 3: Write minimal implementation**

In `protocol/src/polymer_protocol/__init__.py`:

(a) Add imports near the existing `from .oracle import OracleRegistry, oracle_cap` and `from .verify import verify_stage` lines:

```python
from .earned_strength import earn_strength
from .oracle import OracleRegistry, cap_earned, oracle_cap
```

(b) Add both names to `__all__` (in the oracle/verify section, next to `"oracle_cap"`):

```python
    "oracle_cap",
    "cap_earned",
    "earn_strength",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && python -m pytest tests/test_earned_strength.py -q`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/__init__.py protocol/tests/test_earned_strength.py
git commit -m "feat(protocol): export earn_strength + cap_earned

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: umbrella — the live seed licenses on EARNED strength

**Files:**
- Create: `tests/test_earned_strength_live.py`

This is the watchable-deliverable guard: the real-data seed now licenses via the earned path (off the exempt scaffolding) with a tier-capped strength. It also calibrates `_EVIDENCE_SHAPE_K` — if this test fails because the strong seed claim is held PENDING, raise `_EVIDENCE_SHAPE_K` in `earned_strength.py` until seed-md-1 clears (and re-run Task 1's `test_strong_gt_margin_clears_a_two_way_bar`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_earned_strength_live.py`:

```python
"""The 2c reconciliation, end-to-end on the bundled real-data seed: a None-strength + oracle_ref
mean_diff claim now licenses by EARNING its strength from the computed mean difference (off the
exempt scaffolding), tier-capped by the BENCHMARKED apparatus oracle."""
from polymer_grammar import MaterializationContext, Status

from polymer_claims.exec_adapters import (
    apparatus_oracle_registry,
    independent_registry,
    real_data_seed_corpus,
)
from polymer_protocol import run_cycle
from polymer_protocol.cost import CostModel

# mirror the real call site (src/polymer_claims/node.py `_CTX`)
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="d1")


def _adapters():
    from polymer_claims.exec_adapters import StatsPureAdapter, StatsStdlibAdapter
    return (StatsPureAdapter(), StatsStdlibAdapter())


def test_seed_claim_licenses_with_earned_capped_strength():
    corpus, kwargs = real_data_seed_corpus()
    out = run_cycle(
        corpus,
        _adapters(),
        _CTX,
        oracles=apparatus_oracle_registry(),
        adapter_registry=independent_registry(),
        cost_model=CostModel(),
        **kwargs,
    )
    graded = out.corpus.by_id()
    md1 = graded["seed-md-1"]
    # the true high-low diff is 14.0; threshold 10.0 (GT) -> strong margin -> earns + licenses
    assert md1.status == Status.LICENSED
    assert md1.strength is not None                      # EARNED (builder default was None)
    assert md1.strength.evidence_against_null <= 0.6     # capped by BENCHMARKED
    assert md1.strength.magnitude <= 0.6
    assert md1.strength.severity == 0.7                  # theory axis uncapped
    # seed-md-2 wants >20 over a true 14 -> refuted -> rejected (not earned)
    assert graded["seed-md-2"].status == Status.REJECTED
```

Note: confirm `run_cycle`'s exact keyword names by checking its signature (`grep -n "def run_cycle" protocol/src/polymer_protocol/cycle.py`). If it takes `adapters`/`ctx` positionally or under different names (e.g. a single context object), adapt the call — keep the assertions identical. The 2b/2c work already calls `run_cycle` on this seed in `serve --real-data`; mirror that call site (`src/polymer_claims/server.py` / `cli.py`) if the signature is unclear.

- [ ] **Step 2: Run test to verify it fails (or reveals the real signature)**

Run: `cd /Users/zbb2/Desktop/polymer-claims && python -m pytest tests/test_earned_strength_live.py -q`
Expected: FAIL first on any `run_cycle` signature mismatch (fix the call per the note), then — once it runs — it should PASS if `_EVIDENCE_SHAPE_K=8.0` is sufficient. If `seed-md-1` is PENDING, the bar held it: raise `_EVIDENCE_SHAPE_K` (e.g. to 10.0) and re-run.

- [ ] **Step 3: Calibrate if needed**

Only if Step 2 shows `seed-md-1` PENDING: in `protocol/src/polymer_protocol/earned_strength.py` raise `_EVIDENCE_SHAPE_K` until it licenses, then re-run `cd protocol && python -m pytest tests/test_earned_strength.py -q` to confirm the unit thresholds still hold (bump the `>= 0.95` expectation only if you intentionally lowered the curve — raising K only increases evidence).

- [ ] **Step 4: Run the umbrella suite (no regressions)**

Run: `cd /Users/zbb2/Desktop/polymer-claims && python -m pytest tests/ -q`
Expected: PASS — the new live test plus all existing umbrella tests (`test_real_data_generation.py` asserts structure only; `test_exec_adapters.py` asserts the builder default + single-claim asserted cap, all unaffected).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add tests/test_earned_strength_live.py protocol/src/polymer_protocol/earned_strength.py
git commit -m "test(umbrella): real-data seed licenses on EARNED strength (2c reconciliation)

The seed mean_diff claim licenses off the exempt scaffolding by earning its strength
from the computed mean difference, tier-capped by the BENCHMARKED apparatus oracle.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: docs + full gates

**Files:**
- Modify: `docs/superpowers/notes/2026-06-08-earned-strength-followup.md`
- Modify: `docs/superpowers/CONTINUE.md`

- [ ] **Step 1: Update the follow-up note**

Add a section at the END of `docs/superpowers/notes/2026-06-08-earned-strength-followup.md`:

```markdown
## SHIPPED (2026-06-08) — earned strength

`earn_strength` (protocol) derives the StrengthVector from the agreed terminal value's margin
over the criterion threshold; `verify_stage` builds an earned map for None-strength + oracle_ref
claims, scores the RAW earned evidence in the selective-inference bar, and records
`cap_earned(earned, tier)` on license. The reconciliation holds: the bundled true effect
(high-low = 14.0 vs threshold 10.0) earns evidence that clears the bar and licenses, while a
thin-margin rival is correctly held PENDING. Const and asserted-strength paths are unchanged.
Caveat carried forward: evidence is the margin over a pre-registered threshold, NOT a p-value
with n — the test-statistic enrichment is deferred to the 2d arc (adapter emits n+SD).
Spec `docs/superpowers/archive/specs/2026-06-08-earned-strength-design.md`,
plan `docs/superpowers/plans/2026-06-08-earned-strength.md`.
```

- [ ] **Step 2: Run the full local CI gate**

Run: `cd /Users/zbb2/Desktop/polymer-claims && bash scripts/check-all.sh`
Expected: `ALL GREEN` (umbrella + grammar + protocol pytest/ruff + isolation + viewer typecheck/build).

- [ ] **Step 3: Run the install smoke test**

Run the install-smoke step the repo uses (check `scripts/` for the script name, e.g. `bash scripts/install-smoke.sh` or the command referenced in prior CONTINUE.md entries).
Expected: GREEN — the package builds and imports without optional extras.

- [ ] **Step 4: Update CONTINUE.md**

Edit the top `▶▶ NEXT ACTION` block of `docs/superpowers/CONTINUE.md`: mark EARNED-STRENGTH DONE (with the commit range), and set the next action to **Phase 2d** (PolymerGenomicsAPI as a second real data source on the same `Adapter` seam) + the deferred adapter-emitted-n/test-statistic enrichment. Keep the noted minor card gap (`stats::mean_diff` computed value/✓✗) in the list.

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add docs/superpowers/notes/2026-06-08-earned-strength-followup.md docs/superpowers/CONTINUE.md
git commit -m "docs: earned strength shipped — note + CONTINUE; next = Phase 2d

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Problem / reconciliation → Tasks 1+3 (earn + wire). ✓
- D1 (raw earned → bar, cap after) → Task 3 step (e) bar scores raw earned; `_recorded_strength` caps after license. ✓
- D2 (scope: None-strength + oracle_ref + numeric/agreed/satisfied) → `_build_earned` guards in Task 3 (d). ✓
- Derivation axes → Task 1 `earn_strength`. ✓
- Wiring (earned map → bar → cap_earned; MDL branch too) → Task 3 (d)/(e)/(f)/(g). ✓
- "Grammar untouched / Corpus 4" → no grammar task; only protocol + umbrella + docs. ✓
- Builder default unchanged / `_PROVISIONAL_STRENGTH` retained → no change to `exec_adapters.py` builder. ✓
- Testing (earn unit table; single-claim earned+cap; multi-claim reconciliation; const regression; asserted regression; umbrella seed) → Tasks 1, 3, 5. ✓
- Honesty caveat + out-of-scope (n/SD, 2d, card gap) → Task 6 note + CONTINUE. ✓

**Placeholder scan:** No TBD/TODO; the one runtime-confirm (`run_cycle` signature in Task 5) is explicit with a fallback (mirror the existing `serve --real-data` call site) — not a placeholder.

**Type/name consistency:** `earn_strength(value, criterion, *, has_real_data, agreement)`, `cap_earned(strength, claim, registry)`, `_tier_for_claim(claim, registry)`, `_build_earned(corpus, exec_records) -> dict[str, StrengthVector]`, `_permitted_by_bar(corpus, exec_records, earned)`, `_recorded_strength(claim)` — used identically across tasks. `_EVIDENCE_SHAPE_K` named consistently in Tasks 1/5.
