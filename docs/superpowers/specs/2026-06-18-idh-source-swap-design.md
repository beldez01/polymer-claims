# IDH-Source Swap — Design Spec

> **Date:** 2026-06-18 · **Status:** approved, pre-implementation
> **Scope:** local-only earned run (gitignored builder), no `src/` changes
> **Predecessors:** `archive/plans/2026-06-17-phase-a-real-data-swap.md` (n-DMP earned),
> `archive/plans/2026-06-17-region-delta-beta-split.md` (region-Δβ WITHHELD at n=10)

## 1. Goal & scope

Replace the dilution-prone IDH calling — GDC open masked-WXS MAFs, which yielded only
**n=10 IDH-mut** — with complete cBioPortal genotyping (**~30-40 expected**). Rebuild the contract
as `tcga_laml_idh@2` and **re-run region-Δβ at proper power**: the held-out top-10k severity test
that was honestly WITHHELD at n=10 (held-out betting e-value 0.867 < 1, power-limited, not refuted).
The pre-registered threshold **τ stays fixed at 0.10**.

The deliverable is *"region-Δβ re-run at proper power on correctly-genotyped data,"* **not**
*"region-Δβ licensed."* Earned or honestly-pending — never tuned.

**In scope**
- cBioPortal IDH-call branch in the **local, gitignored** builder (`data/tcga_laml/`); nothing added to `src/`
- Rebuild `tcga_laml_idh@2` (same betas, corrected labels, provenance metadata)
- Re-run region-Δβ (headline); evaluate n-DMP on `@2` (demo plumbing only); refresh the two-node viewer demo
- Doc/caveat updates: `CONTINUE.md`, memory

**Out of scope**
- §2E REPLICATED (needs a real 2nd cohort)
- Phase B (`MethylGenerationAdapter`)
- Real HM450 probe manifest / sex-chrom QC
- Any change to `src/` package code or its tests

## 2. Source decision

**cBioPortal datahub flat file** — `data_mutations.txt` for study `laml_tcga_pub` (the 200-patient
Ley et al. NEJM 2013 cohort, fully genotyped), pinned to a specific datahub git commit for
reproducibility.

Rejected alternatives: the marker-paper supplement (definitive but PDF/Excel — fiddly, less
programmatically reproducible); GDC controlled-access MAFs (dbGaP friction, still WXS-based calling
that may undercall).

## 3. Components & data flow

All changes live in `data/tcga_laml/` (gitignored, local-only).

**New/changed local artifacts**
- `data/tcga_laml/cbioportal/data_mutations.txt` (+ clinical files if needed) — downloaded; pinned
  datahub commit SHA recorded
- `build_contract_xena.py` gains a **cBioPortal branch** that:
  1. Parses `data_mutations.txt` inline, tolerant, by column name (`Hugo_Symbol`,
     `HGVSp_Short`/`Protein_Change`, `Tumor_Sample_Barcode`)
  2. Reuses the existing IDH-hotspot logic (IDH1 R132, IDH2 R140/R172) to build the IDH-mut case set
  3. Derives groups over the **intersection** case universe (see §4)
  4. Streams the same Xena beta matrix → betas TSV, writes the `@2` manifest

The existing MAF branch stays in the file (not deleted); it is simply no longer the active source.

```
cBioPortal data_mutations.txt ──┐
                                ├─► IDH-mut case set ──► groups{case→IDH_mut/WT}
Xena methylation450 matrix ─────┘                              │
        (betas, unchanged) ─────────────────────────────► tcga_laml_idh@2 manifest + betas.tsv
```

## 4. Case universe & WT semantics (the dilution fix)

