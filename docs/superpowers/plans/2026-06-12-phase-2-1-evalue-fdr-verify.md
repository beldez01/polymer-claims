# Phase 2.1 — e-value / FDR / VERIFY unification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the evidence atom an e-value, flip the `FDRLedger` to a dependence-robust e-LOND online process, and hard-gate VERIFY licensing on an e-LOND discovery — fusing the corpus error budget and the licensing decision into one mechanism.

**Architecture:** Pure scalar + e-LOND arithmetic + gate live in grammar/protocol; the native e-value computation from per-sample betas lives umbrella-side and is threaded into `run_cycle` via a pre-stamped `evidence` map (the CES-3 `materializations` pattern). Opt-in: `evidence=None` → byte-identical to today.

**Tech Stack:** Python, pydantic v2 (frozen IR models), pytest. Spec: `docs/specs/2026-06-12-phase-2-1-evalue-fdr-verify-design.md`. North Star: `docs/vision/2026-06-12-phase-2-north-star.md` (§2 B/E).

---

## File Structure

- **Modify** `grammar/src/polymer_grammar/fdr.py` — `FDRTest.p_value → e_value`; e-LOND rule (`discovery ⇔ e ≥ 1/α_t`); add `elond_decisions`. Keep entity name, LOND γ-skeleton, Corpus = 4.
- **Modify** `grammar/tests/test_fdr.py` — migrate p-value tests to e-values (expected churn).
- **Create** `src/polymer_claims/evidence.py` — `one_sided_evalue(a, b, threshold, comparator)` (pure math, numpy-free) + `evidence_map(corpus)` (uses the impure `_region_group_means`).
- **Modify** `protocol/src/polymer_protocol/verify.py` — `verify_stage(..., evidence=None)`: advance the ledger via `elond_decisions`, add the 4th gate conjunct, return the advanced ledger.
- **Modify** `protocol/src/polymer_protocol/integrate.py` — remove the p-value FDR advance.
- **Modify** `protocol/src/polymer_protocol/cycle.py` — `run_cycle(..., evidence=None)`; thread to `verify_stage`; fix the integrate audit note.
- **Tests** — grammar fdr; umbrella evidence + e2e; protocol verify gate + the e-LOND FDR-control deliverable.

### Background facts (verified against the code)
- `FDRTest` today: `index, claim_id, p_value (0..1), alpha_allocated, discovery`. `process_test(ledger, claim_id, p_value)` sets `α_t = target_fdr·γ_t·(D_{t-1}+1)`, `discovery = p ≤ α_t`. `_gamma(j) = (6/π²)/j²`.
- `_region_group_means(node) -> (a, b)` returns the per-sample region-mean betas for `level_a`, `level_b` (each value in [0,1]); raises if `node.impl != "methyl::region_delta_beta"`. The agreed effect is `mean(b) − mean(a)` (matches `RegionMeanDiffAdapter`).
- The criterion is `claim.evaluation_plan.criterion` (`SatisfactionCriterion` with `.comparator` and `.threshold`); `Comparator` ∈ `{GT, GE, LT, LE, EQ, NE, WITHIN_TOL}`.
- The VERIFY licensing gate is `verify.py:149`: `ev.satisfaction is not None and c.id in in_ext and c.provenance is not None and c.id in permitted`. `verify_stage` returns `corpus.model_copy(update={"claims": ...})`.
- `integrate.py:47-54` advances the FDR ledger (one `process_test` per executed claim with a terminal value in [0,1]); returns `(new_corpus, skipped_tuple)`.
- `run_cycle` calls `verify_stage(corpus, scaffolding, records, oracles, adapter_registry=...)` (`cycle.py:124`) then `integrate(corpus, scaffolding, records)` (`cycle.py:133`).
- The terminal node of a claim's plan: `g = plan.graph; next(n for n in g.nodes if n.id == g.terminal)` (see `materialization.py:_terminal_node`).

---

## Task 1: e-LOND ledger internals (grammar)

**Files:**
- Modify: `grammar/src/polymer_grammar/fdr.py`
- Modify: `grammar/tests/test_fdr.py`

- [ ] **Step 1: Rewrite `test_fdr.py` for e-values**

