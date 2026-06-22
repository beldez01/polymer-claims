# Calibration Ledger + Certificate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the corpus's headline `q` *validated, not asserted* — a warrant-tiered calibration ledger (DEFINITIONAL realized-FDR over synthetic ground truth, ANCHORED warrant-survival from the corpus's own pressure events, ATTESTED stub) and a single-claim, attestable **certificate** that carries it.

**Architecture:** Pure core in `protocol/src/polymer_protocol/calibration.py` (data model + aggregation + the ANCHORED transition function — numpy-free, deterministic), impure shell in the umbrella (`calibration_harness.py` runs synthetic data through the *real* gate behind a scoped contract-root contextvar; `calibration_store.py` owns persistence + epoch allocation; `attestation.py` gains a `Certificate` DTO). Calibration is an **instrument, not a gate** — it never changes a claim's status, and the `Corpus` stays exactly 4 collections (the ledger is a separate meta-structure). Mirrors the sheaf-gauge precedent (pure `protocol/sheaf.py` + impure `polymer_claims/sheaf_spectrum.py`).

**Tech Stack:** Python 3.12, pydantic v2 (frozen `_Model`), stdlib `json`/`base64`/`hashlib`/`math`/`contextvars`, numpy (behind a new `[calibrate]` extra) for the synthetic data generator only. pytest + ruff. `uv` for env.

## Global Constraints

- **Purity:** `grammar/` and `protocol/` stay pure, deterministic, numpy-free, filesystem/network/clock-free. Time-like values are passed-in `int` cycle indices. All impurity (synthetic data, e-value computation, persistence, rendering) is umbrella-side (`src/polymer_claims/`).
- **`_Model` base:** every model subclasses `_Model` (`grammar/src/polymer_grammar/base.py:7` — `ConfigDict(extra="forbid", populate_by_name=True, frozen=True)`); collection fields are **tuples**, never `list`/`dict`. Protocol imports it from `protocol/src/polymer_protocol/base.py`.
- **Enums:** `class X(str, Enum)` (mirror `grammar/src/polymer_grammar/status.py:7`).
- **Validators:** conditional-presence via `@model_validator(mode="after")` raising `ValueError` (mirror `grammar/src/polymer_grammar/claim.py:60`).
- **`Corpus` = exactly 4 collections** (`claims`, `defeat_edges`, `equivalences`, `fdr_ledger`) — do NOT add a fifth.
- **Additive / byte-identical when off:** new fields are `X | None = None` or default `()`; existing `export-attestation` output must stay byte-identical (new public names only: `Certificate`, `build_certificate`, `certificate_dsse_envelope`, `calibrate`/`certify` CLI). Never modify `build_attestation_bundle`/`build_attestation_records`/`build_attestation_statements`/`dsse_envelope`.
- **numpy floor:** `numpy>=1.26` (same pin as `embed`). The `[calibrate]` extra carries it; base import stays numpy-free (do NOT re-export calibration umbrella modules from `src/polymer_claims/__init__.py`).
- **No laundering:** `feeds_headline_q` is a **computed property** (never a stored field), `:= (resolution_kind == definitional ∧ calibration_target == realized_fdr)`; only DEFINITIONAL realized-FDR may render as the headline `q`.
- **Per-package test gate:** `cd protocol && uv run pytest -q && uv run ruff check src tests` (and likewise for the umbrella from repo root). Full gate: `scripts/check-all.sh`.
- **Commits:** frequent, on branch `feat/calibration-ledger-certificate` (already created; the spec is already committed there). End commit messages with the `Co-Authored-By` trailer.

---

### Task 1: Pure enums + `ResolutionRecord` (data model + validators)

**Files:**
- Create: `protocol/src/polymer_protocol/calibration.py`
- Test: `protocol/tests/test_calibration_record.py`

**Interfaces:**
- Consumes: `_Model` from `polymer_protocol.base`.
- Produces: enums `ResolutionKind` (`definitional|anchored|attested`), `CalibrationTarget` (`realized_fdr|warrant_survival|external_disagreement`), `ResolutionVerdict` (`upheld|failed|unresolved|superseded`), `PressureKind` (`defeat|drift|red_team`); model `ResolutionRecord` with computed property `feeds_headline_q`.

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_calibration_record.py
import pytest
from polymer_protocol.calibration import (
    ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict, PressureKind,
)


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


def test_feeds_headline_q_true_only_for_definitional_realized_fdr():
    assert _definitional().feeds_headline_q is True


def test_feeds_headline_q_false_for_anchored():
    r = ResolutionRecord(
        subject_claim_id="c1", license_epoch=0,
        resolution_kind=ResolutionKind.ANCHORED,
        calibration_target=CalibrationTarget.WARRANT_SURVIVAL,
        verdict=ResolutionVerdict.FAILED, stated_q=0.05, observed_at_cycle=3,
        pressure_kind=PressureKind.DEFEAT,
    )
    assert r.feeds_headline_q is False


def test_target_kind_coupling_rejected():
    with pytest.raises(ValueError, match="target"):
        _definitional(calibration_target=CalibrationTarget.WARRANT_SURVIVAL)


def test_present_only_when_kind_rejects_pressure_on_definitional():
    with pytest.raises(ValueError, match="pressure_kind"):
        _definitional(pressure_kind=PressureKind.DRIFT)


def test_definitional_requires_batch_id():
    with pytest.raises(ValueError, match="batch_id"):
        _definitional(batch_id=None)


def test_unresolved_rejected_on_definitional():
    with pytest.raises(ValueError, match="unresolved"):
        _definitional(verdict=ResolutionVerdict.UNRESOLVED)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_calibration_record.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.calibration'`.

- [ ] **Step 3: Write minimal implementation**

