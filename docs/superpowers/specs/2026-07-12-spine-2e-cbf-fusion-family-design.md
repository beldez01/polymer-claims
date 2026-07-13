# Phase 2e — the CBF-AML fusion-partner re-expression family (design)

**Status:** approved (brainstorm 2026-07-12). Extends the licensed spine (2d-i→iii) to a *family* of claims from
the same two cohorts. Heavy reuse: `build_fusion_expr_contract`, `expression_floor_claim`, `license_replicated`.

## Goal

Generate and license a **2×2 family of fusion-partner re-expression floor claims** across TCGA-LAML + TARGET-AML,
generalizing the RUNX1-RUNX1T1 result. Two core-binding-factor (CBF) AML fusions, each with a gene specifically
elevated in it — the re-expressed fusion partner RUNX1T1 for t(8;21), and a validated CBFB-MYH11 transcriptional
target MN1 for inv(16) (medians, raw TPM; TARGET / TCGA):

|  | RUNX1T1 | MN1 |
|---|---|---|
| **t(8;21)+** | ~94 high (A, licensed) | ~7–9 (below floor) |
| **inv(16)+** | ~0 silent | ~69 / ~93 (clears floor) |
| **other** | ~0 silent | ~5–6 (below floor) |

Four floor+discrimination claims, all through the SAME pipeline (`expression_floor_claim` with different
`gene` + `level_a`/`level_b`):
- **A** — RUNX1T1 clears the 13 TPM floor in `t821` vs `other` (re-confirms the licensed result on the new contract).
- **B** — MN1 clears the 13 TPM floor in `inv16` vs `other` (new re-expression floor).
- **C** — RUNX1T1 clears the floor in `t821` vs `inv16` (specificity — RUNX1T1 distinguishes the two CBF-AMLs).
- **D** — MN1 clears the floor in `inv16` vs `t821` (specificity).

The specificity claims (C, D) are NOT a new claim type — they are the same floor+discrimination machinery with the
comparator `level_b` set to the OTHER fusion instead of `other`. Each marker is low outside its fusion, so the
C/D discriminations are large.

**Marker provenance (integrity — commit-before-data preserved).** The original design proposed MYH11 (the inv(16)
fusion partner), but data verification showed **gene-level MYH11 does NOT mark inv(16)** (median ~6 TPM in inv(16)
≈ ~6 in other; below the floor — the CBFB-MYH11 fusion carries only MYH11's 3′ exons and MYH11 has smooth-muscle
background). A genuine negative result, recorded. The inv(16) marker **MN1** was instead nominated from PRIOR
literature — a mechanistically-validated **direct CBFB-MYH11 transcriptional target** (CBFB-MYH11 knockdown
downregulates MN1; the SPARC/ST18/MN1 target set, bioRxiv 453845) — THEN verified in both cohorts (TCGA inv(16)
median 93 TPM, 10/10 clear the floor; TARGET 69 TPM). Nominated from independent prior knowledge, not fished from
the licensing cohorts, so pre-registration holds. (ST18 had the cleanest fold-change but sits ~10 TPM, below the
floor; MYH11/CYP2E1 fail — all recorded.)

## Data — new 3-valued contracts (reuse the pipeline)

- `se:tcga_laml_cbf_expr@1` and `se:target_aml_cbf_expr@1`: `Sample_Group ∈ {t821, inv16, other}` (3-valued;
  `build_fusion_expr_contract` already sets `Sample_Group = fusion_status[s]` for any label set), panel =
  **{RUNX1T1 (ENSG00000079102), MN1 (ENSG00000169184), ACTB, GAPDH}**. Fetched from the SAME already-downloaded
  TCGA/TARGET STAR-TPM matrices (log2→raw) + cytogenetics: `t821` iff `t(8;21)`, `inv16` iff `inv(16)`/`t(16;16)`,
  else `other` (karyotyped non-CBF). No-karyotype cases DROPPED. Distinct `dimnames_hash` per cohort.