Replace the whole file with:
```python
import math

import pytest
from pydantic import ValidationError

from polymer_grammar.fdr import (
    FDRLedger,
    FDRTest,
    _gamma,
    elond_decisions,
    is_discovery,
    process_stream,
    process_test,
)


def test_gamma_first_term():
    assert _gamma(1) == pytest.approx(6 / math.pi**2)


def test_gamma_monotone_decreasing():
    assert _gamma(1) > _gamma(2) > _gamma(3)


def test_gamma_partial_sum_converges_to_one():
    assert sum(_gamma(j) for j in range(1, 1001)) == pytest.approx(1.0, abs=1e-2)


def test_empty_ledger_properties():
    led = FDRLedger(target_fdr=0.05)
    assert led.n_tests == 0
    assert led.n_discoveries == 0
    assert led.discoveries == frozenset()
    assert led.procedure == "elond"


def test_ledger_properties_over_tests():
    led = FDRLedger(target_fdr=0.05, tests=(
        FDRTest(index=1, claim_id="a", e_value=100.0, alpha_allocated=0.03, discovery=True),
        FDRTest(index=2, claim_id="b", e_value=0.5, alpha_allocated=0.01, discovery=False),
    ))
    assert led.n_tests == 2
    assert led.n_discoveries == 1
    assert led.discoveries == frozenset({"a"})


def test_process_test_elond_rule():
    # t=1: alpha_1 = 0.05 * (6/pi^2) * 1 ~= 0.0304; reject iff e >= 1/alpha_1 ~= 32.9
    led = process_test(FDRLedger(target_fdr=0.05), "a", 40.0)
    t = led.tests[0]
    assert t.discovery is True
    assert t.e_value == 40.0
    assert t.alpha_allocated == pytest.approx(0.05 * _gamma(1) * 1)


def test_process_test_below_bar_is_not_discovery():
    led = process_test(FDRLedger(target_fdr=0.05), "a", 5.0)  # 5 < 1/0.0304
    assert led.tests[0].discovery is False
    assert led.n_discoveries == 0


def test_process_stream_folds_in_order():
    led = process_stream(FDRLedger(target_fdr=0.05), [("a", 40.0), ("b", 40.0)])
    assert led.n_tests == 2
    # second test's alpha grows with prior discoveries (D=1 after 'a' is a discovery)
    assert led.tests[1].alpha_allocated == pytest.approx(0.05 * _gamma(2) * 2)


def test_elond_decisions_matches_iterated_process_test():
    base = FDRLedger(target_fdr=0.05)
    items = [("b", 40.0), ("a", 1.0)]  # deliberately unsorted
    new_led, decisions = elond_decisions(base, items)
    # decisions are computed in claim_id-sorted order: ('a',1.0) then ('b',40.0)
    expected = process_stream(base, sorted(items))
    assert new_led.tests == expected.tests
    assert decisions == {"a": False, "b": True}


def test_validators_reject_negative_evalue():
    with pytest.raises(ValidationError):
        FDRTest(index=1, claim_id="a", e_value=-0.1, alpha_allocated=0.1, discovery=False)
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=0.0)
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=1.5)


def test_models_frozen_and_hashable():
    t = FDRTest(index=1, claim_id="a", e_value=40.0, alpha_allocated=0.03, discovery=True)
    assert isinstance(hash(t), int)
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=0.05, bogus=1)


def test_is_discovery():
    led = process_test(FDRLedger(target_fdr=0.05), "a", 40.0)
    assert is_discovery(led, "a") is True
    assert is_discovery(led, "z") is False
```

- [ ] **Step 2: Run, confirm it FAILS**

Run: `python -m pytest grammar/tests/test_fdr.py -q`
Expected: FAIL — `FDRTest` has no `e_value` / cannot import `elond_decisions` / `procedure` is `"lond"`.

- [ ] **Step 3: Rewrite `fdr.py` for e-LOND**

