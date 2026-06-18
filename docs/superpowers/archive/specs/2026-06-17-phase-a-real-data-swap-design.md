# Phase A — The Real-Data Swap (n-DMP count on real TCGA-LAML betas)

**Date:** 2026-06-17 · **Status:** Design (approved for plan) · **Author:** Z. Belden
**Roadmap home:** Phase A of `docs/superpowers/2026-06-16-autonomous-hypothesis-loop.md`
**North star:** `docs/superpowers/2026-06-12-phase-2-north-star.md` (the recomputation gate, `q` as headline)

> **The one-line goal.** Convert the system's central proof — *a claim licenses on a real,
> independently recomputed, content-addressed analysis that beats a criterion* — from **exercised**
> (synthetic betas) to **earned** (real betas), for the **genome-wide n-DMP count** reduction, at the
> **REPRODUCED** tier. This retires the #1 standing caveat.

---

## 1. Scope & non-goals

**In scope.** License the **genome-wide n-DMP count** on **real TCGA-LAML HM450 betas** (contrast
IDH1/2-mut vs WT) through the existing gate, at the **REPRODUCED** independence tier; record the full
content-address; survive a drift check; report `q`; retire the synthetic-betas caveat *for that tier*.

**Explicitly out of scope** (each is a later phase, deferred by design):
- **No region-Δβ and no region/probe selection of any kind.** Real EWAS does not hand-pick a methylation
  region; the n-DMP count is genome-wide precisely so there is nothing to cherry-pick. Region-Δβ on real
  data is a separate, later slice and keeps its synthetic caveat until then.
- **No agent / hypothesizer** — that is Phase B (`MethylGenerationAdapter`).
- **No 2nd cohort / REPLICATED tier** — that is Phase C; REPLICATED stays synthetic-caveated until a real
  2nd cohort exists.
- **No multi-tenant / federated / auth** — still local-only by design.

**Reuse, don't rebuild.** Every compute seam is reused **unchanged**: `n_dmps_claim` +
`NDmpTTestAdapter`/`NDmpOlsCoefAdapter` (`methyl_ndmp.py`), `load_contract` → `dimnames_hash`
(`contracts/__init__.py`), `materialization.semantic_run_id` (`materialization.py`),
`content_hash`/`profile_oracle_id` (`analysis_profile.py`). New code lives only in the
**acquisition/transform (ingest)**, the **apparatus (a new profile)**, and **wiring/tests**.

---

## 2. The `ingest` command — `polymer-claims ingest tcga-laml`

A first-class CLI subcommand (registered in `cli.py` `_build_parser` alongside `validate`/`serve`),
because the product framing is "`pip install polymer-claims` → a CLI" and Phase C's data-asset catalog
grows directly out of ingestion (a one-off script would not seed it).

### 2.1 Acquisition (pinned, reproducible, gitignored)
- The repo ships a **committed, pinned manifest** (`src/polymer_claims/ingest/tcga_laml_manifest.json`
  or similar): the list of **GDC open-access file UUIDs** — HM450 Level-3 beta files + the open masked
  somatic MAF + the clinical supplement — plus each file's expected MD5. This text recipe **is**
  reproducible and citable; the UUIDs are produced by a one-time GDC query during implementation, then
  frozen in the manifest.
- `ingest` fetches those UUIDs via the **GDC REST `/data` endpoint** (open-access → no token/auth),
  verifies MD5s, and caches into a **gitignored** local dir (default `./data/tcga_laml/`; add
  `/data/` to `.gitignore`). Nothing real is ever committed.

### 2.2 Transform (umbrella-side; may lazy-import numpy)
Assemble the per-aliquot betas + metadata into the **on-disk SE-Contract format the loader already
expects** — keeping the seam unchanged so `load_contract` computes the real `dimnames_hash` with zero
code change:
- `data/tcga_laml/tcga_laml_idh.json` — manifest with `uid` (`tcga_laml_idh@1`), `dim`, `assays`
  (`ref` → the betas TSV), `col_data` (sample_id, `Sample_Group`, Age, Sex), `row_data` (feature_id,
  chr, pos for surviving probes), `metadata` (`genome_assembly: hg38`, `array: HM450`).
- `data/tcga_laml/tcga_laml_idh.betas.tsv` — header = sample IDs, rows = probe id + betas (the existing
  TSV shape consumed by `_load_betas`).
