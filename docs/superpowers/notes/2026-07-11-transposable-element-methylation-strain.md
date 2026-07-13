# TE-family methylation strain — a pre-registered n-DMP sweep (new claim-generation strain)

**Date:** 2026-07-11 · **Branch:** `worktree-te-methylation-strain` · **Arm:** `transposable-elements`

> **TL;DR — do not read "6/6 LICENSED" as a positive finding.** All 6 TE families pass the n-DMP
> count-vs-*chance* gate (real: they are lineage-differentially methylated beyond noise; permutation-null
> confirmed). But the matched-background control shows the genome-wide baseline is ~37–45% DMPs and **no
> family is enriched — most are DEPLETED (0.5–0.8×), only HERV-K ≈ baseline.** Real finding: *young TEs are
> at-or-below the genomic lineage-DMP rate (constitutive silencing); HERV-K alone reaches baseline.*
> Engine lesson: count-vs-chance is the wrong null for an enrichment claim (§ENGINE LESSON).

## What this is

A **new strain of claim generation** for the Polymer Claims universe, distinct from the two existing
data-driven strains (pharmaco gene-body→drug; immuno MHC/HERV-K single claims) and from the WAYLAND
synbio literature strain. It turns the **dormant `transposable-elements` reference subject** (listed in
the reference corpus but with *zero* generated claims) into a **live, data-licensed arm** by sweeping the
major young TE subfamilies as **pre-registered n-DMP count-enrichment claims** over the **real Loyfer
2023 WGBS cell-type atlas** (GSE186458, 47 hematopoietic samples on disk).

Each family asks one severe test:

> Across all elements of family *F*, do ≥ *k* CpG probes come out differentially methylated between the
> **Lymphoid** and **Myeloid** lineages, under **both** a pooled-t leg **and** a rank-sum leg?

One count-enrichment e-value per family is charged to **one shared e-LOND ledger** (Xu & Ramdas 2024),
so the whole sweep is a single online-FDR-controlled experiment — not N independent slot-1 gates.

## Why this strain is worth generating

- **Fills a real gap.** `transposable-elements` was a named reference subject with no generated content;
  this is the first data-licensed TE arm.
- **Generalizes proven machinery, doesn't reinvent it.** The single HERV-K drive (`rip_hervk_ndmp`) is
  lifted to a family sweep by parameterizing exactly one thing — the rmsk locus selector
  (`ingest/te_loci.py::te_family_windows`, which reproduces `hervk_ltr5_windows` byte-for-byte on its
  original filter, asserted in a test). Everything downstream (matrix extraction, SE-Contract, n-DMP
  claim, count e-value, e-LOND gate) is reused unchanged.
- **Scientifically legible.** TE methylation is lineage- and cancer-regulated; which families carry a
  *count-significant* lineage-differential signal through a severe test is a real, interesting question,
  and a spread of licensed/pending/rejected is the honest expected outcome.

## Pre-registration integrity (commit-before-data)

- **PANEL and its ORDER are fixed in source** (`te_ndmp.PANEL`, committed) before any atlas byte is read.
  Registration order sets each slot's locked `α_t = target_fdr · γ_t · (D_{t-1}+1)`, `γ_t = (6/π²)/t²`;
  a wrong order cannot be chosen post hoc to license a family. HERV-K LTR5_Hs is registered **first** as
  the positive control (already LICENSED in the immuno arm).
- **Count floor k is data-blind:** `preregistered_k(n_probes, α) = ceil(3·α·N)` — a function of the probe
  *count* and α only, never of the observed betas.
- **α is locked at registration** (`register_test`) and each family is resolved at its LOCKED α by
  `run_cycle`/verify (match-gate) — the bar a family faces is frozen before its e-value exists.

## The pre-registered panel

| slot | family | rmsk repName/repClass | rationale |
|---|---|---|---|
| 1 | HERV-K(HML-2) | `LTR5_Hs` / `LTR` | positive control (licensed in immuno arm); youngest ERVK promoter LTR |
| 2 | LINE-1 | `L1HS` / `LINE` | only autonomously active human retrotransposon; L1 methylation is lineage/cancer-labile |
| 3 | HERV-H | `LTR7` / `LTR` | LTR7 drives pluripotency-associated transcription; regulatory, lineage-patterned |
| 4 | HERV-W | `LTR17` / `LTR` | ERV1/HERV-W (syncytin-1); placenta/immune-relevant regulatory LTRs |
| 5 | SVA | `SVA_D` / `Retroposon` | youngest large hominid-specific composite element; CpG-rich |
| 6 | Alu (young) | `AluYa5` / `SINE` | most abundant TE class; AluYa5 is a young, still-mobilizing subfamily |

**Excluded (logged, not silently dropped):** `AluY` sensu lato (~105k elements on standard chromosomes)
is over the per-family tractability budget (each family rescans 47 sample BEDs); `AluYa5` (~3.9k elements)
represents SINEs in the panel.

## A real, honest property of the gate (engine observation)

