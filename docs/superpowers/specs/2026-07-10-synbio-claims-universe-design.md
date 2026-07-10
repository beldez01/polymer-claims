# WAYLAND — The Synthetic-Biology Claims Universe: Phase 0 Design

**Date:** 2026-07-10
**Status:** Design (Phase 0 of the Wayland program). Ratifies the claim taxonomy, the two-stratum rule, the firewall, and the expansion doctrine before any code. Supersedes no prior spec.
**Telos:** Onboard a new field (synthetic biology / programmable living medicines) into Polymer Claims *correctly* — expanding what the IR can ingest, never reshaping it to suit one domain — and set up a blinded, pre-registered re-derivation of a genotype-directed therapy (Durendal) as the proof that the engine derives, not just verifies. Program plan: `docs/superpowers/plans/2026-07-10-synbio-claims-universe.md`.

---

## 0. One-paragraph summary

Two existing research bodies — `Research/topics/synthetic-biology/` (a technique vocabulary) and `Research/topics/programmable-living-medicines/` (a first-principles constraint treatise) — are the seed corpus. This spec establishes **how their content maps onto the real v1.3 IR** (grounded in `grammar/src/polymer_grammar/`), and locks four things before Phase 1 touches code: (1) a **two-stratum rule** — most compendium content is *reported* and enters as `LITERATURE_EXTRACTED` proposals that are admissible as priors but **cannot self-license**; only claims **recomputed from real data** join the `AGENT_GENERATED`/licensed spine through the existing two-leg gate; (2) a **firewall** that makes the eventual Durendal re-derivation a genuine held-out prediction, split into IR-enforced data-overlap guards (`prior_cohorts` + shared-cause) and process-enforced conceptual guards (date-cutoff + conclusion-stripping + review); (3) the **expansion doctrine** — every IR strain is classified (general/analysis/subject/domain) and fixed additively, general fixes to the core primitive, domain concepts to the open pattern registry, proven byte-identical against existing corpora; (4) the honest **status ceiling** — a reported fact is `CONJECTURED`, never licensed, until an execution adapter recomputes it. Phase 1 is a five-claim probe that measures the real formalization yield and flushes the first grammar gaps.

---

## 1. Foundations alignment

Cross-checked against the foundations and the real grammar before planning. No architectural violations; the entries below are what make the design canonical.

| Foundation | Requirement | How this design honors it |
|---|---|---|
| de Bruijn kernel (`epistemology.md` §8) | Proposers are untrusted scaffolding; standing comes only from the kernel. | Reported claims are `LITERATURE_EXTRACTED` proposals; they never license. The forge is an untrusted proposer; only `run_cycle`/`verify_stage` confers standing (§3). |
| Compute boundary (`compute-boundary.md`) | Polymer specifies/orchestrates/witnesses/certifies; never hosts wet compute. | The wet Gate-1 (sort-then-seq) is a *proposed, attestable* experiment run by a partner; Polymer licenses the attested log, never runs the assay. |
| e-value / independence (`epistemology.md` §2,§7) | Severity = betting e-value; multiply only across error-independent cohorts. | Computed claims carry a single-leg betting e-value; expression evidence from one atlas never multiplies with itself. `search_cardinality` prices the forge's implicit search (§4). |
| Independence tiers (`licensing.py`) | REPLICATED needs ≥2 `dimnames_hash` + low shared-cause overlap. | Within-atlas licensing capped at REPRODUCED; `shared_cause_factors` populated so §E cannot mint a false REPLICATED. |
| Measurement seam (`measurement-foundation.md`) | Criteria invariant under the assay scale's admissible transforms; a leaf carries no false unit. | Confirmed against `leaf.py`: `QuantityLeaf._basis_discipline` forbids a `unit` on non-FUNDAMENTAL bases and requires a `formula` on DERIVED. The taxonomy (§2) respects this exactly. |
| Residualism (`residualism.md`) | Un-licensed ≠ false; residue structured, never deleted; audit trail monotone. | Defeated design candidates → forbidden-region residue; under-powered → PENDING. The **monotone audit trail** is the precedent for the monotonic-expansion doctrine (§5). |
| Verification philosophy (`§5`) | The gate licenses warrant, not truth; consistency is warrant-only. | A licensed derivation warrants "this is the grounded extension of the sealed seed," never "this therapy works." |
| Corpus / purity invariants | `Corpus` = exactly 4; grammar/protocol pure + numpy-free. | All new code umbrella-side; the `synbio` package adds no `Corpus` collection; Phase 1 uses only core grammar primitives. |