- **Grouping:** `Sample_Group ∈ {WT, IDH_mut}`, derived from the MAF — any IDH1 R132 / IDH2 R140 / IDH2
  R172 somatic call → `IDH_mut`, else `WT`. Carry Age/Sex from clinical into `col_data`.
- **QC is genome-wide apparatus, not selection:** drop probes with any NA across samples,
  cross-reactive probes, and sex-chromosome probes — a *fixed, genome-wide* rule recorded as part of
  the apparatus (§3), applied identically to all probes. The resulting probe set is "all probes passing
  the profile's QC," which `n_dmps_claim(probes=None)` reads in full from `row_data`.
- **Output:** prints contract uid, resulting `dimnames_hash`, sample/probe counts, and the two group
  sizes (expected ≈ 38 IDH-mut vs ≈ 155 WT).

---

## 3. The apparatus — `CANONICAL_HM450_V1` (new `AnalysisProfile`)

Add to `profiles.py` `_REGISTRY` a new profile representing the **GDC SeSAMe-based HM450 Level-3
pipeline** (a real, citable upstream apparatus):
- `array_type="HM450"`, `genome_assembly="hg38"` (GDC-harmonized GRCh38), `manifest` = the HM450
  GRCh38 manifest reference, and norm/detection/QC fields reflecting GDC's SeSAMe Level-3 processing
  + the genome-wide QC filter from §2.2. **Exact method strings are verified against current GDC docs
  during implementation** (the plan's first task).
- Its `content_hash` produces a `profile_hash` **distinct from `CANONICAL_EPICV2_V1`** — itself a proof
  point that the apparatus abstraction spans platforms.
- Bound to the claim via `oracle_ref = profile_oracle_id(CANONICAL_HM450_V1)` and passed into
  `materialization_map(profiles=…)` so `semantic_run_id` records the real address.

---

## 4. The claim + the severity-honest criterion

Build via the unchanged `n_dmps_claim`:
```
n_dmps_claim(
    "tcga-laml-ndmp",
    ref="se:tcga_laml_idh@1",
    group_col="Sample_Group", level_a="WT", level_b="IDH_mut",   # mean(IDH_mut) − mean(WT) > 0 = hypermethylation
    alpha=0.05, k=<pre-registered, see below>, comparator=GE,
    oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
)
```
`probes` is left `None` → `_all_probe_ids(ref)` reads **all** QC-passing probes from `row_data`
(genome-wide; no selection). Sign convention matches the IDH→2-HG→TET2-inhibition→hypermethylation
biology (Figueroa 2010; TCGA 2013).

### 4.1 `alpha` (the per-probe DMP threshold = the e-value null `p0`)
Set **`alpha = 0.05`**, a pre-registered apparatus parameter. Under the global null (no differential
methylation anywhere), per-probe p-values are ~Uniform(0,1), so P(p < α) = α — i.e. **H0: per-probe
DMP-rate ≤ p0 = α *is* the global null**, and enrichment beyond it is real signal. The genome-wide
severity does **not** come from a stringent per-probe α; it comes from the **count-enrichment e-value**
(`count_enrichment_evalue`, `evidence.py`) and the **e-LOND FDR ledger** that governs corpus-level
false-discovery. That is the whole point of the e-value design, so a conventional per-probe α=0.05 is
the honest choice here.

### 4.2 `k` is pre-registered, never read off the betas
Set **`k = ceil(α · n_probes)`** — the expected-under-null false-positive count. Then the SATISFIED
criterion (`count ≥ k`) and the count-enrichment e-value (`rate > α`) state the **same** thing: "this
contrast yields more DMPs than the α false-positive floor," with the e-value supplying the severity.
Both `α` and `k` are fixed **before** the run (computed from the probe count, not the observed DMP
count); because the reduction is genome-wide, there is nothing else to pre-register. This is the
selective-inference discipline made trivial by choosing the reduction that has no selection in it.

### 4.3 Subject slot
Set the claim's subject to honestly represent the **genome-wide IDH-vs-WT contrast** (whole-assay),
rather than the builder's default cosmetic `chr1:1,000,000–1,004,800` window. (Either pass an
assay/genome-level subject, or document the subject semantics for a genome-wide claim — resolved in the
plan.)

---

## 5. Wiring