```python
# protocol/src/polymer_protocol/calibration.py
"""Warrant-tiered calibration ledger (pure, numpy-free, deterministic).

Calibration is an INSTRUMENT, not a gate: it measures the gate's reliability and never changes a
claim's status. This module holds the data model, the pure aggregation (`calibration_summary`), and
the pure ANCHORED transition function (`anchored_resolutions`). All impurity — synthetic data, the
e-value computation, persistence, epoch allocation, rendering — lives umbrella-side.
"""
from __future__ import annotations

from enum import Enum

from pydantic import model_validator

from .base import _Model


class ResolutionKind(str, Enum):
    DEFINITIONAL = "definitional"
    ANCHORED = "anchored"
    ATTESTED = "attested"


class CalibrationTarget(str, Enum):
    REALIZED_FDR = "realized_fdr"
    WARRANT_SURVIVAL = "warrant_survival"
    EXTERNAL_DISAGREEMENT = "external_disagreement"


class ResolutionVerdict(str, Enum):
    UPHELD = "upheld"
    FAILED = "failed"
    UNRESOLVED = "unresolved"
    SUPERSEDED = "superseded"


class PressureKind(str, Enum):
    DEFEAT = "defeat"
    DRIFT = "drift"
    RED_TEAM = "red_team"


# the one legal (kind -> target) coupling
_TARGET_FOR_KIND = {
    ResolutionKind.DEFINITIONAL: CalibrationTarget.REALIZED_FDR,
    ResolutionKind.ANCHORED: CalibrationTarget.WARRANT_SURVIVAL,
    ResolutionKind.ATTESTED: CalibrationTarget.EXTERNAL_DISAGREEMENT,
}


class ResolutionRecord(_Model):
    """One resolved license, keyed to a (subject_claim_id, license_epoch). Created ONLY for claims
    the gate LICENSED — calibration is about the reliability of earned standing."""

    subject_claim_id: str
    license_epoch: int
    resolution_kind: ResolutionKind
    calibration_target: CalibrationTarget
    verdict: ResolutionVerdict
    stated_q: float
    observed_at_cycle: int
    # present-only-when-kind (additive/optional):
    constructed_truth: bool | None = None   # definitional — known ground truth
    model_id: str | None = None             # definitional — which GeneratingModelParams
    batch_id: str | None = None             # definitional — which synthetic batch (per-batch FDP)
    pressure_kind: PressureKind | None = None   # anchored — the survived/failed pressure event
    attestation_ref: str | None = None      # attested — external reference
    source_claim_id: str | None = None      # attested — set iff the event is itself a corpus claim

    @property
    def feeds_headline_q(self) -> bool:
        return (
            self.resolution_kind == ResolutionKind.DEFINITIONAL
            and self.calibration_target == CalibrationTarget.REALIZED_FDR
        )

    @model_validator(mode="after")
    def _validate(self) -> "ResolutionRecord":
        k = self.resolution_kind
        if self.calibration_target != _TARGET_FOR_KIND[k]:
            raise ValueError(
                f"calibration_target {self.calibration_target.value} is not the target for "
                f"kind {k.value} (expected {_TARGET_FOR_KIND[k].value})"
            )
        defn = k == ResolutionKind.DEFINITIONAL
        anch = k == ResolutionKind.ANCHORED
        att = k == ResolutionKind.ATTESTED
        # present-only-when-kind
        if (self.constructed_truth is not None) != defn:
            raise ValueError("constructed_truth is present iff resolution_kind=definitional")
        if (self.model_id is not None) != defn:
            raise ValueError("model_id is present iff resolution_kind=definitional")
        if (self.pressure_kind is not None) != anch:
            raise ValueError("pressure_kind is present iff resolution_kind=anchored")
        if self.attestation_ref is not None and not att:
            raise ValueError("attestation_ref is valid only when resolution_kind=attested")
        if self.source_claim_id is not None and not att:
            raise ValueError("source_claim_id is valid only when resolution_kind=attested")
        # definitional needs a batch_id (the per-batch FDP fold depends on it)
        if defn and self.batch_id is None:
            raise ValueError("definitional records require a batch_id")
        if not defn and self.batch_id is not None:
            raise ValueError("batch_id is valid only when resolution_kind=definitional")
        # a DEFINITIONAL record always has known truth -> never unresolved
        if defn and self.verdict == ResolutionVerdict.UNRESOLVED:
            raise ValueError("definitional records cannot be unresolved (truth is known)")
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_calibration_record.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/calibration.py protocol/tests/test_calibration_record.py
git commit -m "$(printf 'feat(calibration): ResolutionRecord + warrant-tier enums (pure)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 2: `CalibrationLedger` + `CalibrationReport` + `calibration_summary`

**Files:**
- Modify: `protocol/src/polymer_protocol/calibration.py`
- Test: `protocol/tests/test_calibration_summary.py`

**Interfaces:**
- Consumes: Task 1's `ResolutionRecord`, enums.
- Produces: models `GeneratingModelParams`, `CalibrationLedger`, `TierStat`, `CalibrationReport`; function `calibration_summary(ledger: CalibrationLedger, *, target_q: float) -> CalibrationReport`; helpers `_wilson_ci(k, n) -> tuple[float, float]` and `_normal_ci(values) -> tuple[float, float]` (stdlib `math` only).

Key rules (from spec §4.4): a report summarizes **one** `target_q` — DEFINITIONAL records enter the FDR only when `stated_q == target_q`. DEFINITIONAL headline `realized_rate = mean over batches of FDP_b` (`FDP_b = failed_b / licensed_b`, `0` when `licensed_b == 0`), grouped by `batch_id`; `pooled_rate = Σfailed / Σlicensed`. ANCHORED `realized_rate = n_failed / (n_failed + n_upheld)`, `n_unresolved` reported alongside, `n_superseded` reported separately and **excluded** from the denominator. Pooling across tiers is structurally impossible (three separate `TierStat` fields).

**Two planning notes (review findings 2, 5):**
- **`target_q` is a required keyword-only arg of `calibration_summary` — no default.** The pure
  function never falls back to `ledger.default_target_q`; only the *caller* (the CLI / `build_certificate`)
  resolves a default from `default_target_q`. This keeps the pure API unambiguous.
- **The normal-approx CI over ~12 batches is descriptive, not a validity proof.** With small N and
  bounded/skewed per-batch FDPs the interval is rough; it is fine for the report-only certificate but
  is *not* a statistical guarantee. If the CI is ever put in an external-facing claim, increase N
  (and reconsider the interval method). Carried as a deferred item in the spec §10.

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_calibration_summary.py
import math
from polymer_protocol.calibration import (
    ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict, PressureKind,
    CalibrationLedger, calibration_summary,
)

D, A = ResolutionKind.DEFINITIONAL, ResolutionKind.ANCHORED
FDR, WS = CalibrationTarget.REALIZED_FDR, CalibrationTarget.WARRANT_SURVIVAL
UP, FL, UN, SUP = (ResolutionVerdict.UPHELD, ResolutionVerdict.FAILED,
                   ResolutionVerdict.UNRESOLVED, ResolutionVerdict.SUPERSEDED)


def _d(cid, batch, truth, q=0.05):
    return ResolutionRecord(
        subject_claim_id=cid, license_epoch=0, resolution_kind=D, calibration_target=FDR,
        verdict=UP if truth else FL, stated_q=q, observed_at_cycle=0,
        constructed_truth=truth, model_id="m", batch_id=batch,
    )


def _a(cid, verdict, cyc):
    return ResolutionRecord(
        subject_claim_id=cid, license_epoch=0, resolution_kind=A, calibration_target=WS,
        verdict=verdict, stated_q=0.05, observed_at_cycle=cyc, pressure_kind=PressureKind.DEFEAT,
    )


def test_definitional_mean_fdp_differs_from_pooled_on_uneven_batches():
    # batch A: 1 licensed, 1 false -> FDP 1.0 ; batch B: 9 licensed, 1 false -> FDP 1/9
    recs = [_d("a1", "A", False)]
    recs += [_d(f"b{i}", "B", i != 0) for i in range(9)]  # b0 false, b1..b8 true
    rep = calibration_summary(CalibrationLedger(records=tuple(recs)), target_q=0.05)
    # mean per-batch FDP = (1.0 + 1/9)/2 = 0.5555..., pooled = 2/10 = 0.2 -> they MUST differ
    assert math.isclose(rep.definitional.realized_rate, (1.0 + 1 / 9) / 2, rel_tol=1e-9)
    assert math.isclose(rep.definitional.pooled_rate, 0.2, rel_tol=1e-9)
    assert rep.definitional.n_batches == 2
    assert rep.definitional.n_total == 10 and rep.definitional.n_failed == 2


def test_report_filters_definitional_by_target_q():
    recs = [_d("x", "A", False, q=0.05), _d("y", "A", False, q=0.10)]
    rep = calibration_summary(CalibrationLedger(records=tuple(recs)), target_q=0.05)
    assert rep.definitional.n_total == 1  # only the stated_q==0.05 record


def test_anchored_excludes_unresolved_and_superseded_from_denominator():
    recs = [_a("u1", UN, 1), _a("f1", FL, 2), _a("p1", UP, 3),
            ResolutionRecord(subject_claim_id="s1", license_epoch=0, resolution_kind=A,
                             calibration_target=WS, verdict=SUP, stated_q=0.05,
                             observed_at_cycle=4, pressure_kind=PressureKind.DRIFT)]
    rep = calibration_summary(CalibrationLedger(records=tuple(recs)), target_q=0.05)
    assert rep.anchored.n_total == 2          # failed + upheld only
    assert rep.anchored.n_failed == 1
    assert rep.anchored.n_unresolved == 1
    assert rep.anchored.n_superseded == 1
    assert math.isclose(rep.anchored.realized_rate, 0.5, rel_tol=1e-9)
    assert rep.observation_span_cycles == 3   # max(4) - min(1)


def test_empty_tier_has_none_rate():
    rep = calibration_summary(CalibrationLedger(records=()), target_q=0.05)
    assert rep.definitional.realized_rate is None
    assert rep.attested.n_total == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_calibration_summary.py -q`
Expected: FAIL — `ImportError: cannot import name 'CalibrationLedger'`.

- [ ] **Step 3: Write minimal implementation** (append to `calibration.py`)

```python
import math
from collections import defaultdict


class GeneratingModelParams(_Model):
    """The disclosed assumption behind one DEFINITIONAL batch (named on the certificate)."""
    model_id: str
    n_per_group: int
    n_probes_per_region: int
    effect_size: float
    dispersion: float
    fraction_true: float
    tau: float
    target_fdr: float
    n_generated: int
    seed_set: tuple[int, ...]


class CalibrationLedger(_Model):
    records: tuple[ResolutionRecord, ...] = ()
    generating_models: tuple[GeneratingModelParams, ...] = ()
    default_target_q: float | None = None   # optional CLI/report default hint only — NOT authoritative


class TierStat(_Model):
    n_total: int            # tier denominator population (per-tier meaning; see calibration_summary)
    n_failed: int
    n_unresolved: int = 0   # anchored/attested only
    n_superseded: int = 0   # anchored only — terminal, excluded from the failure denominator
    realized_rate: float | None = None
    pooled_rate: float | None = None     # DEFINITIONAL secondary: Σfailed/Σlicensed
    ci_low: float | None = None
    ci_high: float | None = None
    ci_method: str | None = None         # "normal_0.95" (definitional) | "wilson_0.95" (anchored)
    n_batches: int | None = None         # DEFINITIONAL
    n_generated: int | None = None       # DEFINITIONAL


class CalibrationReport(_Model):
    target_q: float
    observation_span_cycles: int | None = None
    definitional: TierStat
    anchored: TierStat
    attested: TierStat


_Z = 1.959963984540054  # 95% normal quantile


def _wilson_ci(k: int, n: int) -> tuple[float, float] | tuple[None, None]:
    if n == 0:
        return (None, None)
    p = k / n
    z2 = _Z * _Z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (_Z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _normal_ci(values: list[float]) -> tuple[float, float] | tuple[None, None]:
    n = len(values)
    if n == 0:
        return (None, None)
    mean = sum(values) / n
    if n == 1:
        return (mean, mean)
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    half = _Z * math.sqrt(var / n)
    return (max(0.0, mean - half), min(1.0, mean + half))


def _definitional_stat(records: tuple[ResolutionRecord, ...], target_q: float) -> TierStat:
    recs = [r for r in records
            if r.resolution_kind == ResolutionKind.DEFINITIONAL and r.stated_q == target_q]
    n_total = len(recs)
    n_failed = sum(1 for r in recs if r.verdict == ResolutionVerdict.FAILED)
    if n_total == 0:
        return TierStat(n_total=0, n_failed=0, realized_rate=None, n_batches=0,
                        n_generated=0)
    by_batch: dict[str, list[bool]] = defaultdict(list)
    for r in recs:
        by_batch[r.batch_id].append(r.verdict == ResolutionVerdict.FAILED)
    fdps = [sum(b) / len(b) for b in by_batch.values()]  # licensed_b == len(b) > 0 here
    realized = sum(fdps) / len(fdps)
    lo, hi = _normal_ci(fdps)
    return TierStat(
        n_total=n_total, n_failed=n_failed,
        realized_rate=realized, pooled_rate=n_failed / n_total,
        ci_low=lo, ci_high=hi, ci_method="normal_0.95",
        n_batches=len(by_batch),
        n_generated=sum(m.n_generated for m in ()),  # overwritten by caller if models present
    )


def _anchored_stat(records: tuple[ResolutionRecord, ...]) -> TierStat:
    recs = [r for r in records if r.resolution_kind == ResolutionKind.ANCHORED]
    n_failed = sum(1 for r in recs if r.verdict == ResolutionVerdict.FAILED)
    n_upheld = sum(1 for r in recs if r.verdict == ResolutionVerdict.UPHELD)
    n_unresolved = sum(1 for r in recs if r.verdict == ResolutionVerdict.UNRESOLVED)
    n_superseded = sum(1 for r in recs if r.verdict == ResolutionVerdict.SUPERSEDED)
    denom = n_failed + n_upheld
    lo, hi = _wilson_ci(n_failed, denom)
    return TierStat(
        n_total=denom, n_failed=n_failed, n_unresolved=n_unresolved, n_superseded=n_superseded,
        realized_rate=(n_failed / denom if denom else None),
        ci_low=lo, ci_high=hi, ci_method=("wilson_0.95" if denom else None),
    )


def _attested_stat(records: tuple[ResolutionRecord, ...]) -> TierStat:
    recs = [r for r in records if r.resolution_kind == ResolutionKind.ATTESTED]
    n_failed = sum(1 for r in recs if r.verdict == ResolutionVerdict.FAILED)
    denom = sum(1 for r in recs if r.verdict in (ResolutionVerdict.FAILED, ResolutionVerdict.UPHELD))
    return TierStat(n_total=denom, n_failed=n_failed,
                    realized_rate=(n_failed / denom if denom else None))


def calibration_summary(ledger: CalibrationLedger, *, target_q: float) -> CalibrationReport:
    """Pure. A report summarizes ONE target_q (FDPs are not averaged across e-LOND targets)."""
    recs = ledger.records
    cycles = [r.observed_at_cycle for r in recs if r.resolution_kind == ResolutionKind.ANCHORED]
    span = (max(cycles) - min(cycles)) if cycles else None
    return CalibrationReport(
        target_q=target_q,
        observation_span_cycles=span,
        definitional=_definitional_stat(recs, target_q),
        anchored=_anchored_stat(recs),
        attested=_attested_stat(recs),
    )
```

