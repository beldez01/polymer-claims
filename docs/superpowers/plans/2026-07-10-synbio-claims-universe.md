# WAYLAND — The Synthetic-Biology Claims Universe: Program Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement the task-decomposed phase (Phase 1) of this plan. Later phases (2–5) are scoped at the program level and each spawns its own spec + plan before execution — do **not** treat their bullet lists as task-ready.

**Codename.** *Wayland* — in the medieval tradition (the Karlamagnús saga) the smith who forged Durendal. The therapy is the sword; this engine is the forge. Rename freely.

**Goal:** Stand up a licensed synthetic-biology sub-universe inside Polymer Claims, then use it to run a **blinded, pre-registered re-derivation of a genotype-directed therapy** — demonstrating that the engine *derives* investable therapeutic programs, not merely verifies them.

**Architecture:** Formalize the two existing research bodies (`Research/topics/synthetic-biology/` = technique vocabulary; `Research/topics/programmable-living-medicines/` = first-principles constraints) into a two-stratum corpus: a **reported constraint/prior layer** (citations, admissible as defeaters, never self-licensing) and a **computed licensed spine** (recomputed from real data through the existing two-leg gate). A generative proposer (the *forge*) walks a fusion catalog, instantiates a `sense_and_kill` design pattern, and the ordinary flywheel (SELECT → EXECUTE → VERIFY → INTEGRATE) resolves a grounded extension. The held-out target is Durendal (RUNX1-RUNX1T1 t(8;21) + topology-rejection + direct-caspase actuation). All new code is umbrella-side; `grammar`/`protocol` stay pure and numpy-free; `Corpus` stays 4.

**Tech Stack:** Python 3.12, pydantic v2, the existing grammar/protocol kernel, numpy (umbrella only), a new opt-in `[synbio]` extra for ingestion/execution deps. Source data: TCGA-LAML (already in `data/`), GTEx expression, a recurrent-fusion catalog (COSMIC/Mitelman-derived).

## Global Constraints

- `grammar/` and `protocol/` stay **pure + numpy-free**; every heavy import (numpy/pandas) lives under `src/polymer_claims/`.
- `Corpus` has **exactly 4 collections** — never add one.
- Heavy scientific/ingestion deps stay behind an opt-in **`[synbio]`** extra; core wheel import must succeed without it (lazy imports).
- Real data and any built SE-Contract are **gitignored** — nothing real is committed. Only the derived claims, gap reports, and specs are.
- Licensing statistics must be **scale-invariant** (rank / median-split), never a raw linear score (`measurement-foundation.md`).
- Proposers (LLM, human, deterministic) are **untrusted scaffolding** (`epistemology.md` §8). Nothing earns standing except by passing the kernel.
- **Two-stratum provenance** (ratified in the Phase 0 spec §3): *reported* claims use `generated_by=LITERATURE_EXTRACTED` (`method`/`version` = the primary ref, `search_cardinality=1`) and cannot license (CONJECTURED ceiling); *computed/forge* claims use `AGENT_GENERATED` with a non-null `agent_id` and license through the two-leg gate. `search_cardinality` (`ge=1`) is required on every claim.
- **Compute boundary (`compute-boundary.md`):** Polymer never runs the wet experiment. A derivation licenses to a *proposed, attestable* Gate-1, not an executed one; a partner lab runs it and Polymer licenses the attested log.
- Residue is first-class: non-hits and refuted candidates are demoted, never deleted (`residualism.md`).
- **MONOTONIC IR EXPANSION (new, load-bearing — see §Expansion doctrine):** every IR change is **additive and backward-compatible**. A new field brought in by synbio may never narrow, reinterpret, or overfit the schema to serve one domain at another's cost. The scope of what the IR can ingest only grows. Proof obligation: after any IR change, every existing corpus (methylation, pharmaco, immuno) still validates **byte-identically** and its test suite stays green.
- **THE FIREWALL (new, load-bearing — see §4):** no claim, ref, or reasoning downstream of the Durendal insight may enter the blinded seed corpus. The derivation is a held-out prediction or it is nothing.

---

## Scope note (read before planning any later phase)

