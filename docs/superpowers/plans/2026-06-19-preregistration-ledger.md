# Pre-Registration Ledger (Phase D, slice 1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a hypothesis commit before it sees data — registration charges + locks the e-LOND α-slot (strict, no refund) and a verify-time match-gate rejects post-hoc changes — so an autonomous agent fishing across N hypotheses can't keep `q` artificially honest.

**Architecture:** Pure-code, additive, opt-in. Grammar gains `commitment_hash` (`grammar/commitment.py`), two `FDRLedger` ops (`register_test`/`resolve_test`) with `FDRTest.e_value` now optional, and one `RejectionReason`. Protocol gains a `register_hypotheses` stage and a match-gate + resolution branch in `verify_stage`. Registration state lives inside the existing `fdr_ledger` (Corpus stays exactly 4). Absent registration, every path is byte-identical to today.

**Tech Stack:** Python 3, Pydantic v2 frozen models (`_Model`), stdlib `hashlib`/`json`/`math`. Packages: `polymer_grammar` (pure), `polymer_protocol` (pure). Tests via `uv run pytest`.

## Global Constraints

- **grammar/protocol stay pure + deterministic + numpy-free** (no clock/random/IO; `commitment_hash` uses stdlib only). Enforced by `grammar/tests/test_isolation.py`.
- **Corpus = exactly 4 collections** (claims, defeat_edges, equivalences, fdr_ledger). Registration lives in `fdr_ledger` — **no new collection**.
- **Additive / opt-in / byte-identical when off.** New fields default (`e_value` may be `None`, `commitment_hash=None`); a `run_cycle` with no registrations must be identical to today. The full existing suite (**351 grammar + 363 protocol + 2 isolation + 261 umbrella**) must stay green unchanged.
- **e-LOND math (unchanged form):** `α_t = target_fdr · γ_t · (D_{t-1}+1)`, `γ_j=(6/π²)/j²`, discovery iff `e ≥ 1/α_t`. Registration locks `α_t` at commit; resolution decides discovery against the locked α.
- **Hypothesis identity:** `commitment_hash(claim) = "sha256:" + sha256(claim.evaluation_plan.model_dump_json()).hexdigest()`.
- **Integrity violation** = `RejectionReason.HYPOTHESIS_ALTERED` (terminal, never reinstatable).
- **Test commands:** grammar → `cd grammar && uv run pytest tests/<f> -q`; protocol → `cd protocol && uv run pytest tests/<f> -q`; full gate → `scripts/check-all.sh`. Working dir `/Users/zbb2/Desktop/polymer-claims`. Suggested branch: `feat/preregistration-ledger`.

---

### Task 1: `commitment_hash` (grammar)

**Files:**
- Create: `grammar/src/polymer_grammar/commitment.py`
- Create: `grammar/tests/test_commitment.py`
- Modify: `grammar/src/polymer_grammar/__init__.py` (export `commitment_hash`)

**Interfaces:**
- Consumes: `Claim`, `EvaluationPlan` (grammar).
- Produces: `commitment_hash(claim: Claim) -> str` — deterministic content hash of `claim.evaluation_plan`; raises `ValueError` if the claim has no plan.

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_commitment.py
import pytest

from polymer_grammar.commitment import commitment_hash
from polymer_grammar.leaf import CategoricalLeaf, MeasurementBasis
from polymer_grammar.operations import (
    Comparator, ComputeGraph, EvaluationPlan, OperationNode, ProducedLeafSpec, SatisfactionCriterion,
)
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import Status
from polymer_grammar.claim import Claim

_PATTERN = PatternRef(id="adjusted_effect", version="v1")   # field is `id` (matches conftest _PATTERN)


def _plan(value: float, threshold: float, comparator=Comparator.GT, region=("cg1", "cg2")):
    node = OperationNode(
        id="n0", impl="builtin::const",
        params=(("value", str(value)), ("region", ",".join(region))),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )


def _claim(cid, plan):
    return Claim(id=cid, title=cid, pattern=_PATTERN,
                 leaves=(CategoricalLeaf(ontology_term="t"),), status=Status.CONJECTURED,
                 evaluation_plan=plan)


def test_hash_is_deterministic_and_prefixed():
    h1 = commitment_hash(_claim("c", _plan(0.2, 0.10)))
    h2 = commitment_hash(_claim("c", _plan(0.2, 0.10)))
    assert h1 == h2 and h1.startswith("sha256:")


def test_hash_independent_of_claim_id():
    # the commitment is the PLAN, not the id
    assert commitment_hash(_claim("a", _plan(0.2, 0.10))) == commitment_hash(_claim("b", _plan(0.2, 0.10)))


