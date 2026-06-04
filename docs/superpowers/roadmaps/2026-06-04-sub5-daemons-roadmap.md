# Sub-project #5 — the daemons + loop-economics: decomposition roadmap

> **Status:** roadmap, 2026-06-04. NOT an implementation plan — it decomposes #5 into buildable slices
> with build order, the seam each hooks into, and the open design forks to resolve in each slice's
> **brainstorm**. Each slice follows the standard rhythm: `superpowers:brainstorming` (2–3 questions →
> spec → plan) → `superpowers:subagent-driven-development` → merge no-ff → memory. Builds on the
> COMPLETE protocol spine (#1), oracle dossier (#2), SELECT (#3a/#3b), GENERATE (#4a + #4b-1/2/3).

## What #5 is

The first four sub-projects built the **on-demand** runtime: `run_cycle` is invoked, does one
REPRESENT→GENERATE→SELECT→EXECUTE→VERIFY→INTEGRATE pass, returns. #5 adds the **standing** processes that
keep the corpus honest over time + the economics that schedule them:

1. **DRIFT** — re-examine LICENSED claims as the world's materialization context moves (data/API versions).
2. **ORACLE-VALIDATION** — the standing D2 daemon: probe oracles with known-answer cases; decay a failing
   oracle's tier so its strength-cap tightens and dependent claims weaken.
3. **REPRESENTATION RED-TEAM** — adversarially attack the corpus's *representation* (where the grammar
   mis-frames a claim); pairs with the grammar `representation_revision` meta-tier.
4. **loop-economics** — schedule `run_cycle` passes + daemon passes against a finite compute budget.

## The purity stance (decided up front, applies to every slice)

The runtime is pure/deterministic/synchronous — **no threads, no clock, no `Date`/random** (the standing
invariant). So a "daemon" is **NOT** a background thread; it is a **pure `Corpus → (Corpus, record)`
transform** (like a stage), invoked on a schedule the **caller drives**. "Standing" = the caller (or
loop-economics) runs the pass periodically. Everything time-like (the "current" context, the probe sets,
the budget) is **passed in**, never read from the environment. This keeps determinism + the one-way
grammar isolation intact, exactly like `run_cycle`.

## Build order + slices

### #5a — DRIFT daemon (build FIRST — most self-contained, clean seam, fully pure)

**Seam:** every LICENSED claim carries `Licensing.satisfactions[*].materialization` =
`MaterializationContext{id, api_version, data_version}` — the exact context it was licensed under. #2's
`ApplicabilityDomain` (`in_domain(domain, subject)`) is the companion seam.

**Pass:** `drift_pass(corpus, *, current: MaterializationContext, oracles?=) -> (corpus, DriftRecord)`.
For each LICENSED claim, compare its minted materialization against the passed-in `current` context; a
claim whose `api_version`/`data_version` no longer matches (the world moved) is **re-opened** — status →
PENDING with a new `PendingReason` (candidate: `materialization_drifted`, a small grammar addition — see
fork D2) — so SELECT can re-pursue it. Pure, deterministic; the "current" context is an argument.

**Open forks for the brainstorm:** (D1) re-open to PENDING vs merely *flag* in the record without
mutating status (cap-not-bar spirit) — recommend re-PENDING only when the claim still has its
`evaluation_plan` (re-executable), else flag; (D2) does this need a new `PendingReason`
(`materialization_drifted`) — a tiny grammar change, the FIRST grammar touch since #4b-1 — or reuse
`UNTESTED`? (D3) version-equality vs a richer "compatible-version" predicate (semver-ish) — start with
equality (YAGNI). (D4) does DRIFT also consult oracle tier movement, or is that strictly #5b's job?
Recommend: DRIFT = materialization only; oracle movement = #5b.

### #5b — ORACLE-VALIDATION daemon (build SECOND — reuses #2 tier/cap machinery)

**Seam:** #2's `OracleDossier` + `ValidationTier` ladder (`_TIER_RANK`, `tier_ceiling`, `weakest_tier`)
and the `OracleRegistry`. The cap already flows into VERIFY's LICENSED seam.