Replace the body of `grammar/src/polymer_grammar/fdr.py` (keep `_gamma`) with:
```python
"""Corpus-level online-FDR ledger — e-LOND (Phase 2.1).

e-LOND (Xu & Ramdas 2024): test t gets level α_t = target_fdr · γ_t · (D_{t-1}+1), where
γ_j = (6/π²)/j² (Σ = 1) and D_{t-1} is the discoveries so far; it is a DISCOVERY iff its
e-value e_t ≥ 1/α_t. Because the γ's sum to 1 and the e-values are valid (E[e] ≤ 1 under the
null), e-LOND controls FDR ≤ target_fdr under ARBITRARY dependence — no positive-dependence
assumption. The grammar computes the allocation + decision; e-values are supplied by the
evaluator/protocol. Standalone — no Claim coupling.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Literal

from pydantic import Field

from .base import _Model


def _gamma(j: int) -> float:
    """LOND discount γ_j = (6/π²)/j² for j ≥ 1 (non-negative, monotone decreasing, Σ = 1)."""
    return (6.0 / math.pi**2) / (j * j)


class FDRTest(_Model):
    index: int                            # 1-based position in the test stream
    claim_id: str
    e_value: float = Field(ge=0.0)        # a valid e-value (E[e] ≤ 1 under the null); no upper bound
    alpha_allocated: float                # the α_t this test was judged at
    discovery: bool                       # e_value >= 1 / alpha_allocated


class FDRLedger(_Model):
    target_fdr: float = Field(gt=0.0, le=1.0)
    procedure: Literal["elond"] = "elond"
    tests: tuple[FDRTest, ...] = ()

    @property
    def n_tests(self) -> int:
        return len(self.tests)

    @property
    def n_discoveries(self) -> int:
        return sum(1 for t in self.tests if t.discovery)

    @property
    def discoveries(self) -> frozenset[str]:
        return frozenset(t.claim_id for t in self.tests if t.discovery)


def process_test(ledger: FDRLedger, claim_id: str, e_value: float) -> FDRLedger:
    """One e-LOND step. The new test gets level α_t = target_fdr · γ_t · (D_{t-1}+1) where t is its
    1-based position and D_{t-1} is the discoveries recorded so far. It is a DISCOVERY iff
    e_value ≥ 1/α_t. Returns a NEW ledger with the test appended (append-only, immutable)."""
    t = ledger.n_tests + 1
    alpha = ledger.target_fdr * _gamma(t) * (ledger.n_discoveries + 1)
    entry = FDRTest(
        index=t, claim_id=claim_id, e_value=e_value,
        alpha_allocated=alpha, discovery=e_value >= 1.0 / alpha,
    )
    return ledger.model_copy(update={"tests": ledger.tests + (entry,)})


def process_stream(ledger: FDRLedger, items: Iterable[tuple[str, float]]) -> FDRLedger:
    """Fold process_test over (claim_id, e_value) pairs in order."""
    for claim_id, e_value in items:
        ledger = process_test(ledger, claim_id, e_value)
    return ledger


def elond_decisions(
    ledger: FDRLedger, items: Iterable[tuple[str, float]]
) -> tuple[FDRLedger, dict[str, bool]]:
    """Advance the ledger over `items` in claim_id-sorted order (deterministic) and return the
    advanced ledger AND the per-claim discovery flags. Single source of truth for the VERIFY gate
    and the committed ledger."""
    ordered = sorted(items)
    advanced = process_stream(ledger, ordered)
    new_entries = advanced.tests[len(ledger.tests):]
    decisions = {t.claim_id: t.discovery for t in new_entries}
    return advanced, decisions


def is_discovery(ledger: FDRLedger, claim_id: str) -> bool:
    """True iff some recorded test for `claim_id` was a discovery."""
    return claim_id in ledger.discoveries
```

- [ ] **Step 4: Run, confirm it PASSES**

Run: `python -m pytest grammar/tests/test_fdr.py -q`
Expected: PASS.

- [ ] **Step 5: Run the grammar suite for fallout**

Run: `python -m pytest grammar/ -q`
Expected: PASS (any other test constructing `FDRTest(p_value=...)` must be migrated to `e_value=...`; search `grep -rn "p_value=" grammar/`). If any fail, migrate them the same way (p_value → e_value, fix the `discovery` flag to `e ≥ 1/alpha`).

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/fdr.py grammar/tests/test_fdr.py
git commit -m "feat(grammar): e-LOND ledger — e-value evidence atom, dependence-robust FDR (Phase 2.1)"
```

---

## Task 2: the native e-value math (umbrella, pure)

**Files:**
- Create: `src/polymer_claims/evidence.py`
- Test: `tests/test_evidence_validity.py`

- [ ] **Step 1: Write the validity guard test**

```python
# tests/test_evidence_validity.py
from __future__ import annotations

import random

from polymer_grammar import Comparator

from polymer_claims.evidence import one_sided_evalue


def test_evalue_nonneg_and_finite():
    e = one_sided_evalue([0.1, 0.2], [0.9, 0.8], threshold=0.10, comparator=Comparator.GT)
    assert e >= 0.0 and e < float("inf")


def test_evalue_validity_under_null_mean_e_le_one():
    # H0 boundary: true effect == theta0. Simulate bounded [0,1] betas whose group-mean
    # difference has expectation exactly theta0; a VALID e-value has E[e] <= 1.
    rng = random.Random(20260612)
    theta0 = 0.10
    n_a = n_b = 12
    total, trials = 0.0, 4000
    for _ in range(trials):
        # group A ~ U(0, 0.4) (mean 0.2); group B mean = 0.2 + theta0 -> U(0.1, 0.5) (mean 0.3)
        a = [rng.uniform(0.0, 0.4) for _ in range(n_a)]
        b = [rng.uniform(0.10, 0.50) for _ in range(n_b)]
        total += one_sided_evalue(a, b, threshold=theta0, comparator=Comparator.GT)
    mean_e = total / trials
    assert mean_e <= 1.0 + 0.05  # E[e] <= 1 under H0 (MC tolerance)