def test_hash_changes_on_threshold_region_or_comparator():
    base = commitment_hash(_claim("c", _plan(0.2, 0.10)))
    assert commitment_hash(_claim("c", _plan(0.2, 0.20))) != base          # threshold
    assert commitment_hash(_claim("c", _plan(0.2, 0.10, region=("cg1",)))) != base  # region
    assert commitment_hash(_claim("c", _plan(0.2, 0.10, comparator=Comparator.LT))) != base  # comparator


def test_hash_requires_a_plan():
    no_plan = Claim(id="c", title="c", pattern=_PATTERN,
                    leaves=(CategoricalLeaf(ontology_term="t"),), status=Status.CONJECTURED)
    with pytest.raises(ValueError):
        commitment_hash(no_plan)
```

- [ ] **Step 2: Run — verify it fails**

Run: `cd grammar && uv run pytest tests/test_commitment.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_grammar.commitment'`.

- [ ] **Step 3: Implement**

```python
# grammar/src/polymer_grammar/commitment.py
"""Hypothesis content-hash for the pre-registration ledger (Phase D). A claim's COMMITMENT is its
`evaluation_plan` — the region/graph + criterion (comparator+threshold) + group levels. Pure: stdlib
only; deterministic because models are frozen with tuple collections (canonical JSON)."""
from __future__ import annotations

import hashlib

from .claim import Claim


def commitment_hash(claim: Claim) -> str:
    """Content hash of the claim's evaluation_plan. Raises ValueError if the claim has no plan."""
    if claim.evaluation_plan is None:
        raise ValueError(f"claim {claim.id!r} has no evaluation_plan to commit")
    payload = claim.evaluation_plan.model_dump_json().encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()
```

Add to `grammar/src/polymer_grammar/__init__.py`: `from .commitment import commitment_hash` and add `"commitment_hash"` to `__all__`.

- [ ] **Step 4: Run — verify it passes**

Run: `cd grammar && uv run pytest tests/test_commitment.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/commitment.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_commitment.py
git commit -m "feat(grammar): commitment_hash — content hash of a claim's evaluation_plan (Phase D)"
```

---

### Task 2: `FDRTest` optional fields + `register_test`/`resolve_test` (grammar)

**Files:**
- Modify: `grammar/src/polymer_grammar/fdr.py`
- Modify: `grammar/src/polymer_grammar/status.py` (add `RejectionReason.HYPOTHESIS_ALTERED`)
- Modify: `grammar/src/polymer_grammar/__init__.py` (export `register_test`, `resolve_test`)
- Create: `grammar/tests/test_fdr_registration.py`

**Interfaces:**
- Consumes: `FDRLedger`, `FDRTest`, `_gamma`, `process_test` (fdr.py).
- Produces: `register_test(ledger, claim_id, commitment_hash) -> FDRLedger`; `resolve_test(ledger, claim_id, e_value) -> FDRLedger`; `FDRTest.e_value: float | None`; `FDRTest.commitment_hash: str | None`.

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_fdr_registration.py
import math

import pytest

from polymer_grammar.fdr import FDRLedger, process_test, register_test, resolve_test

Q = 0.05
G1 = (6.0 / math.pi**2)            # gamma_1


def _ledger():
    return FDRLedger(target_fdr=Q)


def test_register_appends_pending_and_locks_alpha():
    led = register_test(_ledger(), "c1", "sha256:aa")
    assert led.n_tests == 1 and led.n_discoveries == 0       # pending is not a discovery
    t = led.tests[0]
    assert t.e_value is None and t.discovery is False
    assert t.commitment_hash == "sha256:aa"
    assert t.alpha_allocated == pytest.approx(Q * G1 * 1)    # alpha locked at registration


def test_resolve_fills_evalue_and_decides_against_locked_alpha():
    led = register_test(_ledger(), "c1", "sha256:aa")
    alpha = led.tests[0].alpha_allocated
    # an e-value just above 1/alpha is a discovery; just below is not
    led_hit = resolve_test(led, "c1", 1.0 / alpha + 1.0)
    led_miss = resolve_test(led, "c1", 1.0 / alpha - 0.0001)
    assert led_hit.tests[0].discovery is True and led_hit.n_discoveries == 1
    assert led_miss.tests[0].discovery is False and led_miss.n_discoveries == 0


def test_register_then_resolve_in_order_equals_process_test():
    # soundness: a single registered+resolved test == charge-at-verify for the same single test
    e = 25.0
    via_register = resolve_test(register_test(_ledger(), "c1", "sha256:aa"), "c1", e)
    via_process = process_test(_ledger(), "c1", e)
    assert via_register.tests[0].alpha_allocated == pytest.approx(via_process.tests[0].alpha_allocated)
    assert via_register.tests[0].discovery == via_process.tests[0].discovery


