# §2E REPLICATED on a Real Second Cohort — Design Spec

> **Date:** 2026-06-18 · **Status:** approved, pre-implementation
> **Scope:** local-only earned run (gitignored ingestion + run script), no `src/` changes
> **Predecessors:** `2026-06-18-idh-source-swap-design.md` (region-Δβ @2, e₁=5.672 PENDING),
> the §2E tiered-independence design (the REPLICATED machinery — in git history)
> **Roadmap:** autonomous-hypothesis-loop Phase C · north-star arc 1 (§2E) · linchpin C2 (biomarker/REPLICATED tier)

## 1. Goal & scope

Earn the first **real** §2E REPLICATED license. The held-out region-Δβ claim sits at e₁=**5.672** on
`tcga_laml_idh@2` — PENDING because the e-LOND first-test bar is **1/α₁ = 32.90** (q=0.05, γ₁=6/π²).
Bind an **independent adult-AML HM450 cohort (GSE86409, Study Alliance Leukemia)** as cohort B; the
product e-value **e₁·e₂** becomes one e-LOND test. If e₁·e₂ > 32.9 (i.e. e₂ ≳ 5.8), region-Δβ licenses
at **REPLICATED** — the first *earned* (not synthetic-exercised) gold tier.

**Rigorous structure (both legs severe):**
- Region = top-10k selected on cohort-A **discovery** half (already computed, IDH-source-swap run)
- **e₁** = cohort-A **held-out test** half = 5.672 (selection never saw it)
- **e₂** = cohort B (GSE86409), full cohort, same top-10k region, IDH-mut vs WT (selection never saw it)
- **product e₁·e₂** vs 32.9

**Robustness property leaned on:** region-Δβ is a *within-cohort* contrast (mean(IDH_mut) − mean(WT)
inside each cohort), so cross-cohort normalization/batch differences **largely cancel** — cohort B may
be normalized on its own pipeline, which *strengthens* the independence claim rather than threatening
the comparison.

**In scope**
- Local-only gitignored ingestion of GSE86409 → `sal_aml_idh@1` content-addressed contract
- A REPLICATED run script binding cohort B via the existing `build_replication_inputs` /
  `replication_bindings` (already in `src/polymer_claims/replication.py` + `node.py`)
- Honest independence accounting in the caveat
- Doc/memory updates

**Out of scope**
- Any change to `replication.py` / `node.py` / `src/` (the machinery exists and works)
- Phase D integrity ledger; North Star §E common-cause DAG (noted as the deeper independence formalism)
- Committing any real data
- Live-node REPLICATED wiring beyond what `replication_bindings` already supports

**Honest-outcome contract:** deliverable = *"region-Δβ tested for replication on a real independent
cohort,"* not *"REPLICATED licensed."* If e₂ is too weak (low IDH-mut N) and the product misses 32.9,
report PENDING as-is — no tuning of τ, K, or q.

## 2. Cohort B decision

**GSE86409** — Study Alliance Leukemia (SAL) elderly adult AML, **HumanMethylation450 (GPL13534),
n=79**, IDH1-mut vs WT (the cohort the IDH-AML methylation literature pairs *with* TCGA; Glass et al.).
Different consortium + lab + processing pipeline → genuine **conceptual replication**, not a re-run of
cohort A's normalization.

Validation risks resolved in Task 1: per-sample IDH status recoverable (GEO `!Sample_characteristics_ch1`
or the SAL/Glass supplement); IDH-mut N ≥ ~12; complete top-10k probe overlap with cohort A.

## 3. Components & data flow (ingestion)

Local, gitignored, under `data/sal_aml/` (mirrors `data/tcga_laml/`).

**Source artifacts (pinned):**
- GSE86409 **Series Matrix File** — processed HM450 beta matrix (probe × sample) + per-sample
  characteristics. Pinned by download date + checksum in `data/sal_aml/SOURCE.txt`.
- IDH status: from the Series Matrix characteristics if present; else the SAL/Glass paper supplement
  (recorded in `SOURCE.txt`).

**Builder `data/sal_aml/build_contract_gse86409.py` (gitignored):**
1. Parse the Series Matrix → beta matrix + sample characteristics
2. Derive `Sample_Group` = IDH-mut / WT — **contrast-matched to cohort A** (IDH1/2-mut vs WT if
   annotated; if SAL annotates only IDH1, use IDH1-mut vs WT and record the mild contrast caveat —
   IDH1 and IDH2 drive the same 2-HG hypermethylation, so the region replicates either way)
