# Literature-Shared-Cause Gate + Incubation/Ranking (Phase D, slice 2) — Design Spec

> **Date:** 2026-06-19 · **Status:** approved (design), pre-implementation
> **Scope:** pure-code grammar + protocol + minimal viewer + tests (no external data; fully CI-gated)
> **Roadmap:** autonomous-hypothesis-loop §5a (the *literature*-shared-cause leak) + §4 incubation ·
> north-star §E (common-cause DAG — this is its first concrete edge) · §2(B)/(C) e-value/FDR honesty core
> **Predecessor machinery:** Phase D slice 1 (`grammar/commitment.py`, `grammar/fdr.py`
> `register_test`/`resolve_test`, `protocol/register.py`, `protocol/verify.py` match-gate); §2E
> `independence_tier` (`grammar/licensing.py` `MaterializationContext.dimnames_hash` /
> `independence_tier_of`); SELECT ranking (`protocol/select.py`).

## 1. Goal

Close the **§5a *literature*-shared-cause leak** and tie it to honest multi-hypothesis incubation/ranking.

Slice 1 closed the *multiplicity* failure mode of §5a (an agent fishing across many hypotheses and pushing
only winners to verify — now every registered hypothesis pays its e-LOND slot). This slice closes the
**other, orthogonal** §5a failure mode: **shared cause between the hypothesis source and the test data.**

> The leak (roadmap §5a, verbatim): "generate the hypothesis from the research landscape, then test on the
> betas" is clean *only if* the landscape claim was not itself derived from an overlapping cohort. The
> IDH→hypermethylation signal was discovered in overlapping AML cohorts (Figueroa 2010; TCGA 2013), so an
> agent reasoning "IDH should drive hypermethylation" from a literature *born of this same data* is doing
> confirmation, not a held-out severe test. **Track the hypothesis's provenance, not just its phrasing.**

The fix is a deterministic, byte-mechanical gate: a hypothesis records **which cohorts its motivating prior
was established on**; at verify, if those overlap the test cohort, the license is honestly annotated
**CONFIRMATORY** and its *severity* strength axis is capped. The **same** pre-data signal feeds SELECT
ranking, so genuinely-severe (held-out) hypotheses rank above confirmatory ones — which is what makes it
honest for an incubation loop to register and pursue only the ranked top-k under the α-budget.

**The unifying invariant: ranking is data-blind.** The severity/shared-cause signal is computed from the
hypothesis's *prior provenance* and the candidate's *evaluation_plan target cohort* — never from the
held-out test betas. A data-blind prioritization that does not peek at the outcome cannot inflate the
corpus false-license rate `q`; that is precisely why registering only the pursued top-k (rather than every
generated candidate) preserves the slice-1 multiplicity guarantee.

## 2. Decisions (locked)

| Decision | Resolution |
|---|---|
| Enforcement on overlap | **Cap severity + annotate CONFIRMATORY** (A1). License still mints; honest, visible, not discarded. An optional `strict_shared_cause` flag withholds; **off by default**. |
| Which strength axis is capped | **`severity` only.** That is the precise axis the shared-cause leak corrupts. `evidence_against_null` (the e-value), `world_contact`, and the others are untouched. |
| Where the prior-cohort provenance lives | On `Provenance` (`prior_cohorts: tuple[str, ...] = ()`) — the natural home for "where the claim came from". |
| Cohort-identity namespace | Reuse `MaterializationContext.dimnames_hash` strings (the same cohort identity §2E already keys off). Matching is **exact-string set intersection**. |
| Where the tier annotation lives | On `Licensing` (`severity_provenance: SeverityProvenance \| None = None`), mirroring `independence_tier`. |
| Trust model for `prior_cohorts` | **Operator/agent-asserted** (same as adapter independence today). The *gate* is byte-mechanical; *population* is asserted. |
| Incubation register-on-budget | **In scope** — a helper that registers (slice-1 `register_test`) only the SELECT-pursued top-k that fit the α-budget. |
| Viewer | **In scope, minimal** — `severity_provenance` passthrough on `TopologyExport` + node, mirroring `independence_tier`; minimal display. |
| Opt-in signal | **Presence of a non-empty `prior_cohorts`** on a claim. No `prior_cohorts` anywhere → byte-identical to today. |

## 3. Grammar changes (pure, numpy-free, stdlib only)

### 3.1 `provenance.py` — one additive field

`Provenance.prior_cohorts: tuple[str, ...] = ()` — cohort identities (the `dimnames_hash` namespace) that
the hypothesis's motivating prior literature/evidence was established on. Default `()` ⇒ no shared-cause
information ⇒ no gate, no tier, byte-identical. Frozen-model/tuple, content-addressable like every other
collection field. No present-only-when-Y validator needed (empty is the inert default).

### 3.2 `shared_cause.py` (new) — the check + the tier