def test_multiplicity_is_charged():
    # an e-value that is a discovery at t=1 is NOT a discovery at t=10 after 9 prior registrations
    led = _ledger()
    e = 1.0 / (Q * G1) + 1.0          # clears the bar at t=1
    assert resolve_test(register_test(led, "x", "h"), "x", e).tests[-1].discovery is True
    for i in range(9):
        led = register_test(led, f"r{i}", "h")     # 9 prior commitments consume slots
    led = register_test(led, "x", "h")             # x is now test t=10
    led = resolve_test(led, "x", e)
    x = next(t for t in led.tests if t.claim_id == "x")
    assert x.index == 10 and x.discovery is False   # same e, tightened bar -> withheld


def test_strict_no_refund_unexecuted_keeps_its_slot():
    led = register_test(_ledger(), "never_run", "h")   # registered, never resolved
    led = register_test(led, "c2", "h")                # c2 is test t=2, not t=1
    assert led.tests[1].index == 2
    assert led.tests[1].alpha_allocated == pytest.approx(Q * (6.0 / math.pi**2 / 4) * 1)  # gamma_2


def test_resolve_without_pending_raises():
    with pytest.raises(ValueError):
        resolve_test(_ledger(), "ghost", 10.0)


def test_pending_entry_serializes_roundtrip():
    led = register_test(_ledger(), "c1", "sha256:aa")
    again = FDRLedger.model_validate_json(led.model_dump_json())
    assert again.tests[0].e_value is None and again.tests[0].commitment_hash == "sha256:aa"


def test_out_of_order_resolution_is_conservative():
    # register A then B; resolve B (a discovery) BEFORE A. A's alpha was LOCKED at registration with
    # D=0, so it must NOT retroactively benefit from B's later discovery -> conservative (FDR<=q safe).
    led = register_test(_ledger(), "A", "h")
    led = register_test(led, "B", "h")
    a_alpha = next(t for t in led.tests if t.claim_id == "A").alpha_allocated
    led = resolve_test(led, "B", 1e6)          # B resolves first, as a discovery
    led = resolve_test(led, "A", 1e6)          # A resolves second
    a = next(t for t in led.tests if t.claim_id == "A")
    assert a.alpha_allocated == a_alpha == pytest.approx(Q * G1 * 1)   # unchanged; D was 0 at A's registration
    assert a.discovery is True
```

- [ ] **Step 2: Run — verify it fails**

Run: `cd grammar && uv run pytest tests/test_fdr_registration.py -q`
Expected: FAIL — `ImportError: cannot import name 'register_test'`.

- [ ] **Step 3: Implement**

In `grammar/src/polymer_grammar/fdr.py`, change the `FDRTest.e_value` field and add `commitment_hash`, then add the two ops:

```python
class FDRTest(_Model):
    index: int
    claim_id: str
    e_value: float | None = Field(default=None, ge=0.0)   # None = registered, unresolved
    alpha_allocated: float
    discovery: bool
    retracted: bool = False
    commitment_hash: str | None = None
```

(Existing callers always pass `e_value=<float>`, so resolved entries are unchanged.) Append:

```python
def register_test(ledger: FDRLedger, claim_id: str, commitment_hash: str) -> FDRLedger:
    """Pre-registration: advance the e-LOND stream and LOCK α_t for `claim_id` BEFORE its e-value
    exists. Appends a pending FDRTest (e_value=None, discovery=False). Strict: the slot is consumed
    even if the hypothesis is never resolved. Returns a NEW ledger (append-only)."""
    t = ledger.n_tests + 1
    alpha = ledger.target_fdr * _gamma(t) * (ledger.n_discoveries + 1)
    entry = FDRTest(
        index=t, claim_id=claim_id, e_value=None, alpha_allocated=alpha,
        discovery=False, commitment_hash=commitment_hash,
    )
    return ledger.model_copy(update={"tests": ledger.tests + (entry,)})


def resolve_test(ledger: FDRLedger, claim_id: str, e_value: float) -> FDRLedger:
    """Fill the e-value for `claim_id`'s pending registration and decide discovery against the
    LOCKED alpha (e_value >= 1/alpha_allocated). Raises ValueError if no pending entry exists."""
    idx = next(
        (i for i in range(len(ledger.tests) - 1, -1, -1)
         if ledger.tests[i].claim_id == claim_id
         and ledger.tests[i].e_value is None and not ledger.tests[i].retracted),
        None,
    )
    if idx is None:
        raise ValueError(f"no pending registration for claim {claim_id!r}")
    old = ledger.tests[idx]
    resolved = old.model_copy(update={
        "e_value": e_value, "discovery": e_value >= 1.0 / old.alpha_allocated,
    })
    return ledger.model_copy(update={"tests": ledger.tests[:idx] + (resolved,) + ledger.tests[idx + 1:]})
```

In `grammar/src/polymer_grammar/status.py`, add to `RejectionReason`:

```python
    HYPOTHESIS_ALTERED = "hypothesis_altered"     # plan changed after pre-registration (terminal)