This is a **program plan**, not a single implementation plan. The writing-plans scope-check applies: the program spans several independent subsystems (a grammar/pattern layer, an ingestion layer, a blinding harness, a derivation runner, a demo). Fully task-decomposing all of them now would be premature — Phases 2–5 depend on findings from Phase 1. Therefore:

- **Phase 1 is fully TDD-task-decomposed below** and is buildable today.
- **Phases 2–5 are scoped at the program level** with entry gates, deliverables, and exit gates. Each gets its own `docs/superpowers/specs/…` + `docs/superpowers/plans/…` pair authored at the start of that phase, once its predecessor's gate is green.

---

## 1. North star & thesis

The Durendal design record is already a Polymer Claims corpus written in prose: a set of claims with strengths, a defeat graph (each rejected candidate — the SNV lane, FIP1L1-PDGFRA, BCR-ABL, tTA — is defeated by a specific principle), and a grounded extension (the surviving design). The two research bodies are the seed that graph grows from. **Wayland's deliverable is to make that collapse an explicit, auditable, re-runnable computation** instead of one expert's single pass — and to prove it by re-deriving Durendal *without having been shown the answer*.

Why this is not another me-too AI drug-discovery platform, stated as three properties the engine already has the machinery for:

1. **Proof-carrying output.** The unit of output is not `target, 0.87` but *target + the licensed chain of constraints that selects it + the defeaters that would overturn it + the single cheapest experiment that adjudicates it* (VAF graph + provenance + SELECT).
2. **Negatives are assets.** The specificity-wall is a licensed negative that redirected the whole program; STRATA's demoted-not-erased forbidden-region taxonomy means failures compound into a map of what not to try — a moat that grows with use.
3. **Capital-efficiency is native.** SELECT (info-gain × stakes) doesn't just rank targets, it names the one sub-$100K ex-vivo experiment (the Durendal "sort-then-seq" Gate 1) that resolves the most uncertainty.

## 2. Foundations alignment

Cross-checked before planning; substantially aligned. The corrections below are what make it canonically correct.

| Foundation | Requirement | How Wayland honors it |
|---|---|---|
| Compute boundary | Polymer specifies/orchestrates/witnesses/certifies; never a hosted compute utility. | All compute umbrella-side; source data gitignored. Wet Gate-1 is *proposed and attestable*, run by a partner; Polymer licenses the log. |
| de Bruijn kernel (`epistemology.md` §8) | Proposers are untrusted; standing comes only from the kernel. | The forge (LLM/human) proposes design tuples; two legs recompute; only `run_cycle`/`verify_stage` licenses. |
| e-value / independence (`epistemology.md` §2,§7) | Severity = betting e-value; e-values multiply only across error-independent cohorts. | Single-leg betting e-value per computed claim; expression evidence from one atlas does not multiply with itself. |
| Independence tiers (`licensing.py`, `GLOSSARY.md`) | REPLICATED needs ≥2 `dimnames_hash` **and** low shared-cause overlap. | Within-atlas = REPRODUCED ceiling; `shared_cause_factors` populated so §E cannot mint a false REPLICATED. |
| Measurement seam (`measurement-foundation.md`) | Criteria invariant under the assay scale's admissible transforms. | Expression-floor and topology criteria are threshold/rank tests, not linear scores. |
| Residualism | Un-licensed ≠ false; residue structured, queryable, never deleted. | Defeated candidates → forbidden-region residue with their evidence trail; under-powered → PENDING frontier. |
| Verification philosophy | The gate licenses warrant, not truth; consistency is warrant-only. | A licensed derivation warrants "this is the grounded extension under the seed," not "this therapy works." |
| Calibration = instrument (`§5c`) | Calibration/blinding machinery changes no claim status. | The firewall + pre-registration lock α; they gate *admissibility*, not a claim's licensed status. |

## 3. The claim taxonomy — how the compendium maps to the IR

Grounded in the real L0 sum-typed leaf (`grammar/src/polymer_grammar/leaf.py`). Three tiers, by formalization difficulty. **Not everything becomes a claim — forcing Tier 3 is the toy-questionnaire anti-pattern the project explicitly fears.**

