# V2.0 Slice 1 — Evidence-licensed capability (model-vs-baseline benchmark advantage) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status / provenance:** Built from spec `docs/superpowers/specs/2026-06-29-v2-evidence-licensed-capability-design.md` (v3, post-2nd-review). The v3 spec has **not** completed a third independent audit (internal auditors were stopped to route review externally). **Review this plan together with the v3 spec.** Open design risks the external reviewer should weigh are listed in "Known open risks" below.

**Goal:** Register a fourth capability cell, `eval::benchmark_advantage@v1`, that licenses an inferential "model beats a precommitted baseline on held-out examples" claim via a paired sequential betting e-value gated by e-LOND — a second, honest licensing route that does not use the two-adapter recompute air-gap.

**Architecture:** Umbrella-side orchestration (Seam B). A new umbrella primitive computes a paired betting e-value; a typed `BenchmarkAdapter`/`Scorer` interface keeps gold labels out of the model; an umbrella orchestrator emits a typed `ResolvedVerification`; a new protocol dispatch in `run_cycle`/`verify_stage` licenses from it without calling the two-adapter `verify()`. Grammar gains additive, optional fields (a new license route, a verification standing, an evidence-provenance record, an execution-error pending reason) and a pure `EvidencePolicy` content-addressed model.

**Tech Stack:** Python 3, Pydantic frozen `_Model`s, numpy (umbrella `[embed]`/evidence side only), pytest, ruff, `uv`.

## Global Constraints

- `grammar/` and `protocol/` MUST stay pure + deterministic + **numpy-free** (no clock/random/IO; time-like inputs passed in). numpy lives only umbrella-side. (Verbatim invariant from CONTINUE.md.)
- `grammar/` MUST NEVER import `polymer_formalclaim`; `protocol/` depends one-way on `grammar/` (isolation-tested by `grammar/tests/test_isolation.py`).
- `Corpus` = exactly 4 collections (claims, defeat_edges, equivalences, fdr_ledger). Do not add a 5th.
- All models subclass `_Model` (frozen, `extra="forbid"`); collections are **tuples**, never `dict`/`list` fields on models. (Function parameters may be `dict`/`tuple` — only model *fields* are constrained.)
- New cross-cutting fields land **additive/optional** (`X | None = None`) with a present-only-when-relevant validator; opt-in features default to byte-identical behavior when off.
- Per-package tests: `uv run pytest -q` + `uv run ruff check src tests` in each of `grammar/`, `protocol/`, and the umbrella root. Full gate: `scripts/check-all.sh`. TDD: failing test first.
- Merge to `main` `--no-ff` after whole-branch review. Current feature branch: `feat/v2-evidence-capability`.

## Known open risks (for the external reviewer)

1. **E-value validity under the declared regime.** `paired_advantage_evalue` reuses `_grapa_capital` (`src/polymer_claims/evidence.py:28`). Validity of `E_H0[E] ≤ 1` rests on (a) the increments `Wᵢ∈[−1,1]` keeping every capital factor `1+λᵢWᵢ>0` — satisfied because the most-negative increment is `−1` and `λ_max=_C=0.9` ⇒ factors `≥ 0.1`; and (b) the **disclosed assumption** that benchmark examples are an IID/exchangeable draw so `E[Wᵢ|history]≤0` holds under H0. Seed-averaging over orderings is a convex combination of valid e-values, so it preserves `E≤1`. Confirm this argument is acceptable; if a stronger guarantee is wanted, the fallback is a single canonical order plus a documented exchangeability statement.
2. **Protocol blast radius.** Evidence-licensed claims must bypass `execute_ground` (`protocol/.../execute.py:58`), whose `verify()` licenses only with ≥2 distinct adapters (`evaluate.py:394`), AND be licensed in `verify_stage` from the injected `ResolvedVerification`. This touches `run_cycle`, the executability gate, and `verify_stage`. Tasks 11–13 isolate it. *(Minting a single-source `Satisfaction` in the orchestrator is not unprecedented — `replication.py:103,118` already constructs `Satisfaction` outside `verify()`; only the licensing route is new.)*
3. **Compatibility level.** Adding optional fields to frozen models can change `model_dump()`; the target is canonical-serialization + content-address identical for the three existing cells (Task 15 golden). If the serializer does not exclude unset defaults, a one-time documented content-address bump is the fallback.

---

## File structure

**Phase 1a — umbrella primitives + pure policy model (licenses nothing yet; fully unit-testable):**
- Create `grammar/src/polymer_grammar/evidence_policy.py` — `EvidencePolicy` (pure frozen `_Model`; ref = its `content_hash`) + `EvidencePolicyRegistry` (tuple + `resolve`).
- Create `src/polymer_claims/benchmark_evidence.py` — `paired_advantage_evalue`, `PredictionVector`, `score_advantage` (the Scorer), degenerate-input validation.
- Create `src/polymer_claims/benchmark_adapter.py` — `BenchmarkAdapter` Protocol + a deterministic in-repo fixture adapter + baseline.

