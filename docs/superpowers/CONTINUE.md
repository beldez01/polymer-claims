# ⟳ Polymer Claims — RESUME HERE

> This file is surfaced automatically by a SessionStart hook so a fresh-context session
> knows exactly where the v1.3 grammar build stands and how to continue. **Keep it current:
> update the "Current state" + "Next" lines at each phase boundary.**

## Current state (as of 2026-06-01)

Building the **v1.3 grammar** in `grammar/` (package `polymer_grammar`), kept isolated from
the live v1.2 IR in `formalclaim/`. **4 of 8 grammar phases merged to `main`. 87 tests, green.**

- ✅ Phase 1 — foundation: L0 sum-typed leaf, status lifecycle, 6-axis Pareto strength, pattern registry, claim skeleton + deep immutability
- ✅ Phase 2 — L1: molecular Proposition + defeasible Equivalence (identity = licensed equivalence, never a hash)
- ✅ Phase 3 — L2: licensing bridge ((σ,M) satisfaction, severe-test|replication route, required rival_set_closure)
- ✅ Phase 4 — typed causal roles (derived/un-authorable adjustment set; Table-2 guard) + Dimension units algebra

## ▶ NEXT: Phase 5 — L3 VAF defeat graph + Duhem blame-sets

Value-Based Argumentation Framework over claims: typed defeat edges
(`undermine`/`undercut`/`rebut`/`reclassify`/`reinterpret` + `evidence_for`), grounded-extension
membership (which replaces the L1 `status==LICENSED` stand-in for equivalence "IN"-ness), and
Duhem–Quine blame surfaced as a *set* of minimal blame-assignments (intersection=robustly-IN /
union=possibly-IN / difference→PENDING `duhem_underdetermined`). See unified spec §3.5.
**Also resolve the carried-forward question:** where *failed* licensing attempts
(refuted/undetermined satisfactions) live — flagged from L2.

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
- **v1.2 ingestion test (user: "a must"):** ingest the frozen v1.2 corpus (`v1.2/corpus/domains/**/claims/*.json`) into the v1.3 grammar as a preliminary *sensitivity* test — what maps, what the grammar can't yet represent. Likely the next concrete task before/alongside Phase 5.

## Remaining phases after L3

6 — L4 AGM/TMS revision · 7 — protocol-imposed fields (generated_by, oracle credibility,
hazard/governance, online-FDR, representation_revision tier) · 8 — the evaluator. Then the
**protocol runtime** (8-stage flywheel + 3 daemons), then the deferred **3D topology viewer**.