---

## 2. The claim taxonomy — mapped to the real v1.3 IR

Grounded in `grammar/src/polymer_grammar/{leaf,claim,proposition,pattern,strength,provenance,status,defeat}.py`. Three tiers by formalization difficulty. **Tier 3 stays prose — forcing it into claims is the toy-questionnaire anti-pattern the project fears.**

**Tier 1 — near-mechanical (Phase 1 targets).** L0 leaves (`leaf.py`):
- Physical constants (mismatch ΔG ≈ 1–3 kcal/mol; kT ≈ 0.62 kcal/mol @ 310 K) → `QuantityLeaf(measurement_basis=FUNDAMENTAL, unit="kcal/mol")`. Only FUNDAMENTAL may carry a UCUM unit.
- Derived statistics (ADAR ~277-fold dynamic range; expression TPM floors) → `QuantityLeaf(measurement_basis=DERIVED, formula=…, unit=None)`. The validator *requires* the formula and *forbids* the unit.
- Existence findings (a sensor reports a single-base genotype at all) → `ExistenceLeaf(state="observed")`.

**Tier 2 — needs the L1/pattern/defeat layers (Phase 2).**
- Non-monotonic laws ("above a threshold affinity, discrimination degrades") → `PropositionLeaf(warrant_type="mechanistic_analogy")` — the specificity-wall generalized, and a **defeater** (§2a).
- The topology-rejection move → an **L1 `Claim.conclusion`** (`Proposition`) whose `neighborhood` carries `incompatible_with` edges to the WT-off-target propositions. `derived_rebut_edges` (`defeat.py`) then turns that material incompatibility into REBUT defeats **automatically** between LICENSED claims — the argument graph builds itself from the meaning layer.
- The design itself → a new **`sense_and_kill` `Pattern`** registered in the *open* `pattern.registry` (Phase 2), carrying its `estimand × null_model × scale × invariance_group` and ≥1 `excluded_applications` (the Newman-hole pin, e.g. "surface-antigen CAR targeting — use the antigen pattern").

**Tier 3 — stays contextual.** Narrative synthesis, "decoupling as a recurring move," IP/commercial reasoning → `Provenance.rationale` (opaque free-text, display-only) or plain docs, never licensed claims.

### 2a. Correction: design-desirability is NOT the core `StrengthVector`

The program plan loosely equated target-selection axes (recurrence × expression × accessibility × unmet-need) with the 6-axis Pareto strength vector. **`strength.py` shows this is wrong and the conflation would violate the expansion doctrine.** The real `AXES` are *epistemic* — `magnitude, certainty, evidence_against_null, severity, world_contact, explanatory_virtue` — measuring how well-warranted a claim is, not how desirable a therapeutic target is. Design-desirability is **domain-specific ranking** and belongs in the SELECT/scheduler layer (info-gain × stakes) or a domain analysis-profile, **never overloaded onto the core `StrengthVector`.** This is the first worked example of §5's "general to the general, domain to the periphery" rule: cramming synbio target-desirability into the shared epistemic vector is exactly the "influencing it to suit one thing" the user forbade.

### 2b. Defeat is leaf-type-agnostic; reported-stratum edges must be provisional

`defeat.py` confirms the defeat graph is a corpus-level module of edges over claim *ids* — a claim's ability to defeat is **not** gated by its leaf type. So C5 (a `PropositionLeaf` law) defeating the SNV-lane claim is trivially expressible. But `effective_defeats` makes an attack stand whenever the target does not strength-dominate the source, and a reported claim with `strength=None` is never dominated — so **an unlicensed literature prior could knock out a LICENSED computed claim.** That violates "standing only through the kernel." **Decision:** reported-stratum (`LITERATURE_EXTRACTED`) claims may author only **`provisional=True`** defeat/support edges (inert until the source itself gains standing) and may serve as L1 `incompatible_with` context; they may **not** author live non-provisional defeats against licensed claims. Precedent: `bridge_proposer` already coerces untrusted proposal-supplied edges to provisional (the C1 security fix).

---