**Phase 1b — grammar schema deltas + orchestrator + protocol dispatch (end-to-end license):**
- Modify `grammar/src/polymer_grammar/licensing.py` — `LicenseRoute.EVIDENCE_LICENSED`; `independence_tier` → optional; `verification_standing` field; `EvidenceProvenance` DTO.
- Modify `grammar/src/polymer_grammar/status.py` — `PendingReason.EXECUTION_ERROR`.
- Create `grammar/src/polymer_grammar/verification_policy.py` — `VerificationPolicy` + `ResolvedVerification` (pure; carries a `Satisfaction` + provenance + floats/strings).
- Modify `grammar/src/polymer_grammar/capability.py` — optional `verification_policy` field on `CapabilityCell`.
- Create `src/polymer_claims/benchmark_capability.py` — the orchestrator: resolve cell+policy, run adapter, score, compute e-value, validity-checks, mint single-source `Satisfaction`, emit `ResolvedVerification`.
- Modify `src/polymer_claims/capabilities.py` — register `EVAL_BENCHMARK_ADVANTAGE_CELL`; `validate_trust_binding` single-mode branch.
- Modify `protocol/src/polymer_protocol/cycle.py` — thread `resolved_verifications`; gate evidence claims out of `execute_ground`.
- Modify `protocol/src/polymer_protocol/verify.py` — thread `resolved_verifications`; add their e-values to e-LOND; license-from-resolved branch.
- Tests under `grammar/tests/`, `protocol/tests/`, and `tests/capability/`.

---

## Phase 1a — umbrella primitives + pure policy model

### Task 1: Paired betting e-value primitive

**Files:**
- Create: `src/polymer_claims/benchmark_evidence.py`
- Test: `tests/capability/test_benchmark_evidence.py`

**Interfaces:**
- Produces: `paired_advantage_evalue(w: Sequence[float]) -> float` — a deterministic seed-averaged WSR betting e-value for `H0: E[Wᵢ|history] ≤ 0` over increments `Wᵢ ∈ [−1,1]`. Empty input raises `ValueError` (degenerate; caller treats as invalid input, not `0.0`).
- Consumes: `_grapa_capital`, `_C`, `_SEEDS` from `src/polymer_claims/evidence.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/capability/test_benchmark_evidence.py
import itertools
import numpy as np
import pytest
from polymer_claims.benchmark_evidence import paired_advantage_evalue


def test_all_positive_advantage_gives_large_evalue():
    # model right, baseline wrong on every example -> strong evidence
    e = paired_advantage_evalue([1.0] * 30)
    assert e > 20.0


def test_all_ties_give_evalue_one():
    # every W_i == 0 -> capital never moves -> e == 1.0
    assert paired_advantage_evalue([0.0] * 10) == pytest.approx(1.0)


def test_empty_stream_is_rejected():
    with pytest.raises(ValueError):
        paired_advantage_evalue([])


def test_null_mean_does_not_exceed_one_exact_enumeration():
    # EXACT null-mean check (audit #18): enumerate all {-1,0,1}^n weighted by a worst-case
    # boundary null E[W]=0 (symmetric: P(-1)=P(+1)=q, P(0)=1-2q). For the boundary null the
    # e-value must satisfy E[E] <= 1. Enumerate n=4, q=0.5 (P(-1)=P(+1)=0.5, no ties).
    n, q = 4, 0.5
    total = 0.0
    for combo in itertools.product((-1.0, 0.0, 1.0), repeat=n):
        k_neg = combo.count(-1.0); k_pos = combo.count(1.0); k_zero = combo.count(0.0)
        prob = (q ** k_neg) * (q ** k_pos) * ((1 - 2 * q) ** k_zero)
        if prob == 0.0:
            continue
        total += prob * paired_advantage_evalue(list(combo))
    assert total <= 1.0 + 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capability/test_benchmark_evidence.py -q`