def test_evalue_large_when_effect_far_above_threshold():
    # strong effect (Δβ ~ 0.5 >> 0.10) -> a large e-value
    e = one_sided_evalue([0.1] * 10, [0.6] * 10, threshold=0.10, comparator=Comparator.GT)
    assert e > 100.0
```

- [ ] **Step 2: Run, confirm it FAILS**

Run: `python -m pytest tests/test_evidence_validity.py -q`
Expected: FAIL — `cannot import name 'one_sided_evalue'`.

- [ ] **Step 3: Implement `one_sided_evalue` in `src/polymer_claims/evidence.py`**

```python
"""Phase 2.1: the native e-value for an apparatus claim + the per-claim evidence map.

`one_sided_evalue` is the PURE math (numpy-free): a valid one-sided sub-Gaussian e-value for the
severe-test null H0: effect <= threshold, valid from boundedness of betas in [0,1] alone (Hoeffding
proxy 1/4), with a PREDICTABLE lambda (criterion-derived, not data-derived). `evidence_map` resolves
each apparatus claim's per-sample betas (impure: load_contract via _region_group_means) and computes
its e-value. See docs/specs/2026-06-12-phase-2-1-evalue-fdr-verify-design.md.
"""
from __future__ import annotations

import math

from polymer_grammar import Comparator

_EPS = 1e-9
_EXP_CAP = 700.0  # exp(700) ~ 1e304 stays finite; prevents overflow on huge effects


def one_sided_evalue(
    a: list[float], b: list[float], *, threshold: float, comparator: Comparator
) -> float:
    """A valid e-value for the severe-test null that the region effect does NOT clear `threshold`.

    Effect = mean(b) - mean(a) for GT/GE (want effect > threshold); mirrored for LT/LE. Shifts to a
    variable with null mean <= 0, then e = exp(λ·shifted - λ²·σ²/2) with σ² = ¼·(1/n_a + 1/n_b)
    (Hoeffding, betas ∈ [0,1]) and a predictable λ = scale/σ² (scale = max(|threshold|, eps), one
    threshold-unit). Returns 0.0-safe, finite e ≥ 0."""
    n_a, n_b = len(a), len(b)
    if n_a == 0 or n_b == 0:
        return 0.0
    d_hat = sum(b) / n_b - sum(a) / n_a
    if comparator in (Comparator.GT, Comparator.GE):
        shifted = d_hat - threshold          # want > 0
    elif comparator in (Comparator.LT, Comparator.LE):
        shifted = threshold - d_hat          # want > 0
    else:
        return 0.0                           # EQ/NE/WITHIN_TOL: no one-sided e-value
    sigma2 = 0.25 * (1.0 / n_a + 1.0 / n_b)
    scale = max(abs(threshold), _EPS)
    lam = scale / sigma2                      # predictable: depends only on threshold + sizes
    exponent = lam * shifted - 0.5 * lam * lam * sigma2
    return math.exp(min(exponent, _EXP_CAP))
```

- [ ] **Step 4: Run, confirm it PASSES**

Run: `python -m pytest tests/test_evidence_validity.py -q`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/evidence.py tests/test_evidence_validity.py
git commit -m "feat(evidence): one_sided_evalue — Hoeffding-valid severe-test e-value (Phase 2.1)"
```

---

## Task 3: the evidence map (umbrella)

**Files:**
- Modify: `src/polymer_claims/evidence.py`
- Test: `tests/test_evidence_map.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_evidence_map.py
from __future__ import annotations

from polymer_grammar import FDRLedger
from polymer_protocol import Corpus

from polymer_claims.evidence import evidence_map
from polymer_claims.methyl_adapters import region_delta_beta_claim


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_evidence_map_computes_evalue_for_signal_region():
    c = region_delta_beta_claim("c-true", threshold=0.10)  # planted +0.20 Δβ
    m = evidence_map(_corpus(c))
    assert "c-true" in m
    assert m["c-true"] > 1.0  # a real effect well above threshold -> e-value > 1


def test_evidence_map_skips_unresolvable_contract():
    c = region_delta_beta_claim("c-bad", ref="se:does_not_exist@1")
    assert "c-bad" not in evidence_map(_corpus(c))


def test_evidence_map_skips_non_apparatus_claim():
    # a claim with no methyl terminal node gets no entry (no DataHandle / wrong impl).
    from tests.conftest import make_claim, make_plan
    c = make_claim("plain", plan=make_plan(0.01, 0.05))
    assert "plain" not in evidence_map(_corpus(c))
```

