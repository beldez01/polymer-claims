# Semantics Finalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the `StrengthVector.uncertainty` axis to `certainty` (uniform higher-is-better lattice), and allocate ledger credit on survival (move `update_ledger` after `integrate`), pinning that the already-wired `accumulated_belief` compounds on survival-credit.

**Architecture:** Two independent, sequentially-merged branches. Branch A is a grammar-level rename that flows into every `StrengthVector` construction site across both packages. Branch B is a one-block reorder in `cycle.py` plus tests. Both pure, both merged no-ff **locally only** (never pushed).

**Tech Stack:** Python 3, Pydantic v2 (frozen models), `uv`-managed per-package envs, `pytest`, `ruff`. Spec: `docs/superpowers/specs/2026-06-05-semantics-finalization-design.md`.

**Test/lint commands:**
- Grammar: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q` and `uv run ruff check src tests`
- Protocol: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q` and `uv run ruff check src tests`
- Use ABSOLUTE paths — the Bash tool persists cwd between calls.

---

## Branch A — `refactor/certainty-axis`

> Create the branch first: `cd /Users/zbb2/Desktop/polymer-claims && git checkout -b refactor/certainty-axis`

### Task A1: Rename the axis in grammar (src + grammar tests)

**Files:**
- Modify: `grammar/src/polymer_grammar/strength.py`
- Modify: `grammar/src/polymer_grammar/oracle.py`
- Modify (tests): `grammar/tests/test_strength.py`, `grammar/tests/test_oracle.py`, `grammar/tests/test_claim.py`, `grammar/tests/test_leaf.py`, `grammar/tests/test_revision.py`, `grammar/tests/test_defeat.py`
- **Do NOT touch:** `grammar/src/polymer_grammar/leaf.py` (`QuantityLeaf.uncertainty` is a physical error bar) and `OracleDossier.relative_uncertainty` in `oracle.py:121`.

**Disambiguation rule (critical):** only the `StrengthVector` axis is renamed. `QuantityLeaf.uncertainty` and `OracleDossier.relative_uncertainty` stay exactly as they are. When flipping construction sites, only flip `StrengthVector(...)` / strength-threshold constructions.

**Construction-site transformation rule:** every place that builds a `StrengthVector` with `uncertainty=x` becomes `certainty=1 - x` (meaning-preserving inversion). A bare `uncertainty=0.2` (low uncertainty = good) becomes `certainty=0.8` (high certainty = good). Find them with:
`cd /Users/zbb2/Desktop/polymer-claims && grep -rn "uncertainty" grammar/src grammar/tests` and inspect each: StrengthVector axis → flip; QuantityLeaf/OracleDossier → leave.

- [ ] **Step 1: Write the corrected-polarity assertions in `test_strength.py` (failing)**

Add/adjust tests asserting the new higher-is-better polarity for `certainty`:

```python
def test_lower_certainty_does_not_dominate_higher():
    base = dict(magnitude=0.5, evidence_against_null=0.5, severity=0.5,
                world_contact=0.5, explanatory_virtue=0.5)
    low = StrengthVector(certainty=0.2, **base)
    high = StrengthVector(certainty=0.8, **base)
    assert high.dominates(low)
    assert not low.dominates(high)

def test_meet_takes_min_certainty_join_takes_max():
    base = dict(magnitude=0.5, evidence_against_null=0.5, severity=0.5,
                world_contact=0.5, explanatory_virtue=0.5)
    a = StrengthVector(certainty=0.3, **base)
    b = StrengthVector(certainty=0.9, **base)
    assert a.meet(b).certainty == 0.3      # weakest link
    assert a.join(b).certainty == 0.9

def test_licensed_requires_certainty_at_or_above_threshold():
    base = dict(magnitude=0.9, evidence_against_null=0.9, severity=0.9,
                world_contact=0.9, explanatory_virtue=0.9)
    threshold = StrengthVector(certainty=0.7, **base)
    assert licensed(StrengthVector(certainty=0.8, **base), threshold)
    assert not licensed(StrengthVector(certainty=0.6, **base), threshold)
```

- [ ] **Step 2: Run to confirm they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_strength.py -q`
Expected: FAIL/ERROR (`StrengthVector` has no field `certainty`).

- [ ] **Step 3: Rename the axis in `strength.py`**

In `grammar/src/polymer_grammar/strength.py`:
- `AXES`: change `"uncertainty"` to `"certainty"`.
- In `StrengthVector`: replace `uncertainty: float = Field(ge=0.0, le=1.0)` with `certainty: float = Field(ge=0.0, le=1.0)`.
- Leave `meet`/`join`/`dominates`/`comparable`/`licensed` bodies unchanged.
- Update the module docstring: drop the implicit "all axes" caveat is fine; just make sure no prose claims a reverse-polarity axis.

- [ ] **Step 4: Collapse the F2 special-case in `oracle.py`**

In `grammar/src/polymer_grammar/oracle.py`:
- `_GOODNESS_EMPIRICAL_AXES`: add `"certainty"` →
  `_GOODNESS_EMPIRICAL_AXES = ("magnitude", "evidence_against_null", "world_contact", "certainty")`
- `cap_strength` body becomes simply:

```python
def cap_strength(
    strength: StrengthVector | None, tier: ValidationTier
) -> StrengthVector | None:
    """`strength` capped by the tier: goodness empirical axes (magnitude,
    evidence_against_null, world_contact, certainty) meet the tier ceiling
    (componentwise min) — a weak apparatus lowers certainty. Theory axes
    (severity, explanatory_virtue) uncapped. None -> None."""
    if strength is None:
        return None
    return strength.meet(tier_ceiling(tier))
