# #5b ORACLE-VALIDATION daemon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pure, caller-scheduled ORACLE-VALIDATION daemon that decays a failing oracle's `ValidationTier` (proportional to its SPOT-probe pass rate), tightening the existing #2 `oracle_cap` seam — plus the F2 fix making the oracle cap treat the reverse-polarity `uncertainty` axis correctly.

**Architecture:** Two grammar additions in `grammar/oracle.py` (a pure `decay_tier` tier-algebra helper; the F2 reverse-polarity cap fix), then a self-contained protocol module `oracle_validation.py` whose `oracle_validation_pass(registry, *, probes)` returns a threaded registry-delta + a record. No `run_cycle` wiring this slice.

**Tech Stack:** Python 3.14, Pydantic v2 (frozen `_Model`, tuples), `uv`, pytest, ruff. Two packages: `grammar/` (`polymer_grammar`) and `protocol/` (`polymer_protocol`, one-way dep on grammar).

**Spec:** `docs/superpowers/specs/2026-06-04-oracle-validation-design.md`

---

## File Structure

- `grammar/src/polymer_grammar/oracle.py` — **modify**: F2 cap fix (`tier_ceiling`/`cap_strength`, `_GOODNESS_EMPIRICAL_AXES`) + `decay_tier`/`_RANK_TO_TIER`/`MAX_TIER_RANK`.
- `grammar/tests/test_oracle.py` — **modify**: update 3 assertions broken by the F2 fix + add F2 regression tests + `decay_tier` tests.
- `grammar/src/polymer_grammar/__init__.py` — **modify**: export `decay_tier`.
- `protocol/src/polymer_protocol/oracle_validation.py` — **create**: `SpotProbe`, `OracleDecay`, `OracleValidationRecord`, `oracle_validation_pass`.
- `protocol/tests/test_oracle_validation.py` — **create**: daemon tests + the end-to-end cap-tightening seam test.
- `protocol/src/polymer_protocol/__init__.py` — **modify**: export the four protocol names.

Conventions (established): all models subclass `_Model` (frozen, `extra="forbid"`, tuple fields). Frozen models use `model_copy(update=...)` to produce changed copies. Grammar owns tier algebra (`weakest_tier`/`tier_ceiling`); protocol owns the daemon orchestration. `protocol/tests/conftest.py` provides `make_claim`, `make_plan(value, threshold, *, oracle_ref=...)`.

---

### Task 1: Grammar — F2 reverse-polarity cap fix

**Files:**
- Modify: `grammar/src/polymer_grammar/oracle.py`
- Test: `grammar/tests/test_oracle.py`

The `uncertainty` axis is reverse-polarity (confirmed: `belief.py:32` maps high `uncertainty` → low concentration → weaker). The oracle cap currently `meet`s it DOWN like a goodness axis, which makes a weak apparatus look *less* uncertain. Fix: cap the 3 true goodness empirical axes down; floor `uncertainty` UP to `1 − ceiling`.

- [ ] **Step 1: Update the existing assertions the fix will change + add F2 regression tests**

In `grammar/tests/test_oracle.py`:

(a) In `test_tier_ceiling_caps_empirical_leaves_theory_at_one`, change the uncertainty line from `0.4` to `1.0` (tier_ceiling no longer caps uncertainty down — it's handled as a floor in cap_strength):

```python
def test_tier_ceiling_caps_empirical_leaves_theory_at_one():
    c = tier_ceiling(ValidationTier.INDIRECT)
    assert c.magnitude == 0.4
    assert c.uncertainty == 1.0          # no longer a goodness cap; uncertainty is floored in cap_strength
    assert c.evidence_against_null == 0.4
    assert c.world_contact == 0.4
    assert c.severity == 1.0
    assert c.explanatory_virtue == 1.0
```

(b) Replace `test_tier_ceiling_monotone_on_all_empirical_axes` (uncertainty is no longer a monotone down-capped axis in tier_ceiling — it's constant 1.0 there):

```python
def test_tier_ceiling_monotone_on_goodness_axes():
    order = [ValidationTier.UNVALIDATED, ValidationTier.INDIRECT,
             ValidationTier.BENCHMARKED, ValidationTier.ANCHORED, ValidationTier.GOLD]
    for ax in ("magnitude", "evidence_against_null", "world_contact"):
        vals = [getattr(tier_ceiling(t), ax) for t in order]
        assert vals == sorted(vals)
        assert vals[0] == 0.0 and vals[-1] == 1.0
    # uncertainty is constant 1.0 in tier_ceiling (capped as a floor in cap_strength, not here)
    assert all(tier_ceiling(t).uncertainty == 1.0 for t in order)
```

(c) In `test_cap_strength_caps_only_empirical`, the uncertainty assertion flips from capped-down to floored-up. Input `uncertainty=0.9`, INDIRECT c=0.4 → floor up to `max(0.9, 0.6)` = `0.9` (already above the floor, unchanged):

```python
def test_cap_strength_caps_only_empirical():
    s = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                       severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    capped = cap_strength(s, ValidationTier.INDIRECT)
    assert capped.magnitude == 0.4
    assert capped.uncertainty == 0.9          # reverse-polarity floor: max(0.9, 1-0.4=0.6) = 0.9
    assert capped.evidence_against_null == 0.4
    assert capped.world_contact == 0.4
    assert capped.severity == 0.9
    assert capped.explanatory_virtue == 0.9
```

(d) In `test_cap_strength_by_unvalidated_zeroes_empirical`, add an uncertainty assertion (UNVALIDATED c=0.0 → uncertainty floored to `max(0.7, 1.0)` = `1.0`):

```python
def test_cap_strength_by_unvalidated_zeroes_empirical():
    s = StrengthVector(magnitude=0.7, uncertainty=0.7, evidence_against_null=0.7,
                       severity=0.7, world_contact=0.7, explanatory_virtue=0.7)
    capped = cap_strength(s, ValidationTier.UNVALIDATED)
    assert capped.magnitude == 0.0
    assert capped.world_contact == 0.0
    assert capped.uncertainty == 1.0          # reverse polarity: weak apparatus -> maximally uncertain
    assert capped.severity == 0.7
    assert capped.explanatory_virtue == 0.7
```

(e) Add a focused F2 regression test (low uncertainty under a weak tier must come out MORE uncertain):

```python
def test_cap_strength_weak_tier_raises_uncertainty_not_lowers_it():
    # F2: a precise claim (low uncertainty) evaluated on a weak apparatus must become MORE uncertain.
    precise = StrengthVector(magnitude=0.5, uncertainty=0.1, evidence_against_null=0.5,
                             severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    capped = cap_strength(precise, ValidationTier.BENCHMARKED)  # c=0.6 -> floor 1-0.6=0.4
    assert capped.uncertainty == 0.4           # raised from 0.1, NOT lowered
    assert capped.magnitude == 0.5             # goodness axis below ceiling 0.6 -> unchanged
```

Note `test_cap_strength_never_raises_an_axis` uses GOLD (c=1.0 → uncertainty floor `max(v, 0.0)` = v unchanged), so it stays green — leave it.

- [ ] **Step 2: Run the oracle tests to verify the edited ones fail**

Run: `cd grammar && uv run pytest tests/test_oracle.py -q`
Expected: FAIL — the edited assertions (uncertainty 0.4→1.0, 0.4→0.9, the new floor expectations) fail against the current cap-down implementation.

- [ ] **Step 3: Apply the F2 fix in `oracle.py`**

In `grammar/src/polymer_grammar/oracle.py`, replace the `_EMPIRICAL_AXES` constant (line ~41) with a goodness-only constant:

```python
# Goodness empirical axes the tier ceiling caps DOWN (higher = stronger). `uncertainty` is ALSO
# apparatus-bounded but REVERSE-polarity (higher = weaker), so it is floored UP in cap_strength, not
# capped here. severity + explanatory_virtue are theory axes (set by argument) -> never touched.
_GOODNESS_EMPIRICAL_AXES = ("magnitude", "evidence_against_null", "world_contact")
```

Replace `tier_ceiling` (the `_EMPIRICAL_AXES` reference) so only goodness axes carry the ceiling:

```python
def tier_ceiling(tier: ValidationTier) -> StrengthVector:
    """Per-axis ceiling for the GOODNESS empirical axes (capped down to c). `uncertainty` and the theory
    axes stay 1.0 here — uncertainty is reverse-polarity and is floored UP in cap_strength instead."""
    c = _TIER_CEILING[tier]
    return StrengthVector(**{ax: (c if ax in _GOODNESS_EMPIRICAL_AXES else 1.0) for ax in AXES})
```

Replace `cap_strength` to floor uncertainty up:

```python
def cap_strength(
    strength: StrengthVector | None, tier: ValidationTier
) -> StrengthVector | None:
    """`strength` capped by the tier. Goodness empirical axes meet the ceiling (componentwise min);
    the reverse-polarity `uncertainty` axis is floored UP to (1 - ceiling) — a weak apparatus makes a
    claim MORE uncertain, not less (F2). Theory axes (severity, explanatory_virtue) uncapped. None -> None."""
    if strength is None:
        return None
    c = _TIER_CEILING[tier]
    capped = strength.meet(tier_ceiling(tier))  # caps the 3 goodness axes; uncertainty/theory are no-ops
    return capped.model_copy(update={"uncertainty": max(strength.uncertainty, 1.0 - c)})
```

- [ ] **Step 4: Run the oracle tests to verify they pass**

Run: `cd grammar && uv run pytest tests/test_oracle.py -q`
Expected: PASS (all, including the new F2 regression test).

- [ ] **Step 5: Run the full grammar suite + ruff (no regressions)**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: all green, ruff clean. (No other module reads `_EMPIRICAL_AXES` — verified by grep; only `oracle.py` referenced it.)

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/oracle.py grammar/tests/test_oracle.py
git commit -m "fix(grammar): oracle cap floors reverse-polarity uncertainty up (F2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Grammar — `decay_tier` proportional tier-decay helper

**Files:**
- Modify: `grammar/src/polymer_grammar/oracle.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_oracle.py`

- [ ] **Step 1: Write the failing `decay_tier` tests**

Append to `grammar/tests/test_oracle.py`:

```python
def test_decay_tier_full_pass_is_unchanged():
    from polymer_grammar import decay_tier
    assert decay_tier(ValidationTier.GOLD, 1.0) == ValidationTier.GOLD
    assert decay_tier(ValidationTier.INDIRECT, 1.0) == ValidationTier.INDIRECT


def test_decay_tier_zero_pass_is_unvalidated():
    from polymer_grammar import decay_tier
    assert decay_tier(ValidationTier.GOLD, 0.0) == ValidationTier.UNVALIDATED


def test_decay_tier_proportional_from_gold():
    from polymer_grammar import decay_tier
    assert decay_tier(ValidationTier.GOLD, 0.9) == ValidationTier.ANCHORED      # floor(3.6)=3
    assert decay_tier(ValidationTier.GOLD, 0.7) == ValidationTier.BENCHMARKED   # floor(2.8)=2
    assert decay_tier(ValidationTier.GOLD, 0.5) == ValidationTier.BENCHMARKED   # floor(2.0)=2
    assert decay_tier(ValidationTier.GOLD, 0.25) == ValidationTier.INDIRECT     # floor(1.0)=1


def test_decay_tier_is_decay_only_never_promotes():
    from polymer_grammar import decay_tier
    # pass_rate that would "earn" GOLD cannot lift an INDIRECT oracle above INDIRECT.
    assert decay_tier(ValidationTier.INDIRECT, 1.0) == ValidationTier.INDIRECT
    assert decay_tier(ValidationTier.BENCHMARKED, 0.9) == ValidationTier.BENCHMARKED  # min(2, 3)=2


def test_decay_tier_has_stable_fixed_point():
    from polymer_grammar import decay_tier
    once = decay_tier(ValidationTier.GOLD, 0.9)        # ANCHORED
    twice = decay_tier(once, 0.9)                      # min(3, 3) -> ANCHORED
    assert once == twice == ValidationTier.ANCHORED


def test_decay_tier_clamps_out_of_range():
    from polymer_grammar import decay_tier
    assert decay_tier(ValidationTier.GOLD, -0.5) == ValidationTier.UNVALIDATED
    assert decay_tier(ValidationTier.GOLD, 1.7) == ValidationTier.GOLD


def test_decay_tier_unvalidated_stays_unvalidated():
    from polymer_grammar import decay_tier
    assert decay_tier(ValidationTier.UNVALIDATED, 1.0) == ValidationTier.UNVALIDATED
    assert decay_tier(ValidationTier.UNVALIDATED, 0.0) == ValidationTier.UNVALIDATED
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd grammar && uv run pytest tests/test_oracle.py -k decay_tier -q`
Expected: FAIL — `ImportError: cannot import name 'decay_tier'`.

- [ ] **Step 3: Add `decay_tier` to `oracle.py`**

Add after `weakest_tier` in `grammar/src/polymer_grammar/oracle.py`:

```python
MAX_TIER_RANK = max(_TIER_RANK.values())  # 4
_RANK_TO_TIER = {rank: tier for tier, rank in _TIER_RANK.items()}


def decay_tier(tier: ValidationTier, pass_rate: float) -> ValidationTier:
    """The tier a SPOT-probe `pass_rate` earns, capped by the current tier (DECAY-ONLY — never promotes).
    target_rank = floor(clamp(pass_rate, 0, 1) * MAX_TIER_RANK); new_rank = min(current, target). Gives a
    proportional decay with a stable fixed point (a 90%-passing oracle settles at ANCHORED and stays);
    monotone non-increasing; parameter-free. int() truncates toward zero = floor for the non-negative arg."""
    pr = 0.0 if pass_rate < 0.0 else (1.0 if pass_rate > 1.0 else pass_rate)
    target_rank = int(pr * MAX_TIER_RANK)
    new_rank = min(_TIER_RANK[tier], target_rank)
    return _RANK_TO_TIER[new_rank]
```

- [ ] **Step 4: Export `decay_tier` from the grammar package**

In `grammar/src/polymer_grammar/__init__.py`, add `decay_tier` to the `from .oracle import (...)` block (next to `cap_strength`/`tier_ceiling`/`weakest_tier`) and add `"decay_tier",` to `__all__`.

- [ ] **Step 5: Run to verify they pass**

Run: `cd grammar && uv run pytest tests/test_oracle.py -q && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 6: Run the full grammar suite**

Run: `cd grammar && uv run pytest -q`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add grammar/src/polymer_grammar/oracle.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_oracle.py
git commit -m "feat(grammar): decay_tier — proportional decay-only oracle tier helper (#5b)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Protocol — `oracle_validation.py` (the daemon) + tests

**Files:**
- Create: `protocol/src/polymer_protocol/oracle_validation.py`
- Test: `protocol/tests/test_oracle_validation.py`

- [ ] **Step 1: Write the failing daemon tests**

Create `protocol/tests/test_oracle_validation.py`:

```python
from __future__ import annotations

from polymer_grammar import OracleDossier, StrengthVector, ValidationTier

from polymer_protocol.oracle import OracleRegistry, oracle_cap
from polymer_protocol.oracle_validation import (
    OracleValidationRecord,
    SpotProbe,
    oracle_validation_pass,
)
from tests.conftest import make_claim, make_plan


def _registry(*pairs) -> OracleRegistry:
    return OracleRegistry(
        dossiers=tuple(OracleDossier(oracle_id=oid, validation_tier=t) for oid, t in pairs)
    )


def _tier(registry, oracle_id):
    return registry.resolve(oracle_id).validation_tier


def test_failing_oracle_is_decayed_in_new_registry():
    reg = _registry(("o1", ValidationTier.GOLD))
    probes = (
        SpotProbe(oracle_id="o1", passed=True),
        SpotProbe(oracle_id="o1", passed=False),  # 1/2 pass -> floor(0.5*4)=2 BENCHMARKED
    )
    reg2, rec = oracle_validation_pass(reg, probes=probes)
    assert _tier(reg2, "o1") == ValidationTier.BENCHMARKED
    assert _tier(reg, "o1") == ValidationTier.GOLD  # original untouched (pure)
    d = rec.decays[0]
    assert (d.oracle_id, d.probes_run, d.probes_passed) == ("o1", 2, 1)
    assert d.tier_before == ValidationTier.GOLD and d.tier_after == ValidationTier.BENCHMARKED


def test_fully_passing_oracle_unchanged_but_recorded():
    reg = _registry(("o1", ValidationTier.ANCHORED))
    reg2, rec = oracle_validation_pass(reg, probes=(SpotProbe(oracle_id="o1", passed=True),))
    assert _tier(reg2, "o1") == ValidationTier.ANCHORED
    d = rec.decays[0]
    assert d.tier_before == d.tier_after == ValidationTier.ANCHORED


def test_oracle_with_no_probes_is_untouched_and_not_recorded():
    reg = _registry(("o1", ValidationTier.GOLD), ("o2", ValidationTier.GOLD))
    reg2, rec = oracle_validation_pass(reg, probes=(SpotProbe(oracle_id="o1", passed=False),))
    assert _tier(reg2, "o2") == ValidationTier.GOLD
    assert [d.oracle_id for d in rec.decays] == ["o1"]


def test_probe_for_unknown_oracle_is_recorded_not_applied():
    reg = _registry(("o1", ValidationTier.GOLD))
    reg2, rec = oracle_validation_pass(
        reg, probes=(SpotProbe(oracle_id="ghost", passed=False),)
    )
    assert rec.unknown_oracle_ids == ("ghost",)
    assert rec.decays == ()
    assert reg2 is reg  # nothing in the registry changed -> same object


def test_pass_is_deterministic_and_sorted():
    reg = _registry(("b", ValidationTier.GOLD), ("a", ValidationTier.GOLD))
    probes = (SpotProbe(oracle_id="b", passed=False), SpotProbe(oracle_id="a", passed=False))
    r1, rec1 = oracle_validation_pass(reg, probes=probes)
    r2, rec2 = oracle_validation_pass(reg, probes=probes)
    assert rec1 == rec2
    assert [d.oracle_id for d in rec1.decays] == ["a", "b"]  # sorted


def test_decayed_registry_tightens_oracle_cap_end_to_end():
    # The headline property: a decayed registry makes oracle_cap bite harder through the #2 seam.
    strong = StrengthVector(magnitude=0.9, uncertainty=0.2, evidence_against_null=0.9,
                            severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    claim = make_claim("c", plan=make_plan(0.01, 0.05, oracle_ref="o1"), strength=strong)
    reg = _registry(("o1", ValidationTier.GOLD))
    before = oracle_cap(claim, reg)
    assert before == strong  # GOLD caps nothing
    reg2, _ = oracle_validation_pass(reg, probes=(SpotProbe(oracle_id="o1", passed=False),))  # 0% -> UNVALIDATED
    after = oracle_cap(claim, reg2)
    assert after.magnitude < before.magnitude        # goodness axis capped down
    assert after.uncertainty > before.uncertainty    # reverse-polarity floored up (F2)


def test_empty_probes_returns_same_registry():
    reg = _registry(("o1", ValidationTier.GOLD))
    reg2, rec = oracle_validation_pass(reg, probes=())
    assert reg2 is reg
    assert rec == OracleValidationRecord()
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd protocol && uv run pytest tests/test_oracle_validation.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.oracle_validation'`.

- [ ] **Step 3: Create `oracle_validation.py`**

Create `protocol/src/polymer_protocol/oracle_validation.py`:

```python
"""ORACLE-VALIDATION daemon (#5b) — decay a failing oracle's ValidationTier from known-answer SPOT
probes, tightening the #2 oracle_cap seam on the next cycle.

Pure / deterministic / caller-scheduled (the standing #5 invariant): no clock, no randomness, no
environment read — probe OUTCOMES are arguments (the caller ran the oracle on a known input OUTSIDE the
pure core, like adapters live outside the package). Returns a threaded registry-delta + a record; the
registry is execution-environment state, never in the Corpus. Decay-only: never auto-promotes.
"""
from __future__ import annotations

from polymer_grammar import ValidationTier, decay_tier

from .base import _Model
from .oracle import OracleRegistry


class SpotProbe(_Model):
    """One known-answer probe outcome for an oracle. `label` is optional, for the record/audit."""

    oracle_id: str
    passed: bool
    label: str | None = None


class OracleDecay(_Model):
    oracle_id: str
    probes_run: int
    probes_passed: int
    tier_before: ValidationTier
    tier_after: ValidationTier


class OracleValidationRecord(_Model):
    decays: tuple[OracleDecay, ...] = ()        # one per REGISTRY oracle that had >=1 probe
    unknown_oracle_ids: tuple[str, ...] = ()    # probe oracle_ids absent from the registry (inert)


def oracle_validation_pass(
    registry: OracleRegistry, *, probes: tuple[SpotProbe, ...]
) -> tuple[OracleRegistry, OracleValidationRecord]:
    """Run the SPOT probes against the registry's oracles; decay each probed oracle's tier proportional to
    its pass rate. Returns a NEW registry with decayed dossiers (the input is never mutated) + a record.
    Oracles with no probes pass through unchanged; probes for unknown oracle ids are recorded but inert."""
    run: dict[str, int] = {}
    passed: dict[str, int] = {}
    for p in probes:
        run[p.oracle_id] = run.get(p.oracle_id, 0) + 1
        passed[p.oracle_id] = passed.get(p.oracle_id, 0) + (1 if p.passed else 0)

    known = {d.oracle_id for d in registry.dossiers}
    unknown = tuple(sorted(oid for oid in run if oid not in known))

    decays: list[OracleDecay] = []
    new_dossiers = []
    changed = False
    for d in registry.dossiers:
        if d.oracle_id not in run:
            new_dossiers.append(d)
            continue
        n = run[d.oracle_id]
        ok = passed[d.oracle_id]
        new_tier = decay_tier(d.validation_tier, ok / n)
        decays.append(
            OracleDecay(
                oracle_id=d.oracle_id, probes_run=n, probes_passed=ok,
                tier_before=d.validation_tier, tier_after=new_tier,
            )
        )
        if new_tier != d.validation_tier:
            new_dossiers.append(d.model_copy(update={"validation_tier": new_tier}))
            changed = True
        else:
            new_dossiers.append(d)

    record = OracleValidationRecord(
        decays=tuple(sorted(decays, key=lambda x: x.oracle_id)),
        unknown_oracle_ids=unknown,
    )
    if not changed:
        return registry, record
    return OracleRegistry(dossiers=tuple(new_dossiers)), record
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd protocol && uv run pytest tests/test_oracle_validation.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/oracle_validation.py protocol/tests/test_oracle_validation.py
git commit -m "feat(protocol): oracle_validation_pass — SPOT-probe tier decay daemon (#5b)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Protocol — exports + full-suite green

**Files:**
- Modify: `protocol/src/polymer_protocol/__init__.py`

- [ ] **Step 1: Write the failing export test**

Append to `protocol/tests/test_oracle_validation.py`:

```python
def test_oracle_validation_symbols_are_exported_from_package():
    import polymer_protocol as pp

    assert hasattr(pp, "oracle_validation_pass")
    assert hasattr(pp, "SpotProbe")
    assert hasattr(pp, "OracleDecay")
    assert hasattr(pp, "OracleValidationRecord")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd protocol && uv run pytest tests/test_oracle_validation.py::test_oracle_validation_symbols_are_exported_from_package -q`
Expected: FAIL — `AttributeError: module 'polymer_protocol' has no attribute 'oracle_validation_pass'`.

- [ ] **Step 3: Add the imports and `__all__` entries**

In `protocol/src/polymer_protocol/__init__.py`, add an import line next to the other module imports (e.g. after the `from .oracle import ...` line):

```python
from .oracle_validation import OracleDecay, OracleValidationRecord, SpotProbe, oracle_validation_pass
```

And add these four names to the `__all__` list:

```python
    "OracleDecay",
    "OracleValidationRecord",
    "SpotProbe",
    "oracle_validation_pass",
```

- [ ] **Step 4: Run the export test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_oracle_validation.py::test_oracle_validation_symbols_are_exported_from_package -q`
Expected: PASS.

- [ ] **Step 5: Run the full protocol suite + ruff + isolation**

Run: `cd protocol && uv run pytest -q && uv run ruff check src tests`
Expected: all green (existing protocol tests + 8 oracle-validation tests), ruff clean. `tests/test_isolation.py` still passes.

- [ ] **Step 6: Run the full grammar suite (confirm Tasks 1-2 still green)**

Run: `cd grammar && uv run pytest -q`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/__init__.py protocol/tests/test_oracle_validation.py
git commit -m "feat(protocol): export ORACLE-VALIDATION daemon symbols (#5b)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Progress Log

(Update after each task.)

- [ ] Task 1 — grammar F2 reverse-polarity cap fix
- [ ] Task 2 — grammar `decay_tier` helper + export
- [ ] Task 3 — protocol `oracle_validation_pass` daemon
- [ ] Task 4 — exports + full-suite green

## Self-review notes

- **Spec coverage:** F2 fix (tier_ceiling/cap_strength split + uncertainty floor) → Task 1; `decay_tier` proportional/decay-only/stable-fixed-point → Task 2; `SpotProbe`/`OracleDecay`/`OracleValidationRecord`/`oracle_validation_pass` (threaded delta, unknown ids, no-probe untouched, pure, deterministic) → Task 3; end-to-end cap-tightening seam → Task 3 test; exports → Task 4. All spec test bullets map to a named test.
- **Breaking-change handling:** Task 1 updates the 3 existing `test_oracle.py` assertions the F2 fix changes (uncertainty 0.4→1.0 in tier_ceiling; 0.4→0.9 in the INDIRECT cap; the all-empirical monotone test → goodness-only) before implementing — TDD with a behavior change.
- **Fences honored:** decay-only (no promotion); verifier-authority not touched; F2 scoped to the cap (`dominates`/`licensed` unchanged); no `run_cycle` wiring; probes carry boolean outcomes.
- **Type consistency:** `decay_tier(tier, pass_rate) -> ValidationTier`; `SpotProbe(oracle_id, passed, label=None)`; `OracleDecay(oracle_id, probes_run, probes_passed, tier_before, tier_after)`; `OracleValidationRecord(decays, unknown_oracle_ids)`; `oracle_validation_pass(registry, *, probes) -> (OracleRegistry, OracleValidationRecord)` — identical across plan, spec, tests.
- **`int()` vs `math.floor`:** `int(pr * MAX_TIER_RANK)` truncates toward zero = floor for the non-negative clamped arg; avoids adding an `import math` to `oracle.py`.