- [ ] **Step 2: Run, confirm it FAILS**

Run: `python -m pytest tests/test_evidence_map.py -q`
Expected: FAIL — `cannot import name 'evidence_map'`.

- [ ] **Step 3: Add `evidence_map` to `src/polymer_claims/evidence.py`**

Append:
```python
from polymer_grammar import DataHandle
from polymer_protocol.corpus import Corpus

from .methyl_adapters import _IMPL, _region_group_means


def _terminal_node(claim):
    plan = claim.evaluation_plan
    if plan is None:
        return None
    g = plan.graph
    return next((n for n in g.nodes if n.id == g.terminal), None)


def evidence_map(corpus: Corpus) -> dict[str, float]:
    """Per-claim native e-value keyed by claim id. A claim is included iff its terminal node is the
    methyl apparatus (impl == _IMPL) with a DataHandle, its contract resolves, and its criterion is
    one-sided numeric (GT/GE/LT/LE with a threshold). Everything else gets NO entry (caller falls
    back to the existing 3-way gate). Impure: _region_group_means reads the bundled contract."""
    out: dict[str, float] = {}
    for c in corpus.claims:
        node = _terminal_node(c)
        if node is None or node.impl != _IMPL:
            continue
        if not any(isinstance(i, DataHandle) for i in node.inputs):
            continue
        crit = c.evaluation_plan.criterion
        if crit.threshold is None or crit.comparator not in (
            Comparator.GT, Comparator.GE, Comparator.LT, Comparator.LE
        ):
            continue
        try:
            a, b = _region_group_means(node)
        except (FileNotFoundError, KeyError, ValueError):
            continue
        out[c.id] = one_sided_evalue(a, b, threshold=crit.threshold, comparator=crit.comparator)
    return out
```

Note: confirm `_IMPL` is importable from `methyl_adapters` (it is — `_IMPL = "methyl::region_delta_beta"`). `evidence_map` needs neither `base_ctx` nor `profiles` (the e-value is criterion + data only) — a deliberate simplification of the spec's signature.

- [ ] **Step 4: Run, confirm it PASSES**

Run: `python -m pytest tests/test_evidence_map.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/evidence.py tests/test_evidence_map.py
git commit -m "feat(evidence): evidence_map — per-apparatus-claim native e-value (Phase 2.1)"
```

---

## Task 4: the hard 4-way VERIFY gate (protocol)

**Files:**
- Modify: `protocol/src/polymer_protocol/verify.py`
- Test: `protocol/tests/test_verify_evalue_gate.py`

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_verify_evalue_gate.py
from __future__ import annotations

from polymer_grammar import FDRLedger, Status

from polymer_protocol.corpus import Corpus
from polymer_protocol.represent import represent
from polymer_protocol.verify import verify_stage

# Reuse the protocol conftest's machinery to build an executed, agreed, grounded claim.
from tests.conftest import executed_records_for_licensing  # see helper note below


def _setup():
    corpus, records, scaffolding = executed_records_for_licensing()  # one claim 'a', agreed+grounded
    return corpus, records, scaffolding


def test_evalue_discovery_allows_license():
    corpus, records, scaffolding = _setup()
    out = verify_stage(corpus, scaffolding, records, evidence={"a": 1e6})  # huge e -> discovery
    c = next(x for x in out.claims if x.id == "a")
    assert c.status == Status.LICENSED
    assert out.fdr_ledger.n_tests == 1 and out.fdr_ledger.n_discoveries == 1


def test_evalue_below_bar_blocks_license():
    corpus, records, scaffolding = _setup()
    out = verify_stage(corpus, scaffolding, records, evidence={"a": 0.0})  # e=0 -> never a discovery
    c = next(x for x in out.claims if x.id == "a")
    assert c.status != Status.LICENSED
    assert out.fdr_ledger.n_tests == 1 and out.fdr_ledger.n_discoveries == 0


def test_no_evidence_licenses_as_before():
    corpus, records, scaffolding = _setup()
    out = verify_stage(corpus, scaffolding, records)  # evidence=None -> 3-way gate, no e-test
    c = next(x for x in out.claims if x.id == "a")
    assert c.status == Status.LICENSED
    assert out.fdr_ledger.n_tests == 0