Expected: FAIL — `ModuleNotFoundError: polymer_claims.benchmark_evidence`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/polymer_claims/benchmark_evidence.py
"""Evidence-licensed benchmark capability primitives (umbrella, numpy-side).

paired_advantage_evalue is a Waudby-Smith & Ramdas betting e-value for the SEQUENTIAL
null H0: E[W_i | history] <= 0 over paired advantage increments W_i = 1(model correct)
- 1(baseline correct) in {-1,0,+1}. Reuses the shared GRAPA capital core. Valid from
boundedness (Ville) under the disclosed IID/exchangeable sampling of examples; theta0=0
is fixed by construction (no data-dependent null).
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .evidence import _C, _SEEDS, _grapa_capital


def _capital_paired(w: np.ndarray, seed: int) -> float:
    """One betting capital process for H0: E[W] <= 0 over W in [-1, 1]. theta0 = 0, so no
    shift. Order-averaged via the seed (the process is order-dependent)."""
    rng = np.random.default_rng(seed)
    W = w[rng.permutation(len(w))]
    lam_max = _C  # support [-1,1]: most-negative W is -1, so 1 + lam*(-1) >= 1 - _C > 0
    return _grapa_capital(W, lam_max)


def paired_advantage_evalue(w: Sequence[float]) -> float:
    """Deterministic seed-averaged e-value over paired increments W_i in [-1, 1].
    Empty -> ValueError (degenerate input; the caller rejects it, never licenses)."""
    arr = np.asarray(w, dtype=float)
    if arr.size == 0:
        raise ValueError("paired_advantage_evalue: empty increment stream")
    if np.any(arr < -1.0) or np.any(arr > 1.0):
        raise ValueError("paired_advantage_evalue: increments must lie in [-1, 1]")
    es = [_capital_paired(arr, s) for s in _SEEDS]
    return float(sum(es) / len(es))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capability/test_benchmark_evidence.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/benchmark_evidence.py tests/capability/test_benchmark_evidence.py
git commit -m "feat(capability): paired-advantage betting e-value primitive"
```

### Task 2: PredictionVector + Scorer (label-withholding join)

**Files:**
- Modify: `src/polymer_claims/benchmark_evidence.py`
- Test: `tests/capability/test_benchmark_scorer.py`

**Interfaces:**
- Produces:
  - `PredictionVector` — frozen dataclass: `predictions: tuple[tuple[str, str], ...]` (ordered `(example_id, prediction)`).
  - `score_advantage(predictions: PredictionVector, baseline: PredictionVector, labels: Mapping[str, str], order: Sequence[str]) -> list[float]` — returns the `Wᵢ` stream in `order`. Raises `ScoringError` on missing/duplicate/extra/order mismatch.
  - `ScoringError(ValueError)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/capability/test_benchmark_scorer.py
import pytest
from polymer_claims.benchmark_evidence import (
    PredictionVector, ScoringError, score_advantage,
)

ORDER = ("e1", "e2", "e3")
LABELS = {"e1": "A", "e2": "B", "e3": "A"}


def _pv(d):  # helper: dict -> PredictionVector in ORDER
    return PredictionVector(predictions=tuple((k, d[k]) for k in ORDER))


def test_scores_paired_increments_in_order():
    model = _pv({"e1": "A", "e2": "B", "e3": "A"})      # 3/3 correct
    base = _pv({"e1": "A", "e2": "A", "e3": "B"})       # 1/3 correct
    # W = [1-1, 1-0, 1-0] = [0, 1, 1]
    assert score_advantage(model, base, LABELS, ORDER) == [0.0, 1.0, 1.0]


def test_missing_prediction_raises():
    model = PredictionVector(predictions=(("e1", "A"), ("e2", "B")))  # missing e3
    base = _pv({"e1": "A", "e2": "A", "e3": "B"})
    with pytest.raises(ScoringError):
        score_advantage(model, base, LABELS, ORDER)


def test_duplicate_example_id_raises():
    model = PredictionVector(predictions=(("e1", "A"), ("e1", "A"), ("e3", "A")))
    base = _pv({"e1": "A", "e2": "A", "e3": "B"})
    with pytest.raises(ScoringError):
        score_advantage(model, base, LABELS, ORDER)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capability/test_benchmark_scorer.py -q`
Expected: FAIL — names not defined.

- [ ] **Step 3: Write minimal implementation** (append to `benchmark_evidence.py`)

```python
from collections.abc import Mapping
from dataclasses import dataclass


class ScoringError(ValueError):
    """Prediction set does not cleanly join to the benchmark (missing/dup/extra/order)."""


@dataclass(frozen=True)
class PredictionVector:
    predictions: tuple[tuple[str, str], ...]  # ordered (example_id, prediction)

    def as_map(self) -> dict[str, str]:
        ids = [eid for eid, _ in self.predictions]
        if len(set(ids)) != len(ids):
            raise ScoringError("duplicate example_id in prediction vector")
        return dict(self.predictions)


def score_advantage(
    predictions: PredictionVector,
    baseline: PredictionVector,
    labels: Mapping[str, str],
    order: Sequence[str],
) -> list[float]:
    """W_i = 1(model correct) - 1(baseline correct), in `order`. Labels live ONLY here —
    never passed to a BenchmarkAdapter."""
    m = predictions.as_map()
    b = baseline.as_map()
    expected = set(order)
    for name, mp in (("model", m), ("baseline", b)):
        if set(mp) != expected:
            raise ScoringError(f"{name} example ids {set(mp)} != benchmark {expected}")
    w: list[float] = []
    for eid in order:
        if eid not in labels:
            raise ScoringError(f"no gold label for {eid}")
        w.append(float(m[eid] == labels[eid]) - float(b[eid] == labels[eid]))
    return w
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capability/test_benchmark_scorer.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/benchmark_evidence.py tests/capability/test_benchmark_scorer.py
git commit -m "feat(capability): PredictionVector + label-withholding scorer"
```

### Task 3: Degenerate-policy validation (reject, don't clamp)

**Files:**
- Modify: `src/polymer_claims/benchmark_evidence.py`
- Test: `tests/capability/test_benchmark_scorer.py` (extend)

**Interfaces:**
- Produces: `validate_advantage_stream(w: Sequence[float]) -> None` — raises `ScoringError` for empty or baseline-already-perfect (`all(wᵢ ≤ 0)`) streams (audit #13/#19). Ties-only is allowed (yields `e=1`, no license) but all-`≤0` with no positive is rejected as a vacuous benchmark.

- [ ] **Step 1: Write the failing test**

```python
def test_baseline_perfect_stream_rejected():
    from polymer_claims.benchmark_evidence import validate_advantage_stream, ScoringError
    # baseline correct everywhere model can only tie or lose -> no advantage possible
    with pytest.raises(ScoringError):
        validate_advantage_stream([0.0, -1.0, 0.0, -1.0])

def test_mixed_stream_ok():
    from polymer_claims.benchmark_evidence import validate_advantage_stream
    validate_advantage_stream([1.0, 0.0, -1.0])  # no raise
```

- [ ] **Step 2: Run** `uv run pytest tests/capability/test_benchmark_scorer.py -q` → FAIL (name not defined).

- [ ] **Step 3: Implement** (append)

```python
def validate_advantage_stream(w: Sequence[float]) -> None:
    arr = list(w)
    if not arr:
        raise ScoringError("empty advantage stream")
    if all(x <= 0.0 for x in arr):
        raise ScoringError("baseline-perfect / no positive advantage possible (vacuous benchmark)")
```

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/benchmark_evidence.py tests/capability/test_benchmark_scorer.py
git commit -m "feat(capability): reject degenerate advantage streams (no clamp)"
```

### Task 4: `EvidencePolicy` pure model (ref = content_hash)

**Files:**
- Create: `grammar/src/polymer_grammar/evidence_policy.py`
- Modify: `grammar/src/polymer_grammar/__init__.py` (export `EvidencePolicy`, `EvidencePolicyRegistry`)
- Test: `grammar/tests/test_evidence_policy.py`

**Interfaces:**
- Produces:
  - `EvidencePolicy(_Model)` fields: `policy_id: str`, `version: str`, `null_family: Literal["paired_bounded_mean_betting"]`, `theta0: float = 0.0`, `statistic: str = "accuracy_advantage_over_baseline"`, `support: str = "[-1,1]"`, `sampling_regime: str = "exchangeable_iid (disclosed assumption)"`, `baseline_ref: str`, `calibration_population_ref: str`, `evalue_transform: Literal["paired_wsr_betting"]`. Property `ref -> str` returns `self.content_hash` (the project `_Model` content address; **no stored digest field → no self-reference**, audit #10).
  - `EvidencePolicyRegistry(_Model)`: `policies: tuple[EvidencePolicy, ...] = ()`; `resolve(ref: str) -> EvidencePolicy | None` returns the policy whose `content_hash == ref` (digest verified by reconstruction).

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_evidence_policy.py
from polymer_grammar import EvidencePolicy, EvidencePolicyRegistry


def _policy(**kw):
    base = dict(
        policy_id="bench-adv", version="v1", null_family="paired_bounded_mean_betting",
        baseline_ref="bench:demo@1#baseline", calibration_population_ref="bench:demo@1",
        evalue_transform="paired_wsr_betting",
    )
    base.update(kw)
    return EvidencePolicy(**base)


def test_ref_is_content_hash_and_resolves():
    p = _policy()
    reg = EvidencePolicyRegistry(policies=(p,))
    assert reg.resolve(p.ref) is p
    assert p.ref == p.content_hash


def test_ref_changes_with_content():
    assert _policy().ref != _policy(baseline_ref="other").ref


def test_unknown_ref_resolves_none():
    assert EvidencePolicyRegistry().resolve("nope") is None
```

- [ ] **Step 2: Run** `cd grammar && uv run pytest tests/test_evidence_policy.py -q` → FAIL (import error).

- [ ] **Step 3: Implement**

```python
# grammar/src/polymer_grammar/evidence_policy.py
"""Typed, content-addressed EvidencePolicy: the e-value calibration for an evidence-
licensed capability. Pure + numpy-free. Its content address (content_hash) IS its
reference — there is no stored digest field, so the address is never self-referential.
The oracle dossier may still attest apparatus credibility; it is NOT this object.
"""
from __future__ import annotations

from typing import Literal

from ._model import _Model  # adjust to the actual base-model import path in this package


class EvidencePolicy(_Model):
    policy_id: str
    version: str
    null_family: Literal["paired_bounded_mean_betting"]
    theta0: float = 0.0
    statistic: str = "accuracy_advantage_over_baseline"
    support: str = "[-1,1]"
    sampling_regime: str = "exchangeable_iid (disclosed assumption)"
    baseline_ref: str
    calibration_population_ref: str
    evalue_transform: Literal["paired_wsr_betting"]

    @property
    def ref(self) -> str:
        return self.content_hash


class EvidencePolicyRegistry(_Model):
    policies: tuple[EvidencePolicy, ...] = ()

    def resolve(self, ref: str) -> EvidencePolicy | None:
        return next((p for p in self.policies if p.content_hash == ref), None)
```

> **Implementer note:** confirm the base-model import (`grammar` uses a shared frozen base — grep `class CapabilityCell` in `capability.py` for the exact `_Model` import and `content_hash` property name; reuse them verbatim). If `content_hash` is named differently, use that name in `ref`.

- [ ] **Step 4: Run** → PASS, then `cd grammar && uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/evidence_policy.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_evidence_policy.py
git commit -m "feat(grammar): content-addressed EvidencePolicy + registry"
```

### Task 5: `BenchmarkAdapter` protocol + deterministic fixture adapter

**Files:**
- Create: `src/polymer_claims/benchmark_adapter.py`
- Test: `tests/capability/test_benchmark_adapter.py`

**Interfaces:**
- Produces:
  - `BenchmarkExample` — frozen dataclass `example_id: str`, `features: tuple[tuple[str, str], ...]` (NO label field — labels are structurally absent here).
  - `BenchmarkAdapter` — `typing.Protocol` with `identity: str` and `predict(examples: Sequence[BenchmarkExample]) -> PredictionVector`.
  - `FixtureModelAdapter`, `FixtureBaselineAdapter` — deterministic in-repo adapters whose predictions are seeded **independently of labels** (audit #17).

- [ ] **Step 1: Write the failing test**

```python
# tests/capability/test_benchmark_adapter.py
import inspect
from polymer_claims.benchmark_adapter import (
    BenchmarkExample, FixtureModelAdapter, FixtureBaselineAdapter,
)


def test_adapter_predict_signature_has_no_labels():
    # audit #20: the model adapter interface must not receive gold labels
    sig = inspect.signature(FixtureModelAdapter().predict)
    assert "labels" not in sig.parameters
    assert "label" not in str(sig).lower()


def test_fixture_predictions_are_deterministic():
    ex = [BenchmarkExample(example_id=f"e{i}", features=(("x", str(i % 2)),)) for i in range(5)]
    a, b = FixtureModelAdapter(), FixtureModelAdapter()
    assert a.predict(ex).predictions == b.predict(ex).predictions
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement**

```python
# src/polymer_claims/benchmark_adapter.py
"""Typed benchmark adapter interface. The model sees example inputs + ids, NEVER gold
labels (labels live only in the scorer). Fixture adapters are deterministic and seeded
independently of labels (predictions are frozen before labels are revealed)."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .benchmark_evidence import PredictionVector