## 3. The two-stratum rule (the core design decision)

Map the two strata onto the *existing* `GenerationMode` enum (`provenance.py`) — **no new field needed**:

| Stratum | `generated_by` | Can license? | Role | `search_cardinality` |
|---|---|---|---|---|
| **Reported / prior** | `LITERATURE_EXTRACTED` (`method`/`version` = the primary ref) | **No** — CONJECTURED ceiling | priors, defeaters (provisional), material-incompatibility context | 1 (a reported fact is one hypothesis) |
| **Computed / forge** | `AGENT_GENERATED` (+ `agent_id`) | Yes, through the two-leg gate → REPRODUCED | the licensed spine of the derivation | N = candidates the forge considered to surface it |

The skeptic's "this is a formalized lit review" is answered structurally: the lit review is the untrusted prior layer; the licensed spine is recomputed and gated. A reported value stays `Status.CONJECTURED` until an execution adapter recomputes it from data (Phase 2) — Phase 1 deliberately stops at CONJECTURED and does not fake a license.

---

## 4. The firewall — operational checklist

The treatise links to `opto-car` and reasons toward genotype-directed cytotoxicity; the answer is in the source. The firewall makes the re-derivation honest. It has **two enforcement layers** — be precise about which catches what:

**IR-enforced (data-overlap leakage).**
- `Provenance.prior_cohorts` records the cohort identities (`dimnames_hash` namespace) a hypothesis's motivating prior was established on. When the forge's prior overlaps the *test* data, the protocol's strict-shared-cause path withholds severity and stamps `PendingReason.SHARED_CAUSE_CONFIRMATORY` — a held-out test cannot be faked from an overlapping prior.
- `Provenance.preregistration_hash` + the `evaluation_plan` `commitment_hash` lock the primary test before data (the Phase-D slice-1 machinery, 2026-06-19). `register_test` charges + locks the e-LOND α-slot at registration.

**Process-enforced (conceptual leakage — the part the IR cannot see).**
- **Admissibility rule:** a claim enters the blinded seed only if *upstream of and independent from* the Durendal insight. **In:** recognition-thermodynamics constraints, the affinity–discrimination law, expression floors, the technique library, the fusion/expression **data**. **Out:** the opto-car conclusions, RADAR-fusion-sensing *as applied to the answer*, any RUNX1-RUNX1T1-specific reasoning, Part XI's genotype-directed-cytotoxicity synthesis.
- **Two mechanisms together:** a literature-date cutoff (nothing post-dating the insight) **and** conclusion-stripping (a claim that states/implies the answer is inadmissible even if old). Each admitted claim carries an `admissibility` tag (recorded in `Provenance.rationale` or a sidecar) naming the deciding rule.
- **Human review gate:** an independent reviewer signs the boundary set before the seed is sealed (Phase 3 exit gate).

**The claim we earn on success:** "the engine output RUNX1-RUNX1T1 + topology + direct-caspase as the grounded extension of a pre-registered, sealed seed, with a signed certificate" — a held-out prediction, not a fit.

---

## 5. The expansion doctrine (ratified)

The governing meta-goal, per the user directive of 2026-07-10 (memory `feedback_ir_monotonic_expansion`): **onboarding a field expands what the IR can ingest; it never rearranges or narrows the schema to suit one domain. Always expanding, always debugging, never reducing scope.**

**Classify every gap by the scope of its fix:**

| Class | Lands in | Worked example (this field) |
|---|---|---|
| **general** (new kind of input; helps every field) | a core primitive (`Leaf` variant, strength axis) | context-conditioned strength; interval/range values (both below) |
| **analysis-specific** (a statistic/method) | a pattern / analysis-profile extension | the `sense_and_kill` estimand form |
| **subject-specific** (a new entity/ontology slot) | subject/roles + ontology binding | fusion-junction subjects (Phase 2) |
| **domain-specific** (meaningful only here) | the **open `pattern.registry`**, never the core leaf | the `sense_and_kill` pattern; design-desirability ranking (§2a) |

**Two rules that keep expansion from becoming distortion:**
1. **General to the general, domain to the periphery.** A general gap is fixed in the core so *every* field gains; a domain concept lands in the pattern registry (which is designed open — it "reports a coverage metric, never closure") so the core never tilts toward synbio.
2. **Additive-or-nothing, proven.** No IR change ships unless every existing corpus (methylation, pharmaco, immuno) still validates **byte-identically** and its suite stays green. An expansion that would break/narrow/reinterpret an existing field's claims is rejected and re-designed as additive.

