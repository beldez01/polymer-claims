# ⟳ Polymer Claims — RESUME HERE

> This file is surfaced automatically by a SessionStart hook so a fresh-context session
> knows exactly where the v1.3 grammar build stands and how to continue. **Keep it current:
> update the "Current state" + "Next" lines at each phase boundary.**

## Current state (as of 2026-06-01)

Building the **v1.3 grammar** in `grammar/` (package `polymer_grammar`), kept isolated from
the frozen v1.2 IR in `v1.2/formalclaim/`. **5 of 8 grammar phases merged to `main`. 117 tests, green.**

- ✅ Phase 1 — foundation: L0 sum-typed leaf, status lifecycle, 6-axis Pareto strength, pattern registry, claim skeleton + deep immutability
- ✅ Phase 2 — L1: molecular Proposition + defeasible Equivalence (identity = licensed equivalence, never a hash)
- ✅ Phase 3 — L2: licensing bridge ((σ,M) satisfaction, severe-test|replication route, required rival_set_closure)
- ✅ Phase 4 — typed causal roles (derived/un-authorable adjustment set; Table-2 guard) + Dimension units algebra
- ✅ Phase 5 — L3: VAF defeat graph (`defeat.py`) + Duhem blame-sets (`blame.py`). Strength-mediated effective defeat (attack defeats unless target `≥`-dominates source); PTIME grounded extension over the SINGLE effective-defeat relation; opt-in `derived_rebut_edges` from L1 `incompatible_with`; L2 failed-satisfaction → `undermine` adapter; additive `equivalence.grounded_in` path replacing the LICENSED-only "IN" stub; `aggregate_blame` set algebra (intersection→robustly-blamed / difference→PENDING `duhem_underdetermined`). Merge `1cb0b88`. Spec `specs/2026-06-01-L3-defeat-and-blame-spec.md`, plan `plans/2026-06-01-L3-defeat-and-blame.md`.

## ▶ NEXT: Phase 6 — L4 AGM/TMS belief revision

AGM (Alchourrón–Gärdenfors–Makinson 1985) + TMS (Doyle 1979) revision over the corpus with an
entrenchment ordering keyed to evidence_class + severity. Status recompute under a *fixed* defeat
graph is PTIME-monotone (the Phase-5 grounded extension); graph *edits* (add/retract claims & edges)
are the non-monotonic AGM ops to model here. See unified spec §3.5 + §3 (L4 row). Follow the same
rhythm (brainstorm forks → phase spec → plan → subagent-driven). Phase-5 follow-ups to fold in when
relevant: auxiliary assumptions as first-class blame/undercut nodes (the ingestion probe showed all 47
claims carry `external_assumptions`); bounded defeat in-degree write-time cap; named-audience VAF
value-orderings beyond the single Pareto order.

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
