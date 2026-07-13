# Phase 2e — CBF fusion-partner re-expression family Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Generate + license a 2×2 family of CBF-AML expression-floor claims (RUNX1T1/t(8;21) + MN1/inv(16), each vs the other fusion and vs non-CBF) replicated across TCGA-LAML + TARGET-AML.

**Architecture:** Reuse everything — `build_fusion_expr_contract` (3-valued `Sample_Group ∈ {t821,inv16,other}`), `expression_floor_claim(gene, level_a, level_b)`, `license_replicated`. New: two 3-valued CBF contracts + a `propose_cbf_family_claims` builder.

**Tech Stack:** Python 3.12, numpy (`[spine]`), the 2d-i/ii/iii spine pipeline. Spec: `docs/superpowers/specs/2026-07-12-spine-2e-cbf-fusion-family-design.md`.

## Global Constraints

- `grammar/`/`protocol/` untouched, pure + numpy-free. `Corpus` stays 4. numpy umbrella-side (`[spine]`).
- FLOOR = **13.0 TPM** for every claim (pre-registered, gene-agnostic). Genes: RUNX1T1=ENSG00000079102, MN1=ENSG00000169184, ACTB=ENSG00000075624, GAPDH=ENSG00000111640. Labels: `t821` iff `t(8;21)`, `inv16` iff `inv(16)`/`t(16;16)`, else `other`.
- Two-stratum, commit-before-data (floor + factors pre-registered), ONE e-LOND slot per claim, self-contained (big matrices already gitignored, extracts pinned).
- Test command: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/spine/ -q`.

## Precedent to mirror

- `data/target_aml_fusion_expr/build_extract.py` — the 2d-iii extract (Task 1 mirrors it, 3-valued + MN1).
- `src/polymer_claims/expression_floor_populate.py` — `propose_spine_claims`, `license_replicated` (Task 2/3).
- `src/polymer_claims/expression_floor_adapters.py::expression_floor_claim` — has `level_a`/`level_b` params.

---

### Task 1: The two CBF contracts (controller-executed)

**Files:**
- Create: `data/tcga_laml_cbf_fusion_expr/build_extract.py`, `data/target_aml_cbf_fusion_expr/build_extract.py` (+ pinned `panel_tpm.tsv`/`fusion_labels.tsv`/`SOURCE.txt`/`build.log`); committed contracts `src/polymer_claims/contracts/{tcga_laml,target_aml}_cbf_expr.{json,betas.tsv}`.
- Modify: `.gitignore` (the big matrices are already ignored; add the raw `_cyto.json` copies if fetched fresh).

- [ ] **Step 1: TCGA CBF extract.** Copy `data/tcga_laml_fusion_expr/build_extract.py` → `data/tcga_laml_cbf_fusion_expr/build_extract.py`, changing:
  - `PANEL = {"ENSG00000079102":"RUNX1T1", "ENSG00000169184":"MN1", "ENSG00000075624":"ACTB", "ENSG00000111640":"GAPDH"}`; `GENES = ["RUNX1T1","MN1","ACTB","GAPDH"]`.
  - The label map is 3-valued: `fusion = {c: ("t821" if "t(8;21)" in karyo[c] else "inv16" if re.search(r"inv\(16\)|t\(16;16\)", karyo[c]) else "other") for c in universe}` (import `re`).
  - Reuse the SAME already-downloaded matrix (`../tcga_laml_fusion_expr/TCGA-LAML.star_tpm.tsv.gz`) and the TCGA cytogenetics (fetch `laml_tcga_pub` `CYTOGENETICS` to `_cyto.json`, or reuse the one already fetched).
  - `uid_stem="tcga_laml_cbf_expr"`.
  - **Self-checks (per group):** RUNX1T1 median in `t821` ≥ 5× its median in (`inv16`∪`other`); MN1 median in `inv16` ≥ 5× its median in (`t821`∪`other`); RUNX1T1 `t821` median ≥ 13 and MN1 `inv16` median ≥ 13 (both clear the floor); ACTB/GAPDH medians within [0.5,2.0] across all three groups. Assert `3 <= n_t821` and `3 <= n_inv16`. Print n per group.
- [ ] **Step 2: Run it** → confirm the self-checks pass (expected TCGA: t821≈6, inv16≈10; RUNX1T1 t821 ~94, MN1 inv16 ~93). Register `se:tcga_laml_cbf_expr@1`.
- [ ] **Step 3: TARGET CBF extract.** Same, copying `data/target_aml_fusion_expr/build_extract.py` (its matrix + `_cyto.json` are present), `uid_stem="target_aml_cbf_expr"`, out to `data/target_aml_cbf_fusion_expr/`. Run → expected TARGET: t821≈90, inv16≈97; MN1 inv16 ~69. Register `se:target_aml_cbf_expr@1`; ASSERT its `dimnames_hash != se:tcga_laml_cbf_expr@1`'s.
- [ ] **Step 4: `.gitignore`** any fresh `_cyto.json`; confirm `git status` shows only the small extracts + the two contracts.
- [ ] **Step 5: Commit** → `git add data/tcga_laml_cbf_fusion_expr data/target_aml_cbf_fusion_expr src/polymer_claims/contracts/tcga_laml_cbf_expr.* src/polymer_claims/contracts/target_aml_cbf_expr.* .gitignore && git commit -m "feat(spine): TCGA+TARGET CBF 3-valued contracts (t821/inv16/other, RUNX1T1+MN1 panel, 2e)"`

---

### Task 2: `propose_cbf_family_claims` + family/specificity tests

**Files:**
- Modify: `src/polymer_claims/expression_floor_populate.py` (add `propose_cbf_family_claims`)
- Test: `tests/spine/test_cbf_family.py`

**Interfaces:**
- Produces: `propose_cbf_family_claims(ref: str) -> list[Claim]` — the 4 family claims + the ACTB control.

- [ ] **Step 1: Write the failing tests** (`tests/spine/test_cbf_family.py`): (i) family build — `propose_cbf_family_claims` returns 5 claims with the expected ids, all `Status.CONJECTURED`, each leaf a `QuantityLeaf(value=13, low=13)`, and the right `level_a`/`level_b` on each plan (read them from `claim.evaluation_plan.graph`'s terminal node params, or expose them — assert via the claim `title`/params); (ii) planted-family license — build a synthetic 3-group contract (RUNX1T1 high only in t821, MN1 high only in inv16, ACTB high everywhere, all groups n≥6) and assert A/B/C/D reach `Status.LICENSED` at `IndependenceTier.REPRODUCED` (single cohort) via a per-claim `license_batch`, and the ACTB control not; (iii) specificity — claim C (`floor-RUNX1T1-t821-vs-inv16`) licenses while a mis-specified reverse claim (`expression_floor_claim(gene="RUNX1T1", level_a="inv16", level_b="t821")`) does NOT. Model fixtures on `tests/spine/test_expression_floor_license.py` but with a 3-valued `Sample_Group`.

- [ ] **Step 2: Run to verify it fails** → FAIL.

- [ ] **Step 3: Implement `propose_cbf_family_claims`** in `expression_floor_populate.py` (mirror `propose_spine_claims`):

```python
def propose_cbf_family_claims(ref: str) -> list[Claim]:
    """The CBF 2x2 family + ACTB control (all floor=13). A/B are re-expression floors, C/D are the
    cross-fusion specificity claims (comparator = the other fusion)."""
    def _c(cid, gene, la, lb):
        return expression_floor_claim(cid, ref=ref, gene=gene, floor=13.0, tissue="AML",
                                      level_a=la, level_b=lb, search_cardinality=1)
    return [
        _c("floor-RUNX1T1-t821-vs-other", "RUNX1T1", "t821", "other"),   # A
        _c("floor-MN1-inv16-vs-other",    "MN1",     "inv16", "other"),  # B
        _c("floor-RUNX1T1-t821-vs-inv16", "RUNX1T1", "t821", "inv16"),   # C specificity
        _c("floor-MN1-inv16-vs-t821",     "MN1",     "inv16", "t821"),   # D specificity
        _c("floor-ACTB-inv16-vs-other",   "ACTB",    "inv16", "other"),  # control (must NOT license)
    ]