**(A) The milestone — gate + acceptance test.** A real-data n-DMP seed builder (sibling to
`exec_adapters.real_data_seed_corpus`) that plants the §4 claim and uses
`ndmp_independent_registry()` (the two legs) + the HM450 profile in `materialization_map`. Exercised by
the acceptance test in §6.

**(B) Fast-follow in the same spec — light up the universe.** A `serve` path (e.g.
`serve --tcga-laml` or `serve --real-data --methyl`) that seeds the real n-DMP claim into `NodeRunner`
so it licenses **live** and renders in the viewer. Because the gate is a multi-minute **one-shot**
(§8), it runs **once** and the universe then simply displays the licensed claim — it is *not* a
per-tick computation (throttle/compute-once).

---

## 6. Tests & acceptance

**No-real-data unit tests (always run, in CI-substitute `check-all.sh`):**
1. `CANONICAL_HM450_V1` `content_hash`/`profile_hash` is **stable** across runs and **distinct** from
   `CANONICAL_EPICV2_V1`'s.
2. The `ingest` **transform** produces a well-formed SE-Contract with the **correct `dimnames_hash`**
   from a tiny **synthetic GDC-shaped fixture** (exercises the transform + grouping + QC logic with no
   network/download). MAF→`Sample_Group` derivation is unit-tested on fixture rows.

**Skip-if-absent integration test** (`pytest.mark.skipif` on `data/tcga_laml/` absence — so other
machines/CI skip; local runs execute):
3. The n-DMP claim reaches **LICENSED**.
4. Its `Satisfaction`/license records the real `dimnames_hash` + HM450 `profile_hash` +
   `semantic_run_id` (the full content-address).
5. A **drift check** (perturb the content-address) **re-opens** the license.
6. The two legs **agree on the integer count** (air-gap holds on real data).

**Honest failure is an acceptable outcome (asserted as correct behavior):**
7. If real betas do **not** clear the criterion, the gate correctly **withholds** the license — tested
   and reported plainly, not treated as a phase failure.

**Report `q`** (the corpus false-license rate) on the real run.

---

## 7. Docs to update on success

- **Retire the synthetic-betas caveat for the n-DMP / REPRODUCED tier** in `ARCHITECTURE_CURRENT.md`,
  `docs/superpowers/CONTINUE.md`, and canonical-spec §9. (Region-Δβ stays synthetic-caveated until its
  own real run; REPLICATED stays synthetic until Phase C — state this precisely so the retirement is not
  over-claimed.)
- Add `ingest` to the CLI command list in the canonical spec §6 and `README.md`.
- Move this spec to `docs/superpowers/archive/specs/` when shipped (per repo convention).

---

## 8. Known costs & honest limits (stated, not hidden)

- **The pure-Python pooled-t leg stays pure-Python.** Vectorizing it with numpy would collapse the
  air-gap independence (the OLS leg already *is* the numpy leg). So a one-shot license over ~400k
  QC-passing probes × ~194 samples takes **seconds-to-minutes**. Acceptable for a one-shot earned
  license — which is exactly why the live path (§5B) runs it **once**, never per tick.
- **`_load_betas` reads the full multi-GB betas TSV per execution** (twice, once per leg). Fine locally;
  a compact on-disk beta cache is a follow-up that touches **only the contract loader**, not the gate.
- **REPRODUCED, not REPLICATED.** The two legs share the betas, the HM450 manifest, and the
  normalization convention → they are **reproducibility-independent, not error-independent**. The tier
  is REPRODUCED and the e-values are **not** multiplied (the §2E rule) — unchanged from today, surfaced
  here so a REPRODUCED license is never misread as having cleared the cross-cohort independence bar it
  did not clear.
- **Data handling:** fully local, nothing committed — the repo ships the ingest tooling + pinned UUID
  manifest + profile; the SE-Contract is generated locally and gitignored; real-data tests skip-if-absent.

---

## 9. Acceptance summary (the earned milestone)

1. A real TCGA-LAML cohort **licenses the genome-wide n-DMP count at REPRODUCED**, on a value
   **computed from real betas** by two independent legs that agree, beating the pre-registered criterion.
2. The license records its **full content-address** (real `dimnames_hash` + HM450 `profile_hash` +
   `semantic_run_id`) and **survives a drift check**.
3. The **synthetic-betas caveat is retired for the n-DMP / REPRODUCED tier**; `q` is reported on real data.
4. **Honest withholding** on a non-clearing run is verified as the system working correctly.