The count e-value scales steeply with the **complete-case** probe count *N* (CpGs covered in **every** one
of the 47 samples): for a perfectly-separated family the e-value is ~2^(N−k)-ish, so at N=6 it lands at
32.0 — *just under* the severe slot-1 bar of ~32.9 — while at N=12 it is 2048. **Implication:** a family
whose elements are scattered such that few CpGs are covered in *all* samples can fail the gate even with a
genuine biological signal. That is the severe test being appropriately conservative about *evidence*, not
about *effect* — and it is a property to surface, not hide. (See `feedback_flag_engine_gaps`.)

## Artifacts

- `src/polymer_claims/ingest/te_loci.py` — `te_family_windows` (generalized rmsk selector).
- `src/polymer_claims/te_ndmp.py` — `PANEL`, `run_te_family_sweep` (shared-ledger sweep).
- `scripts/rip_te_families_ndmp.py` — real-atlas driver → summary JSON + strict-Corpus arm bundle.
- `data/demo/transposable_elements_universe.json` — the arm bundle (strict Corpus; no raw betas).
- `merge_universes.collect_transposable_elements` — clean `load_corpus` + `from_corpus` lift.
- Tests: `tests/ingest/test_te_loci.py`, `tests/test_te_ndmp.py`, `tests/test_merge_universes.py`
  (collector). All synthetic/fast; the real drive is the script.

## RESULTS (real Loyfer 2023 atlas, Lymphoid vs Myeloid)

**All 6 families LICENSED** through the shared e-LOND ledger (6/6 discoveries, target_fdr=0.05).
Optimized one-pass run; `data/demo/transposable_elements_universe.json` is the strict-Corpus bundle.

| family | elems | probes N | k (floor) | t-leg DMPs | rank DMPs | e-value | e-LOND bar | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| HERV-K LTR5_Hs | 630 | 2587 | 389 | 1083 (41.9%) | 1073 (41.5%) | 3.3e274 | 32.9 | **LICENSED** |
| L1HS | 1620 | 2516 | 378 | 597 (23.7%) | 750 (29.8%) | 2.1e118 | 132 | **LICENSED** |
| HERV-H LTR7 | 2324 | 4306 | 646 | 1185 (27.5%) | 1533 (35.6%) | 1.4e255 | 296 | **LICENSED** |
| HERV-W LTR17 | 833 | 2098 | 315 | 502 (23.9%) | 712 (33.9%) | 1.9e100 | 526 | **LICENSED** |
| SVA_D | 1454 | 2841 | 427 | 704 (24.8%) | 651 (22.9%) | 1.0e144 | 822 | **LICENSED** |
| AluYa5 | 3867 | 3151 | 473 | 639 (20.3%) | 678 (21.5%) | 9.0e114 | 1180 | **LICENSED** |

Notes on reading the table:
- **The e-LOND bar RISES down the column** (32.9 → 1180). Each licensed family increments the discovery
  count *D*, and slot *t*'s level is `target·γ_t·(D+1)` with `γ_t=(6/π²)/t²`; every family's e-value
  (1e100–1e274) still obliterates its bar, so online FDR is satisfied with enormous margin.
- **Complete-case N is healthy** (2100–4300 probes/family) — the small-N licensing worry did not bite for
  these young, CpG-rich families.
- **HERV-K is the standout** (~42% of its CpGs are lineage-DMPs), reproducing its immuno-arm license and
  sitting well above the other families (20–30%).

### What this does and does NOT establish (read before citing)

The n-DMP count floor is `k = 3·α·N` — **3× the chance rate**. So a LICENSE means *"significantly more
DMPs than pure noise"* — i.e. **these TE families are genuinely differentially methylated between the
Lymphoid and Myeloid lineages, beyond chance.** That is a real, legitimate claim and it is what these six
licenses assert.

It does **NOT** establish that TEs are *enriched* for lineage-DMPs **relative to a matched genomic
background** — and the matched-background control below shows they are **NOT** (most are depleted). Two
controls bracket the result:
1. **Permutation null (validity):** shuffle lineage labels → DMP count must collapse. **PASSED** (3–6×
   collapse) — `scripts/check_te_permutation_null.py`; details below.
2. **Matched-background (specificity):** random genomic windows through the same gate. **DONE, decisive** —
   background baseline is ~37–45% DMPs; no family enriched, most depleted. See the section below; this is
   the result that actually matters.

### Matched-background enrichment control — THE decisive result (reframes everything)

Ran 5 replicates × 6000 random 1500bp genomic windows through the identical gate
(`scripts/check_te_background_enrichment.py`). The genome-wide baseline lineage-DMP fraction is **very
high and very stable**:

| | t-leg DMP% | rank DMP% |
|---|---:|---:|
| **random genomic background** (mean of 5, sd ~0.4) | **36.8%** | **44.5%** |

Fold-enrichment of each TE family over that background:

| family | t-DMP% | fold (t) | rank-DMP% | fold (rank) |
|---|---:|---:|---:|---:|
| HERV-K LTR5_Hs | 41.9% | **1.14×** | 41.5% | 0.93× |
| L1HS | 23.7% | 0.64× | 29.8% | 0.67× |
| HERV-H LTR7 | 27.5% | 0.75× | 35.6% | 0.80× |
| HERV-W LTR17 | 23.9% | 0.65× | 33.9% | 0.76× |
| SVA_D | 24.8% | 0.67× | 22.9% | 0.52× |
| AluYa5 | 20.3% | 0.55× | 21.5% | 0.48× |

