# STRATA pharmacogenomic licensing — design

**Date:** 2026-07-08
**Status:** Design (approved for planning). Supersedes no prior spec; new build stage.
**Telos:** Populate the claims universe with *real, licensed, computed* science —
GDSC methylation-marker → drug-response associations run through the actual
licensing gate — so the universe stops being a demo of plumbing and starts
carrying evidential weight. This is build-path step 4 (a legible wedge domain)
grounded in real data.

---

## 0. One-paragraph summary

The STRATA engine (lifted from the `Hack` hackathon project into
`src/polymer_claims/strata/`) proposes candidate `(drug, marker)` pairs from
GDSC cell-line data. It is **untrusted scaffolding** — a proposer, never a source
of standing. A batch runner turns each candidate into a `Claim`, pre-registers
it, and runs it through `run_cycle`, where **two independent adapter legs
re-compute** the association on a pinned, content-addressed SE-Contract; the
kernel licenses only what agrees and clears the e-LOND FDR gate. Positive control
MTAP→Palbociclib must license; negative control MGMT→Temozolomide must not; that
check is a calibration **instrument and publish guard**, not a claim-status gate.
Non-hits and controls persist as **PENDING un-licensed residue** (the negative
space of the morphospace), never as "refuted." Because the hypotheses come from
GDSC and are tested on GDSC, stage 1 is honestly capped at **REPRODUCED** tier
with **CONFIRMATORY** severity; genuine **REPLICATED** + held-out severity is a
deliberate stage 2 over an independent screen (PRISM/CTRP).

---

## 1. Foundations alignment (why this design is shaped the way it is)

This design was cross-checked against the foundations before planning. Verdict:
substantially aligned, no architectural violations; the corrections below are what
make it *canonically* correct. Citations are to the repo docs/code as of this date.

| Foundation | Requirement | How this design honors it |
|---|---|---|
| Compute boundary (`foundations/compute-boundary.md`) | Polymer specifies/orchestrates/witnesses/certifies; never a *hosted compute utility*. Local-first "Science Claw" = BYO-compute, single-user, is explicitly on the right side. | All compute in the umbrella package; GDSC data gitignored + local-only; precedent = `verify-kernel --real`. **The witness/attested log must be air-gapped from the batch runner** ("the log cannot be produced by the thing being witnessed"). |
| de Bruijn kernel (`foundations/epistemology.md` §8) | Proposers (AI, human, deterministic) are untrusted scaffolding; nothing earns standing except by passing the kernel. | STRATA's `r_adj` is proposal-only; the two legs re-compute; only `run_cycle`/`verify_stage` licenses. |
| e-value / independence (`epistemology.md` §2, §7) | Severity = betting e-value; e-values multiply **only** across error-independent cohorts. | Single-leg betting e-value per claim; **no cross-tissue product** (tissues share the GDSC apparatus). |
| Independence tiers (`grammar/.../licensing.py`, `GLOSSARY.md`) | REPLICATED needs ≥2 `dimnames_hash` **and** sub-τ shared-cause overlap. | Two legs / one dataset = **REPRODUCED**; `shared_cause_factors` populated so §E fires and correctly withholds REPLICATED. |
| Measurement seam (`foundations/measurement-foundation.md`) | A criterion must be invariant under the assay scale's admissible transformations. | Licensing statistic is a median-split / rank test (monotone-invariant); linear `r_adj` is demoted to proposal ranking. |
| Residualism (`foundations/residualism.md`) | Un-licensed ≠ false; residue is first-class, structured, queryable; never deleted. | Non-hits + MGMT land as PENDING residue retaining e-value + FDR history; morphospace occupied/empty/forbidden. |
| Verification philosophy (`canonical-spec §5`) | The gate licenses (warrant), it does not mean (truth); consistency is warrant-only. | License = REPRODUCED air-gap + e-LOND discovery; Duhem fold can demote but never refunds the license. |
| Corpus / purity invariants | `Corpus` = exactly 4 collections; grammar/protocol pure + numpy-free. | All new code in the umbrella; zero grammar/protocol change; Corpus stays 4. |
| Calibration = instrument (`canonical-spec §5c`) | Control/calibration machinery changes no claim status. | Control check is a publish guard + DEFINITIONAL-style calibration record only. |