```

If `tests/conftest.py` lacks `executed_records_for_licensing`, build the corpus/records inline in this test the same way an existing protocol licensing test does (search `grep -rln "verify_stage" protocol/tests`), using a claim whose `ev.satisfaction` is non-None, `c.id in grounded_extension`, and `c.provenance` set. Reuse that existing fixture rather than inventing one.

- [ ] **Step 2: Run, confirm it FAILS**

Run: `python -m pytest protocol/tests/test_verify_evalue_gate.py -q`
Expected: FAIL — `verify_stage` has no `evidence` parameter.

- [ ] **Step 3: Wire the gate in `verify.py`**

(a) Import `elond_decisions` (top of file, with the other `polymer_grammar` imports):
```python
from polymer_grammar import (
    ...
    elond_decisions,
    ...
)
```

(b) Add the `evidence` param to `verify_stage`:
```python
def verify_stage(
    corpus: Corpus,
    scaffolding: CycleScaffolding,
    exec_records: tuple[ExecRecord, ...],
    oracles: OracleRegistry | None = None,
    adapter_registry: AdapterRegistry | None = None,
    evidence: dict[str, float] | None = None,
) -> Corpus:
```

(c) After `permitted = _permitted_by_bar(...)` (around line 125), advance the ledger and compute the e-discovery decisions:
```python
    ev_map = evidence or {}
    executed_with_e = [(r.claim_id, ev_map[r.claim_id]) for r in exec_records if r.claim_id in ev_map]
    new_ledger, e_decisions = elond_decisions(corpus.fdr_ledger, executed_with_e)

    def _e_ok(cid: str) -> bool:
        # claims with no e-value are exempt (3-way gate); claims with one must be a discovery.
        return cid not in ev_map or e_decisions.get(cid, False)
```

(d) Add the 4th conjunct to the licensing gate (the `if` at ~line 149):
```python
        if (ev.satisfaction is not None and c.id in in_ext
                and c.provenance is not None and c.id in permitted
                and _e_ok(c.id)):
```

(e) Return the advanced ledger in the final corpus update (the last line):
```python
    return corpus.model_copy(update={"claims": tuple(new_claims), "fdr_ledger": new_ledger})
```

- [ ] **Step 4: Run, confirm it PASSES**

Run: `python -m pytest protocol/tests/test_verify_evalue_gate.py -q`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/verify.py protocol/tests/test_verify_evalue_gate.py
git commit -m "feat(protocol): VERIFY 4-way gate — e-LOND discovery + ledger advance (Phase 2.1)"
```

---

## Task 5: thread evidence through run_cycle; remove FDR from INTEGRATE

**Files:**
- Modify: `protocol/src/polymer_protocol/cycle.py`
- Modify: `protocol/src/polymer_protocol/integrate.py`
- Test: `protocol/tests/test_cycle.py` (add one back-compat test)

- [ ] **Step 1: Write the back-compat test**

Append to `protocol/tests/test_cycle.py`:
```python
def test_run_cycle_evidence_none_is_back_compat(licensing_corpus_fixture):
    # run_cycle without evidence must behave exactly as before: licensing unaffected, and the
    # ledger advances ZERO e-tests (no FDR advance happens without an evidence map).
    from polymer_protocol import run_cycle
    corpus = licensing_corpus_fixture  # a corpus whose claim licenses on one cycle (reuse existing)
    before = corpus.fdr_ledger.n_tests
    result = run_cycle(corpus, _ADAPTERS_FIXTURE, _CTX_FIXTURE)
    assert result.corpus.fdr_ledger.n_tests == before  # no evidence -> no e-tests recorded
```
Adapt `licensing_corpus_fixture`, `_ADAPTERS_FIXTURE`, `_CTX_FIXTURE` to whatever the existing `test_cycle.py` already uses to drive `run_cycle` (reuse its fixtures/imports; do not invent new ones).

- [ ] **Step 2: Run, confirm it FAILS (or errors on the new param)**

