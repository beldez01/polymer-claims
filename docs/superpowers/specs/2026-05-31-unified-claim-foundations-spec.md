# Unified Claim Foundations — Grammar + Protocol (v1.3 Target)

Date: 2026-05-31
Status: Foundations spec for review
Supersedes: `2026-05-29-claim-pattern-architecture-design.md` (the pattern reframe is retained and absorbed here as one element of a deeper target).Source research (read for full justification + citations):
- `~/Desktop/Research/topics/epistemic-claim-foundations/_FINAL_ideal_claim_grammar.md`
- `~/Desktop/Research/topics/epistemic-claim-foundations/generative-protocol/_FINAL_knowledge_generation_protocol.md`

---

## 0. What this is

Polymer Claims is, ultimately, **a protocol for the systematic generation of scientific knowledge**. The claim schema (IR) is not the product — it is the *read/write format* of that protocol. Two artifacts define the system:

- **The Grammar** — what a claim *is*: well-formed, interpreted, licensable. (The IR + type system.)
- **The Protocol** — how a corpus of claims *grows toward truth*: generate → pursue → assess → integrate. (The runtime.)

> The grammar guarantees a claim is well-formed, interpreted, and licensable. The
> protocol guarantees the corpus grows toward truth rather than toward confident,
> well-typed garbage. **The IR is the contract between them.**

This spec defines the **v1.3 target** for the grammar (the buildable schema delta) and the protocol stages it must support, derived from two adversarially-stress-tested research swarms (27 + 23 agents; all critiques integrated).

---

## 1. The success criterion — sensitivity & specificity

Every design decision below is judged against one test:

| | Definition | Served by |
|---|---|---|
| **Sensitivity** | Capture the *fullest* semantic + syntactic richness of real scientific knowledge — lose nothing real. | Sum-typed leaf (qualitative/mechanistic/existence claims get a real home); Toulmin-warrant propositions; mechanism/causal pattern; EXPLORATORY status; oracle-construction as a first-class target. |
| **Specificity** | Admit nothing false; never force or distort science into a shape it isn't. | MECE only over statistical-form axes (never biology); `strength-incomparable` instead of a false scalar; Duhem–Quine blame *sets* not laundered verdicts; `rival_set_closure` instead of LICENSED-simpliciter; provisional-ontology fences instead of forced terms. |

The failure mode we are designing against is the "**toy questionnaire**": a schema that *sounds* rigorous but silently loses (low sensitivity) or distorts (low specificity) the science. Both research keystones are, in effect, long arguments that the naive version fails this test and how to fix it.

---

## 2. Design principles

1. **Foundations locked; surface versioned.** The schema *is allowed to change* as we
   learn what works (§7). What we lock now are the *foundations* — the layer model,
   the sensitivity/specificity criterion, the compiler/runtime split — not every field.
2. **The IR is minimal; complexity lives in typed layers, not free text.** No
   prose-into-JSON path. Every field is a constrained, ontology- or type-backed slot.
3. **Form is computed disjointly from truth — as a *default discipline*, not a firewall.**
   Grammaticality is decided before truth, but that assignment is itself attackable
   (the `reclassify` edge) so we don't re-erect the analytic/synthetic line locally.
4. **No primitive without a justification.** Each primitive below cites the epistemic/ontological constraint that forces it (full citations in the research keystones).
5. **Honest residuals over false closure.** Where exhaustiveness is impossible
   (rival-set closure, ontology coverage, corpus PPV), the residual is *surfaced and
   tracked*, never hidden.

---

## 3. The Grammar — five dependency-ordered layers (v1.3 target)

```
  L4  REVISION    AGM expansion/revision/contraction + entrenchment over the corpus   (temporal change)
  L3  CORPUS      value-based defeat graph (VAF) → set of grounded extensions          (composition, social)
  L2  CLAIM       pattern-typed DAG → 3-valued satisfaction + strength VECTOR           (licensing bridge)
  L1  PROPOSITION typed conclusion content + declared inferential neighborhood          (semantics, molecular)
  L0  LEAF        sum-typed empirical anchor with frame + dual provenance               (empirical)
```