**Tier 1 — near-mechanical (Phase 1 targets).** Hard quantitative floors become L0 leaves:
- Physical constants (mismatch ΔG ≈ 1–3 kcal/mol, kT ≈ 0.62 kcal/mol at 310 K) → `QuantityLeaf(measurement_basis=FUNDAMENTAL, unit=…)`.
- Derived statistics (ADAR ~277-fold dynamic range, expression TPM floors) → `QuantityLeaf(measurement_basis=DERIVED, formula=…, unit=None)`.
- Existence findings (a sensor reports a single-base genotype *at all*) → `ExistenceLeaf`.

**Tier 2 — needs a pattern (Phase 2).** Relational principles and design moves:
- Non-monotonic laws ("above a certain affinity, discrimination gets *worse*") → `PropositionLeaf(warrant_type="mechanistic_analogy")`, the specificity-wall generalized. A first-class **defeater**.
- The topology-rejection move → an **L1 molecular proposition** (conjunction of four leaves: ADAR A·C geometry + marginal-stability thermodynamics + junction conservation + the RUNX1-ubiquitous/ETO-silent expression fact).
- The design itself → a new **`sense_and_kill` pattern** over `(reader, discrimination-topology, actuation, target)` in the open `pattern.registry`. **Correction (Phase 0 spec §2a):** target *desirability* (recurrence × expression × accessibility × unmet-need) is **not** the core `StrengthVector` — those 6 axes are epistemic (`magnitude, certainty, evidence_against_null, severity, world_contact, explanatory_virtue`). Design-desirability is domain-specific ranking in the SELECT layer / an analysis-profile, never overloaded onto the shared vector (a worked example of the expansion doctrine).

**Tier 3 — stays contextual.** Narrative synthesis, "decoupling as a recurring move," IP/commercial reasoning. These live as `Provenance.rationale` / context, not licensed claims.

**The two-stratum rule (core design decision).** Most compendium content is *reported* (provenance = literature), so it enters as **CONJECTURED proposals with citations** — admissible as priors/defeaters but **barred from self-licensing**. Only claims we can **recompute from data** (e.g. "RUNX1-RUNX1T1 clears the 13 TPM floor in AML," computable from TCGA-LAML) can join the **licensed spine**. A skeptic's "this is just a formalized lit review" is answered structurally: the lit review is the untrusted prior layer; the licensed spine is recomputed and gated.

## 4. The firewall — how we prove derivation, not retrofit

The treatise already links to `opto-car` and reasons toward genotype-directed cytotoxicity: **the answer is baked into the source.** Formalizing it as-is and "deriving" Durendal is circular. The firewall makes the re-derivation honest:

1. **Admissibility rule.** A claim may enter the blinded seed only if it is *upstream of and independent from* the Durendal insight: first-principles constraints (recognition thermodynamics, the affinity–discrimination law, expression floors), the technique library, and the fusion/expression **data**. Excluded: the opto-car conclusions, the RADAR fusion-sensing precedent as applied, any RUNX1-RUNX1T1-specific reasoning, and Part XI's genotype-directed-cytotoxicity synthesis.
2. **Two admissibility mechanisms**, applied together: a **literature-date cutoff** (nothing post-dating the insight) *and* **conclusion-stripping** (a claim that states or implies the answer is inadmissible even if old). Each admitted claim carries an `admissibility` provenance tag with the deciding rule; a human reviews the boundary set.
3. **Pre-registration.** Before the seed sees the fusion/expression data, the derivation plan is committed (`commitment_hash`, `register_hypotheses`) and the e-LOND α-slot is locked. This is the machinery shipped 2026-06-19 (Phase D slice 1), used exactly as designed.
4. **The claim we get to make** on success: "the engine output RUNX1-RUNX1T1 + topology + Road B as the grounded extension of a pre-registered, blinded seed, with a signed certificate" — a held-out prediction, not a fit.

## 5. The phased arc

Each phase has an **entry gate** (what must be true to start), a **deliverable**, and an **exit gate** (the pass/fail check that unlocks the next phase).

### Phase 0 — Charter & foundations spec *(spec only, no code)*
- **Entry:** this program plan approved.
- **Deliverable:** `specs/2026-…-synbio-claims-universe-design.md` — the claim taxonomy (§3) ratified against the real grammar, the firewall protocol (§4) written as an operational checklist, the two-stratum rule, and the admissibility boundary for the seed named explicitly (which refs in, which out).
- **Exit gate:** foundations table has no red cells; the firewall boundary list is reviewed and signed.

