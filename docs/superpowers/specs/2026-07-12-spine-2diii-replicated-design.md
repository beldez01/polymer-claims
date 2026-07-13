# Phase 2d-iii — cross-cohort REPLICATED license for the RUNX1-RUNX1T1 expression-floor spine (design)

**Status:** approved (brainstorm 2026-07-12). Third sub-project of the WAYLAND licensed spine; consumes
`se:tcga_laml_fusion_expr@1` (2d-i) + the 2d-ii licensing pipeline.

## Goal

Promote the RUNX1-RUNX1T1 expression-floor claim from single-cohort **REPRODUCED (PENDING at e=9.86, n=6)** to
**REPLICATED@LICENSED** by adding a second, error-independent cohort (**TARGET-AML**, pediatric, ~123 t(8;21)).
The two cohorts' independent betting e-values **multiply** (e₁·e₂) into the claim's single pre-registered
e-LOND slot; if the product clears the 32.9 first-test bar, the claim licenses at `IndependenceTier.REPLICATED`.
Honest outcome throughout: if the product still doesn't clear, it stays an honest PENDING.

## The §2E mechanism (mapped)

- `IndependenceTier` (`grammar/.../licensing.py:113-121`): REPRODUCED (agreeing impls share the dataset) →
  REPLICATED (≥2 datasets with distinct `dimnames_hash`; **the only tier that may MULTIPLY e-values**).
- Promotion (`licensing.py:180-193`): REPLICATED requires (a) ≥2 distinct non-None `dimnames_hash` among the
  satisfactions AND (b) `cohorts_error_independent(...) is not False`.
- Error-independence (`licensing.py:156-166` + `shared_cause.py:55-64`): decided by the **Jaccard overlap of the
  two cohorts' `MaterializationContext.shared_cause_factors`**; `< SHARED_CAUSE_TAU (0.5)` ⇒ independent.
- e-value combination (`src/polymer_claims/replication.py:104-133`): `e2 = betting_evalue(cohort B)`; if
  error-independent, `evidence[cid] = e1 * e2` folded into the SAME e-LOND slot (`resolve_test`,
  `verify.py:185`) — ONE test, not a second registration. The tier is stamped from the extra cohort-B
  satisfaction threaded via `replications={cid: (sat_b,)}` (`verify.py:317-323`).
- Driver: ONE `run_cycle`, pre-computing `ReplicationInputs` via `build_replication_inputs(corpus, base,
  bindings={cid: cohort_b_ref})` (precedent test `tests/test_2e_tiered_independence_e2e.py:27`).

## Second cohort — TARGET-AML (data, reuses 2d-i)

- **Expression:** `TARGET-AML.star_tpm.tsv.gz` (GDC hub / Xena, HTTP 200) — same log2(TPM+1) STAR format as
  TCGA-LAML (convert `raw = 2^x − 1`; verify the scale on fetch, as in 2d-i).
- **Fusion label:** cBioPortal `aml_target_2018_pub` `PRIMARY_CYTOGENETIC_CODE` (patient-level) — `fusion_pos`
  iff the code contains `t(8;21)` (probe: 123 t(8;21) across the cytogenetic universe). The RNA-seq∩karyotyped
  intersection is the case universe; no-karyotype cases DROPPED (never defaulted), same discipline as 2d-i.
- **Contract:** `se:target_aml_fusion_expr@1`, built by the SAME `build_fusion_expr_contract` (2d-i), same fixed
  4-gene panel (RUNX1T1/RUNX1/ACTB/GAPDH). Its `dimnames_hash` differs from TCGA's (distinct sample set) —
  satisfying the "≥2 distinct dimnames_hash" REPLICATED requirement.
- **Self-contained:** big matrix + raw clinical gitignored; small extract pinned (mirror
  `data/tcga_laml_fusion_expr/`).

## Error-independence declaration (user-ratified: error-independent)

The two cohorts are declared **error-independent** with **disjoint, non-empty** `shared_cause_factors`:
- TCGA: e.g. `("tcga-laml-cohort", "adult-aml-population", "tcga-karyotype", "gdc-tcga-batch")`.
- TARGET: e.g. `("target-aml-cohort", "pediatric-aml-population", "target-karyotype", "gdc-target-batch")`.
- Jaccard = 0 ⇒ `cohorts_error_independent = True` ⇒ REPLICATED-eligible + product allowed.