---

## 2. What is already done (the surgical lift)

Merged mechanically before this spec (verified: engine recovers MTAP→Palbociclib
at L3, r_adj=−0.196, and MGMT→Temozolomide as a non-hit, on real GDSC data from
inside the repo; ruff clean; core import unaffected):

- `src/polymer_claims/strata/` — `engine/` (associate, annotate, cluster,
  features), `data/gdsc.py` (COSMIC-keyed loaders), `config.py` (env-overridable
  `STRATA_DATA_ROOT`, no import side effects), `mechanism.py` (the refactored
  tissue-adjusted L0–L3 scorer + `positive_control`/`negative_control`).
- `data/pharmaco/gdsc/` — gitignored, ~81M (methylation matrix, GDSC2
  dose-response xlsx, model list).
- `pyproject.toml` — opt-in `[strata]` extra (pandas/scipy/statsmodels/
  scikit-learn/lifelines/openpyxl) so the core wheel stays lean.

The deployment surface (site/, api/, PDFs, `_archive/`) was intentionally left in
`Hack/`. PRISM/CTRP + CCLE data were left behind — they are the stage-2 material.

---

## 3. The trust positioning

```
  STRATA mechanism scan            two independent legs             kernel
  (PROPOSER, untrusted)            (RECOMPUTE, on pinned data)      (LICENSES)
  ─────────────────────            ────────────────────────        ──────────
  rank (drug, marker) by  ──────▶  Leg A: tissue-stratified   ──▶  verify_stage:
  r_adj (Pile A / de Bruijn)       mean-diff → betting e-value      REPRODUCED iff
                                   Leg B: rank test (air-gap gate)  legs agree +
                                   both_satisfy_criterion           e-LOND discovery
```

STRATA's number is never licensed. The legs resolve the pinned SE-Contract and
compute independently. Only `run_cycle`/`verify_stage` confers standing.

---

## 4. The claim model

Each licensable candidate becomes one `Claim` built by a new factory
`marker_drug_claim(...)` in `src/polymer_claims/pharmaco_adapters.py` (mirroring
`exec_adapters.mean_diff_claim`).