@dataclass(frozen=True)
class BenchmarkExample:
    example_id: str
    features: tuple[tuple[str, str], ...]  # no label field by construction


@runtime_checkable
class BenchmarkAdapter(Protocol):
    identity: str
    def predict(self, examples: Sequence[BenchmarkExample]) -> PredictionVector: ...


class FixtureModelAdapter:
    identity = "fixture-model"
    def predict(self, examples: Sequence[BenchmarkExample]) -> PredictionVector:
        # deterministic rule over features only (label-independent): predict "A" when the
        # int feature is even, else "B". (Fixture: the demo labels are chosen to make this
        # beat the baseline; see Task 9 fixture construction order.)
        out = []
        for ex in examples:
            x = dict(ex.features).get("x", "0")
            out.append((ex.example_id, "A" if (int(x) % 2 == 0) else "B"))
        return PredictionVector(predictions=tuple(out))


class FixtureBaselineAdapter:
    identity = "fixture-baseline"
    def predict(self, examples: Sequence[BenchmarkExample]) -> PredictionVector:
        # precommitted constant majority-class baseline
        return PredictionVector(predictions=tuple((ex.example_id, "A") for ex in examples))
```

- [ ] **Step 4: Run** → PASS; `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/benchmark_adapter.py tests/capability/test_benchmark_adapter.py
git commit -m "feat(capability): typed BenchmarkAdapter protocol + label-free fixture adapters"
```

---

## Phase 1b — grammar schema deltas + orchestrator + protocol dispatch

### Task 6: Grammar — `LicenseRoute.EVIDENCE_LICENSED` + optional `independence_tier` + `verification_standing`

**Files:**
- Modify: `grammar/src/polymer_grammar/licensing.py:53` (LicenseRoute), `:65` (keep IndependenceTier as-is), `:153` (Licensing field)
- Test: `grammar/tests/test_licensing_evidence_route.py`

**Interfaces:**
- Produces: `LicenseRoute.EVIDENCE_LICENSED = "evidence_licensed"`; `Licensing.independence_tier: IndependenceTier | None = None` (was non-optional default REPRODUCED — see compat note); `Licensing.verification_standing: str | None = None`.

> **Compat decision (audit #11):** changing the `independence_tier` default would change existing licenses' serialization. To keep the three existing routes byte-identical, **do not change the existing default**; instead make the field `IndependenceTier | None` and have the EVIDENCE_LICENSED branch (Task 13) set it to `None` explicitly while all existing routes continue to pass `independence_tier_of(sats)`. Add a validator: `verification_standing` is non-None **iff** `route == EVIDENCE_LICENSED`.

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_licensing_evidence_route.py
import pytest
from polymer_grammar import Licensing, LicenseRoute, RivalSetClosure


def test_evidence_route_allows_none_tier_and_standing():
    lic = Licensing(
        route=LicenseRoute.EVIDENCE_LICENSED,
        satisfactions=(),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
        independence_tier=None,
        verification_standing="single_source_baseline",
    )
    assert lic.independence_tier is None
    assert lic.verification_standing == "single_source_baseline"


def test_standing_requires_evidence_route():
    with pytest.raises(ValueError):
        Licensing(
            route=LicenseRoute.SEVERE_TEST, satisfactions=(),
            rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            verification_standing="single_source_baseline",
        )
```