```

- Update `tier_ceiling`'s docstring (it now caps `certainty` down to `c` like the other goodness axes; no axis is left at 1.0 except the two theory axes).
- Update the `_GOODNESS_EMPIRICAL_AXES` comment (delete the reverse-polarity prose).
- **Leave `OracleDossier.relative_uncertainty` untouched.**

- [ ] **Step 5: Update `test_oracle.py` cap assertions + flip grammar construction sites**

In `test_oracle.py`, assert `cap_strength` lowers `certainty` to the tier ceiling:

```python
def test_cap_lowers_certainty_to_ceiling():
    s = StrengthVector(magnitude=1.0, certainty=1.0, evidence_against_null=1.0,
                       severity=1.0, world_contact=1.0, explanatory_virtue=1.0)
    capped = cap_strength(s, ValidationTier.INDIRECT)   # ceiling 0.4
    assert capped.certainty == 0.4
    assert capped.magnitude == 0.4
    assert capped.severity == 1.0          # theory axis uncapped
```

Then flip every remaining `StrengthVector(... uncertainty=x ...)` in all grammar test files to `certainty=1 - x` (see transformation rule above). Run the grep, edit each StrengthVector site, leave QuantityLeaf/OracleDossier sites.

- [ ] **Step 6: Run the full grammar suite + ruff + isolation**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q && uv run ruff check src tests`
Expected: ALL PASS, ruff clean. Confirm `tests/test_isolation.py` passes.

- [ ] **Step 7: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims && git add grammar/ && git commit -m "$(cat <<'EOF'
refactor(grammar): rename StrengthVector.uncertainty -> certainty

Uniform higher-is-better Pareto lattice (no special-casing). Collapses the
F2 oracle cap to strength.meet(tier_ceiling) — certainty is now a normal
apparatus-bounded goodness axis. QuantityLeaf.uncertainty and
OracleDossier.relative_uncertainty (physical measurement error) untouched.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task A2: Propagate the rename into protocol (belief.py + protocol construction sites)

**Files:**
- Modify: `protocol/src/polymer_protocol/belief.py`
- Modify (tests + any src building StrengthVector): all protocol files surfaced by the grep — `protocol/tests/test_verify.py`, `test_oracle_validation.py`, `test_select.py`, `test_economics.py`, `test_oracle.py`, `test_belief.py`, `test_represent.py`, `test_cycle.py` (and any src site, though the grep showed only `belief.py` in src).

- [ ] **Step 1: Update `belief.py` `prior_belief`**

In `protocol/src/polymer_protocol/belief.py`, line ~32, replace:

```python
    kappa = KAPPA_MIN + (KAPPA_MAX - KAPPA_MIN) * (1.0 - s.uncertainty)
```

with:

```python
    kappa = KAPPA_MIN + (KAPPA_MAX - KAPPA_MIN) * s.certainty
```

(Algebraically identical, since `certainty == 1 - uncertainty`.) Update the surrounding docstring/comment if it names `uncertainty`.

- [ ] **Step 2: Flip all protocol `StrengthVector` construction sites**

Run: `cd /Users/zbb2/Desktop/polymer-claims && grep -rn "uncertainty" protocol/src protocol/tests`
For each `StrengthVector(... uncertainty=x ...)`, change to `certainty=1 - x`. (All protocol occurrences are the strength axis — there is no `QuantityLeaf`/`OracleDossier` construction in protocol — but verify each line before editing.)