```

Export `register_test`, `resolve_test` from `grammar/src/polymer_grammar/__init__.py` `__all__`.

- [ ] **Step 4: Run — verify it passes + nothing regressed**

Run: `cd grammar && uv run pytest tests/test_fdr_registration.py -q && uv run pytest -q`
Expected: new file PASS (7 passed); full grammar suite still green (351+ passed) — `e_value` defaulting to `None` must not break existing `process_test` callers (they always pass a float).

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/fdr.py grammar/src/polymer_grammar/status.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_fdr_registration.py
git commit -m "feat(grammar): register_test/resolve_test — pre-registration charges+locks the e-LOND slot (Phase D)"
```

---

### Task 3: `register_hypotheses` stage (protocol)

**Files:**
- Create: `protocol/src/polymer_protocol/register.py`
- Modify: `protocol/src/polymer_protocol/__init__.py` (export `register_hypotheses`)
- Create: `protocol/tests/test_register_hypotheses.py`

**Interfaces:**
- Consumes: `Corpus` (has `.claims`, `.fdr_ledger`), `commitment_hash` (grammar), `register_test` (grammar).
- Produces: `register_hypotheses(corpus, claim_ids=None) -> Corpus` — advances `fdr_ledger` with one pending registration per claim (in claim-id-sorted order); skips claims already pending or without a plan.

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_register_hypotheses.py
from polymer_grammar import Comparator, Status
from polymer_protocol import Corpus, register_hypotheses

from conftest import make_claim, make_plan


def _corpus(*claims):
    from polymer_grammar import FDRLedger
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_registers_one_pending_entry_per_claim_sorted():
    c_b = make_claim("b", Status.CONJECTURED, plan=make_plan(0.2, 0.1, Comparator.GT))
    c_a = make_claim("a", Status.CONJECTURED, plan=make_plan(0.2, 0.1, Comparator.GT))
    out = register_hypotheses(_corpus(c_b, c_a))
    led = out.corpus.fdr_ledger
    assert led.n_tests == 2
    assert [t.claim_id for t in led.tests] == ["a", "b"]            # claim-id-sorted, deterministic
    assert all(t.e_value is None and t.commitment_hash for t in led.tests)


def test_skips_claims_without_a_plan():
    c = make_claim("a", Status.CONJECTURED, plan=None)
    out = register_hypotheses(_corpus(c))
    assert out.corpus.fdr_ledger.n_tests == 0


def test_idempotent_no_double_charge():
    c = make_claim("a", Status.CONJECTURED, plan=make_plan(0.2, 0.1, Comparator.GT))
    once = register_hypotheses(_corpus(c))
    twice = register_hypotheses(once)
    assert twice.fdr_ledger.n_tests == 1                            # second call is a no-op for 'a'


def test_commitment_hash_recorded_matches_grammar():
    from polymer_grammar.commitment import commitment_hash
    c = make_claim("a", Status.CONJECTURED, plan=make_plan(0.2, 0.1, Comparator.GT))
    out = register_hypotheses(_corpus(c))
    assert out.corpus.fdr_ledger.tests[0].commitment_hash == commitment_hash(c)
```

- [ ] **Step 2: Run — verify it fails**

Run: `cd protocol && uv run pytest tests/test_register_hypotheses.py -q`
Expected: FAIL — `ImportError: cannot import name 'register_hypotheses'`.

- [ ] **Step 3: Implement**

```python
# protocol/src/polymer_protocol/register.py
"""REGISTER stage (Phase D): pre-register hypotheses BEFORE execution. Each claim with an
evaluation_plan advances the e-LOND stream and locks its α (register_test) — the commit-before-data
step that makes q honest under an autonomous agent. Pure; Corpus stays 4 (registration lives in
fdr_ledger). Claims already pending or planless are skipped (no double-charge)."""
from __future__ import annotations

from collections.abc import Iterable

from polymer_grammar import register_test
from polymer_grammar.commitment import commitment_hash

from .corpus import Corpus


def register_hypotheses(corpus: Corpus, claim_ids: Iterable[str] | None = None) -> Corpus:
    by_id = {c.id: c for c in corpus.claims}
    targets = sorted(by_id) if claim_ids is None else sorted(set(claim_ids) & set(by_id))
    pending = {t.claim_id for t in corpus.fdr_ledger.tests if t.e_value is None and not t.retracted}
    ledger = corpus.fdr_ledger
    for cid in targets:
        claim = by_id[cid]
        if claim.evaluation_plan is None or cid in pending:
            continue
        ledger = register_test(ledger, cid, commitment_hash(claim))
    if ledger == corpus.fdr_ledger:
        return corpus
    return corpus.model_copy(update={"fdr_ledger": ledger})
