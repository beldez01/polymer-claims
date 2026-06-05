# Semantics Finalization — Design

**Date:** 2026-06-05
**Status:** Approved (three decisions locked via direct user selection)
**Scope:** The last open semantics questions before the public-deploy polish gate. Two
small, separable changes: a grammar-level axis rename, and a one-block reorder in the
protocol cycle. No new epistemic machinery.

---

## Motivation

Three latent semantics questions remained after the protocol runtime was declared complete
(`7e1d5c9`). Each was the user's to decide; all three are now locked:

1. **`strength.py` polarity** — the `uncertainty` axis is reverse-polarity inside an
   otherwise all-higher-is-better Pareto lattice, so the lattice and the oracle cap (F2)
   disagree about which direction is "stronger."
2. **Credit timing** — when does a claim earn ledger/selection credit?
3. **Accumulating belief (F4)** — is it wired into the live loop?

---

## Decision 1 — Rename `uncertainty` → `certainty` (grammar)

**Locked choice:** rename the `StrengthVector` axis so the whole lattice is uniformly
higher-is-better. No special-casing in `dominates`/`meet`/`join`.

### The bug being fixed

`StrengthVector.dominates` is `all(self.ax >= other.ax for ax in AXES)`; `meet`=min,
`join`=max — every axis treated as higher-is-better. But `uncertainty` is honestly named:
higher uncertainty is *weaker*. Today a more-uncertain claim can "dominate" a less-uncertain
one, and `licensed()` lets a high-uncertainty candidate clear a low-uncertainty threshold.
Meanwhile the F2 oracle fix already treats uncertainty as higher-is-worse (it floors it
*up* as a penalty). The lattice and the oracle cap disagree.

### The change

Rename the axis to `certainty` with the natural polarity (higher = better). The lattice
math is then correct with **zero special-casing**, and several call sites simplify:

- **`grammar/src/polymer_grammar/strength.py`**
  - `AXES`: `"uncertainty"` → `"certainty"`.
  - `StrengthVector.certainty: float = Field(ge=0.0, le=1.0)`.
  - `meet`/`join`/`dominates`/`comparable`/`licensed` are **unchanged** (they already do
    the right thing once the axis is higher-is-better).
  - Update the module/method docstrings (drop any "reverse-polarity" notes).

- **`grammar/src/polymer_grammar/oracle.py`** — the F2 special-case *disappears*:
  - Add `"certainty"` to `_GOODNESS_EMPIRICAL_AXES` (it is now a normal apparatus-bounded
    goodness axis — a weak apparatus *lowers* certainty).
  - `cap_strength` collapses to `return strength.meet(tier_ceiling(tier))` — delete the
    `model_copy(update={"uncertainty": max(...)})` floor-up line entirely.
  - `tier_ceiling` no longer special-cases the axis; `certainty` is capped down to `c`
    alongside `magnitude`/`evidence_against_null`/`world_contact`.
  - Update the docstrings (the "reverse-polarity / floored UP" prose is now wrong).

- **`protocol/src/polymer_protocol/belief.py`** — `prior_belief`:
  - `kappa = KAPPA_MIN + (KAPPA_MAX - KAPPA_MIN) * (1.0 - s.uncertainty)` becomes
    `... * s.certainty` (algebraically identical, since `certainty == 1 - uncertainty`).

- **All `StrengthVector` construction sites (grammar + protocol, src + tests)** — flip the
  value to preserve meaning: `uncertainty=x` → `certainty=1 - x`. A vector that meant
  "low uncertainty = 0.2" (good) becomes `certainty=0.8` (good). **This inversion is
  mandatory** — a pure rename that kept the numeric value would silently invert the
  intended strength of every fixture and threshold.

### Explicitly OUT of scope (do NOT rename)

Two unrelated fields share the substring `uncertainty` and carry a *different* meaning
(physical measurement error, not lattice strength). They are left untouched:

- **`QuantityLeaf.uncertainty`** (`grammar/src/polymer_grammar/leaf.py:34`) — a `value ±
  uncertainty` error bar on a physical quantity. Standard scientific meaning. Keep.
- **`OracleDossier.relative_uncertainty`** (`grammar/src/polymer_grammar/oracle.py:121`) —
  oracle measurement-error propagation, deferred per spec §8. Keep.

Implementers must disambiguate: only `StrengthVector`'s axis is renamed.

### Verification

- `grammar/tests/test_strength.py` asserts the corrected polarity: a lower-certainty
  candidate does **not** dominate a higher-certainty one; `meet` takes the **min**
  certainty (weakest link), `join` the max.