### 3.1 SYNTAX (rational pole)
- **Pattern registry** — an *open*, axis-derived registry (estimand × adjustment-role ×
  null-model × scale), each pattern a typed signature + estimand + invariance group + intended/**excluded** applications. MECE holds *over these statistical-form axes only*.
  Merge `partial_correlation_with_control` + `model_delta_over_baseline` → **`adjusted_effect`**.
  Report a `coverage` metric, never closure. *(Replaces the 45/47 tautology.)*
- **Mechanism / causal pattern** — *outside* the associational catalog; conclusion is a causal edge/path; associational claims attach as `evidence_for` edges. *(Sensitivity.)*
- **Typed role slots, fixed arity** — `predictor | outcome | confounder | mediator |
  collider | instrument`; adjustment set *derived*, not authored (Pearl; Table-2 fallacy).
- **Units-of-measure type system** — dimensions as an abelian group; unit mismatch is a decidable type error (Kennedy 1997; Buckingham Π for free).

### 3.2 SEMANTICS (empirical pole)
- **L1 molecular Proposition** — typed conclusion content + a version-pinned *inferential neighborhood* (material-incompatibility/consequence edges). **Replaces hash-identity**
  (Halvorson 2012); byte-hash demoted to dedup caching.
- **Equivalence is an asserted, defeasible claim** — "same claim?" = "is there an IN
  `equivalence` edge?", severity-graded, first-class.
- **Domain Profile** — ontology-backed legality table (the interpretation function);
  `Filler = Known(CURIE) | Provisional(local_ns, members) | Unclassified(provenance)`.
  *(Specificity: frontier biology gets fenced structural force, not exile.)*
- **Functorial ontology-version transitions** — DEPRECATE/MERGE/SPLIT/OBSOLETE as
  Spivak Δ/Σ/Π migrations; `ontology_term_obsolete` reason-code capped below LICENSED.

### 3.3 EMPIRICAL ANCHOR — the sum-typed L0 leaf *(highest-leverage primitive)*
```
Leaf = Quantity(value, unit, uncertainty, measurement_basis)
     | Categorical(ontology_term, assay)
     | Existence(observed | not_detected, detection_limit)
     | Proposition(data, warrant, backing, qualifier, rebuttal)   # Toulmin 1958
```
Only `Quantity` with `measurement_basis = Fundamental(rep_theorem)` asserts a UCUM unit +
meaningfulness class; derived statistics (β, partial-ρ, fold-change) carry their
*generating formula*, not a false unit. *(This is what turns a grammar of statistics into
a grammar of science — the single biggest sensitivity move.)*

### 3.4 LICENSING BRIDGE (the seam)
- **Grounding node, dual provenance**: `produced_by` (causal) + `licensed_by` (normative,
  carrying asserting-agent + role) + mandatory dated `frame` (content-addressed).
- **`(σ, M)` satisfaction storage** — never a context-free Boolean. Replication = sat in M1 ∧ M2.
- **Two licensing routes**: LICENSED via **severe test** (Mayo, confirmatory) **OR**
  **replication** across independent materializations (discovery). The route is tagged.
  *(Critical for the protocol: machine-generated, surprising-but-replicated findings can
  license without a pre-registration they could never have had.)*
- **`rival_set_closure` ∈ {enumerated, ontology_bounded, open_acknowledged}** travels with
  σ; no verdict renders LICENSED-simpliciter. *(Specificity: no smuggled verificationism.)*

### 3.5 STRENGTH, DEFEAT, REVISION
- **Strength = a 6-axis Pareto vector** ⟨magnitude, uncertainty, evidence-against-null, severity, world-contact, explanatory-virtue⟩. AND = componentwise meet, OR = join. Many claims are **`strength-incomparable`** (an explicit value). Total ranking only as a logged, named-dictatorship policy. *(Kills the hidden `min` / Arrow impossibility.)*
- **Defeat is a Value-Based Argumentation Framework** (Bench-Capon 2003): edges
  `undermine | undercut | rebut | reclassify | reinterpret`; inherit VAF tractability (grounded = PTIME).
- **Duhem–Quine blame surfaced** — contradiction emits the *set* of minimal blame-
  assignments; corpus status = intersection (robustly-IN) / union (possibly-IN) /
  difference → PENDING `duhem_underdetermined`.
- **L4 = AGM/TMS revision** (Alchourrón–Gärdenfors–Makinson 1985; Doyle 1979) with an entrenchment ordering keyed to evidence_class + severity. Status recompute under a *fixed* graph is PTIME-monotone (bounded defeat in-degree, enforced at write-time); graph *edits* are non-monotonic AGM ops. *(Corrects the false "monotone fixpoint" claim.)*
- **Status lifecycle**: `CONJECTURED → {EXPLORATORY | PENDING} → {LICENSED | REJECTED}`, where PENDING is a *typed enum the strength fold can see* {untested, underpowered, exploratory_by_design, contested, duhem_underdetermined, definitional_commitment_contested, ontology_term_obsolete, strength_incomparable, **unreproducible_by_governance**}.

---

## 4. The Protocol — the runtime that reads/writes the grammar

Eight stages + three daemons, each a total function `corpus_IR → corpus_IR`. Honestly a **pursuit-and-verification protocol with an *open generation port*** — generation is not claimed to be rule-governed; the rule-governed machinery is select → execute → verify → integrate. Full detail in the protocol keystone; the spine:

```
(0) REPRESENT → (1) GENERATE → (1.5) SAFETY-GATE → (2) CANONICALIZE → (3) SELECT
   → (4) DESIGN/COMMIT → (5) EXECUTE/GROUND → (6) VERIFY → (7) INTEGRATE ↻ back to (1)
daemons: D1 DRIFT · D2 ORACLE-VALIDATION · D3 REPRESENTATION RED-TEAM
```

Keystone closure (the flywheel): **INTEGRATE emits the unresolved-attack frontier, which is identically GENERATE/SELECT's highest-value target — open problems literally are the next experiments.**

Load-bearing guarantees (each a falsifiable invariant): no self-licensing (air-gapped, two-implementation verifier); no LLM-paraphrased statistics (byte-faithful); no HARKing on the primary test (hash-lock) with the implicit search *priced* (selection-aware correction); no confirmation-seeking (direction-blind EIG) and no surprise-Goodharting; no corpus-level Type-I blowup (online-FDR + per-pattern empirical null + PPV floor); no model collapse (exogenous-variance + tail-coverage throttle); no unvalidated oracle certifying truth (D2); no silent Kuhn-loss (anomaly importation + heterodox lane).

**Human judgment re-enters at four audited ports by design**: significance/stakes
weighting (SELECT), novelty-to-field adjudication (VERIFY), high-stakes/contested
escalation (VERIFY→INTEGRATE), biosafety dual-use gate (SAFETY-GATE).

---

## 5. The contract: 6 requirements the protocol imposes back on the grammar

These are *additions to the v1.3 grammar target* without which the protocol cannot run:

1. **`generated_by` + `search_cardinality`** provenance — or selection-aware significance correction is unrepresentable.
2. **Oracle credibility-qualification object** (validation tier + applicability domain + propagated uncertainty) bound to `operations`; strength capped by oracle tier.
3. **`hazard_class` + governance/access-scope dimension** on data dependencies; enables SAFETY-GATE and `unreproducible_by_governance`. *(Load-bearing for the TET2/TCGA surface.)*
4. **Corpus-level online-FDR / error-budget object** as a first-class IR entity (not
   runtime memory).
5. **`representation_revision` meta-tier** — claims *about the IR itself* (new patterns, ontology terms, relaxed constraints), gated more conservatively.
6. **`reinterpret` edge** (meaning moved, statistics unchanged), distinct from `undercut`.

---

## 6. The reconciled build order (8 moves)

Dependency-aware merge of both keystones' "do first" lists. **No implementation begins
until this spec is approved.**

| # | Move | Source | Rationale |
|---|---|---|---|
| 1 | **Oracle-validation dossiers (D2)** on existing MCP/R tools | protocol | Everything conditions on it; tools already exist — cheapest high-leverage |
| 2 | **Sum-type the L0 leaf** (Quantity/Categorical/Existence/Proposition) | grammar | Grammar-of-statistics → grammar-of-science; unblocks mechanistic claims (sensitivity) |
| 3 | **Air-gap EXECUTE** (writer emits ops as data; blind canaries) | protocol | Forecloses the Sakana/EvilGenie self-gaming class before scale |
| 4 | **Strength → 6-axis Pareto vector** + `strength-incomparable` | grammar | Removes hidden scalar / Arrow problem (specificity) |
| 5 | **Online-FDR ledger + per-pattern empirical null + running PPV** | protocol | Biggest reliability gap; bookkeeping on the existing evaluator |
| 6 | **Dual licensing + `rival_set_closure` + `search_cardinality`** | both | Fixes discovery under-licensing, smuggled verificationism, forking paths |
| 7 | **Pattern registry** (merge `adjusted_effect`, add mechanism pattern, axis coverage) | grammar | Real disjoint object replacing the 45/47 tautology |
| 8 | **L4 AGM/TMS + four human ports + SAFETY-GATE** | both | Revision algebra + the seams where automated judgment provably fails |

Each move becomes its own implementation plan (writing-plans) when we get there; this
spec is the target they all serve.

---

## 7. Schema versioning policy (we are allowed to evolve)

The schema *will* change as we learn what captures real science. Discipline:

- **Foundational vs surface.** Foundational (changes only with a major version + migration):
  the 5-layer model, the sensitivity/specificity criterion, the compiler/runtime split,
  the licensing-bridge concept. Surface (minor versions, additive): individual patterns,
  ontology bindings, profile legality tables, strength-axis tuning, PENDING reason-codes.
- **Every claim pins `schema_version` + `pattern.version` + `profile.version`** so old
  claims are *frozen-as-interpreted*, never silently reinterpreted (already in the v1.2 plan).
- **Schema changes are themselves claims** — they live in the `representation_revision`
  meta-tier (§5.5), gated more conservatively than object-level claims, with their own
  provenance and review. Evolving the grammar is a governed scientific act, not an edit.
- **Migrations are functorial** where they touch ontologies (Spivak Δ/Σ/Π).

The goal of strong foundations now is precisely so that *surface* evolution is cheap and
safe while the *foundations* give a claim the sensitivity + specificity to hold the
fullest richness of scientific knowledge.

---

## 8. The claim viewer — already live; topology-as-subject is the deferred extension

**The claims viewer is already built and live on polymerbio.org.** It renders each claim
as its full DAG + grammar panels (`FormalClaim/` suite), and the 3D latent-space universe
exists (`FormalClaimUniverse`, `ClaimUniverse`, `/portal/latent3d`, the `viz` projection
of the 10 in-silico experiments). So the viewing surface is **not** a greenfield build —
it ships today.

**What is deferred (gated on scale) is the *topology-as-subject* mode** — the interactions
that make the latent-space network *itself* the object of investigation:
- **click-drag to lasso** a cluster and operate on it as a set;
- surface **which regions are dense/sparse, which chains are load-bearing, where
  contradictions concentrate, where the frontier is**;
- any **scaling-law structure** of the corpus.

**Why that part is deferred:** these only become meaningful with **scale** — topology,
clusters, and scaling-law structure only emerge with *many, many* more claims (thousands+).
Until the protocol (the corpus-growth engine) is producing claims at volume, the existing
3D view has too little to show for lasso/topology analysis to pay off. Build the generator
first; the observatory already exists, but it needs a fuller sky. The viewer also doubles
as a protocol instrument: REPRESENT (Stage 0) and the REPRESENTATION RED-TEAM daemon (D3)
both operate on exactly this latent space.

---

## 9. Non-goals / accepted limitations

- **Not** mechanizing the creative act — generation is an open port (Popper/Reichenbach).
- **Not** proving the pattern registry covers all of biology — it reports coverage, by
  design a statistics-and-argument grammar, not an oracle.
- **Not** eliminating rival-set closure or corpus PPV uncertainty — surfaced, not closed.
- **Not** building the 3D viewer or the full protocol runtime now — foundations + the
  8-move grammar target first.
- Authoring cost is *reduced* (stub-claim tier, notebook→claim generation) but remains
  real; human-in-the-loop throughput is a binding constraint on the clinical surface — an
  accepted cost, because the alternative (unbounded autonomy) is the failure mode we forbid.

---

## 10. Connections to library

- Supersedes `2026-05-29-claim-pattern-architecture-design.md` (pattern reframe absorbed
  into §3.1) and its companion `2026-05-29-claim-architecture-map.html` (spatial map).
- Research basis: the two keystones + 28 explorer reports + 8 syntheses in
  `~/Desktop/Research/topics/epistemic-claim-foundations/`.
- Memory: `project_polymer_claims_knowledge_protocol` (telos), `project_formal_claim_ir`,
  `project_polymer_claims_phase0`, `project_biomed_ontology_schema_effort`.
- Build home: `internal/epistemic_os/MASTER_PLAN.md`; runtime seat: `petri`; IR substrate:
  `polymer-claims`.