**Honesty rationale (documented, not tagged as a shared cause):** the cohorts DO share the GDC STAR-Counts
quantifier + hg38 + Ensembl annotation. This is a shared *method*, not a plausible shared *error cause* for THIS
claim — the RUNX1T1→t(8;21) signal is fusion-driven biology a standard quantifier does not manufacture, and the
cohorts are independent on the axes that matter (distinct pediatric-vs-adult populations, distinct karyotyping
labs, distinct sequencing batches). The shared method is recorded in `SOURCE.txt`/the writeup for auditability.
**Guardrail:** factor sets MUST be non-empty (empty ⇒ the §E gate goes inert and over-credits — mints REPLICATED
AND multiplies WITHOUT verifying independence, `licensing.py:182-183`) AND provably disjoint (overlap ⇒ silent
REPRODUCED cap). A test asserts the two sets are non-empty and Jaccard 0.

## Components

1. `data/target_aml_fusion_expr/build_extract.py` — one-shot fetch/extract/build (mirror 2d-i `build_extract.py`);
   TARGET-AML STAR TPM (log2→raw) + `PRIMARY_CYTOGENETIC_CODE` t(8;21) labels → pinned extract →
   `se:target_aml_fusion_expr@1`. Self-checks: fusion+ in a sane band (expect ≫6), RUNX1T1 fusion+ ≥5× fusion−,
   housekeeping flat.
2. `src/polymer_claims/expression_floor_replication.py` — the expression-floor analog of the methyl-only
   `replication.py::build_replication_inputs`: mirror it using `ExpressionFloorMeanAdapter`/`ExpressionFloorHLAdapter`
   + `expression_floor_evalue`, guarded to `impl == "expression::floor"`. Both legs must independently clear the
   floor on cohort B before B counts (mirrors `replication.py:95-99` + `both_satisfy_criterion`). Produces
   `(evidence=e1*e2, replications={cid: (sat_b,)})`.
3. `src/polymer_claims/expression_floor_populate.py` — add `license_replicated(corpus, claims, *, ref_a, ref_b,
   factors_a, factors_b)`: runs the per-claim cohort-A cycle (2d-ii), builds the cohort-B replication inputs,
   and threads `evidence`/`replications` into `run_cycle` with the disjoint factors. Reuses the per-claim
   isolation (the 2d-ii reference_leaf workaround still applies).

## Tests

- **Planted two-cohort REPLICATED** (synthetic contracts A + B, both strong, disjoint factors): the claim
  licenses at `IndependenceTier.REPLICATED`; the ledger charges ONE test (`n_tests == 1`); the product e-value
  is used.
- **Shared-cause cap:** same but with OVERLAPPING factors (Jaccard ≥ 0.5) → stays REPRODUCED, no multiply
  (guards the silent-cap risk by making it explicit/tested).
- **Empty-factors guard:** a test that empty `shared_cause_factors` is rejected/asserted-against before
  licensing (guards the over-credit risk).
- **Two distinct dimnames_hash:** assert the two contracts have different `dimnames_hash` (else B can't count).
- **Real run** (controller, slow): license RUNX1-RUNX1T1 across `se:tcga_laml_fusion_expr@1` +
  `se:target_aml_fusion_expr@1`; record e₁, e₂, e₁·e₂, tier, status. LICENSED@REPLICATED if the product clears
  32.9; honest PENDING otherwise. The ACTB control still must NOT license.

## Invariants

- `grammar/` and `protocol/` untouched, pure + numpy-free (the §2E machinery already exists there; we add an
  umbrella-side expression-floor replication builder). `Corpus` stays 4. numpy only umbrella-side (`[spine]`).
- Two-stratum: only the recompute licenses. Commit-before-data: floor/CAP/NULL_GAP + factor sets pre-registered.
- ONE e-LOND slot per claim (product folded in; never register cohort B as a second slot).
- Self-contained: both cohorts' big data gitignored, small extracts pinned.

## Scope / tasks (for writing-plans)

1. TARGET-AML contract — fetch/extract/build `se:target_aml_fusion_expr@1` + self-checks (controller-executed).
2. `expression_floor_replication.py` (build_replication_inputs analog) + unit tests (cohort-B satisfaction, e₂,
   both-legs-clear gate).
3. `license_replicated` in `expression_floor_populate.py` + the four tests above (planted REPLICATED, shared-cause
   cap, empty-factors guard, distinct dimnames_hash).
4. Real run TCGA+TARGET → record tier/status/e-values + continuity + memory + the headline writeup.

## Out of scope

A third cohort (BEAT-AML); other fusions (PAX3-FOXO1); the protocol reference_leaf/batch-license clean-up
(logged in 2d-ii); the Durendal headline re-derivation.