- `grammar/tests/test_oracle.py` asserts `cap_strength` lowers `certainty` to the tier
  ceiling (capped down, not floored up).
- Full grammar + protocol suites green; `ruff` clean; isolation tests still pass.

---

## Decision 2 — Credit on survival (protocol)

**Locked choice:** a claim earns ledger/selection credit only if it is **still LICENSED
after INTEGRATE**, not merely at the moment it licenses in VERIFY.

### The bug being fixed

In `cycle.py`, the credit block runs **before** integrate:

```
121  corpus = verify_stage(...)          # sets LICENSED / REJECTED
125  after = corpus.by_id()              # POST-VERIFY snapshot
127  outcomes = (... after[cid].status == LICENSED ...)
137  led = update_ledger(led, outcomes)  # credit allocated here
139  corpus, skipped = integrate(...)    # can RETRACT a licensed claim (AGM contest)
```

So a claim licensed at VERIFY but demoted by INTEGRATE's consistency contest has already
been credited as a success. That is the "licensed at VERIFY" semantics the user rejected.

### The change

Move the snapshot + credit block (`after = corpus.by_id()` through
`led = update_ledger(led, outcomes)`, current lines 125–137) to **after** the `integrate`
call. `after` then reads the **post-INTEGRATE** corpus, so:

- a claim retracted LICENSED→REJECTED → `rejected=True` → recorded as a failure;
- a claim demoted LICENSED→PENDING (newcomer yields, not rejected) → `licensed=False,
  rejected=False` → no success credit (and the proposing operator's grounding rate drops,
  since `n_high_eig` increments without `n_grounded`);
- a claim still LICENSED after integrate → `licensed=True` → success credit, as intended.

`executed_ids`, `eig_by_id` (from `selection.decisions`), and `operator_of` are all
unaffected by integrate, so only the *status read* moves. `CycleResult.ledger` still
returns `led`.

### Verification

- New `protocol/tests/test_cycle.py` case: a corpus engineered so a claim licenses in
  VERIFY but is retracted by INTEGRATE's AGM contest earns **zero** success credit in the
  returned `ledger` (and a failure if it lands REJECTED).
- Existing cycle tests stay green (claims that survive integrate are credited exactly as
  before).

---

## Decision 3 — Activate accumulating belief (already wired; close the loop)

**Locked choice:** belief should accumulate across cycles.

### Finding

This is **already wired**. `select.py:49` computes selection EIG via
`expected_information_gain(accumulated_belief(claim, ledger))`, and the loop-economics
scheduler (`economics.py:106`) does the same. `prior_belief` is called *only* inside
`accumulated_belief`. The threaded `SelectionLedger` carries per-claim
successes/failures from `update_ledger` into the next cycle's `accumulated_belief`. The
"F4 dormant" note was stale.

### The change

No new wiring. Decision 2 is what makes the *content* of the accumulation correct: once
credit is allocated on survival, `accumulated_belief` compounds on survival-credit rather
than on transient post-VERIFY licensing. The only additive work is a test that pins this
behavior so it cannot silently regress.

### Verification

- New `protocol/tests/test_cycle.py` (or `test_belief.py`) case: run two cycles over a
  claim that licenses and survives; assert its `accumulated_belief` in cycle 2 is shifted
  toward success relative to cycle 1's `prior_belief` (alpha increased by the recorded
  successes).
- **Belief-neutrality re-test:** the daemons / generation still do not move belief except
  through `run_cycle`'s credit path — re-assert through `run_cycle`, consistent with the
  project's standing rule that belief-neutrality is tested through the real loop.

---

## Sequencing

Two branches, each finished and merged no-ff **locally** (never pushed — `beldez01` is
flagged; all publish is user-gated):

1. **`refactor/certainty-axis`** (Decision 1) — grammar first, since the protocol changes
   build on the renamed axis. Lands grammar + protocol construction-site flips together
   (the rename is not green until every call site is updated).
2. **`feat/credit-on-survival`** (Decisions 2 + 3) — protocol-only; depends on branch 1
   being merged.

After both land: the comprehensive architect + security audit + linter pass (the
pre-public-deploy polish gate), then — separately and user-gated — the 3D viewer slice and
the `pip` packaging harness.

## Non-goals

- No change to the `Corpus` 4-collection invariant, the grammar→protocol isolation
  boundary, or any daemon's pure `Corpus→(Corpus, record)` shape.
- No renaming of the two measurement-`uncertainty` fields.
- No packaging/publishing in this slice.