- `class SeverityProvenance(StrEnum)`: `HELD_OUT = "held_out"`, `CONFIRMATORY = "confirmatory"`.
- `shared_cause_overlap(prior_cohorts: tuple[str, ...], test_cohorts: tuple[str, ...]) -> bool` —
  `bool(set(prior_cohorts) & set(test_cohorts))`. Pure, total, stdlib only.
- `severity_provenance_of(prior_cohorts: tuple[str, ...], test_cohorts: tuple[str, ...]) -> SeverityProvenance | None`
  — `None` if `prior_cohorts` is empty (inert); else `CONFIRMATORY` if overlap, `HELD_OUT` otherwise.
- `CONFIRMATORY_SEVERITY_CEILING: float` — a named module constant (defensible default; tunable). When a
  license is CONFIRMATORY, the `severity` axis is set to `min(current, CONFIRMATORY_SEVERITY_CEILING)`.
  Value chosen in Task 1 to sit at/below the "asserted, un-severe" band of the existing `severity` axis
  range; it is a single constant, documented as tunable, not a magic literal scattered in code.
- `cap_severity_for_confirmatory(strength: StrengthVector) -> StrengthVector` — returns a copy with
  `severity = min(strength.severity, CONFIRMATORY_SEVERITY_CEILING)`, all other axes untouched. (If the
  current value is already ≤ ceiling, returns an equal vector.)

`shared_cause.py` imports only the strength/enum types it needs from within `grammar/` — no
`polymer_formalclaim`, no numpy (isolation preserved).

### 3.3 `licensing.py` — one additive field

`Licensing.severity_provenance: SeverityProvenance | None = None` — additive, defaults `None` (byte-identical
when off). Set by the protocol verify stage (§4.1). Parallels `independence_tier`.

## 4. Protocol changes (pure, numpy-free)

### 4.1 The gate in `verify_stage` (`verify.py`)

Additive block, after the existing satisfaction/grounded/permitted/e-OK licensing conditions, for each
claim about to be licensed (or just licensed) whose `provenance.prior_cohorts` is non-empty:

1. `test_cohorts = tuple(s.materialization.dimnames_hash for s in <claim's satisfactions> if dimnames_hash)`.
2. `tier = severity_provenance_of(prior_cohorts, test_cohorts)`.
3. Stamp `licensing.severity_provenance = tier`.
4. If `tier == CONFIRMATORY`: replace the claim's earned/asserted strength with
   `cap_severity_for_confirmatory(strength)`.
5. If `strict_shared_cause` (opt-in flag, default off) **and** `tier == CONFIRMATORY`: withhold the license
   (PENDING) instead of minting it. (Default off ⇒ this branch never runs ⇒ byte-identical.)

**Byte-identity:** a claim with empty/absent `prior_cohorts` skips the whole block — `severity_provenance`
stays `None`, strength is untouched. The full existing suite must stay green unchanged.

**Interaction with slice 1:** independent and composable. The slice-1 match-gate
(`HYPOTHESIS_ALTERED`)/resolution runs first on the e-LOND ledger; the shared-cause block runs on the
strength/licensing annotation. A claim can be registered (slice 1), resolve its e-value, license, and then
be tier-annotated/severity-capped here — no ordering conflict, no shared state mutated twice.

### 4.2 Severity-aware, data-blind ranking (`select.py`)

A new `severity_factor(corpus, claim) -> float` multiplied into `density` alongside the existing
`credit_factor` (`select.py:86`):
- Predict the would-be tier **pre-execution**: derive the candidate's *target* cohort identity from its
  `evaluation_plan` data handle(s) (the same plan→data-handle path the BH cardinality already reads), then
  `severity_provenance_of(claim.provenance.prior_cohorts, target_cohorts)`.
- `CONFIRMATORY` → factor `CONFIRMATORY_RANK_PENALTY` (< 1, named constant); `HELD_OUT`/`None` → `1.0`.
- Default (no `prior_cohorts`, or target cohort not derivable from the plan) → `1.0` ⇒ byte-identical
  ordering. The factor is data-blind: it reads provenance + plan identity, **never** executes or reads the
  test betas.

This rides the existing density/Pareto machinery; it does not add a parallel ranking scheme.

### 4.3 Budget-aware incubation commit (`register.py`, additive)

A new helper alongside `register_hypotheses`:
`register_selected(corpus, selection_record, *, k: int | None = None) -> Corpus` — given a SELECT
`SelectionRecord` (ranked, selected candidates) register (slice-1 `register_test` via the existing
`register_hypotheses` per-claim path) only the **selected** claims, in rank order, optionally truncated to
top-`k`. Unselected/incubated-but-not-pursued candidates are **not** registered and **not** charged.

This is honest because §4.2 ranking is data-blind: the prioritization that chose the top-k did not look at
the outcome, so the unpursued candidates were never "tested" in the selective-inference sense. The slice-1
no-refund/strict accounting is unchanged for the candidates that *are* registered.

