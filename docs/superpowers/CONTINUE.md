# ⟳ Polymer Claims — RESUME HERE

> This file is surfaced automatically by a SessionStart hook so a fresh-context session
> knows exactly where the v1.3 grammar build stands and how to continue. **Keep it current:
> update the "Current state" + "Next" lines at each phase boundary.**

## Current state (as of 2026-06-02)

**Grammar** (`grammar/`, `polymer_grammar`) is complete through all 8 phases. **Protocol runtime sub-project #1 (Corpus + assessment spine) is DONE** — new sibling package `polymer_protocol` (`protocol/`), one-way dep on `polymer_grammar` (isolation-tested), builds the frozen `Corpus` + seven pure stages (`represent / canonicalize / safety_gate / commit / execute_ground / verify_stage / integrate`) wired into a deterministic `run_cycle`; EXECUTE reuses the Phase-8 air-gapped `verify()`; GENERATE/SELECT stubbed as open ports. **49 protocol tests green; ruff clean; isolation holds.** Spec `docs/superpowers/specs/2026-06-02-protocol-spine-design.md`, plan `docs/superpowers/plans/2026-06-02-protocol-spine.md`. Merge commit: `c8b7279` (no-ff to main).

Phase 7 (protocol-imposed fields) had #1 (provenance), #3 (governance),
#4 (online-FDR), #6 (reinterpret) + the `Claim.subject` slot done; #2 (oracle) is now UNBLOCKED
by Phase 8 (the `OperationNode.oracle_ref` slot exists), and only #5 (representation_revision
meta-tier) remains. **240 grammar tests, green; ruff clean; isolation holds.**