- [ ] **Step 3: Run the full protocol suite + ruff**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q && uv run ruff check src tests`
Expected: ALL PASS, ruff clean. (If a belief/value numeric assertion shifts, it means a construction site was flipped wrong — re-check that site against the `certainty = 1 - x` rule; do not "fix" by changing the assertion unless the old assertion encoded the polarity bug.)

- [ ] **Step 4: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims && git add protocol/ && git commit -m "$(cat <<'EOF'
refactor(protocol): follow grammar certainty rename

belief.prior_belief uses s.certainty directly (== 1 - old uncertainty);
all StrengthVector construction sites flipped certainty = 1 - x to
preserve meaning.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

**After A1 + A2 reviewed:** finish branch A via superpowers:finishing-a-development-branch (merge locally, no-ff, no push).

---

## Branch B — `feat/credit-on-survival`

> After branch A is merged to main: `cd /Users/zbb2/Desktop/polymer-claims && git checkout main && git checkout -b feat/credit-on-survival`

### Task B1: Move credit allocation after integrate + tests

**Files:**
- Modify: `protocol/src/polymer_protocol/cycle.py`
- Test: `protocol/tests/test_cycle.py`

**The change:** in `run_cycle`, the block currently at lines ~125–137 (`after = corpus.by_id()` through `led = update_ledger(led, outcomes)`) runs *before* `integrate` (line ~139). Move it to run *after* the `integrate(...)` call so `after` reads the post-INTEGRATE corpus. Nothing else in the block changes — `executed_ids`, `eig_by_id`, `operator_of` are all integrate-invariant.

- [ ] **Step 1: Write the failing credit-on-survival test**

Build (or reuse an existing helper for) a corpus + adapters where a claim licenses in VERIFY but is retracted by INTEGRATE's AGM consistency contest (an entrenched rival rebuts the newcomer). Assert it earns **no success credit**:

```python
def test_claim_retracted_by_integrate_earns_no_success_credit():
    # ... arrange a corpus where `victim` licenses at VERIFY but integrate
    # retracts it (a more-entrenched rival rebuts the newcomer) ...
    result = run_cycle(corpus, adapters, ctx)
    victim_outcome = result.ledger.outcome("victim")
    # retracted => not credited as a success this cycle
    assert (victim_outcome is None) or (victim_outcome.successes == 0)
```

If constructing a guaranteed integrate-retraction is intricate, model it on the existing
integrate/restore_consistency tests (`test_integrate.py`) for the entrenchment setup, and
reuse the cycle-test harness already in `test_cycle.py`.

- [ ] **Step 2: Run to confirm it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_cycle.py::test_claim_retracted_by_integrate_earns_no_success_credit -q`
Expected: FAIL — under the current pre-integrate ordering the claim is credited at VERIFY.

- [ ] **Step 3: Move the block in `cycle.py`**

Relocate the snapshot + `update_ledger` block to immediately **after** the `integrate(...)` call (after the integrate StageAudit append, before computing `frontier`). The `after = corpus.by_id()` now reads the post-integrate corpus. Update the comment above the block to say the snapshot is post-INTEGRATE so credit reflects survival.

- [ ] **Step 4: Run the new test + full suite**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q`
Expected: the new test PASSES and all existing cycle tests stay green (survivors credited as before).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims && git add protocol/ && git commit -m "$(cat <<'EOF'
feat(protocol): allocate ledger credit on survival, not at VERIFY

Move the outcomes snapshot + update_ledger after integrate so a claim
retracted by INTEGRATE's AGM contest earns no success credit. Since
accumulated_belief is already wired into select/economics, belief now
compounds on survival-credit.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task B2: Pin that accumulated_belief compounds on survival-credit

**Files:**
- Test: `protocol/tests/test_cycle.py` (or `test_belief.py`)

- [ ] **Step 1: Write the belief-compounds test**

```python
def test_accumulated_belief_compounds_on_survival():
    # run a cycle over a claim that licenses AND survives integrate
    result1 = run_cycle(corpus, adapters, ctx)
    survivor = result1.corpus.by_id()["survivor"]
    prior = prior_belief(survivor)
    accumulated = accumulated_belief(survivor, result1.ledger)
    # a recorded success shifts the Beta toward success (alpha up)
    assert accumulated.alpha > prior.alpha
```

Add a companion assertion that a second `run_cycle` threading `ledger=result1.ledger`
further increases `alpha` (belief compounds across cycles).

- [ ] **Step 2: Run it**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_cycle.py -q -k compounds`
Expected: PASS (no production change needed — this pins already-correct behavior post-B1).

- [ ] **Step 3: Belief-neutrality re-assertion**

Confirm (reuse/extend an existing belief-neutrality test) that running the daemons /
generation does **not** move belief except through `run_cycle`'s credit path. Run the full
protocol suite: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q && uv run ruff check src tests`
Expected: ALL PASS, ruff clean.

- [ ] **Step 4: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims && git add protocol/ && git commit -m "$(cat <<'EOF'
test(protocol): pin accumulated_belief compounds on survival-credit

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

**After B1 + B2 reviewed:** finish branch B via superpowers:finishing-a-development-branch (merge locally, no-ff, no push).

---

## Self-Review (plan vs spec)

- **Decision 1 (rename):** Tasks A1+A2 cover strength.py, oracle.py collapse, belief.py, all construction sites, and the two out-of-scope fields are called out in A1. ✓
- **Decision 2 (credit on survival):** Task B1 moves the block + tests the retraction case. ✓
- **Decision 3 (accumulated belief):** Task B2 pins compounding + belief-neutrality; spec notes no new wiring needed. ✓
- **Placeholder scan:** the construction-site flips are a rule + grep, not a placeholder (the exact transformation is given); the integrate-retraction arrangement points at the concrete existing test files to model on. ✓
- **Type/name consistency:** `certainty` used uniformly; `cap_strength`/`tier_ceiling`/`_GOODNESS_EMPIRICAL_AXES` signatures unchanged. ✓