- **Pattern:** reuse the registered `adjusted_effect@v1`. The licensed content is a
  **tissue-adjusted association** ("gene-G methylation is associated, tissue-
  adjusted, with drug-D response"), *not* a causal edge — `adjusted_effect@v1`'s
  `excluded_applications` forbids causal-edge assertions. The mechanistic reading
  lives as an L1 interpretation/warrant, not as licensed content.
- **Subject:** `CompositeSubject(parts=(GeneOrProtein(gene), OntologyTerm(CHEBI
  drug)), relation="correlational")`. There is no single gene/drug subject kind.
- **Profile / oracle:** a new pharmaco apparatus profile whose
  `ApplicabilityDomain.subject_kinds` admits the composite subject kind (else the
  claim silently resolves out-of-domain → capped UNVALIDATED). Modeled on the
  existing methylation apparatus oracle.
- **Leaf:** a `CategoricalLeaf` (`ontology_term="pharmacogenomic_association"`),
  matching every shipped Polymer real-data claim (the methyl and mean-diff claims).
  The licensed effect (the Polymer-computed median-split ΔAUC) lives in the verify
  result, **not** baked into a leaf — STRATA's `r_adj` (and its L0–L3 grading) never
  enters the `Claim`, the leaves, or the provenance. (An L0 `QuantityLeaf` for
  sheaf-gauge participation is a possible later enhancement; deferred to keep the
  claim STRATA-free and aligned with shipped practice.)
- **Strength:** `None` for the generated claim (matches every shipped real-data
  claim; a strength-bearing claim would hit the cardinality-scaled bar and never
  license). Earned, oracle-capped strength is a later reconciliation.
- **Provenance:** `generated_by=GenerationMode.AGENT_GENERATED` **with an
  `agent_id`** (required or construction raises); a `preregistration_hash`;
  `search_cardinality` = the *actual* selection breadth that surfaced the claim
  (the per-drug mechanism-gene count only if selection truly ranged over that set);
  `prior_cohorts` = the GDSC cohort `dimnames_hash` — which correctly marks this as
  self-confirmation (see §8).

## 5. The gate

- **e-value from one leg.** Leg A computes a **tissue-stratified mean difference in
  drug response (AUC) between high- and low-methylation lines on a median split**,
  fed to the existing `betting_evalue` (`evidence.py`; boundedness-only,
  deterministic, monotone-friendly). Leg B is a **rank-based tissue-stratified
  test** — the corroborating air-gap gate. They must agree via
  `both_satisfy_criterion`; only Leg A feeds the e-value (mirrors n-DMP, where the
  rank leg gates but does not feed the e-value). **No product of the two legs.**
- **Independence tier = REPRODUCED.** Two legs on one dataset. Every materialization
  **populates `shared_cause_factors`** (GDSC manifest, normalization, reference
  genome, stat library, cell-line panel) so the §E `cohorts_error_independent`
  gate fires. Leaving the factors empty trips the code path that would mint a
  *false* REPLICATED license (the "tier trap") — this design forbids that.
- **No cross-tissue e-value product.** Tissues within GDSC are not error-
  independent; the single-tissue (or pooled tissue-stratified) e-value stands.
- **Pre-registration.** `register_test` charges and **locks** the e-LOND α-slot per
  claim *before* the association is seen; `resolve_test`/`elond_decisions` decides
  against the locked α. The 286-drug scan is exactly the multiplicity surface this
  defends; the slot must be locked per test before data is seen.

## 6. Residue, controls, morphospace

- **Residue.** Non-hits and MGMT→Temozolomide land as **PENDING un-licensed
  residue** in the `claims` collection, retaining their e-value + FDR history —
  queryable and method-diagnostic, never "refuted" (terminal). Rejected means
  unwarranted-for-now, never false.
- **Controls as instrument.** The batch computes MTAP→Palbociclib (must license)
  and MGMT→Temozolomide (must not) as a DEFINITIONAL-style calibration record and a
  **publish guard**: the runner refuses to publish the universe if the controls
  misbehave. It changes **no** claim's epistemic status and lives outside the
  4-collection Corpus.
- **Morphospace framing.** Occupied = licensed; empty-but-reachable = the frontier
  (where to send agents next); forbidden = high-confidence negatives. This ties the
  negative space to the generative telos (the ⑤ forbidden-vs-unobserved backlog
  item) and to `measurement-foundation.md` §6.3.

## 7. Provenance, witness, flywheel

- **Ingestion.** Build a content-addressed SE-Contract `se:gdsc_pharmaco@1` via a
  new `src/polymer_claims/ingest/gdsc_pharmaco.py` (mirroring `ingest/tcga_laml.py`
  → `build_contract`): methylation × drug-response × tissue, keyed on COSMIC_ID,
  with `dimnames_hash`/`profile_hash`/`semantic_run_id`. Gitignored; built on
  demand. Provenance roots at ingestion, not "a file the batch found."
- **Witness air-gap.** Every licensing `Satisfaction` carries an in-toto/SLSA
  attested execution log (this code, on this hashed data, produced this hashed
  output, in this environment), and the log substrate must be one the batch runner
  does not control. The batch generator must not mint its own witness.
- **Flywheel.** Enumerated claims enter the **live Corpus** and stay subject to the
  standing daemons (DRIFT re-opens content-drifted licenses; the Duhem fold demotes
  frustrated cycles; reinstatement can reopen). This is batch *seeding*, not a
  static run_cycle-bypassing export.

## 8. The honest ceiling and stage 2

Because the hypotheses come from GDSC and are tested on GDSC, stage 1 is capped:

- **Tier:** REPRODUCED (air-gap on one dataset).
- **Severity:** CONFIRMATORY (self-confirmation — `prior_cohorts` = the test cohort),
  not HELD_OUT.

This is surfaced, not hidden. The scientifically load-bearing result is stage 2:

- **Stage 2 (deferred, PRISM/CTRP):** re-test surviving leads on a
  provenance-distinct screen with sub-τ shared-cause overlap → **REPLICATED** tier,
  **HELD_OUT** severity, and the *sanctioned* e-value multiply. This is the
  independent-cohort prediction that turns "self-consistent bootstrap" into
  evidence. It needs the stage-2 data (`external_drug.py` + PRISM/CTRP) left out of
  the lift.

## 9. Components to build (all umbrella-side; grammar/protocol untouched)

1. `src/polymer_claims/ingest/gdsc_pharmaco.py` — SE-Contract builder
   `ingest_gdsc_pharmaco(data_dir) -> str` returning `se:gdsc_pharmaco@1`.
2. `src/polymer_claims/pharmaco_adapters.py` —
   - `PharmacoMeanDiffAdapter` (identity `pharmaco-meandiff`; feeds e-value),
   - `PharmacoRankAdapter` (identity `pharmaco-rank`; air-gap gate),
   - a `PHARMACO_ASSOC` capability cell (`agreement_mode="both_satisfy_criterion"`),
   - `pharmaco_independent_registry()` (distinct owner + impl-hash),
   - the pharmaco apparatus profile/oracle admitting the composite subject,
   - `marker_drug_claim(...)` factory.
3. `src/polymer_claims/pharmaco_evidence.py` (or a helper in `evidence.py`) — the
   tissue-stratified mean-diff betting e-value for a `(drug, marker)` claim.
4. `src/polymer_claims/strata_populate.py` + CLI `strata-populate` — the batch
   runner: mechanism scan → per-claim `register_test` → `run_cycle` with the two
   legs + registry + per-claim evidence → land residue as PENDING → control
   instrument / publish guard → seed the live Corpus + export topology.
5. Wiring: a `[strata]`/`[serve]`-gated CLI subcommand; lazy imports so the core
   import stays clean without the extra.

## 10. Testing strategy

Behavior, not implementation; stub/fixture-based, **no network in CI**.

- **Adapters:** on a small synthetic contract, the two legs agree on a planted
  signal and disagree on planted noise; the air-gap holds PENDING when only one leg
  satisfies.
- **e-value:** `betting_evalue` on a planted marker→drug effect exceeds the
  discovery threshold; a null planted effect yields e ≈ 1 (no license).
- **Independence tier:** with `shared_cause_factors` populated for two
  same-GDSC tissues, `independence_tier_of` returns REPRODUCED and the cross-tissue
  product is withheld; a guard test asserts empty factors never silently mint
  REPLICATED (the tier-trap regression).
- **Pre-registration / multiplicity:** slots lock before the association; a fished
  hypothesis pays its slot.
- **Residue:** a non-hit persists as PENDING with e-value + FDR history, never a
  terminal reject.
- **Control instrument:** on the real (gitignored) contract, MTAP→Palbociclib
  licenses and MGMT→Temozolomide does not — marked slow / data-gated, run behind the
  `[strata]` extra, excluded from core CI.
- `scripts/check-all.sh` green; `install-smoke` without `[strata]` green.

## 11. Open questions / deferred

- **Shared-frame independence (the ② backlog item).** Reusing the same two legs
  across all 286 drugs is the code-independence ≠ conceptual-independence risk the
  foundations flag as open. Stage 1 must **log the breadth of independence actually
  sampled**; promoting the common-cause overlap to a first-class defeasible claim is
  future work.
- **Earned strength.** The 6-axis vector (magnitude ← |effect|, evidence_against_null
  ← e-value, severity ← SeverityProvenance, certainty ← tissue-consistency/CI,
  world_contact ← substrate tier, explanatory_virtue ← mechanism rationale),
  oracle-capped, is deferred until the reconciliation with the cardinality bar is
  built.
- **Stage 2 (PRISM/CTRP)** — its own spec.
- **A registered mechanism/causal pattern** — only if/when we want to license causal
  edges rather than adjusted associations.
