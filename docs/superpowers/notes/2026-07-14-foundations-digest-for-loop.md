# Foundations digest — for the backlog loop (2026-07-14)

Synthesis of `foundations/{epistemology,compute-boundary,scaled-infrastructure,measurement-foundation,residualism}.md`,
produced to ground the autonomous backlog loop. Quote-anchored; treat measurement-foundation.md as
brainstorm-stage (self-labeled) and compute-boundary.md as softened to a default (2026-07-13).

## Core model
Coherentist machinery (defeat/equivalence graph, AGM revision, sheaf H⁰/H¹) anchored by an L0 empirical
leaf + mandatory recomputation against content-addressed data. **Licensing = epistemic warrant, not
meaning** ("the agreement gate licenses; it does not mean"). Unlicensed → residue (PENDING), never false.
A claim is a typed IR region (refinement type `{x : Assay │ φ(x)}`) over an assay measurement-space; data
is one point. The **e-value** is the evidence atom (betting score, `E[e] ≤ 1`); "no alpha-wealth, no
license." The **gate** = severity (e-LOND `e_t ≥ 1/α_t`) **and** independence (low common-cause overlap).
The corpus = versioned, content-addressed graph of claims + defeat/equivalence edges + FDR ledger.

## Hard invariants
- **Kernel minimality**: "Nothing earns standing except by passing the kernel." Agents propose, recompute verifies.
- **Purity layering**: pure grammar + pure protocol; impure node/umbrella touches data. e-values supplied
  from umbrella. e-LOND/FDR decision in `grammar/…/fdr.py` (pure). Don't move data-touching code below grammar.
- **Air gap**: two legs = trusted ∧ different owner ∧ different `implementation_hash`; agree within tolerance
  or no e-value. "The log cannot be produced by the thing being witnessed."
- **Two strata of independence**: REPLICATED needs distinct `dimnames_hash`, error-independent; multiply legs
  "only when `cohorts_error_independent(...) is not False`." Independence gates whether you may multiply at all.
- **Attested-log floor**: "no Satisfaction licenses anything without an attested log." Leaves bind to fields
  of the logged output, not agent prose. (Backlog §9 confirms this is NOT currently enforced — a HARDEN item.)
- **Compute boundary** (strong default now): Polymer specifies/orchestrates/witnesses/certifies; never hosts
  the computation. Require a *log*, not a recomputation-you-own.
- **e-LOND**: FDR under arbitrary dependence, no correction factor — never substitute BH/BY. `register_test`
  locks `α_t` BEFORE the e-value exists (pre-registration).
- **Determinism**: `betting_evalue` seed-averaged over a fixed seed set → deterministic given data.
- **Never delete**: defeated claims demoted not erased; `retract_tests` tombstones (alpha refund). "What is
  monotone is the audit trail, not the licensed set."
- **"Corpus stays 4"**: the digest notes this exact phrase is NOT in foundations (there "4" = layers/spine).
  In the SDD history it means **exactly 4 Collections in the grammar `Corpus` object** — the operative
  no-schema-drift guard. Keep it.

## Declared-not-enforced gaps (the loop's §2 + §9 targets)
- **Independence** (headline): gate measures overlap of operator-DECLARED factor labels vs a fixed threshold.
  Intended: measured error-correlation ρ → `N_eff = 2/(1+ρ)`. Design the interface to return/store a
  CONTINUOUS ρ, keep `evidence[cid] *= e2` gated on it; model shared inputs/methods/refs as common-cause DAG
  edges (Reichenbach), not a flat label set.
- **Transparency log**: shipped = local, single-signer, inclusion-only; no consistency proofs / external
  witnesses (needs the tabled Rekor backend).
- **WITNESSED**: deferred; named only by `PendingReason`, not a first-class status.
- **Science Claw + Cohort Foundry**: horizon, no code.

## Measurement-theory discipline for every new IR field
Declare (a) Stevens scale type (nominal/ordinal/interval/ratio) and (b) admissible-transformation group
(permutation / monotone / affine ax+b / similarity ax). Licensing precondition: a claim earns standing only
if its criterion is INVARIANT under the scale's admissible transformations (measurement-foundation §3.1 —
built as `invariance_group`/`scale` fields but NEVER read by any evaluator; §9 HARDEN). Don't add meters to
seconds; ordinal-as-interval must fail to type-check; don't silently unify 450K vs EPIC. Don't sheaf-ify prose.

## Implications for the §1 build targets
- **Persistent claim store**: append-only, fully-versioned, content-addressed at every state; tombstone not
  delete; alpha-refund path; each licensing Satisfaction carries a bound attested log; persist
  pre-registration `α_t` state separately from resolution; fast defeat-reachable subgraph queries.
- **Measurement-space registry**: key by scale-type + admissible-transformation-group (itself a licensable
  meta-claim → registry entries are attackable, not fixed config). Ride MAE for the sample/coordinate axis.
  STRUCTURAL maps (liftover, probe harmonization) = functors you ride; BIOLOGICAL maps (methylation→expression)
  = first-class licensable claims, NOT hardcoded infrastructure.
- **Independence-as-ρ**: see gap above.