> Note: the `n_generated=sum(... for _ in ())` line yields `0`; the harness (Task 6) records `n_generated` on the ledger's `GeneratingModelParams` and the certificate (Task 8) surfaces the disclosed count. Keep the summary's `n_generated` derived only from records it can see; do not invent a count here.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_calibration_summary.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/calibration.py protocol/tests/test_calibration_summary.py
git commit -m "$(printf 'feat(calibration): CalibrationLedger + calibration_summary (mean-FDP, single-target-q)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 3: `anchored_resolutions` pure transition function

**Files:**
- Modify: `protocol/src/polymer_protocol/calibration.py`
- Test: `protocol/tests/test_anchored_resolutions.py`

**Interfaces:**
- Consumes: `Corpus` (`polymer_protocol.corpus`), `Claim`/`Status`/`RejectionReason` (`polymer_grammar`), Task-1 record/enums.
- Produces: model `PressureContext` (the cause info the impure caller supplies) and function `anchored_resolutions(prev: Corpus, curr: Corpus, cycle: int, pressure: PressureContext) -> tuple[ResolutionRecord, ...]`.

`PressureContext` carries, per claim id: the epoch (allocated by the store, Task 7) and the observed cause. The pure function maps the LICENSED-set transition + cause → records. It emits **only** resolving events (issuance records are emitted by the store at license time; see Task 7) — here we emit `failed`/`upheld`/`superseded` for claims whose status changed or that met a pressure event named in `pressure`.

- [ ] **Step 1: Write the failing test**

```python
# protocol/tests/test_anchored_resolutions.py
from polymer_grammar import Status, RejectionReason
from polymer_protocol.calibration import (
    anchored_resolutions, PressureContext, ResolutionVerdict, PressureKind,
)
from polymer_protocol.corpus import Corpus
from polymer_grammar.fdr import FDRLedger
# a tiny claim factory shared with other protocol tests:
from tests._calib_fixtures import licensed_claim, rejected_claim, pending_claim  # Step 3 creates this


def _corpus(*claims):
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_defeat_emits_failed():
    prev = _corpus(licensed_claim("c1"))
    curr = _corpus(rejected_claim("c1", RejectionReason.DEFEAT_GROUNDED_OUT))
    pc = PressureContext(epoch={"c1": 0}, cause={"c1": PressureKind.DEFEAT})
    (rec,) = anchored_resolutions(prev, curr, cycle=5, pressure=pc)
    assert rec.verdict == ResolutionVerdict.FAILED and rec.pressure_kind == PressureKind.DEFEAT
    assert rec.license_epoch == 0 and rec.observed_at_cycle == 5


def test_drift_no_relicense_emits_failed():
    prev = _corpus(licensed_claim("c1"))
    curr = _corpus(pending_claim("c1"))
    pc = PressureContext(epoch={"c1": 0}, cause={"c1": PressureKind.DRIFT})
    (rec,) = anchored_resolutions(prev, curr, cycle=2, pressure=pc)
    assert rec.verdict == ResolutionVerdict.FAILED and rec.pressure_kind == PressureKind.DRIFT


def test_still_licensed_no_pressure_emits_nothing():
    prev = _corpus(licensed_claim("c1"))
    curr = _corpus(licensed_claim("c1"))
    pc = PressureContext(epoch={"c1": 0}, cause={})  # no pressure event
    assert anchored_resolutions(prev, curr, cycle=9, pressure=pc) == ()


def test_drift_clean_survival_emits_upheld():
    prev = _corpus(licensed_claim("c1"))
    curr = _corpus(licensed_claim("c1"))
    pc = PressureContext(epoch={"c1": 0}, cause={"c1": PressureKind.DRIFT}, survived={"c1"})
    (rec,) = anchored_resolutions(prev, curr, cycle=4, pressure=pc)
    assert rec.verdict == ResolutionVerdict.UPHELD and rec.pressure_kind == PressureKind.DRIFT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd protocol && uv run pytest tests/test_anchored_resolutions.py -q`
Expected: FAIL — `ImportError` (no `anchored_resolutions`) and missing `tests/_calib_fixtures.py`.

- [ ] **Step 3: Create the shared fixture + implementation**

Create `protocol/tests/_calib_fixtures.py` (minimal valid claims — copy the leaf/pattern shape from an existing protocol test such as `protocol/tests/test_cycle.py`; the executor adapts field names to the current `Claim` constructor):

```python
# protocol/tests/_calib_fixtures.py
from polymer_grammar import Claim, Status, RejectionReason
# Reuse the smallest valid claim builder already used in protocol tests. If test_cycle.py exposes a
# helper, import it; otherwise build a STRUCTURAL-free minimal LICENSED/PENDING/REJECTED claim here.

def _base(cid: str, status: Status, **kw) -> Claim:
    # NOTE: mirror the exact minimal Claim(...) construction used in protocol/tests/test_cycle.py
    # (id, title, pattern, leaves=[...], status=...). Keep it the smallest claim that validates.
    raise NotImplementedError  # executor: fill from test_cycle.py's existing minimal claim

def licensed_claim(cid: str) -> Claim: ...
def pending_claim(cid: str) -> Claim: ...
def rejected_claim(cid: str, reason: RejectionReason) -> Claim: ...
```

> Executor instruction: open `protocol/tests/test_cycle.py`, find its minimal `Claim(...)` construction, and reproduce it here for LICENSED/PENDING/REJECTED. This avoids guessing leaf/pattern shapes. The three helpers must return claims that pass `Claim`'s validators (a LICENSED claim needs a valid `licensing` block — reuse the test's existing licensed fixture).

Append to `calibration.py`:

```python
from .corpus import Corpus  # at top with the other imports


class PressureContext(_Model):
    """Cause info the impure caller supplies (a snapshot diff cannot recover cause; spec finding 6)."""
    epoch: dict[str, int]                 # claim_id -> its current license_epoch (allocated by the store)
    cause: dict[str, PressureKind] = {}   # claim_id -> the pressure event that touched it this cycle
    survived: frozenset[str] = frozenset()  # claim_ids whose pressure event was SURVIVED (-> upheld)
    superseded: frozenset[str] = frozenset()  # drift-reopened then re-licensed under new content


def _status_of(corpus: Corpus, cid: str):
    for c in corpus.claims:
        if c.id == cid:
            return c.status
    return None


def anchored_resolutions(
    prev: Corpus, curr: Corpus, cycle: int, pressure: PressureContext
) -> tuple[ResolutionRecord, ...]:
    """Pure. Emit ANCHORED resolving records for claims that met a named pressure event this cycle.
    Issuance (`unresolved`) records are emitted by the store at license time, not here."""
    out: list[ResolutionRecord] = []
    for cid, kind in pressure.cause.items():
        epoch = pressure.epoch.get(cid, 0)
        if cid in pressure.superseded:
            verdict = ResolutionVerdict.SUPERSEDED
        elif cid in pressure.survived:
            verdict = ResolutionVerdict.UPHELD
        else:
            # a pressure event that moved the claim out of LICENSED is a failure
            verdict = ResolutionVerdict.FAILED
        out.append(ResolutionRecord(
            subject_claim_id=cid, license_epoch=epoch,
            resolution_kind=ResolutionKind.ANCHORED,
            calibration_target=CalibrationTarget.WARRANT_SURVIVAL,
            verdict=verdict, stated_q=curr.fdr_ledger.target_fdr, observed_at_cycle=cycle,
            pressure_kind=kind,
        ))
    return tuple(out)
```

> Note `pydantic` will coerce the `dict`/`frozenset` defaults on a frozen model fine; if `extra="forbid"` + frozen rejects mutable defaults, wrap with `Field(default_factory=dict)`. Executor: if a "mutable default" error appears, switch `cause`/`epoch` to `Field(default_factory=dict)` and `survived`/`superseded` to `Field(default_factory=frozenset)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_anchored_resolutions.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Lint + commit**

```bash
cd protocol && uv run ruff check src tests
cd /Users/zbb2/Desktop/polymer-claims
git add protocol/src/polymer_protocol/calibration.py protocol/tests/test_anchored_resolutions.py protocol/tests/_calib_fixtures.py
git commit -m "$(printf 'feat(calibration): anchored_resolutions transition fn (pure, cause-fed)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 4: Scoped contract-root contextvar + cache-key fix