- [ ] **Step 2: Run** `cd grammar && uv run pytest tests/test_licensing_evidence_route.py -q` → FAIL.

- [ ] **Step 3: Implement** — add the enum member; change the field type to `IndependenceTier | None = IndependenceTier.REPRODUCED` (default unchanged → existing serialization unchanged); add `verification_standing: str | None = None`; add a `model_validator(mode="after")` enforcing the iff with `EVIDENCE_LICENSED`. (Show the exact field block and validator inline when editing.)

- [ ] **Step 4: Run** → PASS; `cd grammar && uv run pytest -q` (full grammar suite stays green); `uv run ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/licensing.py grammar/tests/test_licensing_evidence_route.py
git commit -m "feat(grammar): EVIDENCE_LICENSED route + optional independence_tier + verification_standing"
```

### Task 7: Grammar — `PendingReason.EXECUTION_ERROR`

**Files:**
- Modify: `grammar/src/polymer_grammar/status.py:17-34`
- Test: `grammar/tests/test_status_execution_error.py`

- [ ] **Step 1: Failing test**

```python
# grammar/tests/test_status_execution_error.py
from polymer_grammar import PendingReason
def test_execution_error_member_exists():
    assert PendingReason.EXECUTION_ERROR.value == "execution_error"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — add `EXECUTION_ERROR = "execution_error"` to the enum.
- [ ] **Step 4: Run** → PASS; full grammar suite green.
- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/status.py grammar/tests/test_status_execution_error.py
git commit -m "feat(grammar): PendingReason.EXECUTION_ERROR"
```

### Task 8: Grammar — `EvidenceProvenance` DTO on `Licensing`

**Files:**
- Modify: `grammar/src/polymer_grammar/licensing.py`
- Test: `grammar/tests/test_licensing_evidence_route.py` (extend)

**Interfaces:**
- Produces: `EvidenceProvenance(_Model)` fields: `execution_credential_ids: tuple[str, ...]`, `evidence_policy_ref: str`, `benchmark_ref: str`, `baseline_ref: str`, `oracle_dossier_ref: str | None = None`, `observed_advantage: float`, `criterion_threshold: float`, `theta0: float`, `e_value: float`, `criterion_satisfied: bool`. New optional field `Licensing.evidence_provenance: EvidenceProvenance | None = None` (present-only-when `route == EVIDENCE_LICENSED`).

