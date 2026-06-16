# #5b ORACLE-VALIDATION daemon — design spec

> **Status:** approved design, 2026-06-04. Second slice of sub-project #5 (the daemons + loop-economics).
> Roadmap: `docs/superpowers/roadmaps/2026-06-04-sub5-daemons-roadmap.md`. Builds on the COMPLETE protocol
> spine (#1–#4b) + #5a DRIFT. Rhythm: this spec → plan (writing-plans) → subagent-driven build → merge no-ff → memory.

## What this builds

The **ORACLE-VALIDATION daemon**: a pure, caller-scheduled pass that runs known-answer **SPOT probes**
against the oracles in an `OracleRegistry` and **decays** a failing oracle's `ValidationTier` down the
ladder. Because the #2 `oracle_cap` seam (already wired into `verify_stage`) caps a licensed claim's
empirical strength by its weakest oracle's tier, a decayed registry — passed into the next cycle's
`run_cycle(..., oracles=...)` — automatically tightens the cap on every claim that oracle underwrites.
This is the standing "an oracle that starts failing weakens everything it underwrites" property deferred
from #2.

The slice also folds in the latent **F2** audit finding: the #2 oracle cap `meet`s the reverse-polarity
`uncertainty` axis the wrong way (a weak apparatus currently makes a claim look *less* uncertain). The
code confirms `uncertainty` is genuinely reverse-polarity — `belief.py:32` reads
`kappa = KAPPA_MIN + (KAPPA_MAX - KAPPA_MIN) * (1.0 - s.uncertainty)`, so a high `uncertainty` field →
low concentration → more posterior spread → genuinely weaker. The fix floors `uncertainty` *up* under a
weak tier instead of capping it down.

## Resolved forks (from the brainstorm)

- **O1 — proportional to pass rate** (not one-rung): the pass rate determines the tier an oracle has
  *earned*, capped by where it already is.
- **O2 — threaded registry-delta**: the pass returns a new `OracleRegistry` with decayed dossiers; the
  caller threads it across cycles (the SelectionLedger / #5a discipline). NOT recompute-from-history.
- **F2 scope — fix only the oracle cap**: floor `uncertainty` up to `1 − ceiling`; leave the parallel
  `dominates`/`licensed` polarity question to a dedicated strength-semantics pass (out of scope, noted).

## The seams (already in the codebase)

- **`ValidationTier`** ladder (`grammar/oracle.py`): `UNVALIDATED<INDIRECT<BENCHMARKED<ANCHORED<GOLD`,
  ranked by `_TIER_RANK` {0,1,2,3,4}.
- **`tier_ceiling(tier)` / `cap_strength(strength, tier)`** (`grammar/oracle.py`): the per-axis empirical
  ceiling and the `meet`-based cap. `_EMPIRICAL_AXES = (magnitude, uncertainty, evidence_against_null,
  world_contact)`; `_TIER_CEILING = {UNVALIDATED:0.0, INDIRECT:0.4, BENCHMARKED:0.6, ANCHORED:0.85,
  GOLD:1.0}`. Theory axes (`severity`, `explanatory_virtue`) stay 1.0 (uncapped).
- **`OracleDossier`** (`grammar/oracle.py`): `{oracle_id, validation_tier, applicability_domain, anchor,
  relative_uncertainty}`, frozen.
- **`OracleRegistry`** (`protocol/oracle.py`): `{dossiers: tuple[OracleDossier, ...]}` + `.resolve(id)`,
  passed into `run_cycle`, NOT persisted in the Corpus. `oracle_cap(claim, registry)` writes a claim's
  capped strength via `weakest_tier` of its referenced oracles.

## Component 1 — grammar `grammar/oracle.py`

### 1a. `decay_tier` (the proportional rule)

```python
MAX_TIER_RANK = max(_TIER_RANK.values())  # 4
_RANK_TO_TIER = {rank: tier for tier, rank in _TIER_RANK.items()}

def decay_tier(tier: ValidationTier, pass_rate: float) -> ValidationTier:
    """The tier a `pass_rate` earns, capped by the current tier (DECAY-ONLY, never promotes).
    `target_rank = floor(clamp(pass_rate,0,1) * MAX_TIER_RANK)`; `new_rank = min(current, target)`.
    Proportional + stable fixed point (a 90%-passing oracle settles at ANCHORED and stays);
    monotone non-increasing; parameter-free."""
    pr = 0.0 if pass_rate < 0.0 else (1.0 if pass_rate > 1.0 else pass_rate)
    target_rank = int(math.floor(pr * MAX_TIER_RANK))
    new_rank = min(_TIER_RANK[tier], target_rank)
    return _RANK_TO_TIER[new_rank]
```

Worked values (MAX_TIER_RANK=4): pr=1.0 → target 4 (no cap); pr=0.9 → floor(3.6)=3 (ANCHORED); pr=0.7 →
floor(2.8)=2 (BENCHMARKED); pr=0.5 → 2; pr=0.25 → floor(1.0)=1 (INDIRECT); pr=0.0 → 0 (UNVALIDATED). The
`min(current, target)` makes it decay-only: a GOLD oracle at pr=0.9 → ANCHORED; re-running at pr=0.9 →
`min(3, 3)` = ANCHORED (idempotent, no death-spiral). An already-UNVALIDATED oracle stays UNVALIDATED.

### 1b. F2 fix — reverse-polarity `uncertainty` in the cap

Split the empirical axes so the cap treats `uncertainty` as reverse-polarity:

```python
_GOODNESS_EMPIRICAL_AXES = ("magnitude", "evidence_against_null", "world_contact")  # capped DOWN to c

def tier_ceiling(tier: ValidationTier) -> StrengthVector:
    """Per-axis ceiling for the goodness empirical axes (capped down to c); uncertainty and the theory
    axes are left at 1.0 here (uncertainty is handled as a reverse-polarity FLOOR in cap_strength)."""
    c = _TIER_CEILING[tier]
    return StrengthVector(**{ax: (c if ax in _GOODNESS_EMPIRICAL_AXES else 1.0) for ax in AXES})

def cap_strength(strength: StrengthVector | None, tier: ValidationTier) -> StrengthVector | None:
    """Goodness empirical axes meet the tier ceiling (componentwise min); `uncertainty` is floored UP to
    (1 - c) — reverse polarity, a weak apparatus makes a claim MORE uncertain, not less. Theory axes
    (severity, explanatory_virtue) uncapped. None in -> None out."""
    if strength is None:
        return None
    c = _TIER_CEILING[tier]
    capped = strength.meet(tier_ceiling(tier))  # caps the 3 goodness axes down; uncertainty/theory no-op
    return capped.model_copy(update={"uncertainty": max(strength.uncertainty, 1.0 - c)})
```

GOLD (c=1.0): uncertainty floored to `max(u, 0.0)` = unchanged; goodness axes capped to 1.0 = unchanged →
whole cap is a no-op (correct). UNVALIDATED (c=0.0): uncertainty floored to `max(u, 1.0)` = 1.0 (maximally
uncertain); goodness axes capped to 0.0. The `_EMPIRICAL_AXES` constant is replaced by
`_GOODNESS_EMPIRICAL_AXES`; remove the now-unused `_EMPIRICAL_AXES` (grep for other readers — only the
oracle tests reference it).

**Out of scope (noted):** `dominates`/`licensed`/`meet`/`join` in `strength.py` still treat `uncertainty`
as higher-is-better. That is a real but separate inconsistency with a large blast radius (the Pareto order
+ licensing gate + many strength tests); it is NOT fixed here. The cap fix has zero live interaction with
dominance today (capped strength only lands on terminal LICENSED claims, never re-read by SELECT).

## Component 2 — protocol `protocol/src/polymer_protocol/oracle_validation.py` (new module)

Sibling to `drift.py`. Imports `OracleRegistry` from `.oracle`, tier types + `decay_tier` from
`polymer_grammar`, `_Model` from `.base`.

```python
class SpotProbe(_Model):
    """One known-answer probe outcome. The caller ran the oracle on a known input OUTSIDE the pure core
    (oracles live outside the package, like adapters) and recorded pass/fail. label is for the record."""
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
    decays: tuple[OracleDecay, ...] = ()          # one per REGISTRY oracle that had >=1 probe
    unknown_oracle_ids: tuple[str, ...] = ()      # probe oracle_ids absent from the registry (inert)

def oracle_validation_pass(
    registry: OracleRegistry, *, probes: tuple[SpotProbe, ...]
) -> tuple[OracleRegistry, OracleValidationRecord]:
    ...
```

Behavior:
1. Group probes by `oracle_id`: per oracle, `run = count`, `passed = count(p.passed)`, `pass_rate = passed/run`.
2. For each dossier in the registry that HAS probes: `new_tier = decay_tier(dossier.validation_tier, pass_rate)`;
   record an `OracleDecay(oracle_id, run, passed, tier_before=old, tier_after=new_tier)` (recorded even when
   unchanged, for audit). Rebuild the dossier with `model_copy(update={"validation_tier": new_tier})` only
   if it changed.
3. Probe `oracle_id`s with no matching dossier → collect into `unknown_oracle_ids` (sorted, unique); they
   cannot decay anything.
4. Registry oracles with no probes pass through unchanged (no evidence → no decay).
5. Return `(registry', OracleValidationRecord(decays=<sorted by oracle_id>, unknown_oracle_ids=<sorted>))`.
   `registry'` is a NEW `OracleRegistry`; if nothing changed, return the input registry object.

Pure / deterministic: no clock, no randomness, no environment read; probe outcomes are arguments. Sorted
iteration for determinism. The original registry is never mutated (frozen models; `model_copy` produces
new dossiers).

## Data flow

`oracle_validation_pass` is a standalone pure function. The caller (eventually #5d loop-economics) runs it
periodically and threads `registry'` into the next `run_cycle(..., oracles=registry')`. The existing
`oracle_cap` in `verify_stage` then reads the decayed tiers and caps dependent claims harder — **no new
`run_cycle` wiring this slice**. This mirrors #5a: detect/produce-state here, schedule + apply in #5d.

## Scope fences (explicit non-goals)

- **Decay-only.** The daemon never auto-promotes a tier. An oracle that recovers (probes pass again) stops
  decaying but does NOT climb back — re-earning a tier requires a fresh dossier (real re-validation). Out
  of scope.
- **Verifier-authority decay DEFERRED.** Only the oracle `ValidationTier` is decayed. Verifier authority
  (the air-gapped `verify()` adapters) is a separate concept; not touched here.
- **F2 scoped to the cap.** `dominates`/`licensed` polarity unchanged (separate pass).
- **No `run_cycle` wiring.** When to probe + how to thread the registry is #5d.
- **Probes carry their boolean outcome.** The daemon does NOT execute oracles (that needs real adapters,
  outside the pure core); it consumes recorded pass/fail.

## Invariants preserved

- One-way isolation: `oracle_validation.py` imports `polymer_grammar` + `.base` + `.oracle`; grammar never
  imports protocol. The grammar additions (`decay_tier`, F2 cap fix) import nothing new.
- Corpus stays **4 collections**. The registry is execution-environment state (threaded), never in the Corpus.
- All new models frozen + tuples. Pure / deterministic / synchronous; everything time-like (probe outcomes)
  passed in.
- Exports: add `decay_tier` (+ `MAX_TIER_RANK` if useful) to `grammar/__init__.py`; add `SpotProbe`,
  `OracleDecay`, `OracleValidationRecord`, `oracle_validation_pass` to `protocol/__init__.py`.

## Testing

**Grammar — F2 cap fix (`grammar/tests/` oracle test file):**
- `cap_strength(s, UNVALIDATED)`: `uncertainty == 1.0`; the 3 goodness axes == 0.0; severity & explanatory_virtue unchanged.
- `cap_strength(s, GOLD)`: returns `s` unchanged (whole cap a no-op).
- `cap_strength(s, INDIRECT)` (c=0.4): goodness axes `min(·, 0.4)`; `uncertainty == max(s.uncertainty, 0.6)`.
- A claim with low `uncertainty` (precise) under a weak tier comes out MORE uncertain, not less (the F2 regression pin).
- `cap_strength(None, tier) is None`.
- Update any existing oracle-cap test that asserted the old (capped-down) uncertainty.

**Grammar — `decay_tier`:**
- pr=1.0 → unchanged; pr=0.0 → UNVALIDATED; pr=0.9 from GOLD → ANCHORED; pr=0.5 from GOLD → BENCHMARKED.
- Monotone/decay-only: `decay_tier(tier, pr)` rank ≤ input rank for all pr∈[0,1]; never promotes (pr=1.0 from INDIRECT stays INDIRECT, not GOLD).
- Stable fixed point: `decay_tier(decay_tier(GOLD, 0.9), 0.9) == decay_tier(GOLD, 0.9)` (ANCHORED, idempotent).
- Clamp: pr<0 → UNVALIDATED; pr>1 → unchanged. UNVALIDATED stays UNVALIDATED at any pr.

**Protocol — `oracle_validation_pass`:**
- An oracle failing probes (pr<1) → its dossier in `registry'` has the decayed tier; `OracleDecay` recorded with right counts.
- An oracle passing all probes (pr=1.0) → unchanged; recorded with `tier_before==tier_after`.
- A registry oracle with no probes → untouched, not in `decays`.
- A probe naming an oracle absent from the registry → in `unknown_oracle_ids`, decays nothing.
- Original registry not mutated; deterministic (same inputs → equal `registry'` + record); when nothing changes, returns the input registry object.
- **End-to-end seam:** build a claim + registry where the oracle is GOLD; `oracle_cap` gives strength X; run `oracle_validation_pass` with failing probes; `oracle_cap` on `registry'` gives a strictly tighter (lower goodness / higher uncertainty) strength — pins that the daemon's output bites through the #2 seam.

## Files

- Modify: `grammar/src/polymer_grammar/oracle.py` (`decay_tier`, `_RANK_TO_TIER`, `MAX_TIER_RANK`, F2 cap fix, `_GOODNESS_EMPIRICAL_AXES`)
- Modify: `grammar/src/polymer_grammar/__init__.py` (export `decay_tier`)
- Test:   the grammar oracle test file (F2 + `decay_tier`)
- Create: `protocol/src/polymer_protocol/oracle_validation.py`
- Modify: `protocol/src/polymer_protocol/__init__.py` (4 exports)
- Test:   `protocol/tests/test_oracle_validation.py`