The n=10 bug is one line of intent: `derive_groups` labelled **any case absent from the MAFs as WT**,
so a genuinely IDH-mut case whose masked MAF undercalled it (or wasn't downloaded) became a false WT.
WT was a dustbin for missing data, which both shrank IDH-mut and diluted the contrast.

**Fix — WT must mean "genotyped and not an IDH hotspot," never "no genotype":**
- **Case universe = intersection** of (Xena beta cases) ∩ (cBioPortal-genotyped cases).
- Within that universe: `IDH_mut` if a hotspot variant is present, else `WT` — now a *real negative
  call*, because cBioPortal genotyped the whole cohort.
- A case with a beta column but **no cBioPortal genotype is dropped, not defaulted to WT**.

**Effect on identity.** `laml_tcga_pub` genotyped the full ~200-patient cohort and Xena
methylation450 has ~194 cases, so the intersection should be ≈ all current samples.
- Headline change is **relabeling**: false-WTs flip to IDH_mut → n-mut rises to ~30-40. Same samples,
  better labels.
- If a few Xena cases are ungenotyped, they are dropped → betas TSV columns and `dimnames_hash` shift
  slightly from @1. **That is correct, not a regression.** The builder logs the exact drop count and reason.

So "betas byte-identical to @1" holds only if the intersection is the full set; the builder reports
the actual drop count rather than assuming it.

## 5. Contract identity & provenance

Rebuild the stem-named files in place (`load_contract` resolves by stem; `@N` lives only in the
manifest `uid`):

**`tcga_laml_idh.json` manifest changes**
- `uid`: `tcga_laml_idh@2` → surfaces as `contract_uid` and `self_uri = drs://local/tcga_laml_idh@2`
- `metadata` gains:
  - `idh_call_source: "cbioportal:laml_tcga_pub@<datahub-commit-sha>"`
  - `group_digest: "<sha256 of the ordered Sample_Group vector>"` — makes the relabeling
    content-addressed even though `dimnames_hash` may not change
  - `idh_mut_n`, `wt_n`, `dropped_ungenotyped_n` — the run's actual counts, recorded in the contract
- `col_data`: same `sample_id` order, new `Sample_Group` values

**On "@1 preserved".** Files are stem-named, so rebuilding overwrites @1's manifest on disk. What's
preserved for side-by-side is the **prior run's logs** (`gate_output.log`, `region_split_output.log`)
plus the run scripts in git history — not a parallel on-disk contract. The betas TSV is unchanged
(unless drops occur), so @1↔@2 differ only in labels + metadata.

**Split sub-contracts.** `split_contract()` copies `**manifest` then overrides `uid` to
`tcga_laml_idh_disc@1` / `_test@1`, so the new `metadata` (incl. `idh_call_source`, `group_digest`)
**propagates automatically** into the disc/test sub-contracts. The `@1` suffix on the derived
sub-contracts is left as-is — the parent provenance is what matters.

## 6. Re-runs & pre-registration discipline

Run order on `@2`, holding all pre-registered knobs **fixed**:

1. **region-Δβ — headline** (`run_region_split.py`, refs → `@2`):
   - `split_contract()` → stratified 50/50 disc/test (deterministic, unchanged)
   - `top_k_hypermethylated` on **discovery only**, **K=10_000 fixed**
   - License Δβ on the **held-out test half**, **comparator GT, τ=0.10 fixed**
   - With ~15-20 IDH-mut per half (vs ~5 at n=10) the betting e-value should have real power.
   - If it still does not clear 1.0, it is reported **PENDING** — τ is not moved.

2. **n-DMP on @2 — demo plumbing only** (`run_gate.py`, refs → `@2`):
   - Re-evaluated solely so both demo nodes share one contract version. `k = ceil(0.05·n_probes)`
     floor unchanged. Not a headline deliverable.

3. **Refresh two-node viewer demo** (`two_node_demo.py`):
   - Both nodes (n-DMP licensed ↔ region-Δβ) on `@2`, reflecting the new outcomes.

**Discipline guarantee (must be explicit in run output):** the only inputs that change between @1 and
@2 are the IDH labels (and possibly a few dropped ungenotyped cases). Every statistical knob — K, τ,
α, k-floor, the split rule — is byte-identical to the WITHHELD run. That is what makes the comparison
fair.

Each run captures a refreshed `*_output.log` showing e-values, status, `independence_tier`,
content-address digests, and FDR ledger state.

## 7. Verification & honesty self-checks

No package tests (nothing in `src/`); correctness rests on inline asserts in the builder plus the
gate's own air-gap.

**Builder self-checks (hard asserts, abort on failure)**
- **Known-positive controls:** a small hardcoded set of TCGA-LAML case IDs with literature-confirmed
  IDH1/IDH2 hotspots must be called `IDH_mut`. Any miss → abort (parse is wrong).
- **Count sanity band:** `idh_mut_n` must land in ~20-50. ~10 means the swap silently failed; ~100
  means a parsing/label bug. Out of band → abort with the count.
- **Universe accounting:** `idh_mut_n + wt_n + dropped_ungenotyped_n == |Xena beta cases|`; `dropped`
  is logged explicitly.
- **Loader round-trip:** `load_contract("se:tcga_laml_idh@2")` resolves, `contract_uid ==
  "tcga_laml_idh@2"`, dims match.

**Run-level verification**
- region-Δβ and n-DMP execute through the real `run_cycle` gate (two independent legs must agree — the
  existing air-gap), so a mislabelled contract cannot quietly license.
- Capture @1 vs @2 logs side by side in the CONTINUE update.

**Honest-outcome contract.** Deliverable = *"region-Δβ re-run at proper power on correctly-genotyped
data."* If it earns the license, that is the headline result. If it is still PENDING at fixed τ, that
is a real finding too (and points beyond power). Either way the result is reported as-is.

## 8. Doc & memory updates (on completion)

- `CONTINUE.md`: update Standing caveats (region-Δβ outcome, IDH-mut n, source) + the NEXT menu
  (region-Δβ status moves out of "power-limited WITHHELD")
- Memory: `project_polymer_claims_knowledge_protocol` — record the IDH-source swap + region-Δβ outcome

## 9. Open implementation details (for the plan)

- Exact cBioPortal datahub path/commit pin and download mechanism (curl raw GitHub vs API)
- `data_mutations.txt` protein-change column name in `laml_tcga_pub` (`HGVSp_Short` vs `Protein_Change`)
  and barcode→case_id join
- Confirm `run_region_split.py` / `run_gate.py` ref strings and whether sub-contract `@` suffixes need touching
- The known-positive control case-ID list (from the marker paper / cBioPortal) for the builder assert