- [ ] **Step 1: Failing test** — construct a `Licensing` with a populated `EvidenceProvenance`; assert round-trip + that it's rejected on a non-evidence route.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the DTO + optional field + validator extension.
- [ ] **Step 4: Run** → PASS; grammar suite green.
- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/licensing.py grammar/tests/test_licensing_evidence_route.py
git commit -m "feat(grammar): EvidenceProvenance record on Licensing"
```

### Task 9: Grammar — `VerificationPolicy` + `ResolvedVerification`

**Files:**
- Create: `grammar/src/polymer_grammar/verification_policy.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_verification_policy.py`

**Interfaces:**
- Produces:
  - `VerificationPolicy(_Model)`: `execution: Literal["recompute_pair","single"] = "recompute_pair"`, `result_rule: Literal["criterion"] = "criterion"`, `independence_requirement: Literal["implementation","baseline_ground_truth"] = "implementation"`, `evidence_policy_ref: str | None = None`, `min_adapters: int = 2`. Validator: `execution=="single"` requires `evidence_policy_ref is not None` and `min_adapters == 1`.
  - `ResolvedVerification(_Model)`: `claim_id: str`, `route: LicenseRoute`, `verification_standing: str`, `satisfaction: Satisfaction`, `evidence_provenance: EvidenceProvenance`, `e_value: float`, `criterion_satisfied: bool`.

- [ ] **Step 1: Failing test** — build a `single` policy (rejects without `evidence_policy_ref`); build a `ResolvedVerification` and assert fields/round-trip.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** both models + validator; export.
- [ ] **Step 4: Run** → PASS; grammar suite + `test_isolation.py` green (no numpy import).
- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/verification_policy.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_verification_policy.py
git commit -m "feat(grammar): VerificationPolicy + ResolvedVerification models"
```

### Task 10: Grammar — optional `verification_policy` on `CapabilityCell`

**Files:**
- Modify: `grammar/src/polymer_grammar/capability.py:115-155`
- Test: `grammar/tests/test_capability_descriptors.py` (extend)

**Interfaces:**
- Produces: `CapabilityCell.verification_policy: VerificationPolicy | None = None` (default `None` ⇒ behaves as the implicit `recompute_pair` default; existing three cells unchanged).

- [ ] **Step 1: Failing test** — a cell with `verification_policy=VerificationPolicy(execution="single", evidence_policy_ref="x", min_adapters=1)` round-trips; a cell without one keeps `content_hash` identical to the pre-change value (use a stored constant from a golden in Task 15, or assert `verification_policy is None`).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the optional field.
- [ ] **Step 4: Run** → PASS; full grammar suite green.
- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/capability.py grammar/tests/test_capability_descriptors.py
git commit -m "feat(grammar): optional VerificationPolicy on CapabilityCell"
```

### Task 11: Umbrella — orchestrator emits `ResolvedVerification`

**Files:**
- Create: `src/polymer_claims/benchmark_capability.py`
- Test: `tests/capability/test_benchmark_orchestrator.py`

**Interfaces:**
- Consumes: Tasks 1–5, 9; `Satisfaction`, `SatisfactionVerdict`, `MaterializationContext`, `EvidenceProvenance`, `ResolvedVerification`, `LicenseRoute` from grammar.
- Produces: `resolve_benchmark_verification(*, claim_id, cell, policy, benchmark, labels, order, model, baseline, ctx, criterion_threshold) -> ResolvedVerification | RuntimeFailure`. Computes `Wᵢ` (Task 2), `validate_advantage_stream` (Task 3), `paired_advantage_evalue` (Task 1), observed advantage = mean(model_correct) − mean(baseline_correct), `criterion_satisfied = observed_advantage > criterion_threshold` (`τ ≥ 0`), mints a single-source `Satisfaction(verdict=SATISFIED, materialization=ctx, credential_ids=(model.identity,))`, builds `EvidenceProvenance`, returns `ResolvedVerification(route=EVIDENCE_LICENSED, verification_standing="single_source_baseline", ...)`. Adapter/scoring failures → `RuntimeFailure(reason="execution_error")`; degenerate/validity failures → `RuntimeFailure(reason="invalid_input")`.

- [ ] **Step 1: Write the failing test**

```python
# tests/capability/test_benchmark_orchestrator.py
from polymer_claims.benchmark_capability import resolve_benchmark_verification, RuntimeFailure
from polymer_claims.benchmark_adapter import BenchmarkExample, FixtureModelAdapter, FixtureBaselineAdapter
from polymer_grammar import EvidencePolicy, LicenseRoute
# ... build ctx via the project's MaterializationContext test helper ...

def _benchmark():
    # 20 examples; feature x = i%2; labels chosen so model (even->A) beats baseline (always A)
    return [BenchmarkExample(example_id=f"e{i}", features=(("x", str(i % 2)),)) for i in range(20)]