```

Export `register_hypotheses` from `protocol/src/polymer_protocol/__init__.py`.

- [ ] **Step 4: Run — verify it passes**

Run: `cd protocol && uv run pytest tests/test_register_hypotheses.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/register.py protocol/src/polymer_protocol/__init__.py protocol/tests/test_register_hypotheses.py
git commit -m "feat(protocol): register_hypotheses — commit-before-data REGISTER stage (Phase D)"
```

---

### Task 4: verify match-gate + resolution (protocol)

**Files:**
- Modify: `protocol/src/polymer_protocol/verify.py` (the FDR block, ~lines 133-146)
- Create: `protocol/tests/test_verify_preregistration.py`

**Interfaces:**
- Consumes: `register_hypotheses`, `commitment_hash`, `resolve_test`, `run_cycle`.
- Produces: behavior — a pre-registered claim resolves against its locked α; a claim whose plan changed after registration is REJECTED with `HYPOTHESIS_ALTERED`; non-registered claims unchanged.

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_verify_preregistration.py
from polymer_grammar import Comparator, MaterializationContext, RejectionReason, Status
from polymer_grammar import IdentityAdapter, ReferenceAdapter
from polymer_protocol import Corpus, register_hypotheses, run_cycle

from conftest import make_claim, make_plan

ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
CTX = MaterializationContext(id="M", api_version="v1", data_version="d1")


def _run(corpus, evidence):
    return run_cycle(corpus, ADAPTERS, CTX, evidence=evidence)


def test_registered_claim_resolves_and_can_license():
    # const plan value=12 > threshold 10 -> satisfied; big e-value -> discovery at t=1
    from polymer_grammar import FDRLedger
    c = make_claim("c", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
    corpus = register_hypotheses(Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05)))
    out = _run(corpus, {"c": 1e6})
    led = out.corpus.fdr_ledger
    assert led.n_tests == 1 and led.tests[0].e_value == 1e6 and led.tests[0].discovery is True
    assert out.corpus.claims[0].status is Status.LICENSED


def test_post_hoc_alteration_is_rejected():
    # register with threshold 10, then run with the plan mutated to threshold 5 (a different hypothesis)
    from polymer_grammar import FDRLedger
    registered = make_claim("c", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
    corpus = register_hypotheses(Corpus(claims=(registered,), fdr_ledger=FDRLedger(target_fdr=0.05)))
    altered = make_claim("c", Status.PENDING, plan=make_plan(12.0, 5.0, Comparator.GT))   # same id, new plan
    corpus = corpus.model_copy(update={"claims": (altered,)})
    out = _run(corpus, {"c": 1e6})
    c_out = out.corpus.claims[0]
    assert c_out.status is Status.REJECTED
    assert c_out.rejection_reason is RejectionReason.HYPOTHESIS_ALTERED
    # the slot stays consumed and pending (never a discovery)
    assert out.corpus.fdr_ledger.tests[0].e_value is None and out.corpus.fdr_ledger.n_discoveries == 0


def test_no_registration_is_byte_identical():
    # a run WITHOUT register_hypotheses uses the existing charge-at-verify path unchanged
    from polymer_grammar import FDRLedger
    c = make_claim("c", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
    plain = Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05))
    out = _run(plain, {"c": 1e6})
    assert out.corpus.fdr_ledger.n_tests == 1 and out.corpus.fdr_ledger.tests[0].commitment_hash is None
    assert out.corpus.claims[0].status is Status.LICENSED   # identical outcome to pre-Phase-D


def test_strict_no_refund_across_a_cycle():
    # a registered claim with NO evidence this cycle keeps its pending slot (not refunded)
    from polymer_grammar import FDRLedger
    c = make_claim("c", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
    corpus = register_hypotheses(Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05)))
    out = _run(corpus, {})            # no e-value supplied -> not resolved
    assert out.corpus.fdr_ledger.n_tests == 1 and out.corpus.fdr_ledger.tests[0].e_value is None
```

- [ ] **Step 2: Run — verify it fails**

