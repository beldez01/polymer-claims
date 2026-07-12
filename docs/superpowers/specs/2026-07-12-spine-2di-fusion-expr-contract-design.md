# Phase 2d-i — TCGA-LAML fusion-expression SE-Contract (design)

**Status:** approved shape (brainstorm 2026-07-12). First sub-project of the WAYLAND licensed spine.
**Scope boundary:** 2d-i builds and validates the *data contract only*. **No licensing, no `run_cycle`, no
claim** — that is 2d-ii. 2d-i de-risks the data and reveals the real RUNX1T1 distribution.

## Goal

Build `se:tcga_laml_fusion_expr@1`: a feature×sample SE-Contract carrying TCGA-LAML RNA-seq expression
(TPM) for a small gene panel, with each case labeled fusion+/fusion− for the **RUNX1-RUNX1T1 (t(8;21))**
fusion. This is the measurement seam 2d-ii's two-leg recompute will license against.

## Why this shape

Expression is **net-new** — no RNA-seq/TPM contract exists; all current contracts are methylation-beta
(`meth::`) or pharmaco (`auc::`). We mirror `build_pharmaco_contract`
(`src/polymer_claims/ingest/gdsc_pharmaco.py:15-62`) verbatim: feature ids `expr::<GENE>`, TPM values, a
categorical group in `col_data`. The loader (`contracts/__init__.py:117`) pins `group_col=Sample_Group`, so
**the fusion label lives under `Sample_Group`** (values `"fusion_pos"` / `"fusion_neg"`), with `Fusion_Status`
and `tissue` as redundant self-documenting fields (mirrors pharmaco's parallel `tissue`).

## Data sources (all reachable; pin the extracted subset into `data/`)

- **Expression:** `TCGA-LAML.star_tpm.tsv.gz` (GDC hub / UCSC Xena, HTTP 200). STAR gene-level TPM,
  gene×sample. We extract only the small gene panel × LAML cases we use.
- **Fusion label — primary:** cBioPortal `laml_tcga_pub/data_sv.txt` (HTTP 200) — the RUNX1-RUNX1T1
  structural-variant call per sample.
- **Fusion label — independent robustness check:** cBioPortal `laml_tcga_pub/data_clinical_*.txt` t(8;21)
  cytogenetics/karyotype. Two methodologically independent calls of the same fusion; their agreement is a
  hard self-check (like the IDH controls in `build_contract_xena.py:77-79`), NOT a second contract.

**Self-containment (memory `feedback_...` + compute-boundary):** the multi-hundred-MB source matrices are
fetched once and stay external/gitignored; regeneration reads only a **small pinned extract** committed to
`data/tcga_laml_fusion_expr/` — the gene-panel TPM subset (a few genes × ~151 cases) plus the fusion label
table. Mirrors the `data/tcga_laml/` local-only pattern (raw external, extract + builder + logs pinned).

## Gene panel

Fixed at exactly four genes (pre-registered here, so 2d-ii cannot gene-fish):
- `RUNX1T1` — the readout (silent in normal hematopoiesis; re-expressed by the t(8;21) fusion).
- `RUNX1` — the other fusion partner (context; broadly expressed, should NOT discriminate on fusion status).
- `ACTB`, `GAPDH` — housekeeping negative controls that must NOT differ by fusion status.

## The claim's floor is NOT set here (integrity)

The "~13 TPM floor" is a **literature-anchored, pre-registered** threshold (2d-ii sources the exact value +
citation from the compendia and commits it before touching TCGA). 2d-i must **not** derive the floor from the
data — its sanity check only confirms *signal exists* (RUNX1T1 clearly higher in fusion+), never sets or tunes
a threshold. Keeping floor-selection out of 2d-i preserves commit-before-data for 2d-ii.

## Components (isolation boundaries)

1. **Fetch + extract** (`data/tcga_laml_fusion_expr/build_extract.py`, local-only/gitignored raw, mirrors
   `build_contract_xena.py`): stream the STAR TPM matrix (no full load), pull the panel genes for LAML cases;
   parse `data_sv.txt` for RUNX1-RUNX1T1 → fusion+ case set; parse clinical for t(8;21) karyotype → robustness
   set. Writes the **pinned extract**: `panel_tpm.tsv` (gene × case) + `fusion_labels.tsv`
   (`case_id, fusion_status_sv, fusion_status_karyotype`). Sample ids `case_id`-normalized (`TCGA-AB-####`).
2. **Contract builder** (`src/polymer_claims/ingest/tcga_laml_fusion_expr.py::build_fusion_expr_contract`):
   reads the pinned extract → writes `contracts/tcga_laml_fusion_expr.json` + `.betas.tsv` in the exact loader
   format (`assays[0].name="tpm"`, ref `tcga_laml_fusion_expr.betas.tsv`; `row_data` `expr::<GENE>`; `col_data`
   `{sample_id, Sample_Group=fusion_status_sv, Fusion_Status, tissue="AML"}`; `metadata.genome_assembly="hg38"`
   — REQUIRED or the loader KeyErrors). Register: write into `Path(contracts.__file__).parent`,
   `clear_contract_cache()`, `load_contract("se:tcga_laml_fusion_expr@1")`.

## Tests (behavior, not implementation)

- **Contract loads + shape:** `load_contract("se:tcga_laml_fusion_expr@1")` succeeds; features are exactly the
  panel `expr::<GENE>`; every `col_data.Sample_Group ∈ {"fusion_pos","fusion_neg"}`; `dimnames_hash` is stable
  across two builds from the same extract (byte-determinism).
- **Fusion+ count in a sane band:** t(8;21) is ~5–7% of AML → assert `3 <= n_fusion_pos <= 20` (abort-if-out,
  mirroring the IDH band check) — guards against a labeling swap.
- **Label agreement self-check:** for the cases where both a SV call and a karyotype call exist, they must
  agree on fusion status **exactly** (zero mismatches). Any genuine discordance must be explicitly enumerated
  in a documented whitelist in the extract step and asserted against by name — never silently tolerated.
- **Signal sanity (NOT a threshold):** median `RUNX1T1` TPM in fusion+ is ≥ 5× the fusion− median, while both
  housekeeping controls (`ACTB`, `GAPDH`) have a fusion+/fusion− median ratio within [0.5, 2.0] (no
  discrimination). Confirms the seam carries real, correctly-oriented signal — without setting the 2d-ii floor.
- **Runs against a tiny fixture** for CI (a committed mini extract) so the suite needs no network; the full
  real build is a documented one-shot (like `build_contract_xena.py`).

## Global constraints / invariants

- `grammar/` and `protocol/` untouched, pure + numpy-free. `Corpus` stays 4. No claim built, nothing licensed.
- Compute-boundary: the builder writes a contract (a data seam); it runs no analysis pipeline and mints no claim.
- Self-contained regeneration reads only `data/`; the network fetch is a one-shot extract step, not part of
  regeneration.
- numpy may appear only behind the existing opt-in extras used by ingest builders (not in grammar/protocol).

## Out of scope (2d-ii)

The `expression_floor_claim` wired to this contract; the pre-registered literature floor (~13 TPM); the two
independent recompute legs (mean-diff + Hodges-Lehmann) + betting e-value; `register_hypotheses` +
`license_batch` via `run_cycle` → LICENSED@REPRODUCED. 2d-i's real RUNX1T1 distribution informs 2d-ii's power.