```

> **Implementer note:** `expression_floor_claim` already accepts `level_a`/`level_b` (confirm in `expression_floor_adapters.py`). For the planted-license test, license each claim through the existing per-claim `license_batch` (single cohort → REPRODUCED); the `_expr_split` reads `level_a`/`level_b` so a claim only compares those two groups.

- [ ] **Step 4: Run to verify it passes** → tests PASS. Then `uv run --project . pytest tests/spine/ -q`.
- [ ] **Step 5: Commit** → `git add src/polymer_claims/expression_floor_populate.py tests/spine/test_cbf_family.py && git commit -m "feat(spine): propose_cbf_family_claims (2x2 CBF family + ACTB control) + specificity tests"`

---

### Task 3: Real run across both CBF cohorts + continuity (CONTROLLER-EXECUTED)

- [ ] **Step 1: Run the real family license.** A driver `data/target_aml_cbf_fusion_expr/license_cbf_family.py` (mirror `license_replicated_spine.py`): `propose_cbf_family_claims("se:tcga_laml_cbf_expr@1")` → `preregister` → `license_replicated(..., ref_a="se:tcga_laml_cbf_expr@1", ref_b="se:target_aml_cbf_expr@1", factors_a=("tcga-laml-cohort","adult-aml-population","tcga-karyotype"), factors_b=("target-aml-cohort","pediatric-aml-population","target-karyotype"))`. For each claim print e₁ (TCGA), e₂ (TARGET), product, tier, status; run `check_controls(positive="floor-MN1-inv16-vs-other", negative="floor-ACTB-inv16-vs-other")`.
- [ ] **Step 2: Record the outcome (do NOT assert).** Expect A + B likely LICENSED@REPLICATED (RUNX1T1 t821 and MN1 inv16 both strong across cohorts); C + D honest per the data; ACTB not licensed. Whatever the real result, record it.
- [ ] **Step 3: Continuity + writeup.** Update `CONTINUE.md` (2e shipped; the family results incl. the honest MYH11→MN1 pivot) + memory. Commit.

---

## Self-review (against the spec)

- **3-valued CBF contracts (RUNX1T1+MN1)** → Task 1. ✔
- **2×2 family via level_a/level_b + ACTB control** → Task 2 `propose_cbf_family_claims`. ✔
- **Specificity (C licenses, reverse does not)** → Task 2 test (iii). ✔
- **Replicated real run + honest outcomes** → Task 3. ✔
- **Reuse (build_fusion_expr_contract, expression_floor_claim, license_replicated); grammar/protocol untouched; floor=13 pre-registered; one e-LOND slot** → Global Constraints; no new licensing machinery. ✔
- **Type consistency:** `propose_cbf_family_claims(ref)` (Task 2) called in Task 3; `expression_floor_claim(level_a,level_b)` used consistently; contract uids `se:{tcga_laml,target_aml}_cbf_expr@1` consistent across Tasks 1/3. ✔
