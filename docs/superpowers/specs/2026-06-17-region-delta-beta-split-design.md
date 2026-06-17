# Region-Δβ on top-10k DMPs, severe via sample-splitting (real TCGA-LAML)

**Date:** 2026-06-17 · **Status:** Design (approved for plan) · **Author:** Z. Belden
**Builds on:** the earned Phase A n-DMP run (same real `se:tcga_laml_idh@1` contract, same gate).
**Prototypes:** the §5b sample-splitting severity discipline of
`docs/superpowers/2026-06-16-autonomous-hypothesis-loop.md` (Phase D) — on real data.

> **Goal.** Earn the **region-Δβ** reduction (CES-2) on real TCGA-LAML betas at **REPRODUCED**, the
> *honest* way: no hand-picked region. The probe set is the **top-10k differentially-methylated probes**,
> and the selective-inference problem that creates is dissolved by a **discovery/test sample split** —
> probes are chosen on discovery samples and the Δβ e-value is computed on **held-out** test samples.

---

## 1. Why this shape (the severity argument)

A region-Δβ claim needs a probe set. Real methylation analysis does **not** hand-pick a region — it
selects probes systematically. The natural selection is "the top-k most differentially-methylated
probes," but done naively (rank by Δβ, then test Δβ on the *same* betas) it is **circular** — selection
on the outcome, an invalid e-value, the engine of the replication crisis. The fix is **sample-splitting**
(Wimsatt/Mayo severity; roadmap §5b): select the probe set on a **discovery** half, test it on a
**held-out** half. The held-out e-value is then valid because the probe set is independent of the test
betas. This is exactly the discipline an autonomous agent must obey, prototyped here on real data.

---

## 2. Design — three deterministic stages

**Stage 1 — stratified split.** Partition the 194 contract samples into a **discovery** and a **test**
half, stratified within each `Sample_Group` (sort sample ids per group, assign even index → discovery,
odd → test). Deterministic (no RNG) so the sub-contracts are content-addressable. Yields two sub-contracts
over the **same probes**, disjoint samples: `tcga_laml_idh_disc@1`, `tcga_laml_idh_test@1` (~5 IDH-mut +
~92 WT each).

**Stage 2 — discovery selection.** On the **discovery** contract only, compute each probe's
Δβ = mean(IDH_mut) − mean(WT), rank **descending**, take the **top 10,000** most-hypermethylated probes.
Selection reads discovery betas exclusively; the test contract is never touched.

**Stage 3 — held-out licensing.** On the **test** contract, run the existing
`region_delta_beta_claim(ref="se:tcga_laml_idh_test@1", region_probes=<top-10k>, comparator=GT,
threshold=τ, oracle_ref=HM450)` → the two independent legs (`RegionMeanDiffAdapter` "methyl-meandiff-beta",
`RegionLmCoefAdapter` "methyl-lm-coef") compute the test-half mean Δβ → license at REPRODUCED on the
**betting e-value** (`evidence_map` → `betting_evalue(a, b, threshold=τ, comparator=GT)`) clearing the
e-LOND threshold, gated by `methyl_independent_registry()` + the HM450 oracle.

---

## 3. Pre-registered parameters (fixed before the test betas)

| Param | Value | Rationale |
|---|---|---|
| split ratio | 50/50 stratified | balances selection power vs test power |
| rank metric | discovery Δβ (IDH_mut − WT), descending | directional: IDH→hypermethylation |
| k | 10,000 | a fixed, stated probe budget |
| τ (threshold) | **0.10** | the CES-2 a-priori effect-size floor (10-point β difference) |
| comparator | GT | hypermethylation (Δβ > τ) |
| tier | REPRODUCED | two legs share the betas (reproducibility, not error, independence) |

None is read off the test betas.

---

## 4. Code — reuse + the new severity helpers

**Reused unchanged:** `region_delta_beta_claim`, `RegionMeanDiffAdapter`, `RegionLmCoefAdapter`,
`methyl_independent_registry`, `evidence_map`/`betting_evalue`, `materialization_map`, `load_contract`,
`CANONICAL_HM450_V1`.

**New (umbrella-side, CI-tested on synthetic fixtures):**
- `split_contract_samples(manifest, betas_rows) -> (disc_cols, test_cols)` (or a `split_contract(in_dir,
  out_dir)` that writes the two sub-contracts) — deterministic stratified split. Streams the betas TSV
  (no full-matrix load); reuses the manifest shape `load_contract` reads. The split logic
  (`stratified_split(sample_groups) -> (disc_ids, test_ids)`) is a **pure function**, unit-tested for
  disjointness, stratification, and determinism.
- `top_k_hypermethylated(ref, k, group_col, level_a, level_b) -> tuple[str, ...]` — discovery-side
  per-probe Δβ ranking → the top-k probe ids. Pure-over-the-contract; unit-tested on a synthetic fixture
  where planted-signal probes rank top and a non-signal control probe does not.

**Local-run (gitignored `data/tcga_laml/`, like the n-DMP earned run):** a script that splits the real
contract, selects the top-10k on discovery, builds the test-half region-Δβ claim, runs the gate, and
reports LICENSED/withheld + the test-half mean Δβ + e-value + content-address.

---

## 5. Tests

**CI-safe unit tests (always run, no real data):**
1. `stratified_split` — discovery ∩ test = ∅, union = all, each group split ~evenly, deterministic
   across calls.
2. `split_contract` round-trips: both sub-contracts resolve via `load_contract` with disjoint sample
   sets and the same probes; `dimnames_hash` differs between them.
3. `top_k_hypermethylated` on a synthetic fixture (a few planted high-Δβ probes + control probes) returns
   the planted probes in the top-k and is deterministic; it reads only the named contract.

**Local earned run (not committed):** real split → top-10k → held-out region-Δβ → report.

---

## 6. Honest caveats (carried)

- **Power:** n=10 IDH-mut → ~5 per split. The test half is low-powered; the run **may honestly withhold**
  (a valid, informative outcome, per project ethos — not a failure). The top-10k are enriched for real
  hypermethylation, so a license is plausible, but it is not guaranteed.
- **Severity is the point:** the discovery/test split is what makes top-k selection valid; without it the
  e-value is invalid. The implementation must never let the test half influence selection.
- Betas are Xena-rehosted GDC Level-3; IDH status from GDC open MAFs (conservative n=10); sex-chromosome
  QC still skipped (no probe chr/pos); data local-only, gitignored. REPRODUCED, not REPLICATED.

---

## 7. Acceptance

1. `stratified_split` + `split_contract` + `top_k_hypermethylated` land with CI-safe unit tests; full
   gate green.
2. The local run executes the three stages on real betas and **reports** the test-half mean Δβ, the
   betting e-value, and the gate verdict (LICENSED at REPRODUCED **or** an honest withhold), with the
   full content-address on a license.
3. Docs note region-Δβ's status: **earned via held-out top-10k** if it licenses, or **attempted, withheld
   at n=10** if it does not — either is reported plainly; REPLICATED stays synthetic.