**Interpretation — the naive read is WRONG.** Lymphoid and Myeloid lineages differ at ~37–45% of CpGs
*genome-wide* (these are deeply divergent, highly-purified sorted populations in WGBS). Against that
baseline **no TE family is enriched**: HERV-K is at baseline (~1×), and every other young family is
**DEPLETED** (0.5–0.8×). Biologically sensible: young L1/Alu/SVA/HERV-H/W are held under constitutive,
lineage-invariant methylation silencing, so they vary *less* by lineage than the genome average. HERV-K
(the known-active, regulatory family) is the lone exception at baseline.

**The real finding of this strain is therefore NOT "6 TE families are lineage-DMP hotspots."** It is:
*young transposable-element families are at-or-below the genome-wide lineage-DMP rate — most are depleted
— consistent with constitutive silencing; HERV-K alone reaches baseline.*

### ENGINE LESSON (load-bearing): count-vs-chance is the wrong null for an enrichment claim

All 6 families LICENSE against the n-DMP `k = 3·α·N` floor, yet the background control shows they are
**at or below** genomic baseline. The count-enrichment pattern tests *"more DMPs than NOISE,"* which is
almost always true when two conditions differ globally — it does **not** test *"more DMPs than a matched
BACKGROUND."* A claim of the form "region-class X is special for signal S" needs a **background-null
(fold-enrichment) pattern**, which the current grammar does not express. This is the highest-value gap
this strain surfaced (see [[feedback_flag_engine_gaps]]): the licenses are *valid* (beyond-chance,
permutation-confirmed) but *semantically weaker than they read* — they must not be cited as enrichment.

### Permutation-null control — PASSED

Shuffling the Lymphoid/Myeloid labels (5 deterministic permutations) collapses the DMP count, confirming
the signal is a real lineage effect, not an artifact of testing a large probe set:

| family | N | real (t / rank) | ~chance (5%·N) | permuted mean (t / rank) |
|---|---:|---:|---:|---:|
| HERV-K LTR5_Hs | 2587 | 1083 / 1073 | 129 | 185 / 216 |
| AluYa5 | 3151 | 639 / 678 | 158 | 139 / 271 |

**Read:** real counts are **3–6× the permuted counts** — the license margin is genuine. Secondary
(honest) observation: the permuted means sit modestly *above* the naive 5%·N chance line (esp. the
rank-sum leg), i.e. the per-probe test runs slightly **anti-conservative** under permutation. The
real-vs-permuted gap is so large that verdicts are unaffected, but it is a real property worth flagging
(see follow-ups). This control validates *reality of signal*; it does **not** test *TE-vs-background
enrichment* — that remains the matched-window follow-up.

## Follow-ups (deferred — do not block this strain)

- **HEADLINE (engine): add a background-null / fold-enrichment claim pattern.** The matched-background
  control (DONE) proved the count-vs-chance gate cannot answer "is region-class X special." The grammar
  needs a claim pattern whose null is a matched genomic background (fold-enrichment ≥ threshold), not
  chance. That pattern would let the TE arm assert the *actual* finding (HERV-K ≈ baseline; young families
  depleted) as a first-class licensed claim instead of the semantically-weaker beyond-chance claim.
- **Recast the 6 claims once the pattern exists.** The current bundle's 6 licenses are valid-but-weak
  (beyond-chance). With a background-null pattern, re-express as fold-enrichment claims — most would come
  back CONJECTURED/REJECTED (depleted), HERV-K borderline. That is the honest arm.
- **Engine gap: per-probe n-DMP test is mildly anti-conservative under permutation** (permuted DMP counts
  ~1.5–2× the nominal α·N, esp. the rank-sum leg on n≈small groups). Verdicts here are unaffected (huge
  margin), but on borderline claims this matters — worth a calibration pass on the rank-sum small-sample
  p-value. (See `feedback_flag_engine_gaps`.)
- **Merge into the unified viewer.** `merge_universes.py` in the main checkout currently carries the
  synbio instance's uncommitted rename; regenerating `merged-universe.json` needs all arms (pharmaco needs
  the `pandas` extra) and must resolve that rename. Left as an integration step for whoever merges.
  (The collector `collect_transposable_elements` is already wired here and unit-tested.)
- **More contrasts.** Only Lymphoid vs Myeloid here; T-vs-B, or progenitor-vs-mature, are natural next axes.
- **Complete-case N per family** is the licensing bottleneck for scattered families — worth reporting
  alongside verdicts (the summary JSON already records `n_probes`).
- **Perf (engine gap): the sweep re-parses the full 491 MB `rmsk.txt` once per family (6×).**
  `_build_family_claim` calls `te_family_windows(rmsk, …)` per family, each a full-file scan. A single
  pass that buckets windows by (repName, repClass) for the whole panel would cut rmsk I/O ~6×. Left as
  an optimization (would need a byte-identical re-run to confirm verdicts unchanged before committing).