## 5. Viewer (minimal)

- `TopologyExport` node carries `severity_provenance` (passthrough, mirroring `independence_tier`).
- Minimal node display surfacing CONFIRMATORY vs HELD_OUT (a small badge / field), so a CONFIRMATORY
  license is never misread as a severe one. `tsc` + build stay clean; sample-timeline contract version
  bumped if the export shape changes (additive optional field).

## 6. What this does NOT change (invariants)

- **Corpus = exactly 4 collections.** No new collection; `prior_cohorts` rides `Provenance`,
  `severity_provenance` rides `Licensing`.
- **grammar/protocol stay pure + numpy-free.** `shared_cause.py` is stdlib only; isolation tests stay green
  (`grammar/` never imports `polymer_formalclaim`; `protocol/` → `grammar/` one-way).
- **Additive/opt-in, byte-identical when off.** Every new field defaults inert; a corpus with no
  `prior_cohorts` anywhere is byte-identical to today (golden equality test). The existing grammar + protocol
  suites stay green unchanged.
- **One e-test per claim lifetime.** Unchanged — this slice annotates licensing/strength and ranks; it does
  not add or duplicate e-tests. `strict_shared_cause` (off by default) only *withholds*, never adds a test.
- **§2E independence accounting is orthogonal and preserved.** `independence_tier` (REPRODUCED/REPLICATED)
  answers "did agreeing legs share a common cause?"; `severity_provenance` answers "did the hypothesis
  source share a common cause with the test data?". Distinct axes, both kept visible (§5b requirement).

## 7. Success criteria (what the tests must prove)

1. **Overlap → CONFIRMATORY + severity cap:** a licensed claim whose `prior_cohorts` overlaps its test
   `dimnames_hash` is stamped `CONFIRMATORY` and its `severity` axis is `min(prior, ceiling)`; all other
   strength axes are byte-unchanged.
2. **No overlap → HELD_OUT, no cap:** non-overlapping `prior_cohorts` → `HELD_OUT`, strength untouched.
3. **Strict mode:** with `strict_shared_cause=True`, a CONFIRMATORY claim is withheld (PENDING), not
   licensed; default off reproduces criterion 1.
4. **Ranking demotes confirmatory:** given two otherwise-equal candidates, the one whose plan target cohort
   overlaps its `prior_cohorts` ranks strictly below the held-out one.
5. **Ranking is data-blind:** the severity factor is computed without any execution/adapter call / beta
   access (asserted by construction + a test that the factor is identical whether or not the dataset is
   materialized).
6. **Budget-aware top-k:** `register_selected` charges e-LOND slots for the pursued top-k only; incubated
   non-selected candidates have **no** ledger entry.
7. **Byte-identical when off:** a `run_cycle` (and a SELECT pass) with no `prior_cohorts` anywhere is
   identical to today — existing suites green + a golden equality test on the resulting corpus/ledger/order.
8. **Invariants:** Corpus still exactly 4 collections; grammar isolation + numpy-free import preserved;
   §2E `independence_tier` behavior unchanged.

## 8. Out of scope (later slices)

- **Fuzzy literature→cohort resolution** — matching a DOI/citation to the cohort(s) it was built on.
  `prior_cohorts` is supplied as cohort-identity strings; resolving them from free-text citations is future.
- **The full common-cause DAG (North Star §E)** — shared inputs/methods/assumptions as graph edges, with
  probabilistic independence as a *derived* (Reichenbach screening-off) claim. This slice builds the
  **first edge** (derivation-cohort overlap); the DAG is built when a second edge type actually appears.
- **Byte-derived / credential-backed `prior_cohorts`** — population is operator-asserted here, exactly like
  adapter `implementation_hash` today; hardening it is the same deferred class of work.
- **Live-node / autonomous-agent wiring** of the incubation loop (mass-generate → rank → register top-k →
  pull → execute) — this slice ships the mechanism + tests, demonstrated via the offline stages.
- **Fractional / weighted overlap scores** — overlap is boolean here; a graded shared-cause score is future
  (and is the natural §E generalization).

## 9. Open implementation details (for the plan)

- `CONFIRMATORY_SEVERITY_CEILING` and `CONFIRMATORY_RANK_PENALTY` exact values — pick defensible defaults in
  Task 1 against the real `severity` axis range and the `density` scale; document as tunable constants.
- Exact path from `evaluation_plan` to the *target* cohort identity in SELECT (§4.2) — confirm the data
  handle exposes a `dimnames_hash`-comparable identity pre-execution; if a plan has no derivable target
  cohort, the factor must default to `1.0` (inert).
- Whether the verify severity-cap rewrites `earned` strength, asserted strength, or both — confirm against
  `verify.py`'s strength source of truth so the cap lands on the value the license actually carries.
- Viewer contract-version bump + sample-timeline regeneration if the export shape changes.