**Two general gaps already identified from reading `leaf.py`** (both help every field, so both are core-primitive fixes, not synbio patches):
- **Context-conditioned strength.** `QuantityLeaf` carries `value`/`uncertainty`/`unit`/`formula` but has **no field for the context a derived statistic holds in** (ADAR "277-fold *in this cell line*"). Candidate additive resolutions (weigh in Phase 2 with a byte-identical proof): an optional `context: str | None` on `QuantityLeaf`, or a structured `MeasurementContext` model. Cost: touches a core primitive → strongest backward-compat obligation.
- **Interval/range values.** A CAR threshold of 10²–10⁴ /cell cannot be honestly carried by a single `value` + symmetric `uncertainty`. Candidate: an additive `IntervalLeaf` variant in the `Leaf` sum type, or an optional `[low, high]` on `QuantityLeaf`. Phase 1 refuses to fake a symmetric bar (leaves `uncertainty=None`) and logs the gap.

The living record is `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`; each entry carries constraint, current IR behavior, candidate resolution, `expansion_class`, purity/backward-compat cost, and the byte-identical proof once resolved.

---

## 6. What Phase 1 must produce, and the plan corrections it forces

Phase 1 (task-decomposed in the plan) is the five-claim probe. Reading the real IR forces these corrections to the plan's Phase 1 — apply them at execution:

1. **Provenance mode.** C1–C5 are reported literature facts → `generated_by=LITERATURE_EXTRACTED` with `method`/`version` = the source, **not** `AGENT_GENERATED`/`agent_id="synbio-formalizer"`. (The agent is the extractor, not the warrant.)
2. **`search_cardinality=1`** must be set on each (the field is required, `ge=1`).
3. **Status ceiling is `CONJECTURED`**, asserted honestly — no license without recompute.
4. **The context/interval gaps** are `general`-class core-primitive candidates, logged with a byte-identical plan — not synbio-local hacks.
5. **Global-constraint fix:** the plan's "every claim uses `AGENT_GENERATED`" line is superseded by the §3 two-stratum table.

**Exit gate:** all five validate through the real grammar; the gap report classifies every strain by `expansion_class` with a backward-compat plan.

---

## 7. Decision points — resolved

The five open questions from the plan, ratified here:

1. **Codename:** Wayland (keep; rename anytime).
2. **Repo vs. Research:** ingest **in place, read-only** from `Research/`; commit only derived claims, gap reports, and specs. (No lift-into-repo; the compendia are living documents.)
3. **Blinding strictness:** date-cutoff **and** conclusion-stripping together (§4). The stricter, defensible option.
4. **Headline target:** warm up the licensed spine on a higher-expression validation fusion (PAX3-FOXO1) at Phase 2's gate to isolate actuation-selection at max signal; **headline on Durendal (RUNX1-RUNX1T1) at Phase 4.**
5. **Fallback framing:** pre-committed now — a null forge result (can't invent the topology move) becomes the honest "research-strategy engine" claim (engine licenses/ranks/prunes human-proposed candidates), not a failure. Decided before the run.

---

## 8. Non-goals (this phase and program)

- **Not** claiming the therapy works — only that it is the grounded extension of the sealed seed worth the cheapest experiment.
- **Not** running any wet assay (compute boundary) — Gate-1 is proposed and attestable, run by a partner.
- **Not** dissolving the whole treatise into claims — Tier 3 stays prose.
- **Not** adding a `Corpus` collection or any grammar field in Phase 1.

## 9. Deferred to later-phase specs

- The `sense_and_kill` `Pattern` full signature + its excluded_applications (Phase 2).
- The markdown→claims ingestion design + human-in-the-loop review protocol (Phase 2).
- The execution adapters over the expression atlas / genome annotation, and the two-leg registry reuse (Phase 2).
- The resolution (or deferral) of the context-conditioning and interval gaps, each with its byte-identical proof (Phase 2, gap-report-driven).
- The blinded-seed assembly + pre-registration mechanics (Phase 3).
- The forge proposer + derivation-run wiring + certificate (Phase 4).
