# Phase 7 — Online-FDR Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone corpus-level online-FDR ledger (LOND) — a first-class immutable IR entity that allocates per-test significance levels from a discovery-earned error budget, controlling corpus FDR over an open-ended test stream.

**Architecture:** One new module `grammar/fdr.py` of pure functions + frozen models, depending only on `base._Model` + stdlib `math` (no `claim`/`defeat`/`revision` import). The grammar computes the LOND recurrence (`α_t = target·γ_t·(D+1)`, `γ_j = (6/π²)/j²`); p-values are supplied by the caller. No `Claim` field, no `status` coupling.

**Tech Stack:** Python 3.12, pydantic v2 (`_Model` frozen + `extra="forbid"`), pytest, uv. Tests: `cd grammar && uv run pytest -q`; lint: `uv run ruff check src tests`.

**Spec:** `docs/superpowers/specs/2026-06-01-fdr-ledger-spec.md`

---

## File Structure

- Create: `grammar/src/polymer_grammar/fdr.py` — `_gamma`; `FDRTest`; `FDRLedger` (+ `n_tests`/`n_discoveries`/`discoveries` properties); `process_test`; `process_stream`; `is_discovery`.
- Create: `grammar/tests/test_fdr.py`.
- Modify: `grammar/src/polymer_grammar/__init__.py` — re-export the public symbols.

All work on a feature branch `phase7-fdr-ledger`; merge `--no-ff` to `main` at the end. Isolation guard (`test_isolation.py`) must stay green — no `polymer_formalclaim` import. Keep all module-level imports at the TOP of files (ruff E402); ruff clean (no unused imports F401).

---

### Task 1: The LOND discount sequence `_gamma`

**Files:**
- Create: `grammar/src/polymer_grammar/fdr.py`
- Test: `grammar/tests/test_fdr.py`

- [ ] **Step 1: Write the failing test** — create `grammar/tests/test_fdr.py`:

```python
import math

import pytest

from polymer_grammar.fdr import _gamma


def test_gamma_first_term():
    assert _gamma(1) == pytest.approx(6 / math.pi**2)


def test_gamma_monotone_decreasing():
    assert _gamma(1) > _gamma(2) > _gamma(3)


def test_gamma_partial_sum_converges_to_one():
    # Σ_{j≥1} (6/π²)/j² = 1 (Basel); first 1000 terms get within 1e-2.
    assert sum(_gamma(j) for j in range(1, 1001)) == pytest.approx(1.0, abs=1e-2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_fdr.py -q`
Expected: FAIL (ModuleNotFoundError: No module named 'polymer_grammar.fdr')

- [ ] **Step 3: Write minimal implementation** — create `grammar/src/polymer_grammar/fdr.py`:

```python
"""Corpus-level online-FDR ledger (spec §5 #4 / unified spec §4).

A first-class, immutable IR entity controlling the false-discovery rate over an
open-ended stream of significance tests, via LOND (Levels based On Number of Discoveries,
Javanmard & Montanari 2018): test t gets level α_t = target_fdr · γ_t · (D_{t-1} + 1),
where γ_j = (6/π²)/j² (Σ = 1) and D_{t-1} is the number of discoveries so far. The grammar
computes the allocation; p-values are supplied by the evaluator/protocol. Standalone — no
Claim coupling; imports nothing from polymer_formalclaim.
"""
from __future__ import annotations

import math


def _gamma(j: int) -> float:
    """LOND discount γ_j = (6/π²)/j² for j ≥ 1 (non-negative, monotone decreasing, Σ = 1)."""
    return (6.0 / math.pi**2) / (j * j)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_fdr.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/fdr.py grammar/tests/test_fdr.py
git commit -m "feat(grammar): LOND discount sequence for online-FDR ledger"
```

---

### Task 2: `FDRTest` + `FDRLedger` models

**Files:**
- Modify: `grammar/src/polymer_grammar/fdr.py`
- Test: `grammar/tests/test_fdr.py`

- [ ] **Step 1: Write the failing test** — APPEND to `grammar/tests/test_fdr.py`; add `from pydantic import ValidationError` to the top imports, and add `FDRLedger, FDRTest` to the existing `from polymer_grammar.fdr import (...)` line:

```python
def test_empty_ledger_properties():
    led = FDRLedger(target_fdr=0.05)
    assert led.n_tests == 0
    assert led.n_discoveries == 0
    assert led.discoveries == frozenset()
    assert led.procedure == "lond"


def test_ledger_properties_over_tests():
    led = FDRLedger(target_fdr=0.05, tests=(
        FDRTest(index=1, claim_id="a", p_value=0.01, alpha_allocated=0.03, discovery=True),
        FDRTest(index=2, claim_id="b", p_value=0.40, alpha_allocated=0.01, discovery=False),
    ))
    assert led.n_tests == 2
    assert led.n_discoveries == 1
    assert led.discoveries == frozenset({"a"})


def test_validators_reject_out_of_range():
    with pytest.raises(ValidationError):
        FDRTest(index=1, claim_id="a", p_value=1.5, alpha_allocated=0.1, discovery=False)
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=0.0)     # must be > 0
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=1.5)     # must be <= 1


def test_models_frozen_and_hashable():
    t = FDRTest(index=1, claim_id="a", p_value=0.01, alpha_allocated=0.03, discovery=True)
    assert isinstance(hash(t), int)
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=0.05, bogus=1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_fdr.py -q`
Expected: FAIL (ImportError: cannot import name 'FDRLedger')

- [ ] **Step 3: Write minimal implementation** — in `grammar/src/polymer_grammar/fdr.py`, add `from typing import Literal`, `from pydantic import Field`, and `from .base import _Model` to the imports at the top, then APPEND:

```python
class FDRTest(_Model):
    index: int                            # 1-based position in the test stream
    claim_id: str
    p_value: float = Field(ge=0.0, le=1.0)
    alpha_allocated: float                # the α_t this test was judged at (may exceed 1 if budget is large)
    discovery: bool                       # p_value <= alpha_allocated


class FDRLedger(_Model):
    target_fdr: float = Field(gt=0.0, le=1.0)
    procedure: Literal["lond"] = "lond"
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_fdr.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/fdr.py grammar/tests/test_fdr.py
git commit -m "feat(grammar): FDRTest + FDRLedger models (first-class FDR IR entity)"
```

---

### Task 3: `process_test` — the LOND step

**Files:**
- Modify: `grammar/src/polymer_grammar/fdr.py`
- Test: `grammar/tests/test_fdr.py`

- [ ] **Step 1: Write the failing test** — APPEND to `grammar/tests/test_fdr.py`; add `process_test` to the existing `from polymer_grammar.fdr import (...)` line:

```python
def test_process_first_test_discovery():
    led = process_test(FDRLedger(target_fdr=0.5), "c1", 0.30)
    assert led.n_tests == 1
    t = led.tests[0]
    assert t.index == 1
    assert t.alpha_allocated == pytest.approx(0.5 * (6 / math.pi**2))   # target·γ_1·1 ≈ 0.304
    assert t.discovery is True                                          # 0.30 <= ~0.304


def test_process_first_test_non_discovery():
    led = process_test(FDRLedger(target_fdr=0.5), "c1", 0.50)
    assert led.tests[0].discovery is False                             # 0.50 > ~0.304


def test_budget_grows_with_discoveries():
    # Stream A: test 1 is a discovery -> D=1 raises the budget, so a borderline p=0.10
    # at test 2 (α_2 = 0.5·γ_2·2 ≈ 0.152) PASSES.
    a = process_test(process_test(FDRLedger(target_fdr=0.5), "c1", 0.30), "c2", 0.10)
    assert a.discoveries == frozenset({"c1", "c2"})
    # Stream B: test 1 fails (0.50 > ~0.304) -> D stays 0, so the SAME p=0.10 at test 2
    # (α_2 = 0.5·γ_2·1 ≈ 0.076) FAILS.
    b = process_test(process_test(FDRLedger(target_fdr=0.5), "x1", 0.50), "c2", 0.10)
    assert b.discoveries == frozenset()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_fdr.py -q`
Expected: FAIL (ImportError: cannot import name 'process_test')

- [ ] **Step 3: Write minimal implementation** — APPEND to `grammar/src/polymer_grammar/fdr.py`:

```python
def process_test(ledger: FDRLedger, claim_id: str, p_value: float) -> FDRLedger:
    """One LOND step. The new test gets level α_t = target_fdr · γ_t · (D_{t-1}+1) where
    t is its 1-based position and D_{t-1} is the discoveries recorded in `ledger` so far.
    It's a discovery iff p_value <= α_t. Returns a NEW ledger with the test appended
    (append-only, immutable)."""
    t = ledger.n_tests + 1
    alpha = ledger.target_fdr * _gamma(t) * (ledger.n_discoveries + 1)
    entry = FDRTest(
        index=t, claim_id=claim_id, p_value=p_value,
        alpha_allocated=alpha, discovery=p_value <= alpha,
    )
    return ledger.model_copy(update={"tests": ledger.tests + (entry,)})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_fdr.py -q`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/fdr.py grammar/tests/test_fdr.py
git commit -m "feat(grammar): LOND process_test step (budget grows with discoveries)"
```

---

### Task 4: `process_stream` + `is_discovery`

**Files:**
- Modify: `grammar/src/polymer_grammar/fdr.py`
- Test: `grammar/tests/test_fdr.py`

- [ ] **Step 1: Write the failing test** — APPEND to `grammar/tests/test_fdr.py`; add `process_stream, is_discovery` to the existing `from polymer_grammar.fdr import (...)` line:

```python
def test_process_stream_equals_iterated_process_test():
    items = [("a", 0.01), ("b", 0.40), ("c", 0.02)]
    streamed = process_stream(FDRLedger(target_fdr=0.1), items)
    manual = FDRLedger(target_fdr=0.1)
    for cid, p in items:
        manual = process_test(manual, cid, p)
    assert streamed.tests == manual.tests