### Phase 1 — The formalization probe *(TDD, decomposed below)*
- **Entry:** Phase 0 signed.
- **Deliverable:** 5 Tier-1 claims constructed and validated **through the real grammar**, each with attested literature provenance and the honest status it can reach (CONJECTURED, not licensed — no recompute yet), plus a **grammar gap report**.
- **Exit gate:** all 5 claims validate; the gap report names every place a claim did not fit the IR cleanly (predicted: context-conditioned strength; interval/range values). This is the cheap experiment that de-risks the whole program before pattern/ingestion work — the Wayland analog of sort-then-seq.

### Phase 2 — Patterns, ingestion & execution adapters *(own spec+plan)*
- **Entry:** Phase 1 gap report in hand (it dictates whether the grammar needs an additive extension and how big).
- **Deliverables:** the `sense_and_kill` pattern + the constraint/floor pattern; a reviewed markdown→claims ingestion for the two compendia (structured extraction, human-in-the-loop, provenance to primary refs); execution adapters over the real substrate (expression atlas + genome annotation, reusing the SE-Contract seam and the two-leg registry from STRATA/methyl).
- **Exit gate:** at least one **computed** claim licenses at REPRODUCED through `run_cycle` (candidate: RUNX1-RUNX1T1 clears the TPM floor in AML) — proving the licensed spine is real, not just the reported layer.

### Phase 3 — The blinded seed & pre-registration *(own spec+plan)*
- **Entry:** Phase 2 licensed spine demonstrated.
- **Deliverables:** the assembled blinded seed corpus (admissibility-tagged); the pre-registered derivation plan with α locked.
- **Exit gate:** an independent reviewer confirms the seed contains no answer-leakage; `commitment_hash` recorded; α-slot charged.