def test_orchestrator_licenses_and_carries_provenance(materialization_ctx):
    ex = _benchmark()
    labels = {f"e{i}": ("A" if i % 2 == 0 else "B") for i in range(20)}  # model is 20/20, baseline 10/20
    order = tuple(e.example_id for e in ex)
    policy = EvidencePolicy(policy_id="p", version="v1", null_family="paired_bounded_mean_betting",
                            baseline_ref="b", calibration_population_ref="c", evalue_transform="paired_wsr_betting")
    rv = resolve_benchmark_verification(
        claim_id="c1", cell=None, policy=policy, benchmark=ex, labels=labels, order=order,
        model=FixtureModelAdapter(), baseline=FixtureBaselineAdapter(), ctx=materialization_ctx,
        criterion_threshold=0.0,
    )
    assert rv.route == LicenseRoute.EVIDENCE_LICENSED
    assert rv.criterion_satisfied is True
    assert rv.e_value > 20.0
    assert rv.evidence_provenance.observed_advantage > 0.0
    assert rv.satisfaction.credential_ids == ("fixture-model",)
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the orchestrator + `RuntimeFailure` dataclass per the interface above (full code written at implementation time; mirror the field names in the test).
- [ ] **Step 4: Run** → PASS; `uv run ruff check src tests`.
- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/benchmark_capability.py tests/capability/test_benchmark_orchestrator.py
git commit -m "feat(capability): benchmark orchestrator emits ResolvedVerification"
```

### Task 12: Protocol — thread `resolved_verifications` through `run_cycle` + gate out of `execute_ground`

**Files:**
- Modify: `protocol/src/polymer_protocol/cycle.py:40-61` (run_cycle signature + pass-through), and the executability gate so evidence-licensed claim ids are NOT sent to `execute_ground` (which would raise `SelfLicensingError` on <2 adapters).
- Test: `protocol/tests/test_evidence_dispatch.py`

**Interfaces:**
- Produces: `run_cycle(..., resolved_verifications: dict[str, ResolvedVerification] | None = None)`; forwards to `verify_stage`; excludes `resolved_verifications` claim ids from the 2-adapter execution set.

- [ ] **Step 1: Write the failing test** — run a cycle on a corpus containing one evidence-licensed claim (no adapters that match it) + `resolved_verifications={"c1": rv}`; assert the cycle does **not** raise and `c1` is not in the executed-with-2-adapters set. (Use a minimal corpus + the Task 11 `rv`.)
- [ ] **Step 2: Run** `cd protocol && uv run pytest tests/test_evidence_dispatch.py -q` → FAIL.
- [ ] **Step 3: Implement** the signature + pass-through + the gate (filter evidence ids before `execute_ground`).
- [ ] **Step 4: Run** → PASS; full protocol suite green (existing cycles unaffected when `resolved_verifications is None`).
- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/cycle.py protocol/tests/test_evidence_dispatch.py
git commit -m "feat(protocol): thread resolved_verifications; gate evidence claims out of execute_ground"
```

### Task 13: Protocol — license-from-`ResolvedVerification` branch in `verify_stage`

**Files:**
- Modify: `protocol/src/polymer_protocol/verify.py:150-159` (signature), `:188-201` (add evidence e-values to `executed_with_e` + `_e_ok`), `:209-210` (per-claim loop: handle resolved claims first)
- Test: `protocol/tests/test_evidence_dispatch.py` (extend)

**Interfaces:**
- Consumes: `resolved_verifications: dict[str, ResolvedVerification] | None`.
- Behavior: for each `c.id` in `resolved_verifications`: (a) include `(c.id, rv.e_value)` in the e-LOND `elond_decisions` intake so FDR is controlled across all e-tests; (b) at the top of the per-claim loop, if a resolved verification exists, license iff `rv.criterion_satisfied and _e_ok(c.id)` (e-LOND discovery), constructing `Licensing(route=EVIDENCE_LICENSED, satisfactions=(rv.satisfaction,), rival_set_closure=OPEN_ACKNOWLEDGED, independence_tier=None, verification_standing=rv.verification_standing, evidence_provenance=rv.evidence_provenance)`; else `PENDING` (criterion unmet or sub-threshold). Resolved claims never reach the 2-adapter block.

- [ ] **Step 1: Write the failing tests**

```python
# extend protocol/tests/test_evidence_dispatch.py
def test_resolved_claim_licenses_without_two_adapters(...):
    # rv with criterion_satisfied=True, large e_value, fresh FDR ledger
    out = run_cycle(corpus, adapters=(), ctx=ctx, resolved_verifications={"c1": rv})
    c = out.corpus.by_id()["c1"]
    assert c.status == Status.LICENSED
    assert c.licensing.route == LicenseRoute.EVIDENCE_LICENSED
    assert c.licensing.independence_tier is None
    assert c.licensing.verification_standing == "single_source_baseline"
    assert c.licensing.evidence_provenance.e_value == rv.e_value

def test_subthreshold_evalue_stays_pending(...):
    # rv with a tiny e_value (< 1/alpha) -> PENDING, never LICENSED, never REPRODUCED
    out = run_cycle(corpus, adapters=(), ctx=ctx, resolved_verifications={"c1": rv_low})
    assert out.corpus.by_id()["c1"].status == Status.PENDING
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the signature + e-LOND intake addition + the per-claim resolved branch (insert before the `rec = rec_by_id.get(c.id)` handling at `verify.py:217`).
- [ ] **Step 4: Run** → PASS; **full protocol suite green** (`cd protocol && uv run pytest -q`) — confirm no existing test regresses (the branch is inert when `resolved_verifications is None`).
- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/verify.py protocol/tests/test_evidence_dispatch.py
git commit -m "feat(protocol): license claims from injected ResolvedVerification (no two-adapter verify)"
```

### Task 14: Umbrella — register the cell + single-mode `validate_trust_binding`

**Files:**
- Modify: `src/polymer_claims/capabilities.py:25-61` (register `EVAL_BENCHMARK_ADVANTAGE_CELL`), `:130-132` (`validate_trust_binding` single-mode branch)
- Test: `tests/capability/test_cells.py` (extend), `tests/capability/test_binding.py` (extend)

**Interfaces:**
- Produces: `EVAL_BENCHMARK_ADVANTAGE_CELL` with `verification_policy=VerificationPolicy(execution="single", independence_requirement="baseline_ground_truth", evidence_policy_ref=<policy ref>, min_adapters=1)`, registered in `CAPABILITY_CELLS`. `validate_trust_binding`: when `cell.verification_policy.execution == "single"`, do **not** require an independent credential pair (skip `BINDING_NO_INDEPENDENT_PAIR`); instead require the single execution credential resolvable + (if `cell.oracle.required`) a resolvable in-domain oracle.