Run: `cd protocol && uv run pytest tests/test_verify_preregistration.py -q`
Expected: FAIL — `test_post_hoc_alteration_is_rejected` (no match-gate yet) and `test_registered_claim_resolves...` (registered claim's pending entry blocks the existing `already_tested` path so it never resolves → not LICENSED).

- [ ] **Step 3: Implement the match-gate + resolution in `verify_stage`**

In `protocol/src/polymer_protocol/verify.py`, replace the FDR block (currently `verify.py:133-146`) so pre-registered claims are handled before the charge-at-verify path. Add near the top of the file: `from polymer_grammar import resolve_test` and `from polymer_grammar.commitment import commitment_hash`.

```python
    ev_map = evidence or {}
    led = corpus.fdr_ledger

    # --- Phase D: resolve pre-registered claims (match-gate + locked-alpha resolution) ---
    pending = {t.claim_id: t for t in led.tests if t.e_value is None and not t.retracted}
    by_id = {c.id: c for c in corpus.claims}
    altered_ids: set[str] = set()
    reg_decisions: dict[str, bool] = {}
    for rec in exec_records:
        cid = rec.claim_id
        if cid in pending and cid in ev_map:
            claim = by_id.get(cid)
            if claim is None or claim.evaluation_plan is None:
                continue
            if commitment_hash(claim) != pending[cid].commitment_hash:
                altered_ids.add(cid)                      # post-hoc change -> integrity violation
                continue
            led = resolve_test(led, cid, ev_map[cid])
            reg_decisions[cid] = led.tests[next(
                i for i in range(len(led.tests) - 1, -1, -1) if led.tests[i].claim_id == cid
            )].discovery

    # --- existing charge-at-verify path (unchanged) for NON-registered, NON-altered claims ---
    already_tested = {t.claim_id for t in led.tests if not t.retracted}
    executed_with_e = [
        (r.claim_id, ev_map[r.claim_id])
        for r in exec_records
        if r.claim_id in ev_map and r.claim_id not in already_tested and r.claim_id not in altered_ids
    ]
    new_ledger, e_decisions = elond_decisions(led, executed_with_e)

    def _e_ok(cid: str) -> bool:
        if cid in altered_ids:
            return False
        return (cid not in ev_map
                or reg_decisions.get(cid, e_decisions.get(cid, cid in corpus.fdr_ledger.discoveries)))
```

Then in the per-claim loop (`for c in corpus.claims:`), before the normal licensing decision, add the integrity rejection:

```python
        if c.id in altered_ids:
            new_claims.append(_with_status(
                c, status=Status.REJECTED, pending_reason=None,
                rejection_reason=RejectionReason.HYPOTHESIS_ALTERED,
            ))
            continue
```

Use the existing `_with_status` helper (`verify.py:112`) — like every other status mutation in this file — so `Claim` validators re-run after the copy (a bare `model_copy` skips them). Ensure `RejectionReason` is imported in verify.py (`Status` already is).

- [ ] **Step 4: Run — verify it passes + nothing regressed**

Run: `cd protocol && uv run pytest tests/test_verify_preregistration.py -q && uv run pytest -q`
Expected: new file PASS (4 passed); full protocol suite still green (363+ passed) — the `test_no_registration_is_byte_identical` case and every existing verify test confirm the non-registered path is unchanged.

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/verify.py protocol/tests/test_verify_preregistration.py
git commit -m "feat(protocol): verify match-gate + locked-alpha resolution for pre-registered claims (Phase D)"
```

---

### Task 5: reinstatement guard + multiplicity e2e (protocol)

**Files:**
- Modify: `protocol/src/polymer_protocol/integrate.py` (confirm/guard `HYPOTHESIS_ALTERED` is not reinstatable)
- Create: `protocol/tests/test_preregistration_e2e.py`

**Interfaces:**
- Consumes: the full register→run_cycle path; `integrate`'s reinstatement pass.
- Produces: confirmation that a `HYPOTHESIS_ALTERED` rejection never reopens, and an end-to-end demonstration that registration charges the multiplicity.

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_preregistration_e2e.py
from polymer_grammar import Comparator, FDRLedger, MaterializationContext, RejectionReason, Status
from polymer_grammar import IdentityAdapter, ReferenceAdapter
from polymer_protocol import Corpus, register_hypotheses, run_cycle

from conftest import make_claim, make_plan

ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
CTX = MaterializationContext(id="M", api_version="v1", data_version="d1")


def test_multiplicity_charged_end_to_end():
    # One real claim that would license alone; preceded by 9 registered decoys (fished hypotheses).
    # The locked alpha at t=10 raises the bar so a moderate e-value is WITHHELD.
    import math
    q, g1 = 0.05, 6.0 / math.pi**2
    moderate_e = 1.0 / (q * g1) + 5.0                 # clears t=1 bar, far below the t=10 bar
    target = make_claim("zzz_target", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
    decoys = [make_claim(f"decoy{i}", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
              for i in range(9)]
    corpus = register_hypotheses(
        Corpus(claims=(*decoys, target), fdr_ledger=FDRLedger(target_fdr=q)))
    out = run_cycle(corpus, ADAPTERS, CTX, evidence={"zzz_target": moderate_e})   # returns CycleResult
    t = next(x for x in out.corpus.fdr_ledger.tests if x.claim_id == "zzz_target")
    assert t.index == 10 and t.discovery is False         # multiplicity charged -> withheld
    target_out = next(c for c in out.corpus.claims if c.id == "zzz_target")
    assert target_out.status is not Status.LICENSED


def test_hypothesis_altered_is_not_reinstatable():
    # an integrity rejection must stay terminal even if its (nonexistent) attacker scenario is run
    from polymer_protocol.integrate import _reinstate  # the per-claim reinstatement helper
    rejected = make_claim("c", Status.REJECTED, rejection_reason=RejectionReason.HYPOTHESIS_ALTERED)
    out = _reinstate(rejected)
    assert out.status is Status.REJECTED                  # NOT reopened to PENDING
    assert out.rejection_reason is RejectionReason.HYPOTHESIS_ALTERED
```

- [ ] **Step 2: Run — verify it fails (or reveals the guard already holds)**

Run: `cd protocol && uv run pytest tests/test_preregistration_e2e.py -q`
Expected: `test_hypothesis_altered_is_not_reinstatable` may FAIL if `_reinstate` reopens any REJECTED claim regardless of reason. Inspect `integrate.py:_reinstate`.

- [ ] **Step 3: Implement the guard (REQUIRED — `_reinstate` is currently unconditional)**

`integrate.py:_reinstate` (lines ~50-62) **always** returns `status=PENDING` — the reason gate lives in the caller `integrate()`, not here. Make `_reinstate` defensive so a non-reinstatable reason is never reopened (this is what `test_hypothesis_altered_is_not_reinstatable` pins). Add as the **first statement** of `_reinstate`:

```python
def _reinstate(c: Claim) -> Claim:
    # only a defeat-grounded-out rejection reopens; refuted / robustly-blamed / hypothesis-altered
    # are terminal. (Mirrors the integrate() gate; makes _reinstate safe to call directly.)
    if c.rejection_reason is not RejectionReason.DEFEAT_GROUNDED_OUT:
        return c
    return Claim.model_validate(
        c.model_copy(update={
            "status": Status.PENDING, "licensing": None,
            "pending_reason": PendingReason.REINSTATED, "rejection_reason": None,
        }).model_dump()
    )
```

Ensure `RejectionReason` is imported in `integrate.py` (it already is — used for `DEFEAT_GROUNDED_OUT`). This is a real, required code change — not a no-op.

- [ ] **Step 4: Run — verify it passes + full protocol suite**

Run: `cd protocol && uv run pytest tests/test_preregistration_e2e.py -q && uv run pytest -q`
Expected: PASS (2 passed); full protocol suite green.

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/integrate.py protocol/tests/test_preregistration_e2e.py
git commit -m "test(protocol): multiplicity-charged e2e + HYPOTHESIS_ALTERED is terminal (Phase D)"
```

---

### Task 6: Full gate — isolation, numpy-free, byte-identical, ruff

**Files:** none new (verification + any lint fixes).

**Interfaces:** none.

- [ ] **Step 1: Run the grammar isolation + numpy-free guards**

Run: `cd grammar && uv run pytest tests/test_isolation.py -q`
Expected: PASS — `polymer_grammar` still imports without `polymer_formalclaim`/numpy; the new `commitment.py` uses stdlib only.

- [ ] **Step 2: Run the full local gate**

Run: `scripts/check-all.sh`
Expected: ALL GREEN — umbrella (261) + grammar (351 + new) + protocol (363 + new) + isolation (2); ruff clean on `src tests` for each package; viewer tsc/build unaffected. The byte-identical guarantee is evidenced by the *existing* suites passing unchanged.

- [ ] **Step 3: Fix any ruff findings**

Run: `cd grammar && uv run ruff check src tests` and `cd protocol && uv run ruff check src tests`
Expected: clean. Fix imports/formatting if flagged (e.g. unused import, line length); re-run.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A && git commit -m "chore: ruff + gate green for the pre-registration ledger (Phase D)" || echo "nothing to fix"
```

- [ ] **Step 5: Finish the branch** — use `superpowers:finishing-a-development-branch`.

---

## Completeness & Validity Audit

**A. Spec-requirement → task → test coverage (every §-requirement maps to a covering test):**

| Spec requirement | Task | Covering test(s) |
|---|---|---|
| §3.1 `register_test` advances stream + locks α at commit | 2 | `test_register_appends_pending_and_locks_alpha` |
| §3.1 `resolve_test` decides against locked α | 2 | `test_resolve_fills_evalue_and_decides_against_locked_alpha` |
| §1.2 strict, no refund | 2, 4 | `test_strict_no_refund_unexecuted_keeps_its_slot`, `test_strict_no_refund_across_a_cycle` |
| §7.1 multiplicity charged | 2, 5 | `test_multiplicity_is_charged`, `test_multiplicity_charged_end_to_end` |
| §3.1 soundness (register+resolve == process_test in order) | 2 | `test_register_then_resolve_in_order_equals_process_test` |
| §7.4 out-of-order resolution is conservative | 2 | `test_out_of_order_resolution_is_conservative` |
| §3.1 pending not a discovery / serialization | 2 | `test_register_appends_pending_and_locks_alpha`, `test_pending_entry_serializes_roundtrip` |
| §3.2 `commitment_hash` deterministic + plan-sensitive | 1 | `test_hash_is_deterministic_and_prefixed`, `test_hash_changes_on_threshold_region_or_comparator`, `test_hash_independent_of_claim_id` |
| §4.1 REGISTER sorted/idempotent/plan-guarded | 3 | `test_registers_one_pending_entry_per_claim_sorted`, `test_idempotent_no_double_charge`, `test_skips_claims_without_a_plan`, `test_commitment_hash_recorded_matches_grammar` |
| §1.3/§4.2 match-gate rejects post-hoc change | 4 | `test_post_hoc_alteration_is_rejected` |
| §4.2 registered claim resolves + licenses | 4 | `test_registered_claim_resolves_and_can_license` |
| §3.3 `HYPOTHESIS_ALTERED` terminal (not reinstatable) | 5 | `test_hypothesis_altered_is_not_reinstatable` |
| §2/§5 opt-in byte-identical | 4, 6 | `test_no_registration_is_byte_identical` + full existing suites green (Task 6) |
| §5 Corpus=4 / numpy-free / isolation | 6 | `tests/test_isolation.py`, `scripts/check-all.sh` |

**B. Validity arguments (not just coverage — why the mechanism is sound):**
1. **FDR control preserved.** Each registration locks `α_t = q·γ_t·(D_{t-1}+1)` with the standard e-LOND form; resolution only fills the e-value and applies the unchanged discovery rule `e ≥ 1/α_t`. `test_register_then_resolve_in_order_equals_process_test` pins equivalence to the proven `process_test` for the in-order case.
2. **Conservative under deferred/out-of-order resolution.** Locking α with discoveries-known-at-registration can only *undercount* `D_{t-1}` ⇒ smaller α ⇒ stricter bar ⇒ FDR ≤ q still holds (no anti-conservative path exists, since `register_test` never *raises* α relative to the ideal).
3. **Anti-fishing is real, not cosmetic.** The slot is consumed at registration regardless of outcome (`test_strict_no_refund_*`), and the e2e test shows a real claim withheld purely because decoys consumed earlier slots — the multiplicity is paid.
4. **Integrity is content-addressed.** The match-gate compares `commitment_hash` of the *executed* plan against the *registered* one; any region/criterion/level change flips the hash (`test_hash_changes_on_...`) ⇒ REJECTED, terminal (`test_hypothesis_altered_is_not_reinstatable`).
5. **Zero blast radius when off.** No registration ⇒ no pending entries ⇒ the new branch is skipped and the existing charge-at-verify path runs verbatim (`test_no_registration_is_byte_identical` + the unchanged 351+363 suites in Task 6).

**C. Gap analysis (known limitations, explicitly out of scope — not silent):**
- Deferred-resolution conservatism is argued + unit-checked **in-order and out-of-order within a single ledger** (`test_out_of_order_resolution_is_conservative`). A multi-cycle *interleaved* register/resolve **property** test (randomized, many cycles) is not included — the unit tests bound the behavior `run_cycle` actually produces today (register-then-resolve within a cycle). Flagged for a future property test if cross-cycle interleaving is added.
- `commitment_hash` hashes the entire `evaluation_plan`; a benign re-serialization that changed plan JSON without changing meaning would (conservatively) trip the gate. Pydantic frozen+tuple canonical JSON makes this stable, but it is a *conservative* hash by design (false-positive REJECT, never false-negative ALLOW).
- No live-node/agent wiring (§6) — the mechanism is proven through `run_cycle`, which is the substrate the live node already uses.

## Independent Audit Resolution (2026-06-19)

This plan passed an independent adversarial completeness audit that verified the test code against the real APIs. All findings folded:
- **Critical — `run_cycle` returns `CycleResult`, not `Corpus`.** Every test now uses `out.corpus.fdr_ledger` / `out.corpus.claims` (and `next(c for c in out.corpus.claims …)` for lookups).
- **Critical — `PatternRef` field is `id`, version `v1`.** Fixed in `test_commitment.py` `_PATTERN`.
- **Critical — `integrate._reinstate` is unconditional.** Task 5 Step 3 now *requires* adding the `DEFEAT_GROUNDED_OUT`-only guard to `_reinstate` (no "no-op" hedge).
- **Important — status mutation must re-run validators.** Task 4 uses the existing `_with_status` helper, not a bare `model_copy`.
- **Important — export ordering.** Task 2 Step 3 exports `register_test`/`resolve_test` from `polymer_grammar.__init__`; Task 4's `verify.py` import depends on Task 2 completing first (task order already enforces this).
- **Minor — out-of-order conservatism** now has a dedicated test (`test_out_of_order_resolution_is_conservative`).
- Confirmed non-issues: `_e_ok` prior-discovery fallback reads the pre-cycle ledger by design; `γ₂` precedence is correct; the `register_hypotheses` pending-set snapshot is safe for a single call.