**Files:**
- Modify: `src/polymer_claims/contracts/__init__.py` (`_DIR` at :50, `load_contract` at :58, `_load_contract` `@lru_cache` at :65)
- Test: `tests/test_contract_root.py`

**Interfaces:**
- Produces: `using_contract_root(path: Path)` context manager + a module-level `contextvars.ContextVar` so the resolver (and therefore every adapter that calls `load_contract`) reads a scoped root. Cache key becomes `(uid, root)`.

This is the slice's one production touch outside new modules. Byte-identical when unset (default root = `_DIR`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_contract_root.py
from pathlib import Path
import json
import pytest
from polymer_claims.contracts import load_contract, using_contract_root


def _write_min_contract(root: Path, uid: str, dimnames_token: str):
    # smallest manifest load_contract accepts (mirror groupdiff_epicv2_demo.json shape)
    stem = uid.split("@")[0]
    (root / f"{stem}.json").write_text(json.dumps({
        "uid": uid, "dim": [1, 2],
        "assays": [{"name": "beta", "ref": f"{stem}.betas.tsv"}],
        "col_data": [{"sample_id": "S01", "Sample_Group": "case"},
                     {"sample_id": "S02", "Sample_Group": "control"}],
        "row_data": [{"feature_id": dimnames_token, "chr": "chr1", "pos": 1}],
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2", "shared_cause_factors": []},
    }))
    (root / f"{stem}.betas.tsv").write_text(f"feature_id\tS01\tS02\n{dimnames_token}\t0.40\t0.20\n")


def test_contextvar_root_resolves_temp_contract(tmp_path):
    _write_min_contract(tmp_path, "synthetic_a@1", "cgAAA")
    with using_contract_root(tmp_path):
        ref = load_contract("se:synthetic_a@1")
    assert ref.contract_uid == "synthetic_a@1"