def test_is_discovery_query():
    led = process_test(FDRLedger(target_fdr=0.5), "c1", 0.30)   # discovery
    led = process_test(led, "c2", 0.99)                         # not a discovery
    assert is_discovery(led, "c1") is True
    assert is_discovery(led, "c2") is False
    assert is_discovery(led, "absent") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_fdr.py -q`
Expected: FAIL (ImportError: cannot import name 'process_stream')

- [ ] **Step 3: Write minimal implementation** — in `grammar/src/polymer_grammar/fdr.py`, add `from collections.abc import Iterable` to the imports at the top, then APPEND:

```python
def process_stream(
    ledger: FDRLedger, items: Iterable[tuple[str, float]]
) -> FDRLedger:
    """Fold process_test over (claim_id, p_value) pairs in order. Each step sees the
    discoveries of the prior steps (so the result equals iterated process_test)."""
    for claim_id, p_value in items:
        ledger = process_test(ledger, claim_id, p_value)
    return ledger


def is_discovery(ledger: FDRLedger, claim_id: str) -> bool:
    """True iff some recorded test for `claim_id` was a discovery. The protocol uses this
    to gate licensing; keeps the ledger decoupled from Claim."""
    return claim_id in ledger.discoveries
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_fdr.py -q`
Expected: PASS (12 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/fdr.py grammar/tests/test_fdr.py
git commit -m "feat(grammar): FDR process_stream fold + is_discovery query"
```

---

### Task 5: Package exports + whole-package verification

**Files:**
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_fdr.py`

- [ ] **Step 1: Write the failing test** — APPEND to `grammar/tests/test_fdr.py`:

```python
def test_public_api_exports():
    import polymer_grammar as pg

    for name in ["FDRTest", "FDRLedger", "process_test", "process_stream", "is_discovery"]:
        assert hasattr(pg, name), f"{name} not exported from polymer_grammar"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_fdr.py::test_public_api_exports -q`
Expected: FAIL (AssertionError: FDRTest not exported from polymer_grammar)

- [ ] **Step 3: Write minimal implementation** — in `grammar/src/polymer_grammar/__init__.py`, ADD a new import block after the existing ones:

```python
from .fdr import (
    FDRLedger,
    FDRTest,
    is_discovery,
    process_stream,
    process_test,
)
```

And ADD these strings to the `__all__` list (anywhere in the list):

```python
    "FDRLedger",
    "FDRTest",
    "is_discovery",
    "process_stream",
    "process_test",
```

(Note: `_gamma` is private and is intentionally NOT exported.)

- [ ] **Step 4: Run the whole suite + lint**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: PASS — all prior tests (147) + the new FDR tests (13) = ~160 green; ruff clean. Confirm `tests/test_isolation.py` passes (no `polymer_formalclaim` import leaked in).

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/__init__.py grammar/tests/test_fdr.py
git commit -m "feat(grammar): export online-FDR ledger public API"
```

---

## Final integration

- [ ] **Merge to main** (no-ff, per project rhythm):

```bash
cd ~/Desktop/polymer-claims
git checkout main
git merge --no-ff phase7-fdr-ledger -m "merge: online-FDR ledger (Phase 7 — protocol requirement #4)"
cd grammar && uv run pytest -q   # verify green on the merged result
git branch -d phase7-fdr-ledger
```

- [ ] **Update** the Progress Log (below), `docs/superpowers/CONTINUE.md`, the root README, and memory `project_polymer_claims_knowledge_protocol`. Note this completes unified-spec §5 requirement #4 (and #6 was done in L3); requirements #1, #2, #3, #5 remain for future protocol-field phases.

---

## Progress Log

_(Update after every completed task: check the box, note the commit SHA + any decisions.)_

- [x] Task 1 — LOND discount sequence `_gamma` — `4120b9c`
- [x] Task 2 — FDRTest + FDRLedger models — `85510e5`
- [x] Task 3 — process_test (LOND step) — `2ce31fd`
- [x] Task 4 — process_stream + is_discovery — `67edc0d`
- [x] Task 5 — exports + whole-package verify — `590e454`
- [x] Final — merged `--no-ff` to main (`f41375b`), 160 tests green + ruff clean on merged result, branch deleted. Opus final review = READY TO MERGE (LOND recurrence hand-verified; immutability + edge cases + isolation confirmed). Docs + memory updated. Completes unified-spec §5 #4 (#6 done in L3); #1/#2/#3/#5 remain.