3. QC: drop NA probes; the kept probe set MUST include cohort-A's top-10k (Task asserts overlap)
4. Write `sal_aml_idh@1` SE-Contract (manifest + betas TSV) in the exact `load_contract` shape, metadata:
   `idh_call_source="geo:GSE86409@<date>"`, `group_digest`, `idh_mut_n`, `wt_n`, `platform="HM450"`

**Data flow:**
```
GSE86409 Series Matrix ──► betas (probe×sample) + IDH characteristics
                              ├─► Sample_Group {IDH_mut/WT}
                              └─► sal_aml_idh@1 manifest + betas.tsv   (dimnames_hash ≠ cohort A)
```

## 4. The REPLICATED run (binding + product gate)

Local run script `data/sal_aml/run_replicated.py` (gitignored):

1. **Reconstruct cohort-A's held-out region claim** (same as `data/tcga_laml/run_region_split.py`):
   split `tcga_laml_idh@2` → discovery/test, select top-10k on discovery, build region-Δβ on the test
   half. `evidence_map` e-value = **e₁ = 5.672**. K=10_000, τ=0.10 fixed.
2. **Bind cohort B:** `bindings = {"tcga-laml-region-split": "se:sal_aml_idh@1"}`;
   `repl = build_replication_inputs(corpus, BASE, bindings=bindings)`. This air-gaps cohort B on the
   same top-10k region with both region legs, checks agree ∧ Δβ>τ ∧ `dimnames_hash` differs, returns
   `repl.evidence[cid] = e₁·e₂` and cohort B's Satisfaction.
3. **Gate:** `run_cycle(corpus, (RegionMeanDiffAdapter(), RegionLmCoefAdapter()), BASE,
   adapter_registry=methyl_independent_registry(), oracles=..., materializations=...,
   replications=repl.replications, evidence=repl.evidence)`. Two satisfactions (distinct cohorts) →
   `independence_tier = REPLICATED`; the product is the single e-LOND test vs 32.9.
4. **Report + capture** `run_replicated_output.log`: e₁, e₂, product, status, `independence_tier`, both
   cohorts' content-address, FDR ledger.

**Severity bookkeeping:** the top-10k region was selected only on cohort-A's discovery half, so e₁
(cohort-A test half) and e₂ (all of cohort B) are both valid severe e-values on data unused for
selection. Cohort B contributes full power (no split — selection never touched it). License iff
e₁·e₂ > 32.9.

## 5. Verification & honesty self-checks

No package tests (nothing in `src/`); correctness rests on inline builder asserts + the real
`run_cycle` air-gap (both region legs must agree on each cohort).

**Builder self-checks (hard asserts, abort on failure):**
- IDH-mut N in a sane band (≥ ~12; cohort too small to give e₂ ≳ 5.8 is surfaced, not silently run)
- **Top-10k overlap complete:** every cohort-A top-10k probe is present in cohort B (else the rebind
  cannot compute e₂) — abort listing any missing probes
- Known IDH-positive control sample(s) called IDH_mut, if identifiable from GEO metadata
- Loader round-trip: `load_contract("se:sal_aml_idh@1")` resolves with a `dimnames_hash` ≠ cohort A's

**Run-level:** `build_replication_inputs` itself enforces the air-gap (drops cohort B if the two legs
disagree or Δβ ≤ τ), so a mis-ingested cohort B cannot silently inflate the product.

**Independence honesty (explicit in the caveat):** state exactly what independence is *earned* —
different consortium (SAL vs TCGA), different lab, independently normalized betas, distinct
`dimnames_hash` — and what is *not* yet formally proven (the North Star §E common-cause DAG: shared
HM450 manifest + shared "IDH→hypermethylation" prior remain un-screened). REPLICATED is never read as
having cleared the formal independence bar §E will define.

## 6. Doc & memory updates (on completion)

- `CONTINUE.md`: Standing caveats (region-Δβ REPLICATED outcome + cohort-B source + e₁/e₂/product) +
  NEXT menu (region-Δβ moves out of "PENDING < 32.9"; REPLICATED no longer "synthetic-only")
- Memory `project_polymer_claims_knowledge_protocol` + `INDEX.md`

## 7. Open implementation details (for the plan)

- GSE86409 Series Matrix exact URL + pin mechanism (FTP `GSE86nnn/GSE86409/matrix/` vs GEO query)
- The `!Sample_characteristics_ch1` field name carrying IDH status (or the supplement table id)
- Whether SAL annotates IDH2 or only IDH1 (sets the contrast + caveat)
- Confirm the region-Δβ claim id used by the run (`tcga-laml-region-split`) and the `_test` sub-contract refs
- Known IDH-positive control GSM id(s) for the builder assert