- ✅ Phase 1 — foundation: L0 sum-typed leaf, status lifecycle, 6-axis Pareto strength, pattern registry, claim skeleton + deep immutability
- ✅ Phase 2 — L1: molecular Proposition + defeasible Equivalence (identity = licensed equivalence, never a hash)
- ✅ Phase 3 — L2: licensing bridge ((σ,M) satisfaction, severe-test|replication route, required rival_set_closure)
- ✅ Phase 4 — typed causal roles (derived/un-authorable adjustment set; Table-2 guard) + Dimension units algebra
- ✅ Phase 5 — L3: VAF defeat graph (`defeat.py`) + Duhem blame-sets (`blame.py`). Strength-mediated effective defeat (attack defeats unless target `≥`-dominates source); PTIME grounded extension over the SINGLE effective-defeat relation; opt-in `derived_rebut_edges` from L1 `incompatible_with`; L2 failed-satisfaction → `undermine` adapter; additive `equivalence.grounded_in` path replacing the LICENSED-only "IN" stub; `aggregate_blame` set algebra (intersection→robustly-blamed / difference→PENDING `duhem_underdetermined`). Merge `1cb0b88`. Spec `specs/2026-06-01-L3-defeat-and-blame-spec.md`, plan `plans/2026-06-01-L3-defeat-and-blame.md`.
- ✅ Phase 7 (#4 of 6) — online-FDR ledger (`fdr.py`). Corpus-level immutable IR entity controlling false-discovery rate over an open-ended test stream via **LOND** (`α_t = target·γ_t·(D_{t-1}+1)`, `γ_j = (6/π²)/j²`). `FDRTest`/`FDRLedger` frozen models; `process_test`/`process_stream` (append-only) + `is_discovery` query. Standalone — grammar computes the allocation, evaluator supplies p-values; no `Claim` coupling. Merge `f41375b`. Spec `specs/2026-06-01-fdr-ledger-spec.md`, plan `plans/2026-06-01-fdr-ledger.md`. (Protocol requirement #6 `reinterpret` was done in L3.)
- ✅ Phase 7 (#1 + #3) — **`Provenance`** (`provenance.py`) + **`Governance`** (`governance.py`), two additive-optional `Claim` fields. Provenance: `GenerationMode` enum + required `search_cardinality≥1` (prices the implicit search for selection-aware correction) + `preregistration_hash` (anti-HARKing hash-lock); `agent_generated⇒agent_id` validator. Governance: `HazardClass`/`AccessScope` enums (claim-level) + `blocks_reproduction` (→ dormant `unreproducible_by_governance` status) + `requires_safety_review` (→ SAFETY-GATE) helpers — grammar represents, protocol decides. Absorbs the largest re-ingest homeless cluster (premises + provenance metadata). Merge `738acfc`. Spec `specs/2026-06-02-provenance-governance-spec.md`, plan `plans/2026-06-02-provenance-governance.md`.
- ✅ Phase 7 (subject slot) — polymorphic **`Claim.subject`** (`subject.py`). 10-variant discriminated union (genomic_region, variant_vrs, s4_object, phenopacket, ontology_term, gene_or_protein, pathway, cohort, literal, composite) faithful to v1.2's SubjectRef, adapted to v1.3 frozen+hashable+forbid (no `dict` fields: canonical_allele dropped, phenopacket inline→JSON string, cohort predicates→`tuple[str,...]`, source_dataset.extra dropped; lists→tuples; literal structured→tuple-of-pairs). Mirrors `leaf.Leaf`; recursive `composite` via `model_rebuild()`. Additive-optional `Claim.subject: Subject | None = None` (back-compat). Closes the 47/47-homeless ingestion gap. Merge `eecf318`. Spec `specs/2026-06-02-subject-slot-spec.md`, plan `plans/2026-06-02-subject-slot.md`.
- ✅ Phase 8 — **the evaluator** (`operations.py` IR + `evaluate.py` runtime). The compiler/runtime split made real: a typed compute-graph IR (`DataHandle`/`NodeRef`/`OperationNode` w/ unbound `oracle_ref` slot → `ComputeGraph` acyclic/unique/resolvable + topo + content_hash → `SatisfactionCriterion` → `EvaluationPlan`), wired as additive-optional `Claim.evaluation_plan`. Runtime: pure adapter-injected `evaluate()` (topo exec, typed-leaf wrap, 3-valued criterion, drift, dimension-equality check; NEVER raises on a node/wrap error) + the **air-gapped `verify()` gate** (≥2 DISTINCT adapter identities or `SelfLicensingError`; mints an L2 `Satisfaction` ONLY on cross-adapter agreement [value-within-tol + verdict] AND SATISFIED — closes the L2 loop, no self-licensing; never assembles Licensing/Status). Two deterministic reference adapters (`IdentityAdapter` sum/len vs `ReferenceAdapter` `statistics.fmean`) give a genuine two-implementation check. Scope fence held: NO real network/R/scipy adapters, NO oracle dossier (slot only), NO full UCUM (equality only), NO Licensing/Status assembly. Merge `<fill>`. Spec `specs/2026-06-02-evaluator-spec.md`, plan `plans/2026-06-02-evaluator.md`. **Open follow-up:** `_check_agreement` compares value+verdict, not `terminal.dimension` (safe today since dimension is driven by the shared `produces` spec — revisit when real adapters land).
- ✅ Phase 6 — L4: AGM/TMS belief revision (`revision.py`). Belief-BASE AGM with `Cn` = L1 `entails`-neighborhood closure, inconsistency = `incompatible_with`. **Partial** entrenchment from StrengthVector (severity, evidence_against_null) + Status tier (`INCOMPARABLE` first-class). `restore_consistency` = Hansson consolidation: entrenchment-guided incision, robust/underdetermined spread + conservative consistent core (the locus of partial-entrenchment ambiguity). `expand`/`contract`/`revise` (Levi identity, success-privileged). **Edge hygiene**: every retracting op drops authored defeat edges incident to a retracted claim (no zombie-attack via grounded_extension's endpoint injection). Status recompute reuses Phase-5 `grounded_extension`. AGM postulates (success/inclusion/vacuity/consistency/extensionality) tested; base-contraction non-recovery documented, not faked. Merge `55096fd`. Spec `specs/2026-06-01-L4-revision-spec.md`, plan `plans/2026-06-01-L4-revision.md`.

## ▶ NEXT: protocol sub-project #2 — the Oracle dossier

**The protocol runtime arc has STARTED.** Sub-project #1 is DONE (see Current state). The 5-sub-project decomposition:
1. **Corpus + the assessment spine** ✅ DONE (merged no-ff to main, commit `c8b7279`).
2. **Oracle dossier** ← NEXT (unified spec §5 #2; binds to the `OperationNode.oracle_ref` slot Phase 8 left; same rhythm: brainstorm forks → spec → plan → subagent-driven).
3. SELECT — the pursuit/value engine (two-axis posterior, EIG, three-axis Pareto, cost model, quality-diversity portfolio + firewalls).
4. GENERATE — the proposer bus (5 operators + representation-revision lane; the open generation port).
5. The 3 daemons (DRIFT, ORACLE-VALIDATION, REPRESENTATION RED-TEAM) + loop-economics.

**Sub-project #1 design (approved, in the spec):** new sibling uv pkg `protocol/` → import pkg `polymer_protocol`, one-way dep on `polymer_grammar` (isolation-tested); **writes ONLY grammar IR** (no new grammar fields, no per-claim wrapper — stage outputs map onto existing fields: equivalence_class→`equivalences` tuple, hazard gate→`governance` predicate, hash-lock→`provenance.preregistration_hash`, status/license→`Claim.status`/`Licensing`, FDR→`fdr_ledger`). `Corpus` = (claims, defeat_edges, equivalences, fdr_ledger), frozen. 7 pure stages `represent/canonicalize/safety_gate/commit/execute_ground/verify_stage/integrate` + `run_cycle`; EXECUTE reuses Phase-8 `verify()` (air-gap); GENERATE+SELECT are stubbed open ports (claims injected exogenously, execute-all-committed). End goal: `pip install polymer-claims` (grammar+protocol+CLI bundled later) → local node → federated claims universe ([[platform vision]]). Deep design source: `~/Desktop/Research/topics/epistemic-claim-foundations/generative-protocol/_FINAL_knowledge_generation_protocol.md`.

- Protocol frontier test: add an integration-depth test where INTEGRATE changes the defeat graph (derived rebut edges / retraction) so the post-INTEGRATE frontier genuinely differs from the head scaffolding — pins that run_cycle emits the tail represent() frontier, not the head. (Needs a conclusion-bearing multi-claim fixture; plan-deferred to integration tests.)
- Protocol follow-ups surfaced by the whole-package review (own them in #3 SELECT): (a) the emitted `frontier` is status-blind — a REJECTED claim can still appear (its attacker's rejection doesn't strip the edge); a downstream consumer must not assume `frontier ⊆ live claims` until the calibrated-posterior/strength feedback lands. (b) the "locked" predicate (`provenance.preregistration_hash` present) is expressed independently in `execute._is_locked/_is_executable`, `commit._is_locked`, and `cycle._locked_ids` — consolidate into one shared helper before commit semantics grow. (c) `Corpus.by_id()` returns a mutable `dict` (cosmetic vs the tuples-only/frozen discipline).
- **Smoke/validity audit 2026-06-02 (8 live `run_cycle` scenarios)** — spine sound (air-gap holds end-to-end incl. same-identity; determinism byte-identical ×5; multi-cycle stable; AGM contest restores consistency; writes-only-IR confirmed). **FIXED on `main` (`78af588`): canonicalize collapsed claims on a degenerate all-absent key** (bare same-pattern skeletons → false `a==b`, even across a defeat pair) — added `_has_discriminating_content` guard. **Still-open #3 follow-ups filed by the audit:** (d) **LICENSED ⊬ FDR-discovery** — `verify_stage` decides licensing without consulting `fdr_ledger`, so a claim can be LICENSED while the corpus error budget doesn't count it a discovery; the selection-aware/cardinality-scaled threshold (#3) must reconcile. (e) **`commit` hash-locks safety-gated claims** (COMMIT runs after SAFETY and doesn't re-check the gate; harmless — EXECUTE re-checks and skips — but a human-review-lane claim gets autonomously pre-registered; have commit skip gated claims). (f) **equivalence-consumption caveat for #3:** two claims with identical content but different governance still (correctly) collapse to one equivalence class — when #3 starts CONSUMING `equivalences` (semantic dedup / propagating status across a class), it MUST reconcile governance (take the stricter posture) and must NOT propagate LICENSED across a class without re-gating, or a hazardous claim could inherit licensing from a public twin.

Phase-8 carry-forwards (none blocking): real network/R/scipy adapters outside the package; full UCUM dimensional algebra (only equality now); `_check_agreement` dimension-awareness; vector-valued `ExecValue`/`Leaf`; then the deferred 3D topology viewer.

**Carry-forward follow-ups (open):** a faithful subject-carrying v1.2→v1.3 re-ingest (now possible — the slot exists); a real cohort predicate algebra (currently prose `tuple[str,...]`); vector-valued `Leaf` (the remaining ingestion gap); auxiliary assumptions as first-class blame/undercut/retraction nodes (all 47 v1.2 claims carry `external_assumptions`); n-ary `incompatible_with` + conjunctive `entails` (would make L4 contraction's entrenchment choice bite); bounded defeat in-degree cap; named-audience VAF value-orderings; per-pattern stratified FDR + PPV-floor (the other two parts of §4); LORD++ upgrade. Same rhythm always: brainstorm forks → phase spec → plan → subagent-driven.

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