- Cohort counts (probed): TCGA t821≈6/inv16≈11; TARGET t821≈90/inv16≈112 (RNA-seq∩karyotype narrows these;
  the extract prints the real n per group). MN1 = ENSG00000169184.
- Self-contained: big matrices already gitignored; new small extracts pinned under `data/{tcga,target}_cbf_fusion_expr/`.

## The floor (pre-registered, shared)

FLOOR = **13.0 TPM** for every family claim — the same domain-standard "robustly expressed" threshold, NOT
gene-tuned. The extract confirms each partner clears it in its fusion (RUNX1T1 in t821, MN1 in inv16) as a
sanity check, NOT a threshold source. A floor-robustness note is carried in the writeup.

## Claims + licensing (reuse)

- `propose_cbf_family_claims(ref) -> list[Claim]`: builds A/B/C/D via `expression_floor_claim(gene=..., floor=13.0,
  tissue="AML", level_a=..., level_b=..., search_cardinality=...)` — ids `floor-RUNX1T1-t821-vs-other`,
  `floor-MN1-inv16-vs-other`, `floor-RUNX1T1-t821-vs-inv16`, `floor-MN1-inv16-vs-t821`. Plus the ACTB control
  claim (`floor-ACTB-inv16-vs-other`, must NOT license).
- License the batch REPLICATED across the two CBF contracts via the existing `license_replicated` (per-claim
  isolation already handles ≥2 reference_leaf claims; each charges its own pre-registered e-LOND slot; the
  front-loaded γ_t means the strongest go first). Disjoint non-empty `shared_cause_factors` (same as 2d-iii).
- Each claim's discrimination e-value is between its `level_a` and `level_b` groups (the existing
  `expression_floor_evalue` / `_expr_split` read `level_a`/`level_b`).

## Tests

- **Family builds:** `propose_cbf_family_claims` returns the 5 claims (4 + ACTB control), all `CONJECTURED`, unique
  ids, each a `QuantityLeaf(value=13, low=13)` floor with the right `level_a`/`level_b` params.
- **Planted family licenses:** a synthetic 3-group contract (RUNX1T1 high only in t821, MN1 high only in inv16,
  ACTB high everywhere) → A/B/C/D LICENSED, ACTB not; the e-LOND ledger charges one test per claim.
- **Specificity is real:** on the planted fixture, claim C (RUNX1T1 t821-vs-inv16) licenses (RUNX1T1 high in t821,
  ~0 in inv16) AND the reverse mis-specified claim (RUNX1T1 inv16-vs-t821) does NOT (RUNX1T1 low in inv16).
- **Real run** (controller): license the family across `se:tcga_laml_cbf_expr@1` + `se:target_aml_cbf_expr@1`;
  record each claim's e₁/e₂/product/tier/status. Honest outcomes (some may PENDING at small n; the inv16 arm is
  well-powered: TARGET n≈112).

## Invariants

- `grammar/`/`protocol/` untouched, pure + numpy-free. `Corpus` stays 4. numpy umbrella-side (`[spine]`).
- Two-stratum (only recompute licenses), commit-before-data (floor + factors pre-registered), ONE e-LOND slot per
  claim, self-contained (big data gitignored, extracts pinned).

## Scope / tasks (for writing-plans)

1. TCGA + TARGET CBF contracts (`se:{cohort}_cbf_expr@1`) — controller-executed extracts (mirror 2d-i/2d-iii;
   3-valued labels + MN1), self-checks per group.
2. `propose_cbf_family_claims` + a family-build unit test + a planted-family license test (incl. the specificity
   test) + the `[spine]` reuse.
3. Real run across both CBF contracts → record tier/status/e-values for A/B/C/D + ACTB; continuity + writeup.

## Out of scope

Other fusions (inv(3), MLL — too few cross-cohort cases); a new claim type for "stays-below-floor" absence
(the specificity is captured by the vs-other-fusion discrimination); the Durendal re-derivation.