- [ ] **Step 1: Write the failing tests** — (a) `CAPABILITY_CELLS.resolve("eval::benchmark_advantage","v1")` is not None and is `single`; (b) `validate_trust_binding` on the single cell with ONE credential returns `.ok` (no `BINDING_NO_INDEPENDENT_PAIR`); (c) the three existing `recompute_pair` cells still require the pair.
- [ ] **Step 2: Run** `uv run pytest tests/capability/test_cells.py tests/capability/test_binding.py -q` → FAIL.
- [ ] **Step 3: Implement** registration + the single-mode branch.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/capabilities.py tests/capability/test_cells.py tests/capability/test_binding.py
git commit -m "feat(capability): register eval::benchmark_advantage; single-mode trust binding"
```

### Task 15: Compatibility goldens + end-to-end honest license

**Files:**
- Create: `tests/capability/test_benchmark_end_to_end.py`, `tests/capability/test_existing_cells_golden.py`
- Test data: `data/demo/benchmark_advantage_fixture.json` (the frozen-before-labels tiny benchmark)

**Interfaces:** consumes everything above.

- [ ] **Step 1: Write the failing tests**
  - **Golden (audit #11/#32):** assert the canonical serialization (`model_dump(mode="json")`) and `content_hash` of `MEAN_DIFF_CELL`, `REGION_DELTA_BETA_CELL`, `N_DMPS_CELL` equal committed golden constants. (Capture the goldens from `main` BEFORE Task 6–10 if not already; if the optional fields changed the hash, this test documents the one-time bump per the compat decision.)
  - **End-to-end:** load the fixture, run `resolve_benchmark_verification` → `run_cycle(..., resolved_verifications=...)` → assert the claim is `LICENSED`, `route=EVIDENCE_LICENSED`, `verification_standing="single_source_baseline"`, `independence_tier is None`, provenance populated, and the e-value is a hand-checkable multiple of `1/α`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Add the fixture + make the tests pass** (the fixture's predictions/baseline are generated by a label-independent seed; a comment documents the construction order — predictions frozen, then labels assigned — per audit #17).
- [ ] **Step 4: Run** `scripts/check-all.sh` → ALL GREEN (grammar + protocol + umbrella + ruff + isolation; viewer unaffected).
- [ ] **Step 5: Commit**

```bash
git add tests/capability/test_benchmark_end_to_end.py tests/capability/test_existing_cells_golden.py data/demo/benchmark_advantage_fixture.json
git commit -m "test(capability): existing-cell goldens + end-to-end evidence license"
```

### Task 16: Validity-protection checks (audit #16) wired into the orchestrator

**Files:**
- Modify: `src/polymer_claims/benchmark_capability.py`
- Test: `tests/capability/test_benchmark_validity_protection.py`

**Interfaces:**
- Produces: the orchestrator verifies, before emitting a `ResolvedVerification`: `policy.ref` resolves in the supplied `EvidencePolicyRegistry` and `policy.calibration_population_ref == benchmark_ref`; `policy.baseline_ref == baseline_ref`; model credential identity matches the cell's bound execution credential; the `(benchmark_ref, policy.ref, claim_id)` triple has not already produced a result in this run (no reuse under a different claim/benchmark). Any failure → `RuntimeFailure` (no `ResolvedVerification`; claim never licenses).

- [ ] **Step 1: Write the failing tests** — one per mismatch: benchmark-digest mismatch, policy-ref unresolvable, baseline mismatch, credential mismatch, duplicate/missing example ids (already covered by Task 2 — assert it surfaces as `RuntimeFailure` here), result-reuse under a second claim. Each asserts `isinstance(result, RuntimeFailure)` and that a subsequent `run_cycle` leaves the claim unlicensed.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the checks.
- [ ] **Step 4: Run** → PASS; `scripts/check-all.sh` green.
- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/benchmark_capability.py tests/capability/test_benchmark_validity_protection.py
git commit -m "feat(capability): validity-protection checks (digest/credential/reuse) before licensing"
```

---

## Self-review (coverage map spec → tasks)

- §2 capability / inferential claim → Tasks 5, 11, 14, 15.
- §3 statistical core (paired increments, sequential null, paired e-value, degenerate rejection, criterion↔null) → Tasks 1, 2, 3, 11.
- §4 typed objects (VerificationPolicy, EvidencePolicy, provenance, ResolvedVerification) → Tasks 4, 8, 9, 10.
- §5 benchmark-adapter/scorer/label-withholding → Tasks 2, 5.
- §6 lifecycle + EXECUTION_ERROR → Tasks 7, 11, 13.
- §7 schema + runtime seam (route, standing, optional tier, protocol dispatch, four-layer validation, compat) → Tasks 6, 10, 12, 13, 14, 15.
- §8 validity-protection IN slice 1 → Task 16.
- §9 fixture frozen-before-labels → Tasks 5, 15.
- §10 tests (exact enumeration, degenerate, label-withholding, paired, standing serialization, runtime guard, e2e, goldens) → Tasks 1, 3, 5, 6, 12, 13, 15, 16.
- §11 acceptance criteria → all tasks; final gate Task 15/16.

**Deferred to Slice 2/3 (not in this plan):** full attestation chain + certificate/SLSA (Slice 2); defeat/drift/reinstatement/replay-over-time + tamper depth + out-of-domain/downgraded-oracle behavior (Slice 3).

## Optional internal split (per spec §12)

- **1a = Tasks 1–5** (umbrella primitives + pure `EvidencePolicy`; licenses nothing; fully unit-tested) — mergeable on its own.
- **1b = Tasks 6–16** (grammar schema + orchestrator + protocol dispatch + end-to-end) — depends on 1a.

## Execution rhythm

`subagent-driven-development` (fresh subagent per task + two-stage review) → whole-branch review → merge `--no-ff` → update `CONTINUE.md` + memory.