### Phase 4 — The derivation run (the forge) *(own spec+plan) — HEADLINE*
- **Entry:** Phase 3 seed sealed.
- **Deliverables:** the generative proposer walks the fusion catalog → instantiates `sense_and_kill` per fusion → SELECT ranks by info-gain × stakes → defeat graph prunes → grounded extension resolves. Emit the certificate (June calibration/certificate machinery).
- **Exit gate (the whole program's crux):** RUNX1-RUNX1T1 + topology + direct-caspase surfaces as the grounded extension under the locked plan; the certificate verifies. **Honest fallback if the forge can't invent the topology move:** demote to human-proposed candidates + engine licenses/ranks/prunes (a weaker but true claim — a research-strategy engine, not a muse). Decide the framing *before* the run, not after.

### Phase 5 — The wedge & the demo *(own spec+plan)*
- **Entry:** Phase 4 result (either the strong or the fallback framing).
- **Deliverables:** the auditable-derivation artifact (target + argument + defeaters + cheapest-next-experiment); the viewer rendering the design corpus as a live argument graph; the "next three targets" the engine surfaces beyond Durendal (PAX3-FOXO1, SS18-SSX, NPM1-ALK), each with its own Gate-1; the investor framing (§1's three properties made concrete).
- **Exit gate:** a coherent narrated demo runs end-to-end from a clean checkout.

---

## Phase 1 — TDD task decomposition

**Module scaffold.** All Phase 1 code lives in a new `src/polymer_claims/synbio/` package plus a test tree `tests/synbio/`. No grammar/protocol changes; no new `Corpus` collection; no heavy deps (Phase 1 uses only the grammar leaf primitives, already core).

**Before you start — read these templates:**
- `grammar/src/polymer_grammar/leaf.py` — the L0 sum type: `QuantityLeaf` (note the `_basis_discipline` validator: `unit` is allowed **only** for `FUNDAMENTAL`; `DERIVED` **must** carry `formula`), `CategoricalLeaf`, `ExistenceLeaf`, `PropositionLeaf`.
- `src/polymer_claims/methyl_adapters.py` — `region_delta_beta_claim(...)`, the closest claim-factory template (how a leaf is wrapped into a full `Claim` with subject, pattern, roles, provenance).
- `src/polymer_claims/real_kernel_proof.py` — the proven `run_cycle` wiring, for reference on how a claim reaches a status. Phase 1 does **not** license (no recompute); it stops at a validated CONJECTURED claim.

**The five claims (fixed content — the numbers, units, and sources are not TBD):**

| # | Claim | Leaf mapping | Source | Stresses |
|---|---|---|---|---|
| C1 | Single Watson-Crick mismatch discrimination energy ≈ 2 kcal/mol (range 1–3) vs kT ≈ 0.62 kcal/mol at 310 K | `QuantityLeaf(FUNDAMENTAL, unit="kcal/mol", value=2.0, uncertainty=1.0)` | programmable-living-medicines Part I | the FUNDAMENTAL+unit path (UCUM code choice) |
| C2 | ADAR RNA-sensor dynamic range ≈ 277-fold | `QuantityLeaf(DERIVED, formula="edited_payload/unedited_payload", value=277.0, unit=None)` | Part III | DERIVED+formula path; **context-conditioning gap** |
| C3 | CAR triggering threshold ≈ 10²–10⁴ molecules/cell | `QuantityLeaf(DERIVED, formula="antigen_copies_at_half_max_activation", value=1e3, uncertainty=…)` | Part VI/VII | **interval/range gap** (single value+uncertainty can't carry two orders of magnitude honestly) |
| C4 | Endosomal escape efficiency ≈ 1–5% | `QuantityLeaf(DERIVED, formula="cytosolic_fraction/endosomal_uptake", value=0.03)` | Part XIII | interval gap again; flags the multiplicative-bottleneck defeater |
| C5 | Above a threshold affinity, single-base discrimination degrades (non-monotonic) | `PropositionLeaf(warrant_type="mechanistic_analogy", data=…, warrant=…)` | Part II | whether a **principle/defeater** is a first-class claim with expressible warrant |

### Task 1: Scaffold the `synbio` package + the claim-source registry

**Files:**
- Create: `src/polymer_claims/synbio/__init__.py`
- Create: `src/polymer_claims/synbio/sources.py`
- Test: `tests/synbio/test_sources.py`

**Interfaces:**
- Produces: `ClaimSource(ref: str, title: str, admissibility: str | None)` (a frozen dataclass/`_Model`) recording a primary-literature citation and, optionally, its firewall admissibility tag; `SOURCES: dict[str, ClaimSource]` keyed by short id (e.g. `"PLM-I"`, `"PLM-III"`).

- [ ] **Step 1: Write the failing test**

```python
from polymer_claims.synbio.sources import SOURCES, ClaimSource

def test_sources_carry_ref_and_are_frozen():
    s = SOURCES["PLM-III"]
    assert isinstance(s, ClaimSource)
    assert s.ref  # non-empty citation
    # admissibility is populated later (Phase 3); None is legal in Phase 1
    assert s.admissibility is None or isinstance(s.admissibility, str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/synbio/test_sources.py -v`
Expected: FAIL with `ModuleNotFoundError: polymer_claims.synbio.sources`.

- [ ] **Step 3: Write minimal implementation** — a frozen model + the five sources the Phase-1 claims cite (real ref strings from the treatise front-matter).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/synbio/test_sources.py -v` → PASS.

- [ ] **Step 5: Commit** — `feat(synbio): claim-source registry scaffold`.

### Task 2: C1 — the FUNDAMENTAL quantity claim factory

**Files:**
- Create: `src/polymer_claims/synbio/claims.py`
- Test: `tests/synbio/test_claims_c1.py`

**Interfaces:**
- Consumes: `polymer_grammar.leaf.QuantityLeaf`/`MeasurementBasis`, the `Claim` constructor pattern from `methyl_adapters.region_delta_beta_claim`.
- Produces: `mismatch_energy_claim() -> Claim` — a CONJECTURED claim whose single leaf is `QuantityLeaf(measurement_basis=FUNDAMENTAL, unit="kcal/mol", value=2.0, uncertainty=1.0)`, provenance `generated_by=LITERATURE_EXTRACTED` with `method`/`version` = `SOURCES["PLM-I"]` and `search_cardinality=1` (a reported fact — NOT `AGENT_GENERATED`; see Phase 0 spec §3).

- [ ] **Step 1: Write the failing test**

```python
from polymer_claims.synbio.claims import mismatch_energy_claim
from polymer_grammar.leaf import QuantityLeaf, MeasurementBasis
from polymer_grammar.status import Status  # confirm exact import at build time

def test_c1_is_fundamental_energy_and_conjectured():
    claim = mismatch_energy_claim()
    leaf = claim.leaves[0]  # confirm accessor against Claim shape
    assert isinstance(leaf, QuantityLeaf)
    assert leaf.measurement_basis is MeasurementBasis.FUNDAMENTAL
    assert leaf.unit == "kcal/mol"
    assert leaf.value == 2.0 and leaf.uncertainty == 1.0
    assert claim.status is Status.CONJECTURED  # unlicensed: reported, not recomputed
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/synbio/test_claims_c1.py -v` → FAIL (`mismatch_energy_claim` undefined). *If the accessor `claim.leaves[0]` or `claim.status` is wrong, fix the test against the real `Claim` shape from the template before proceeding — do not guess.*

- [ ] **Step 3: Implement** `mismatch_energy_claim()` by mirroring `region_delta_beta_claim`'s claim-assembly, swapping in the FUNDAMENTAL leaf and a `subject` naming "Watson-Crick single mismatch at 310 K."

- [ ] **Step 4: Run to verify it passes** → PASS.

- [ ] **Step 5: Commit** — `feat(synbio): C1 mismatch-energy fundamental-quantity claim`.

### Task 3: C2 — the DERIVED quantity claim + the context-conditioning gap

**Files:**
- Modify: `src/polymer_claims/synbio/claims.py`
- Test: `tests/synbio/test_claims_c2.py`

**Interfaces:**
- Produces: `adar_dynamic_range_claim() -> Claim` — leaf `QuantityLeaf(DERIVED, formula="edited_payload/unedited_payload", value=277.0, unit=None)`.

- [ ] **Step 1: Write the failing test**

```python
from polymer_claims.synbio.claims import adar_dynamic_range_claim
from polymer_grammar.leaf import MeasurementBasis

def test_c2_derived_requires_formula_and_no_unit():
    claim = adar_dynamic_range_claim()
    leaf = claim.leaves[0]
    assert leaf.measurement_basis is MeasurementBasis.DERIVED
    assert leaf.unit is None          # validator forbids a unit on DERIVED
    assert leaf.formula               # validator requires a formula
    assert leaf.value == 277.0
```

- [ ] **Step 2: Run to verify it fails** → FAIL.

- [ ] **Step 3: Implement** `adar_dynamic_range_claim()`.

- [ ] **Step 4: Run to verify it passes** → PASS.

- [ ] **Step 5: GAP PROBE (no code) — record the finding.** In a new `tests/synbio/test_context_gap.py`, write an *expected-to-fail-cleanly* assertion documenting that the 277-fold value is **context-dependent** (it degrades outside the reported cell line) and the `QuantityLeaf` has **no field to carry that context**. Mark it `@pytest.mark.xfail(reason="grammar gap: QuantityLeaf lacks context-conditioning; see gap report")` and append the finding to `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`.

- [ ] **Step 6: Commit** — `feat(synbio): C2 ADAR dynamic-range claim + context-conditioning gap probe`.

### Task 4: C3 + C4 — interval-valued claims + the range gap

**Files:**
- Modify: `src/polymer_claims/synbio/claims.py`
- Modify: `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`
- Test: `tests/synbio/test_claims_intervals.py`

**Interfaces:**
- Produces: `car_threshold_claim() -> Claim` and `endosomal_escape_claim() -> Claim`.

- [ ] **Step 1: Write the failing test** — assert both build as DERIVED leaves with a representative point value and a `formula`, and assert (documenting the gap) that the two-orders-of-magnitude spread of C3 cannot be faithfully carried by a single `value`+`uncertainty`.

```python
from polymer_claims.synbio.claims import car_threshold_claim, endosomal_escape_claim

def test_c3_c4_build_and_expose_range_gap():
    c3, c4 = car_threshold_claim(), endosomal_escape_claim()
    assert c3.leaves[0].value == 1e3 and c4.leaves[0].value == 0.03
    # documented gap: a symmetric uncertainty cannot express 1e2..1e4 honestly
    assert c3.leaves[0].uncertainty is None  # we refuse to fake a symmetric bar
```

- [ ] **Step 2: Run to verify it fails** → FAIL.
- [ ] **Step 3: Implement** both factories; leave `uncertainty=None` for C3 rather than fabricate a symmetric error bar.
- [ ] **Step 4: Run to verify it passes** → PASS.
- [ ] **Step 5: Record** the interval/range gap in the gap report (candidate resolutions to weigh in Phase 2: an additive `IntervalLeaf`, or a `[low, high]` on `QuantityLeaf` — both touch grammar purity, so flag as a real cost).
- [ ] **Step 6: Commit** — `feat(synbio): C3/C4 interval claims + range gap`.

### Task 5: C5 — the principle/defeater as a proposition claim

**Files:**
- Modify: `src/polymer_claims/synbio/claims.py`
- Test: `tests/synbio/test_claims_c5.py`

**Interfaces:**
- Produces: `affinity_discrimination_law_claim() -> Claim` — a `PropositionLeaf(warrant_type="mechanistic_analogy")` capturing the specificity-wall as a general law (`data` = the observation, `warrant` = kinetic-proofreading mechanism, `rebuttal` = where it fails).

- [ ] **Step 1: Write the failing test**

```python
from polymer_claims.synbio.claims import affinity_discrimination_law_claim
from polymer_grammar.leaf import PropositionLeaf

def test_c5_is_a_warranted_proposition():
    claim = affinity_discrimination_law_claim()
    leaf = claim.leaves[0]
    assert isinstance(leaf, PropositionLeaf)
    assert leaf.warrant and leaf.data
    assert leaf.warrant_type == "mechanistic_analogy"
```

- [ ] **Step 2: Run to verify it fails** → FAIL.
- [ ] **Step 3: Implement** `affinity_discrimination_law_claim()`.
- [ ] **Step 4: Run to verify it passes** → PASS.
- [ ] **Step 5: GAP PROBE — record** the defeater semantics. `defeat.py` confirms defeat is a corpus-level edge graph over claim *ids*, leaf-type-agnostic — so a `PropositionLeaf` law defeating the SNV lane is expressible. The real finding (Phase 0 spec §2b): a reported claim with `strength=None` is never Pareto-dominated, so an unlicensed prior could knock out a LICENSED claim — therefore reported-stratum edges MUST be `provisional=True` (inert until the source gains standing). Record this constraint for Phase 2's `sense_and_kill` wiring. Append to the gap report.
- [ ] **Step 6: Commit** — `feat(synbio): C5 affinity–discrimination law as proposition defeater`.

### Task 6: The probe harness + gap report finalization

**Files:**
- Create: `src/polymer_claims/synbio/probe.py`
- Modify: `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`
- Test: `tests/synbio/test_probe.py`

**Interfaces:**
- Produces: `build_all() -> list[Claim]` (the five factories) and `probe_report() -> dict` (per-claim: leaf kind, validated bool, status, source ref, gap tags).

- [ ] **Step 1: Write the failing test** — assert `build_all()` returns 5 claims, all validate through the grammar, all are CONJECTURED, and `probe_report()` enumerates the recorded gaps (context-conditioning, interval, defeater-origin).

- [ ] **Step 2: Run to verify it fails** → FAIL.
- [ ] **Step 3: Implement** `build_all` / `probe_report`.
- [ ] **Step 4: Run to verify it passes** → PASS.
- [ ] **Step 5: Finalize** the gap report: for each gap, state the constraint, the current IR behavior, the candidate resolution, its purity cost, and — per the expansion doctrine — its **expansion_class** (general / analysis / subject / domain) and the **backward-compatibility plan** (which additive change, and how the byte-identical proof will be shown). This document is the **entry gate for Phase 2**.
- [ ] **Step 6: Run the full suite** — `scripts/check-all.sh` (or the repo's canonical runner). Expected: all green, new `tests/synbio/` included.
- [ ] **Step 7: Commit** — `feat(synbio): formalization probe harness + grammar gap report`.

---

## Cross-cutting — the expansion doctrine & the grammar gap-log (agent-science mode)

This is the meta-goal of applying Polymer Claims to any new field, and it governs every phase. **The point of onboarding a new domain is to expand what the IR can ingest — never to rearrange it to suit one field.** We are always debugging and always expanding; we never reduce scope. When a field engages the schema, we watch closely for where the IR strains, and we treat each strain as a candidate *additive* expansion, classified and backward-compatible.

**Classify every gap by the scope of its fix** (this decides where the change lands and how much it compounds):

| Class | Meaning | Lands in | Value |
|---|---|---|---|
| **general** | adapts a wholly new *kind* of input; helps every field | a core primitive (a new `Leaf` variant, a strength axis) | highest — compounds across all domains |
| **analysis-specific** | a statistic/method the IR can't yet carry | a pattern or an analysis-profile extension | high — reused by any field using that method |
| **subject-specific** | a new entity/ontology slot | the subject/roles layer, ontology binding | medium |
| **domain-specific** | a concept meaningful only to this field | a **domain-namespaced pattern/extension**, never the core leaf | contained by design |

**The two rules that keep expansion from becoming distortion:**
1. **General to the general, domain to the periphery.** A general gap (e.g. context-conditioned strength, interval values) is fixed in the core primitive so *every* field gains it. A domain-only concept (e.g. sensor-topology) is added as a namespaced pattern/extension so the core stays clean and lopsided-toward-synbio never happens.
2. **Additive-or-nothing, proven.** No expansion ships unless every existing corpus still validates byte-identically and its suite stays green (the Global-Constraints proof obligation). An expansion that would break, narrow, or reinterpret an existing field's claims is rejected and re-designed as additive.

**The gap-log** `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md` is the living record. Each entry carries: the constraint, current IR behavior, candidate resolution, **expansion_class** (from the table), **purity/backward-compat cost**, and the byte-identical proof once resolved. Two gaps are already predicted from reading `leaf.py`, both **general** (they help every field, not just synbio): **context-conditioned strength** and **interval/range values**. Never a silent workaround.

## Decision points (resolve at Phase 0 sign-off; defaults in brackets)

1. **Codename** — [Wayland]. Yours to keep or change.
2. **Repo vs. Research** — lift the compendia into the repo (STRATA precedent) or ingest in place from `Research/`? [Ingest in place read-only; commit only derived claims.]
3. **Blinding strictness** — date-cutoff + conclusion-stripping together [yes], or cutoff alone? The former is more defensible and is the recommendation.
4. **Headline target** — re-derive **Durendal (RUNX1-RUNX1T1)** directly [yes, it's the point], or warm up on a higher-expression validation fusion (PAX3-FOXO1) first to isolate the actuation-selection step at maximum signal? [Warm up in Phase 2's licensed-spine gate; headline on Durendal in Phase 4.]
5. **Fallback framing** — commit *now* to the honest position that a null forge result (can't invent the topology move) becomes the research-strategy claim, not a failure. [Yes.]

## Risks & mitigations

- **Answer-leakage / circularity (highest).** The treatise knows the answer. → The §4 firewall (date-cutoff + conclusion-stripping + independent review + pre-registration). If the boundary can't be drawn cleanly, the whole derivation claim collapses — better to find that at Phase 3 than at demo.
- **Low formalization yield** (Tier 3 dominates). → Phase 1 measures the real yield on 5 hard cases *before* committing to ingestion. If Tier-1/2 is thin, re-scope.
- **Grammar can't carry context/intervals.** → Surfaced in Phase 1 as explicit gaps with purity-costed resolutions; decided deliberately in Phase 2, not patched silently.
- **The creative-leap problem** (proposer won't invent topology-rejection). → Pre-committed fallback (decision point 5). The strategy-engine claim is weaker but true and still not-me-too.
- **Wet verification is out of scope** (compute boundary). → The derivation licenses to a *proposed, attestable* Gate-1; we never claim the therapy works, only that it is the grounded extension worth the cheapest experiment.

---

## Execution handoff

Phase 1 is task-ready. Phases 2–5 each need their own spec + plan authored at phase entry.

**Two execution options for Phase 1:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, fast iteration (`superpowers:subagent-driven-development`).
2. **Inline Execution** — tasks in this session with checkpoints (`superpowers:executing-plans`).

Before either, **Phase 0 (the design spec) should be written and signed** — it ratifies the taxonomy and firewall this plan assumes.