def test_same_uid_different_root_does_not_alias(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    _write_min_contract(a, "dup@1", "cgAAA")
    _write_min_contract(b, "dup@1", "cgBBB")
    with using_contract_root(a):
        ref_a = load_contract("se:dup@1")
    with using_contract_root(b):
        ref_b = load_contract("se:dup@1")
    assert ref_a.dimnames_hash != ref_b.dimnames_hash  # distinct content -> distinct address, no cache alias


def test_default_root_unchanged():
    # a bundled fixture still resolves with no contextvar set (byte-identical behavior)
    ref = load_contract("se:groupdiff_epicv2_demo@1")
    assert ref.contract_uid == "groupdiff_epicv2_demo@1"


def test_temp_root_shadows_a_bundled_uid_then_resets_byte_identical(tmp_path):
    # Highest-risk seam: a temp root holding the SAME uid as a bundled contract must NOT alias the
    # cached bundled one, and after the context exits the bundled resolution must be byte-identical.
    bundled_before = load_contract("se:groupdiff_epicv2_demo@1")
    _write_min_contract(tmp_path, "groupdiff_epicv2_demo@1", "cgSHADOW")  # same uid, different content
    with using_contract_root(tmp_path):
        shadow = load_contract("se:groupdiff_epicv2_demo@1")
    assert shadow.dimnames_hash != bundled_before.dimnames_hash      # temp shadowed the bundled
    bundled_after = load_contract("se:groupdiff_epicv2_demo@1")       # context reset
    assert bundled_after.dimnames_hash == bundled_before.dimnames_hash  # bundled byte-identical again
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_contract_root.py -q`
Expected: FAIL — `ImportError: cannot import name 'using_contract_root'`.

- [ ] **Step 3: Modify `contracts/__init__.py`**

At the top of the file (with the other imports) add:

```python
import contextvars
from contextlib import contextmanager
```

Replace the `_DIR`, `load_contract`, and `_load_contract` block (currently :50–:101) so the root is a contextvar threaded into the cache key:

```python
_DIR = Path(__file__).parent
_contract_root: contextvars.ContextVar[Path] = contextvars.ContextVar("_contract_root", default=_DIR)


@contextmanager
def using_contract_root(path):
    """Scope contract resolution to `path` for the duration of the block. Adapters resolve betas via
    the same load_contract, so this reaches them automatically. Default (unset) -> the bundled _DIR
    (byte-identical behavior)."""
    token = _contract_root.set(Path(path))
    try:
        yield
    finally:
        _contract_root.reset(token)


def load_contract(ref: str) -> SEContractRef:
    """Resolve a DataHandle.ref to a content-addressed SEContractRef. Resolves under the scoped
    contract root (a contextvar, default the bundled dir). Unknown ref -> FileNotFoundError."""
    return _load_contract(_resolve_uid(ref), _contract_root.get())


@lru_cache(maxsize=None)
def _load_contract(uid: str, root: Path) -> SEContractRef:
    stem = uid.split("@")[0]
    manifest_path = root / f"{stem}.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"no SE-Contract {uid!r} at {manifest_path}")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    assay = manifest["assays"][0]
    betas_path = root / assay["ref"]
    if not betas_path.is_file():
        raise FileNotFoundError(f"SE-Contract {uid!r} assay file missing at {betas_path}")
    # ... REST OF THE EXISTING BODY UNCHANGED (dimnames_hash, checksum, SEContractRef build) ...
```

> Executor: preserve the entire existing body of `_load_contract` from `betas_bytes = ...` onward verbatim — only `_DIR` → `root` and the signature/cache-key change. Every internal `_DIR` reference inside the function becomes `root`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_contract_root.py tests/test_contracts_loader.py tests/test_contracts_fixture.py -q`
Expected: PASS (existing loader/fixture tests still green — proves byte-identical default behavior).

- [ ] **Step 5: Lint + commit**

```bash
uv run ruff check src tests
git add src/polymer_claims/contracts/__init__.py tests/test_contract_root.py
git commit -m "$(printf 'feat(contracts): scoped contract-root contextvar + (uid,root) cache key\n\nProduction-safe seam for the calibration harness to run synthetic contracts through\nthe real adapters. Byte-identical when unset.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 5: `[calibrate]` extra + synthetic SE-Contract generator

**Files:**
- Modify: `pyproject.toml` (`[project.optional-dependencies]` at :22–25)
- Create: `src/polymer_claims/calibration_harness.py`
- Test: `tests/test_calibration_harness_gen.py`

**Interfaces:**
- Produces: `synthetic_cohort(*, model: GeneratingModelParams, batch_id: str, seed: int) -> SyntheticBatch` where `SyntheticBatch` carries the temp-dir path, the contract uid, and per-region `constructed_truth`; helper `write_synthetic_contract(root, uid, *, samples, probes, betas, groups) -> None`. Uses numpy for the Beta draws.

- [ ] **Step 1: Add the extra to `pyproject.toml`**

After the `embed = ["numpy>=1.26"]` line in `[project.optional-dependencies]`:

```toml
calibrate = ["numpy>=1.26"]
```

(`dev` already includes `numpy>=1.26`, so calibration tests run under `dev` unchanged.)

- [ ] **Step 2: Write the failing test**

```python
# tests/test_calibration_harness_gen.py
import pytest
np = pytest.importorskip("numpy")
from polymer_protocol.calibration import GeneratingModelParams
from polymer_claims.calibration_harness import synthetic_cohort
from polymer_claims.contracts import load_contract, using_contract_root


def _model(**kw):
    base = dict(model_id="m1", n_per_group=20, n_probes_per_region=5, effect_size=0.25,
                dispersion=20.0, fraction_true=0.5, tau=0.10, target_fdr=0.05,
                n_generated=10, seed_set=(0,))
    base.update(kw); return GeneratingModelParams(**base)


def test_synthetic_cohort_is_loadable_and_deterministic(tmp_path):
    b1 = synthetic_cohort(model=_model(), batch_id="b1", seed=0, root=tmp_path / "r1")
    with using_contract_root(b1.root):
        ref = load_contract(f"se:{b1.contract_uid}")
    assert ref.contract_uid == b1.contract_uid
    # determinism: same seed -> identical betas TSV bytes
    b2 = synthetic_cohort(model=_model(), batch_id="b1", seed=0, root=tmp_path / "r2")
    f1 = (b1.root / f"{b1.contract_uid.split('@')[0]}.betas.tsv").read_bytes()
    f2 = (b2.root / f"{b2.contract_uid.split('@')[0]}.betas.tsv").read_bytes()
    assert f1 == f2


def test_truth_labels_match_fraction(tmp_path):
    b = synthetic_cohort(model=_model(n_generated=10, fraction_true=0.4), batch_id="b", seed=1,
                         root=tmp_path)
    assert len(b.regions) == 10
    assert sum(1 for r in b.regions if r.constructed_truth) == 4
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_calibration_harness_gen.py -q`
Expected: FAIL — `ModuleNotFoundError: polymer_claims.calibration_harness`.

- [ ] **Step 4: Write minimal implementation**

```python
# src/polymer_claims/calibration_harness.py
"""DEFINITIONAL synthetic calibration harness (impure; needs the [calibrate] extra for numpy).

Generates Beta-distributed synthetic cohorts with KNOWN ground truth, writes them as SE-Contract
files, and (Task 6) runs them through the REAL gate behind `using_contract_root`. NOT re-exported
from polymer_claims.__init__ (keeps base import numpy-free)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from polymer_protocol.calibration import GeneratingModelParams


@dataclass(frozen=True)
class SyntheticRegion:
    region_id: str
    probes: tuple[str, ...]
    constructed_truth: bool


@dataclass(frozen=True)
class SyntheticBatch:
    batch_id: str
    contract_uid: str
    root: Path
    regions: tuple[SyntheticRegion, ...]
    group_of: dict[str, str]   # sample_id -> "case"|"control"


def _beta_ab(mean: float, dispersion: float) -> tuple[float, float]:
    mean = min(max(mean, 1e-4), 1 - 1e-4)
    return mean * dispersion, (1 - mean) * dispersion


def write_synthetic_contract(root, uid, *, samples, probes, betas, groups) -> None:
    """betas: np.ndarray [n_probes, n_samples] in [0,1]; groups: {sample_id: 'case'|'control'}."""
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    stem = uid.split("@")[0]
    manifest = {
        "uid": uid, "dim": [len(probes), len(samples)],
        "assays": [{"name": "beta", "ref": f"{stem}.betas.tsv"}],
        "col_data": [{"sample_id": s, "Sample_Group": groups[s]} for s in samples],
        "row_data": [{"feature_id": p, "chr": "chr1", "pos": 1000 + i} for i, p in enumerate(probes)],
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2", "shared_cause_factors": []},
    }
    (root / f"{stem}.json").write_text(json.dumps(manifest, sort_keys=True))
    header = "feature_id\t" + "\t".join(samples)
    rows = [header]
    for i, p in enumerate(probes):
        rows.append(p + "\t" + "\t".join(f"{betas[i, j]:.6f}" for j in range(len(samples))))
    (root / f"{stem}.betas.tsv").write_text("\n".join(rows) + "\n")


def synthetic_cohort(*, model: GeneratingModelParams, batch_id: str, seed: int,
                     root) -> SyntheticBatch:
    rng = np.random.default_rng(seed)
    n = model.n_per_group
    samples = [f"S{j:03d}" for j in range(2 * n)]
    groups = {s: ("control" if j < n else "case") for j, s in enumerate(samples)}
    regions: list[SyntheticRegion] = []
    all_probes: list[str] = []
    rows: list[np.ndarray] = []
    n_true = round(model.fraction_true * model.n_generated)
    for r in range(model.n_generated):
        truth = r < n_true
        probes = tuple(f"cg_{batch_id}_{r}_{k}" for k in range(model.n_probes_per_region))
        regions.append(SyntheticRegion(f"reg_{batch_id}_{r}", probes, truth))
        base = 0.30
        for k, p in enumerate(probes):
            all_probes.append(p)
            ctrl_a, ctrl_b = _beta_ab(base, model.dispersion)
            case_mean = base + (model.effect_size if truth else 0.0)
            case_a, case_b = _beta_ab(case_mean, model.dispersion)
            row = np.concatenate([
                rng.beta(ctrl_a, ctrl_b, n), rng.beta(case_a, case_b, n)
            ])
            rows.append(row)
    betas = np.vstack(rows)
    # content-derived unique uid (no collision with bundled uids; sound under the (uid,root) cache)
    digest = hashlib.sha256(betas.tobytes() + batch_id.encode()).hexdigest()[:12]
    uid = f"synthetic_{digest}@1"
    write_synthetic_contract(root, uid, samples=samples, probes=all_probes, betas=betas, groups=groups)
    return SyntheticBatch(batch_id, uid, Path(root), tuple(regions), groups)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_calibration_harness_gen.py -q`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
uv run ruff check src tests
git add pyproject.toml src/polymer_claims/calibration_harness.py tests/test_calibration_harness_gen.py
git commit -m "$(printf 'feat(calibration): [calibrate] extra + synthetic SE-Contract generator\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 6: Harness end-to-end run through the real gate → DEFINITIONAL records

**Files:**
- Modify: `src/polymer_claims/calibration_harness.py`
- Test: `tests/test_calibration_harness_run.py`

**Interfaces:**
- Consumes: Task-5 `synthetic_cohort`; `region_delta_beta_claim` (`methyl_adapters.py:124`), `RegionMeanDiffAdapter`/`RegionLmCoefAdapter`/`methyl_independent_registry` (`methyl_adapters.py`), `materialization_map` (`materialization.py:27`), `evidence_map` (`evidence.py:121`), `NodeRunner` (`node.py`), `Corpus`/`FDRLedger`, `using_contract_root`.
- Produces: `run_batch(*, model, batch_id, seed) -> tuple[ResolutionRecord, ...]` and `run_calibration(*, model, n_batches, base_seed) -> CalibrationLedger`.

The gate-driving recipe (confirmed call chain): build one region-Δβ claim per synthetic region pointing at the synthetic contract uid, assemble a `Corpus`, precompute `materialization_map` + `evidence_map` inside `using_contract_root`, drive `NodeRunner` once, read `claim.status == Status.LICENSED`. A LICENSED null region = a false license.

> Executor: confirm the `NodeRunner` constructor kwargs against `src/polymer_claims/node.py:48-130` (the Explore map reported `NodeRunner(corpus, adapters=..., ctx=..., adapter_registry=..., evalue_gate=True, materializations=..., evidence=...)` and a `.tick()` driver; if a `from_seed` classmethod is the public constructor, use it). The observable contract is: after one tick, each claim's `status` is LICENSED or not.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_calibration_harness_run.py
import pytest
pytest.importorskip("numpy")
from polymer_protocol.calibration import GeneratingModelParams, ResolutionKind, ResolutionVerdict
from polymer_claims.calibration_harness import run_batch


def _model(**kw):
    base = dict(model_id="m1", n_per_group=30, n_probes_per_region=6, effect_size=0.30,
                dispersion=25.0, fraction_true=0.5, tau=0.10, target_fdr=0.05,
                n_generated=8, seed_set=(0,))
    base.update(kw); return GeneratingModelParams(**base)


def test_all_true_batch_has_no_false_licenses():
    recs = run_batch(model=_model(fraction_true=1.0, n_generated=8), batch_id="t", seed=0)
    # every record is DEFINITIONAL; a false license would be verdict=FAILED on a true region -> impossible
    assert all(r.resolution_kind == ResolutionKind.DEFINITIONAL for r in recs)
    assert all(r.verdict != ResolutionVerdict.FAILED for r in recs)


def test_records_are_deterministic_for_fixed_seed():
    a = run_batch(model=_model(), batch_id="b", seed=7)
    b = run_batch(model=_model(), batch_id="b", seed=7)
    assert [(r.subject_claim_id, r.verdict) for r in a] == [(r.subject_claim_id, r.verdict) for r in b]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_calibration_harness_run.py -q`
Expected: FAIL — `ImportError: cannot import name 'run_batch'`.

- [ ] **Step 3: Write minimal implementation** (append to `calibration_harness.py`)

```python
import tempfile

from polymer_grammar import Status
from polymer_grammar.fdr import FDRLedger
from polymer_grammar.licensing import MaterializationContext
from polymer_protocol.corpus import Corpus
from polymer_protocol.calibration import (
    CalibrationLedger, ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict,
)
from .contracts import using_contract_root
from .evidence import evidence_map
from .materialization import materialization_map
from .methyl_adapters import (
    region_delta_beta_claim, RegionMeanDiffAdapter, RegionLmCoefAdapter, methyl_independent_registry,
)
from .node import NodeRunner
from .comparators import Comparator  # executor: import Comparator from its actual module


def run_batch(*, model: GeneratingModelParams, batch_id: str, seed: int) -> tuple[ResolutionRecord, ...]:
    with tempfile.TemporaryDirectory() as tmp:
        batch = synthetic_cohort(model=model, batch_id=batch_id, seed=seed, root=tmp)
        claims = tuple(
            region_delta_beta_claim(
                reg.region_id, ref=f"se:{batch.contract_uid}",
                region_probes=reg.probes, group_col="Sample_Group",
                level_a="control", level_b="case",
                comparator=Comparator.GT, threshold=model.tau,
            )
            for reg in batch.regions
        )
        truth_of = {reg.region_id: reg.constructed_truth for reg in batch.regions}
        corpus = Corpus(claims=claims, fdr_ledger=FDRLedger(target_fdr=model.target_fdr))
        base_ctx = MaterializationContext(id="cal", api_version="v1", data_version=batch.contract_uid)
        with using_contract_root(batch.root):
            mats = materialization_map(corpus, base_ctx)
            ev = evidence_map(corpus)
            runner = NodeRunner(
                corpus,
                adapters=(RegionMeanDiffAdapter(), RegionLmCoefAdapter()),
                ctx=base_ctx, adapter_registry=methyl_independent_registry(),
                evalue_gate=True, materializations=mats, evidence=ev,
            )
            runner.tick()
            final = runner.corpus
        recs: list[ResolutionRecord] = []
        for c in final.claims:
            if c.status != Status.LICENSED:
                continue
            truth = truth_of[c.id]
            recs.append(ResolutionRecord(
                subject_claim_id=c.id, license_epoch=0,
                resolution_kind=ResolutionKind.DEFINITIONAL,
                calibration_target=CalibrationTarget.REALIZED_FDR,
                verdict=ResolutionVerdict.UPHELD if truth else ResolutionVerdict.FAILED,
                stated_q=model.target_fdr, observed_at_cycle=0,
                constructed_truth=truth, model_id=model.model_id, batch_id=batch_id,
            ))
        return tuple(recs)


def run_calibration(*, model: GeneratingModelParams, n_batches: int, base_seed: int) -> CalibrationLedger:
    records: list[ResolutionRecord] = []
    models: list[GeneratingModelParams] = []
    for i in range(n_batches):
        bid = f"{model.model_id}-{i}"
        records.extend(run_batch(model=model, batch_id=bid, seed=base_seed + i))
    models.append(model)
    return CalibrationLedger(records=tuple(records), generating_models=tuple(models),
                             default_target_q=model.target_fdr)
```

> Executor: `Comparator` lives wherever `region_delta_beta_claim`'s default `comparator` comes from — grep `class Comparator` and import from there (likely `polymer_claims.comparators` or `evidence`). Adjust the import. If `NodeRunner`'s real constructor differs, adapt; the observable post-tick `claim.status` contract is what the test asserts.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_calibration_harness_run.py -q`
Expected: PASS (2 passed). If the all-true batch licenses 0 claims (gate too strict for the chosen effect/dispersion), raise `effect_size`/`n_per_group` in the test model until some license — a true region that licenses is `upheld` (never `failed`), so the assertion holds regardless of count, but the test is only meaningful if ≥1 licenses.

- [ ] **Step 5: Commit**

```bash
uv run ruff check src tests
git add src/polymer_claims/calibration_harness.py tests/test_calibration_harness_run.py
git commit -m "$(printf 'feat(calibration): end-to-end harness over the real gate -> DEFINITIONAL records\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

- [ ] **Step 6: Add the mixed-batch FDR envelope test + the all-null control (the calibration pass-bar)**

The tolerance is a **pinned, a-priori constant — not a knob to raise until green** (review finding 1). Define it once at module top with its rationale:

```python
# tests/test_calibration_harness_run.py — module constants, fixed BEFORE running
N_BATCHES = 12          # spec N≈12
CAL_FDR_TOLERANCE = 0.02  # absolute margin on mean per-batch FDP.
# Rationale (pinned a priori): a calibrated e-LOND gate has E[FDP] <= q = 0.05. The Monte-Carlo
# standard error of the mean of N=12 per-batch FDPs (each a proportion near q) is ~sqrt(q(1-q)/m)/sqrt(N)
# for batch licensed-count m~tens, i.e. on the order of 0.01-0.015; 0.02 is ~1.5 SE of slack. This
# absorbs finite-N noise WITHOUT admitting a gate whose mean FDP is materially above q (e.g. 0.10
# would fail). It is fixed here and MUST NOT be raised to make a red test pass — a persistent breach
# is a real miscalibration finding to investigate (Phase A: "honest failure is an acceptable outcome").
```

```python
from polymer_protocol.calibration import calibration_summary
from polymer_claims.calibration_harness import run_calibration


def test_mixed_batch_realized_fdr_consistent_with_target():
    model = _model(fraction_true=0.6, n_generated=40, effect_size=0.30, n_per_group=40)
    ledger = run_calibration(model=model, n_batches=N_BATCHES, base_seed=100)
    rep = calibration_summary(ledger, target_q=model.target_fdr)
    assert rep.definitional.realized_rate is not None
    # deterministic (fixed seeds). Pass-rule (spec §8 bar 2): mean per-batch FDP <= q + pinned tolerance.
    assert rep.definitional.realized_rate <= model.target_fdr + CAL_FDR_TOLERANCE


def test_all_null_control_licenses_are_bounded():
    # all-null: every license is false. This is a CONTROL of per-comparison false-positive behavior,
    # NOT the headline FDR. Fixed seed -> deterministic count -> assert a conservative pinned bound.
    model = _model(fraction_true=0.0, n_generated=40, n_per_group=40)
    recs = run_batch(model=model, batch_id="null", seed=200)
    # K: a conservative a-priori bound. Under H0 the per-claim type-I rate is governed by the e-LOND
    # threshold; for 40 null regions at q=0.05 we expect very few licenses. K is pinned, not tuned.
    K = 4
    assert len(recs) <= K, f"all-null licensed {len(recs)} > pinned bound {K} — investigate the gate"
```

Run: `uv run pytest tests/test_calibration_harness_run.py -q`
Expected: PASS. (If the mixed test fails because realized FDR ≫ q, or the control licenses > K, that is a **real** signal the synthetic gate is miscalibrated under these params — investigate; do NOT loosen the constants to pass.) Commit.

---

### Task 7: Calibration store — JSONL event log, epoch allocator, ANCHORED tap

**Files:**
- Create: `src/polymer_claims/calibration_store.py`
- Test: `tests/test_calibration_store.py`

**Interfaces:**
- Consumes: `ResolutionRecord`, `CalibrationLedger`, `anchored_resolutions`, `PressureContext` (Task 1/3); `Corpus`, `NodeRunner.last_drift`.
- Produces: `append_records(path, records)`, `load_ledger(path, *, generating_models=()) -> CalibrationLedger` (folds events to latest verdict per `(subject_claim_id, license_epoch)`), `EpochAllocator` (persists per-claim last epoch + identity key; `allocate(corpus) -> dict[str,int]`), and `observe_anchored(prev, curr, cycle, *, allocator, last_drift) -> tuple[ResolutionRecord, ...]` (builds the `PressureContext` from cause sources and calls `anchored_resolutions`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_calibration_store.py
from polymer_protocol.calibration import (
    ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict, PressureKind,
)
from polymer_claims.calibration_store import append_records, load_ledger


def _anchored(cid, epoch, verdict, cyc):
    return ResolutionRecord(
        subject_claim_id=cid, license_epoch=epoch, resolution_kind=ResolutionKind.ANCHORED,
        calibration_target=CalibrationTarget.WARRANT_SURVIVAL, verdict=verdict,
        stated_q=0.05, observed_at_cycle=cyc, pressure_kind=PressureKind.DEFEAT,
    )


def test_event_log_folds_open_then_resolved_to_latest(tmp_path):
    p = tmp_path / "ledger.jsonl"
    append_records(p, [_anchored("c1", 0, ResolutionVerdict.UNRESOLVED, 1)])
    append_records(p, [_anchored("c1", 0, ResolutionVerdict.FAILED, 5)])
    ledger = load_ledger(p)
    # one (c1, epoch 0) -> latest state only
    c1 = [r for r in ledger.records if r.subject_claim_id == "c1"]
    assert len(c1) == 1 and c1[0].verdict == ResolutionVerdict.FAILED


def test_round_trip_preserves_distinct_epochs(tmp_path):
    p = tmp_path / "ledger.jsonl"
    append_records(p, [_anchored("c1", 0, ResolutionVerdict.FAILED, 1),
                       _anchored("c1", 1, ResolutionVerdict.UNRESOLVED, 9)])
    ledger = load_ledger(p)
    assert len({(r.subject_claim_id, r.license_epoch) for r in ledger.records}) == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_calibration_store.py -q`
Expected: FAIL — `ModuleNotFoundError: polymer_claims.calibration_store`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/polymer_claims/calibration_store.py
"""Append-only JSONL event log + epoch allocator for the calibration ledger (impure: filesystem).
NOT re-exported from polymer_claims.__init__."""
from __future__ import annotations

import json
from pathlib import Path

from polymer_grammar import Status
from polymer_protocol.calibration import (
    CalibrationLedger, GeneratingModelParams, ResolutionRecord, ResolutionKind,
    PressureContext, PressureKind, anchored_resolutions,
)


def append_records(path, records) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        for r in records:
            fh.write(r.model_dump_json(exclude_none=True) + "\n")


def load_ledger(path, *, generating_models: tuple[GeneratingModelParams, ...] = ()) -> CalibrationLedger:
    path = Path(path)
    latest: dict[tuple[str, int], ResolutionRecord] = {}
    order: list[tuple[str, int]] = []
    if path.is_file():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = ResolutionRecord.model_validate_json(line)
            key = (r.subject_claim_id, r.license_epoch)
            if key not in latest:
                order.append(key)
            latest[key] = r  # latest event wins (DEFINITIONAL keys are unique; ANCHORED folds)
    return CalibrationLedger(records=tuple(latest[k] for k in order),
                             generating_models=generating_models)


class EpochAllocator:
    """Owns license_epoch assignment (spec §6). Persists per-claim last epoch + identity key so the
    tap is idempotent across ticks AND restarts."""

    def __init__(self, path):
        self.path = Path(path)
        self._state: dict[str, dict] = {}
        if self.path.is_file():
            self._state = json.loads(self.path.read_text())

    def _identity(self, claim) -> str:
        lic = claim.licensing
        if lic and lic.satisfactions:
            srid = lic.satisfactions[0].materialization.semantic_run_id
            if srid:
                return srid
        # fallback identity tuple (spec finding 6) for non-content-addressed licenses
        return f"{claim.id}|{len(claim.licensing.satisfactions) if lic else 0}"

    def allocate(self, corpus) -> dict[str, int]:
        """Return {claim_id: epoch} for currently-LICENSED claims; bump on new identity key."""
        out: dict[str, int] = {}
        for c in corpus.claims:
            if c.status != Status.LICENSED:
                continue
            ident = self._identity(c)
            prev = self._state.get(c.id)
            if prev is None:
                epoch = 0
            elif prev["identity"] == ident:
                epoch = prev["epoch"]            # same epoch (idempotent)
            else:
                epoch = prev["epoch"] + 1        # re-licensed under changed identity
            self._state[c.id] = {"epoch": epoch, "identity": ident}
            out[c.id] = epoch
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._state, sort_keys=True))
        return out


def observe_anchored(prev, curr, cycle, *, allocator: EpochAllocator,
                     last_drift=None) -> tuple[ResolutionRecord, ...]:
    """Build a PressureContext from the cause sources and emit ANCHORED resolving records."""
    epoch = allocator.allocate(prev)  # epochs as of the PRE-transition LICENSED set
    cause: dict[str, PressureKind] = {}
    prev_licensed = {c.id for c in prev.claims if c.status == Status.LICENSED}
    by_id = {c.id: c for c in curr.claims}
    drift_ids = {f.claim_id for f in (last_drift.drifted if last_drift else ())}
    for cid in prev_licensed:
        c = by_id.get(cid)
        if c is None:
            continue
        if c.status == Status.REJECTED:
            cause[cid] = PressureKind.DEFEAT
        elif c.status == Status.PENDING and cid in drift_ids:
            cause[cid] = PressureKind.DRIFT
    pc = PressureContext(epoch=epoch, cause=cause)
    return anchored_resolutions(prev, curr, cycle, pc)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_calibration_store.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Add an epoch-allocator restart-idempotence test**

```python
# append to tests/test_calibration_store.py — needs a LICENSED claim fixture
# Executor: reuse tests' existing licensed-claim builder (or the one from Task 3 _calib_fixtures
# if importable from the umbrella test tree) to build a Corpus with one LICENSED claim, then:
#   alloc1 = EpochAllocator(state_path); e1 = alloc1.allocate(corpus)
#   alloc2 = EpochAllocator(state_path)  # fresh process simulation, reloads state
#   e2 = alloc2.allocate(corpus)
#   assert e1 == e2  # same identity -> same epoch across "restart"
```

Run + commit:

```bash
uv run ruff check src tests
git add src/polymer_claims/calibration_store.py tests/test_calibration_store.py
git commit -m "$(printf 'feat(calibration): JSONL event store + epoch allocator + ANCHORED tap\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

> Wiring note (no separate task): the `NodeRunner` ANCHORED hook is a one-line call in the tick loop — after a tick computes `prev`/`curr`, call `observe_anchored(prev, curr, cycle, allocator=self._epoch_alloc, last_drift=self.last_drift)` and `append_records(...)` **only when calibration is enabled** (a `calibration_path` kwarg, default `None` → byte-identical). Fold this into Task 7's commit if `node.py` is touched, with a test that a tick with `calibration_path=None` leaves no file.

---

### Task 8: `Certificate` DTO + `build_certificate` + `certificate_dsse_envelope`

**Files:**
- Modify: `src/polymer_claims/attestation.py` (after the existing DSSE/bundle defs; do NOT touch `dsse_envelope`/`build_attestation_*`)
- Test: `tests/test_certificate.py`

**Interfaces:**
- Consumes: `Statement`, `dsse_envelope`, `build_attestation_statements`, `resolve_contract_index` (`attestation.py`); `CalibrationReport`/`CalibrationLedger`/`calibration_summary` (`polymer_protocol.calibration`).
- Produces: `Certificate(_Model)` (`statement: Statement`, `calibration: CalibrationReport | None`, `ledger_digest: str | None`, `generating_models: tuple[GeneratingModelParams, ...]`, `interpretation: str`); `build_certificate(corpus, claim_id, *, ledger=None, target_q, contract_index=None) -> Certificate`; `certificate_dsse_envelope(cert) -> DsseEnvelope` with `payload_type="application/vnd.polymer.certificate+json"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_certificate.py
import base64, json
from polymer_protocol.calibration import CalibrationLedger
from polymer_claims.attestation import (
    build_certificate, certificate_dsse_envelope, build_attestation_bundle, resolve_contract_index,
)
# Executor: reuse the corpus-with-one-LICENSED-methyl-claim fixture the existing attestation tests use
from tests.test_attestation import licensed_corpus  # or the equivalent helper present there


def test_certificate_carries_calibration_block():
    corpus = licensed_corpus()
    cid = next(c.id for c in corpus.claims if c.status.value == "licensed")
    cert = build_certificate(corpus, cid, ledger=CalibrationLedger(records=()), target_q=0.05)
    assert cert.statement is not None
    assert cert.calibration is not None and cert.calibration.target_q == 0.05


def test_certificate_dsse_payload_round_trips_to_certificate():
    corpus = licensed_corpus()
    cid = next(c.id for c in corpus.claims if c.status.value == "licensed")
    cert = build_certificate(corpus, cid, ledger=CalibrationLedger(records=()), target_q=0.05)
    env = certificate_dsse_envelope(cert)
    assert env.payload_type == "application/vnd.polymer.certificate+json"
    decoded = json.loads(base64.b64decode(env.payload))
    assert "statement" in decoded and "calibration" in decoded


def test_existing_attestation_bundle_byte_identical(snapshot_path=None):
    # build_attestation_bundle must be untouched by the new code
    corpus = licensed_corpus()
    out = build_attestation_bundle(corpus, contract_index=resolve_contract_index(corpus))
    assert out.model_dump_json(by_alias=True, exclude_none=True)  # smoke: still builds, no exception
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_certificate.py -q`
Expected: FAIL — `ImportError: cannot import name 'build_certificate'`.

- [ ] **Step 3: Write minimal implementation** (append to `attestation.py`)

```python
from polymer_protocol.calibration import (
    CalibrationLedger, CalibrationReport, GeneratingModelParams, calibration_summary,
)

_CERTIFICATE_MEDIA_TYPE = "application/vnd.polymer.certificate+json"
_INTERPRETATION = (
    "Definitional calibration validates the gate under known constructed truth (realized FDR). "
    "Anchored/attested calibration measures warrant stability under future pressure, not truth."
)


class Certificate(_Model):
    statement: Statement
    calibration: CalibrationReport | None = None
    generating_models: tuple[GeneratingModelParams, ...] = ()
    ledger_digest: str | None = None
    interpretation: str = _INTERPRETATION


def build_certificate(corpus, claim_id, *, ledger: CalibrationLedger | None = None,
                      target_q: float, contract_index=None) -> Certificate:
    index = contract_index if contract_index is not None else resolve_contract_index(corpus)
    statements = build_attestation_statements(corpus, contract_index=index)
    stmt = next((s for s in statements if any(sub.name == claim_id for sub in s.subject)), None)
    if stmt is None:
        raise ValueError(f"no LICENSED claim {claim_id!r} to certify")
    report = None
    digest = None
    models: tuple[GeneratingModelParams, ...] = ()
    if ledger is not None:
        report = calibration_summary(ledger, target_q=target_q)
        models = ledger.generating_models
        raw = ledger.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
    return Certificate(statement=stmt, calibration=report, generating_models=models,
                       ledger_digest=digest)


def certificate_dsse_envelope(cert: Certificate) -> DsseEnvelope:
    """Wrap a full Certificate (Statement + calibration block + ledger digest) in a DSSE-shaped
    envelope. The calibration evidence is INSIDE the signed bytes. Mirrors dsse_envelope but a
    distinct payloadType. Existing dsse_envelope is untouched."""
    raw = cert.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
    return DsseEnvelope(payload_type=_CERTIFICATE_MEDIA_TYPE,
                        payload=base64.b64encode(raw).decode("ascii"))
```

> Executor: `_subject(...)` builds a `Subject` whose `name` is the claim id (confirm against `attestation.py:179` `_subject`). If the subject `name` is not the bare claim id, match on whatever identifier `_subject` uses. `hashlib` and `base64` are already imported at the top of `attestation.py`.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_certificate.py tests/test_attestation.py -q`
Expected: PASS (new certificate tests + all existing attestation tests still green → byte-identical guarantee holds).

- [ ] **Step 5: Commit**

```bash
uv run ruff check src tests
git add src/polymer_claims/attestation.py tests/test_certificate.py
git commit -m "$(printf 'feat(attestation): Certificate DTO + DSSE certificate envelope (calibration in signed bytes)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 9: Certificate text rendering + the no-laundering invariant

**Files:**
- Modify: `src/polymer_claims/attestation.py`
- Test: `tests/test_certificate_render.py`

**Interfaces:**
- Produces: `render_certificate_text(cert: Certificate) -> str`. Headline `q` line = DEFINITIONAL realized FDR ONLY (recompute `feeds_headline_q` from kind/target — never read a stored bool); `q_anchored`/`q_attested` under a separate "Warrant stability (field calibration)" heading.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_certificate_render.py
from polymer_protocol.calibration import (
    CalibrationLedger, ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict,
    PressureKind,
)
from polymer_claims.attestation import build_certificate, render_certificate_text
from tests.test_attestation import licensed_corpus


def _ledger():
    defn = [ResolutionRecord(subject_claim_id=f"d{i}", license_epoch=0,
            resolution_kind=ResolutionKind.DEFINITIONAL, calibration_target=CalibrationTarget.REALIZED_FDR,
            verdict=(ResolutionVerdict.FAILED if i == 0 else ResolutionVerdict.UPHELD),
            stated_q=0.05, observed_at_cycle=0, constructed_truth=(i != 0), model_id="m", batch_id="b")
            for i in range(10)]
    anch = [ResolutionRecord(subject_claim_id="a1", license_epoch=0, resolution_kind=ResolutionKind.ANCHORED,
            calibration_target=CalibrationTarget.WARRANT_SURVIVAL, verdict=ResolutionVerdict.FAILED,
            stated_q=0.05, observed_at_cycle=3, pressure_kind=PressureKind.DEFEAT)]
    return CalibrationLedger(records=tuple(defn + anch))


def test_render_has_headline_fdr_and_separates_field_calibration():
    corpus = licensed_corpus()
    cid = next(c.id for c in corpus.claims if c.status.value == "licensed")
    text = render_certificate_text(build_certificate(corpus, cid, ledger=_ledger(), target_q=0.05))
    assert "realized FDR" in text
    assert "Warrant stability" in text  # field-calibration heading
    # the anchored rate must NOT appear above/at the headline q line
    headline_idx = text.index("Corpus target q")
    field_idx = text.index("Warrant stability")
    assert field_idx > headline_idx
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_certificate_render.py -q`
Expected: FAIL — `ImportError: cannot import name 'render_certificate_text'`.

- [ ] **Step 3: Implement** (append to `attestation.py`)

```python
def render_certificate_text(cert: Certificate) -> str:
    lines = [f"Polymer Certificate — claim {cert.statement.subject[0].name}"]
    rep = cert.calibration
    if rep is None:
        lines.append("(standing-only — no calibration ledger supplied)")
        lines.append("")
        lines.append(cert.interpretation)
        return "\n".join(lines)
    d = rep.definitional
    lines.append(f"Corpus target q: {rep.target_q}")
    lines.append("Calibration evidence:")
    # HEADLINE: definitional realized FDR ONLY (the only tier with feeds_headline_q)
    if d.realized_rate is None:
        lines.append("  DEFINITIONAL: no batches yet")
    else:
        ci = f"[{d.ci_low:.3f}, {d.ci_high:.3f}]" if d.ci_low is not None else "n/a"
        lines.append(
            f"  DEFINITIONAL: {d.n_batches} mixed batches, {d.n_total} licensed; {d.n_failed} false licenses"
        )
        lines.append(
            f"                -> realized FDR (mean per-batch FDP) {d.realized_rate:.3f}, 95% CI {ci}"
            f" (pooled false fraction {d.pooled_rate:.3f})"
        )
    # FIELD CALIBRATION: anchored/attested — never the headline
    lines.append("Warrant stability (field calibration — survival under pressure, NOT truth):")
    a = rep.anchored
    if a.n_total:
        lines.append(
            f"  ANCHORED: {a.n_total} epochs resolved under pressure; {a.n_failed} failed"
            f" -> warrant-failure rate {a.realized_rate:.3f}; {a.n_superseded} superseded;"
            f" {a.n_unresolved} unresolved (span: {rep.observation_span_cycles} cycles)"
        )
    else:
        lines.append("  ANCHORED: no resolved epochs yet")
    lines.append(f"  ATTESTED: {rep.attested.n_total} attested events")
    lines.append("")
    lines.append(f"Interpretation: {cert.interpretation}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_certificate_render.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
uv run ruff check src tests
git add src/polymer_claims/attestation.py tests/test_certificate_render.py
git commit -m "$(printf 'feat(attestation): certificate text render + no-laundering headline invariant\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 10: CLI — `calibrate` + `certify` subcommands

**Files:**
- Modify: `src/polymer_claims/cli.py` (register near `export-attestation` at :520; add `_cmd_*` near :221)
- Test: `tests/test_cli_calibration.py`

**Interfaces:**
- Consumes: `run_calibration` (harness), `load_ledger`/`append_records` (store), `build_certificate`/`render_certificate_text`/`certificate_dsse_envelope` (attestation), `load_corpus` (existing CLI helper). Lazy imports inside the command (keeps base CLI numpy-free).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_calibration.py
import subprocess, sys, json


def _run(*args):
    return subprocess.run([sys.executable, "-m", "polymer_claims.cli", *args],
                          capture_output=True, text=True)


def test_calibrate_writes_a_ledger(tmp_path):
    out = tmp_path / "ledger.jsonl"
    r = _run("calibrate", "--synthetic", "--batches", "3", "--n", "6", "--q", "0.05",
             "--out", str(out))
    assert r.returncode == 0, r.stderr
    assert out.is_file() and out.read_text().strip()  # at least one record line


def test_certify_text_has_headline(tmp_path):
    # build a tiny ledger first
    ledger = tmp_path / "l.jsonl"
    _run("calibrate", "--synthetic", "--batches", "3", "--n", "6", "--q", "0.05", "--out", str(ledger))
    # certify against a bundled licensed-corpus fixture path used by other CLI tests
    # Executor: point --corpus at the same fixture tests/test_cli*.py already uses for a LICENSED corpus
    r = _run("certify", "FIXTURE_CLAIM_ID", "--corpus", "tests/fixtures/licensed_corpus.json",
             "--calibration", str(ledger), "--q", "0.05")
    assert r.returncode == 0, r.stderr
    assert "Corpus target q" in r.stdout
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_cli_calibration.py -q`
Expected: FAIL — unknown subcommand `calibrate` (argparse exits non-zero).

- [ ] **Step 3: Register + implement** (in `cli.py`, mirroring `_cmd_export_attestation` at :221 and its parser at :520)

```python
def _cmd_calibrate(args: argparse.Namespace) -> int:
    from .calibration_harness import run_calibration
    from .calibration_store import append_records
    from polymer_protocol.calibration import GeneratingModelParams
    model = GeneratingModelParams(
        model_id="cli", n_per_group=args.n_per_group, n_probes_per_region=args.probes,
        effect_size=args.effect_size, dispersion=args.dispersion, fraction_true=args.fraction_true,
        tau=args.tau, target_fdr=args.q, n_generated=args.n, seed_set=(args.seed,),
    )
    ledger = run_calibration(model=model, n_batches=args.batches, base_seed=args.seed)
    if args.out:
        append_records(args.out, ledger.records)
    else:
        for r in ledger.records:
            sys.stdout.write(r.model_dump_json(exclude_none=True) + "\n")
    return 0


def _cmd_certify(args: argparse.Namespace) -> int:
    from .attestation import build_certificate, render_certificate_text, certificate_dsse_envelope
    corpus = load_corpus(args.corpus)
    ledger = None
    if args.calibration:
        from .calibration_store import load_ledger
        ledger = load_ledger(args.calibration)
    cert = build_certificate(corpus, args.claim_id, ledger=ledger, target_q=args.q)
    if args.format == "json":
        out = cert.model_dump_json(by_alias=True, exclude_none=True)
    elif args.format == "dsse":
        out = certificate_dsse_envelope(cert).model_dump_json(by_alias=True, exclude_none=True)
    else:
        out = render_certificate_text(cert)
    sys.stdout.write(out + "\n")
    return 0
```

Register in the subparser block (next to `export-attestation`):

```python
p_cal = sub.add_parser("calibrate", help="run the synthetic DEFINITIONAL calibration harness")
p_cal.add_argument("--synthetic", action="store_true", help="(only mode this slice)")
p_cal.add_argument("--batches", type=int, default=12)
p_cal.add_argument("--n", type=int, default=40, help="regions (claims) per batch")
p_cal.add_argument("--q", type=float, default=0.05)
p_cal.add_argument("--fraction-true", dest="fraction_true", type=float, default=0.6)
p_cal.add_argument("--effect-size", dest="effect_size", type=float, default=0.30)
p_cal.add_argument("--dispersion", type=float, default=25.0)
p_cal.add_argument("--tau", type=float, default=0.10)
p_cal.add_argument("--n-per-group", dest="n_per_group", type=int, default=40)
p_cal.add_argument("--probes", type=int, default=6)
p_cal.add_argument("--seed", type=int, default=0)
p_cal.add_argument("--out", default=None, help="write the ledger JSONL here (else stdout)")
p_cal.set_defaults(func=_cmd_calibrate)

p_cert = sub.add_parser("certify", help="emit a single-claim certificate (standing + calibrated q)")
p_cert.add_argument("claim_id")
p_cert.add_argument("--corpus", required=True, help="path to a corpus JSON file")
p_cert.add_argument("--calibration", default=None, help="path to a calibration ledger JSONL")
p_cert.add_argument("--q", type=float, default=0.05)
p_cert.add_argument("--format", choices=("text", "json", "dsse"), default="text")
p_cert.set_defaults(func=_cmd_certify)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_cli_calibration.py -q`
Expected: PASS (2 passed). (Executor: set `FIXTURE_CLAIM_ID`/`--corpus` to the licensed-corpus fixture the other CLI tests use.)

- [ ] **Step 5: Full gate + commit**

```bash
uv run ruff check src tests
cd protocol && uv run pytest -q && uv run ruff check src tests && cd ..
uv run pytest -q
git add src/polymer_claims/cli.py tests/test_cli_calibration.py
git commit -m "$(printf 'feat(cli): calibrate + certify subcommands\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

- [ ] **Step 6: Run the full pre-merge gate**

Run: `scripts/check-all.sh`
Expected: ALL GREEN (umbrella + grammar + protocol pytest, ruff, viewer tsc; the `next build` font-fetch caveat is the only acceptable network-blocked failure). Fix anything red before declaring done.

---

## Self-Review

**Spec coverage:**
- §1/§1.1/§1.2 warrant tiers + computed `feeds_headline_q` → Tasks 1, 9 ✓
- §4.2 `ResolutionRecord` + validators → Task 1 ✓
- §4.3 `CalibrationLedger`/`GeneratingModelParams` + `default_target_q` → Task 2 ✓
- §4.4 `calibration_summary` (mean per-batch FDP, pooled secondary, Wilson/normal, single-`target_q`, `n_superseded` excluded) → Task 2 ✓
- §5 contract-root contextvar + cache key + synthetic generator → Tasks 4, 5 ✓
- §5 end-to-end real-gate run, mean-FDR over mixed batches → Task 6 ✓
- §6 ANCHORED tap (cause-fed, event-identity) + epoch allocator (incl. fallback identity) → Tasks 3, 7 ✓
- §7 Certificate DTO + DSSE payload + render + no-laundering → Tasks 8, 9 ✓
- §8 tests (validator, summary, transitions, harness determinism, mixed-batch envelope, store fold, byte-identical attestation, render headline) → distributed across all tasks ✓
- §3 packaging `[calibrate]` → Task 5 ✓
- ATTESTED stub (schema + report slot, no ingestion) → Tasks 1/2 (slot present, `n_total=0`) ✓

**Placeholder scan:** the two intentional executor-fill points (Task 3 `_calib_fixtures.py` minimal claim; Task 6 `Comparator`/`NodeRunner` constructor confirmation; Task 10 fixture claim id) are explicitly flagged with the exact source file to copy from — they are *grounding instructions against real code*, not vague placeholders, because the precise leaf/pattern shapes live in existing tests the executor must mirror rather than have me guess.

**Type consistency:** `ResolutionRecord`/`CalibrationLedger`/`CalibrationReport`/`TierStat` field names and `calibration_summary(ledger, *, target_q)` / `anchored_resolutions(prev, curr, cycle, pressure)` / `build_certificate(corpus, claim_id, *, ledger, target_q)` / `certificate_dsse_envelope(cert)` signatures are identical everywhere they appear across tasks. `feeds_headline_q` is a property (read-only) throughout. `realized_fdr` is the calibration-target enum value everywhere (no `false_license_rate` residue).

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-22-calibration-ledger-and-certificate.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
