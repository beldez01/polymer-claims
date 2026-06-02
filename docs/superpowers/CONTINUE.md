# ⟳ Polymer Claims — RESUME HERE

> This file is surfaced automatically by a SessionStart hook so a fresh-context session
> knows exactly where the v1.3 grammar build stands and how to continue. **Keep it current:
> update the "Current state" + "Next" lines at each phase boundary.**

## Current state (as of 2026-06-01)

Building the **v1.3 grammar** in `grammar/` (package `polymer_grammar`), kept isolated from
the frozen v1.2 IR in `v1.2/formalclaim/`. **6 of 8 layer phases done; Phase 7 (protocol-imposed
fields) underway — requirement #4 (online-FDR ledger) shipped. 160 tests, green.**

- ✅ Phase 1 — foundation: L0 sum-typed leaf, status lifecycle, 6-axis Pareto strength, pattern registry, claim skeleton + deep immutability
- ✅ Phase 2 — L1: molecular Proposition + defeasible Equivalence (identity = licensed equivalence, never a hash)
- ✅ Phase 3 — L2: licensing bridge ((σ,M) satisfaction, severe-test|replication route, required rival_set_closure)
- ✅ Phase 4 — typed causal roles (derived/un-authorable adjustment set; Table-2 guard) + Dimension units algebra
- ✅ Phase 5 — L3: VAF defeat graph (`defeat.py`) + Duhem blame-sets (`blame.py`). Strength-mediated effective defeat (attack defeats unless target `≥`-dominates source); PTIME grounded extension over the SINGLE effective-defeat relation; opt-in `derived_rebut_edges` from L1 `incompatible_with`; L2 failed-satisfaction → `undermine` adapter; additive `equivalence.grounded_in` path replacing the LICENSED-only "IN" stub; `aggregate_blame` set algebra (intersection→robustly-blamed / difference→PENDING `duhem_underdetermined`). Merge `1cb0b88`. Spec `specs/2026-06-01-L3-defeat-and-blame-spec.md`, plan `plans/2026-06-01-L3-defeat-and-blame.md`.
- ✅ Phase 7 (#4 of 6) — online-FDR ledger (`fdr.py`). Corpus-level immutable IR entity controlling false-discovery rate over an open-ended test stream via **LOND** (`α_t = target·γ_t·(D_{t-1}+1)`, `γ_j = (6/π²)/j²`). `FDRTest`/`FDRLedger` frozen models; `process_test`/`process_stream` (append-only) + `is_discovery` query. Standalone — grammar computes the allocation, evaluator supplies p-values; no `Claim` coupling. Merge `f41375b`. Spec `specs/2026-06-01-fdr-ledger-spec.md`, plan `plans/2026-06-01-fdr-ledger.md`. (Protocol requirement #6 `reinterpret` was done in L3.)
- ✅ Phase 6 — L4: AGM/TMS belief revision (`revision.py`). Belief-BASE AGM with `Cn` = L1 `entails`-neighborhood closure, inconsistency = `incompatible_with`. **Partial** entrenchment from StrengthVector (severity, evidence_against_null) + Status tier (`INCOMPARABLE` first-class). `restore_consistency` = Hansson consolidation: entrenchment-guided incision, robust/underdetermined spread + conservative consistent core (the locus of partial-entrenchment ambiguity). `expand`/`contract`/`revise` (Levi identity, success-privileged). **Edge hygiene**: every retracting op drops authored defeat edges incident to a retracted claim (no zombie-attack via grounded_extension's endpoint injection). Status recompute reuses Phase-5 `grounded_extension`. AGM postulates (success/inclusion/vacuity/consistency/extensionality) tested; base-contraction non-recovery documented, not faked. Merge `55096fd`. Spec `specs/2026-06-01-L4-revision-spec.md`, plan `plans/2026-06-01-L4-revision.md`.

## ▶ NEXT: more Phase-7 protocol fields, OR the subject-slot gap, OR Phase 8 (evaluator)

Phase 7 (protocol-imposed fields, unified spec §5) is **partially done**: #4 (online-FDR ledger) ✅ + #6 (`reinterpret` edge, in L3) ✅. **Remaining §5 requirements** (each additive, no foundational change — pick one for the next phase or bundle a coherent subset): (1) `generated_by` + `search_cardinality` provenance (a `Provenance` object on Claim — additive, clean); (3) `hazard_class` + governance/access-scope (a `Governance` object on Claim; activates the dormant `unreproducible_by_governance` status — additive, clean, load-bearing for TET2/TCGA); (2) oracle credibility-qualification object — **blocked**: binds to `operations`, which v1.3 dropped → belongs with the Phase-8 evaluator; (5) `representation_revision` meta-tier — conceptually heavy (claims about the IR itself), its own phase.

**Strong alternative the controller recommended (user chose FDR first):** the **`subject` slot** — a polymorphic `Claim.subject` (gene/variant/region/cohort/ontology-term). Biggest fidelity hole (ingestion probe: 47/47 v1.2 claims homeless); foundational; unblocks faithful v1.2→v1.3 ingest.

**Then Phase 8 = the evaluator** (runs the grammar), then the **protocol runtime** (8-stage flywheel + 3 daemons) + the deferred 3D topology viewer + the [[platform vision]] (users deploy agents on their own compute to elaborate the claims universe).

**Carry-forward follow-ups (open):** auxiliary assumptions as first-class blame/undercut/retraction nodes (all 47 v1.2 claims carry `external_assumptions`); vector-valued `Leaf` (the other ingestion gap); n-ary `incompatible_with` + conjunctive `entails` (would make L4 contraction's entrenchment choice bite); bounded defeat in-degree cap; named-audience VAF value-orderings; per-pattern stratified FDR + PPV-floor (the other two parts of §4); LORD++ upgrade. Same rhythm always: brainstorm forks → phase spec → plan → subagent-driven.

## How to resume (the established rhythm)

1. Read memory **`project_polymer_claims_knowledge_protocol`** (full phase history + follow-ups).
2. Read the **unified spec**: `docs/superpowers/specs/2026-05-31-unified-claim-foundations-spec.md`
   (+ the HTML schema overview / spatial map alongside it).
3. Brainstorm only the genuine forks (2–3 questions max), write a **phase spec** →
   `docs/superpowers/specs/`, then a **plan** (writing-plans skill) → `docs/superpowers/plans/`.
4. Execute **subagent-driven** (superpowers:subagent-driven-development): fresh implementer +
   spec-compliance review + code-quality review per task; final whole-package review (Opus);
   then merge to `main` (no-ff), verify tests on merged result, delete the branch.
5. **Update the plan's Progress Log after every task**, and this file + memory at phase end.

## Invariants / working agreements (don't relearn these)

- `grammar/` must NEVER import `polymer_formalclaim` — enforced by `grammar/tests/test_isolation.py`.
- All models subclass `_Model` (frozen, `extra="forbid"`). **Collections are tuples** (deep
  immutability + hashability for content-addressing). No `dict`/`list` fields on models.
- New cross-cutting fields land **additive/optional** (`X | None = None`) with a
  *present-only-when-Y* validator, mirroring `conclusion`/`licensing`/`roles`. Hard "required"
  gates are deferred to a later tightening phase.
- Tests: `cd grammar && uv run pytest -q` (+ `uv run ruff check src tests`). TDD: failing test first.
- Momentum over exhaustive questions; merge to `main` locally (commits are NOT pushed to origin).
- Subagent connection-drops happen — work is usually already committed; verify + finish controller-side.

## Open follow-ups (tracked, none blocking)

- Reconcile `CausalRoles.adjustment_set` with `Pattern.adjustment_role` (free-str placeholder).
- Hard `LICENSED ⇒ licensing` + `conclusion required` tightening phase (will flip back-compat tests).
- UCUM↔Dimension parsing + evaluator dimensional enforcement (Phase 8).
- Optional `min_length=1` guards on role variable names + dimension base names.
- `.pytest_cache`/`.ruff_cache` → root `.gitignore`; document extended `MeasurementBasis`.
- **Ontology (carry-forward, user-flagged important for v1.3):** the small-IR + versioned ontology-bound *domain profile* idea (v1.2 note now at `v1.2/docs/FormalClaim_Domain_Ontology_Note.md`) is load-bearing for v1.3 — absorbed into the unified spec §3.1 (profiles = ontology slot-legality) + §7 (functorial ontology migration). Keep it live when patterns/profiles get built; don't treat it as frozen with v1.2.
- **v1.2 ingestion test (user: "a must") — DONE 2026-06-01.** Probe `grammar/scripts/probe_v12_ingest.py`; findings `docs/superpowers/specs/2026-06-01-v12-ingestion-findings.md`. 47/47 claims build a Claim *skeleton* but only via a PropositionLeaf fallback + fabricated pattern. **Confirmed Phase 5 is well-motivated** (all 47 carry external_assumptions + depends_on). **Two OFF-ROADMAP gaps surfaced:** (1) no `Claim.subject` slot (biggest fidelity hole), (2) vector-valued statistics have no single-`Leaf` home (~29 in corpus). Pattern-inference (raw claim → registry pattern) unsolved. Decide sequencing of these vs Phase 5 next.

## Remaining phases after L3

6 — L4 AGM/TMS revision · 7 — protocol-imposed fields (generated_by, oracle credibility,
hazard/governance, online-FDR, representation_revision tier) · 8 — the evaluator. Then the
**protocol runtime** (8-stage flywheel + 3 daemons), then the deferred **3D topology viewer**.