**Pass:** `oracle_validation_pass(registry, *, probes) -> (registry', OracleValidationRecord)`. Run the
passed-in **SPOT probes** (known-answer cases) against each oracle; on failure, **decay** the oracle's
effective `ValidationTier` down the ladder (+ optional verifier-authority decay). The lowered tier
tightens `tier_ceiling`, so the next cycle's VERIFY caps dependent claims' empirical strength harder —
the standing "an oracle that starts failing weakens everything it underwrites" property (deferred from #2).

**Open forks:** (O1) decay one rung per failed probe vs proportional to failure rate; (O2) is decay
**persistent** (mutate the registry, threaded like the ledger) or recomputed each pass from a probe
history — recommend a threaded registry-delta, mirroring #3b's `SelectionLedger`; (O3) verifier-authority
decay as a separate axis or folded into tier; (O4) probes as injected data (like adapters) — yes, keep
them passed-in/pure.

### grammar `representation_revision` meta-tier (PREREQUISITE for #5c — last Phase-7 item, §5 #5)

The one remaining grammar gap. A meta-tier where **schema/representation changes are themselves claims**
(the corpus can revise how it represents, under the same licensing discipline). This is grammar work
(its own brainstorm→spec→plan in `grammar/`), and it **unblocks** the red-team daemon's revision lane.
Sequence it before #5c, or build #5c's non-revision parts first (fork below).

### #5c — REPRESENTATION RED-TEAM daemon (build AFTER the meta-tier, or a stub first)

**Seam:** the grammar `representation_revision` meta-tier (above) + the GENERATE bus (a red-team is a
specialized adversarial proposer/critic). **Pass:** `red_team_pass(corpus, ...) -> (corpus, record)` that
hunts representational failures (a claim whose pattern/subject/leaves mis-frame what it asserts) and
proposes a representation-revision claim. Partly grammar-blocked.

**Open forks:** (R1) full daemon (needs the meta-tier) vs a non-revision **stub** that only *flags*
suspected mis-representations into a record (buildable now, no grammar change); (R2) is the red-team an
injected `GenerationAdapter` (reusing #4b-3's seam + `compile_untrusted`) rather than a new mechanism —
**strongly recommend yes** (it's exactly the intelligent-operator pattern; the red-team is an adversarial
adapter behind the bus).

### #5d — loop-economics (build LAST — schedules the cycle + the daemons)

**Seam:** #3a's `CostModel`/cost vector + #3b/#4b-2's `SelectionLedger` credit. **Pass:** a pure scheduler
`next_action(state, *, budget) -> Action` that, given the corpus + ledgers + a passed-in compute budget,
decides whether to run a `run_cycle` pass or which daemon pass to run next (DRIFT/ORACLE/RED-TEAM), and
returns the chosen action for the caller to execute. Pure planning; the caller executes + loops. Ties the
whole runtime into one budget-governed loop — the closest thing to "the daemons run."

**Open forks:** (E1) round-robin vs value-ranked scheduling (reuse the EIG/credit machinery to prioritize
the highest-expected-value pass); (E2) does loop-economics OWN the loop (a `run_until(budget)` driver) or
just RECOMMEND the next action (caller loops) — recommend recommend-only (purity); (E3) per-daemon budget
shares vs a single shared budget the scheduler allocates.

## Recommended sequence

**#5a DRIFT → #5b ORACLE-VALIDATION → grammar `representation_revision` meta-tier → #5c RED-TEAM →
#5d loop-economics.** #5a/#5b are pure and self-contained (start here); #5c is gated on the grammar
meta-tier (or do its flag-only stub earlier); #5d schedules everything so it comes last. Each is its own
brainstorm→spec→plan→subagent-driven build, merged no-ff, memory updated — same rhythm that landed
#1–#4b.

## Cross-cutting invariants (hold for every #5 slice)

- Pure/deterministic/synchronous: no threads/clock/`Date`/random; everything time-like is passed in.
- Daemon = `Corpus→(Corpus, record)` (or registry/ledger delta) transform, caller-scheduled.
- One-way isolation (`grammar` never imports `protocol`); `Corpus` stays 4 collections (daemon state is
  threaded like `SelectionLedger`, NOT a 5th collection) — unless a slice's brainstorm explicitly decides
  a grammar field is warranted (e.g. #5a's `materialization_drifted` PendingReason, #5c's meta-tier).
- Reuse before inventing: DRIFT reuses #2 contexts, ORACLE reuses #2 tiers, RED-TEAM reuses #4b-3's
  adapter seam, loop-economics reuses #3a cost + #3b credit.

## Latent items to fold in along the way (already tracked)

- **F2** (audit): #2 oracle cap `meet`s the reverse-polarity `uncertainty` axis the wrong way —
  unreachable today; **#5b ORACLE-VALIDATION is the natural place to fix it** (it's already in the tier/cap
  code). Resolve it there.
- **F4** (audit): per-claim accumulating belief lightly exercised — DRIFT re-opening licensed claims may
  finally exercise the multi-outcome accumulation path; revisit the `SETTLED_CONCENTRATION` guard then.