Run: `python -m pytest protocol/tests/test_cycle.py -q`
Expected: FAIL/ERROR — `run_cycle` has no `evidence` param yet (or, if added without wiring, the assertion still passes; the real proof is Task 6's e2e). If it already passes trivially, proceed — the wiring below is still required for Task 6.

- [ ] **Step 3: Add `evidence` to `run_cycle` and thread it**

In `cycle.py`, add the param to the `run_cycle` signature (next to `materializations`):
```python
    materializations: dict[str, MaterializationContext] | None = None,
    evidence: dict[str, float] | None = None,
```
Pass it to `verify_stage` (the call at ~line 124):
```python
    corpus = verify_stage(
        corpus, scaffolding, records, oracles,
        adapter_registry=adapter_registry, evidence=evidence,
    )
```

- [ ] **Step 4: Remove the FDR advance from `integrate.py`**

Replace the FDR block in `integrate.py` (the loop at lines ~46-54 and its `process_test` import). The new `integrate`:
```python
from polymer_grammar import derived_rebut_edges, restore_consistency  # drop process_test

...

def integrate(
    corpus: Corpus,
    scaffolding: CycleScaffolding,
    exec_records: tuple[ExecRecord, ...],
) -> tuple[Corpus, tuple[str, ...]]:
    # 1. derived rebut edges from the post-VERIFY claims, merged with authored.
    merged = _merge_edges(corpus.defeat_edges, derived_rebut_edges(corpus.claims))

    # 2. entrenchment contest (newcomer yields per AGM).
    rr = restore_consistency(
        corpus.claims, merged, prior_in=frozenset(scaffolding.grounded_extension)
    )

    # NOTE: the FDR ledger is now advanced in VERIFY (Phase 2.1: licensing owns the e-LOND ledger).
    new_corpus = corpus.model_copy(update={"claims": rr.claims, "defeat_edges": rr.edges})
    return new_corpus, ()
```
Delete the now-unused `_terminal_value` helper if nothing else uses it (`grep -n "_terminal_value" protocol/src/polymer_protocol/integrate.py`).

- [ ] **Step 5: Fix the integrate audit note in `cycle.py`**

The `integrate` audit note (cycle.py ~line 133-141) references FDR tests added. Replace it with:
```python
    corpus, _skipped = integrate(corpus, scaffolding, records)
    audit.append(
        StageAudit(
            stage="integrate",
            note=f"AGM revision; fdr ledger {corpus.fdr_ledger.n_tests} test(s) total",
            count=corpus.fdr_ledger.n_tests,
        )
    )
```

- [ ] **Step 6: Run the protocol suite**

Run: `python -m pytest protocol/ -q`
Expected: PASS. If existing tests asserted FDR advancement via `integrate` or `run_cycle` without evidence, migrate them: the ledger now advances in VERIFY only when an `evidence` map is supplied. Update those assertions (the FDR ledger no longer advances on a bare `run_cycle`). Search `grep -rn "fdr_ledger\|n_tests\|process_test" protocol/tests`.

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/cycle.py protocol/src/polymer_protocol/integrate.py protocol/tests/test_cycle.py
git commit -m "feat(protocol): thread evidence through run_cycle; FDR advance moves to VERIFY (Phase 2.1)"
```

---

## Task 6: end-to-end + the e-LOND FDR-control deliverable

**Files:**
- Test: `tests/test_evalue_licensing_e2e.py`
- Test: `protocol/tests/test_elond_fdr_control.py`

- [ ] **Step 1: Write the e2e methylation test**

```python
# tests/test_evalue_licensing_e2e.py
from __future__ import annotations

from polymer_grammar import FDRLedger, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.evidence import evidence_map
from polymer_claims.methyl_adapters import (
    RegionLmCoefAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (RegionMeanDiffAdapter(), RegionLmCoefAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")


def _run(claim):
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    return run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        evidence=evidence_map(corpus),
    )


def test_signal_region_licenses_via_e_discovery():
    result = _run(region_delta_beta_claim("c-true", threshold=0.10))  # planted +0.20 Δβ
    c = next(x for x in result.corpus.claims if x.id == "c-true")
    assert c.status == Status.LICENSED
    assert result.corpus.fdr_ledger.n_discoveries == 1


def test_threshold_above_effect_blocks_license():
    # demand Δβ > 0.30 when the planted effect is ~0.20: e-value below the bar -> NOT licensed.
    result = _run(region_delta_beta_claim("c-weak", threshold=0.30))
    c = next(x for x in result.corpus.claims if x.id == "c-weak")
    assert c.status != Status.LICENSED
```

- [ ] **Step 2: Run, confirm it PASSES**

Run: `python -m pytest tests/test_evalue_licensing_e2e.py -q`
Expected: PASS. If `c-weak` still licenses, the e-value at threshold 0.30 vs effect 0.20 is below `1/α_t` — confirm by printing `evidence_map(corpus)["c-weak"]` and `1/(0.05*_gamma(1))`; the planted effect (~0.20) is below 0.30 so the shifted variable is negative → e < 1 → not a discovery. If it does NOT behave this way, do not weaken the test — investigate the e-value sign/threshold handling in `one_sided_evalue`.

- [ ] **Step 3: Write the e-LOND FDR-control deliverable**

```python
# protocol/tests/test_elond_fdr_control.py
"""The headline rigor deliverable: e-LOND controls FDR under ARBITRARY dependence."""
from __future__ import annotations

import math
import random

from polymer_grammar.fdr import FDRLedger, process_stream


def _null_evalue(z: float, lam: float = 1.0) -> float:
    # e = exp(lam*z - lam^2/2): a valid e-value when z ~ N(0,1) under the null (E[e]=1).
    return math.exp(lam * z - 0.5 * lam * lam)


def test_elond_controls_fdr_under_dependence():
    rng = random.Random(20260612)
    target = 0.10
    m = 60                     # hypotheses per stream
    pi0 = 0.7                  # fraction null
    trials = 300
    fdps = []
    for _ in range(trials):
        shared = rng.gauss(0.0, 1.0)          # a SHARED latent factor -> strong dependence
        items, truth = [], {}
        for i in range(m):
            is_null = rng.random() < pi0
            z = 0.6 * shared + 0.8 * rng.gauss(0.0, 1.0)   # dependent noise
            if not is_null:
                z += 3.0                       # non-nulls shifted up
            cid = f"h{i}"
            items.append((cid, _null_evalue(z)))
            truth[cid] = is_null
        led = process_stream(FDRLedger(target_fdr=target), items)
        disc = led.discoveries
        if disc:
            false_disc = sum(1 for cid in disc if truth[cid])
            fdps.append(false_disc / len(disc))
        else:
            fdps.append(0.0)
    mean_fdp = sum(fdps) / len(fdps)
    assert mean_fdp <= target + 0.03   # FDR controlled under dependence (MC tolerance)
```

- [ ] **Step 4: Run, confirm it PASSES**

Run: `python -m pytest protocol/tests/test_elond_fdr_control.py -q`
Expected: PASS — `mean_fdp <= target + tol`. If it exceeds, do NOT relax the bound; first confirm `_null_evalue` is a valid e-value (E≈1 under the null) and that non-nulls are genuinely separated; the e-LOND guarantee is theoretical, so a failure means the simulation's null e-values are invalid.

- [ ] **Step 5: Commit**

```bash
git add tests/test_evalue_licensing_e2e.py protocol/tests/test_elond_fdr_control.py
git commit -m "test: e-value licensing e2e + e-LOND FDR-control under dependence (Phase 2.1)"
```

---

## Task 7: full-suite green

**Files:** none (verification).

- [ ] **Step 1: Umbrella suite**

Run: `python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 2: check-all.sh**

Run: `./scripts/check-all.sh`
Expected: ALL GREEN (grammar fdr migrated; protocol verify/integrate/cycle updated; viewer untouched). If anything red, fix forward; do not relax assertions.

- [ ] **Step 3: Commit any lint/format fixups**

```bash
git add -A
git commit -m "chore(phase2.1): lint/format fixups"
```
(Skip if nothing changed.)

---

## Self-Review (completed)

**Spec coverage:** §2 e-LOND ledger → Task 1; §3.1 native e-value → Task 2; §3 evidence_map → Task 3; §4 4-way gate + ledger-advance-in-VERIFY → Task 4; §4 run_cycle threading + INTEGRATE removal → Task 5; §7 tests (validity guard, FDR control, e2e, back-compat) → Tasks 2/4/5/6. All spec sections map to a task.

**Deviations from spec (intentional, noted inline):** `evidence_map(corpus)` drops the spec's `base_ctx`/`profiles` params (the e-value is criterion + data only — simpler, no behavior change). The e-value uses the algebraically-equivalent "shift to null-mean-≤-0" form of spec §3.1 (λ = scale/σ², scale = one threshold-unit), which equals the spec's δ₁ = θ₀ + scale.

**Type/name consistency:** `e_value` (not `p_value`), `elond_decisions(ledger, items) -> (ledger, dict)`, `one_sided_evalue(a, b, *, threshold, comparator)`, `evidence_map(corpus) -> dict[str,float]`, `verify_stage(..., evidence=None)`, `run_cycle(..., evidence=None)`, `procedure="elond"` used identically across tasks.

**Risk flagged:** Task 5 — existing protocol tests that asserted FDR advancement on a bare `run_cycle`/`integrate` will need migration (the ledger now advances in VERIFY only when an `evidence` map is supplied). Task 5 Step 6 calls this out explicitly. Task 4's protocol test depends on an existing licensing fixture — reuse it rather than invent one.
