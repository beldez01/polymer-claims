# CES-2 — license a claim on a real-computed methylation Δβ (generic, canonical profile)

**Status:** Design / phase spec. v0.1
**Date:** 2026-06-12
**Author:** Z. Belden
**Depends on:** CES-0 (`2026-06-10-ces-0-analysis-profile-design.md` — `CANONICAL_EPICV2_V1`,
`profile_oracle_registry`, substrate→tier), CES-1 (`2026-06-11-ces-1-data-seam-design.md` —
`load_contract`, the SE-Contract fixture shape), and the Phase-2a real-execution pattern
(`src/polymer_claims/exec_adapters.py`). Slice CES-2 of the CES decomposition; the real-data half
of the credibility-arc spine.
**Decided this session:** generic methylation (NOT the worked example material) under the canonical
profile `CANONICAL_EPICV2_V1`; **synthetic** betas (real public-data sourcing is a deferred slice);
region Δβ reduction (n-DMPs-at-FDR deferred); a static end-to-end test (not wired into `serve`).

---

## 0. Goal

Make one claim **license on a value computed from a methylation matrix**, not asserted — closing the
last gap in the credibility-arc's "real" leg for the methylation path. A region differential-
methylation claim ("methylation in `level2` exceeds `level1` at region R by ≥ θ") is executed by two
methodologically-independent adapters over a bundled EPICv2 SE-Contract, under the pinned
`CANONICAL_EPICV2_V1` profile-as-apparatus, and licenses through `run_cycle` on their agreed computed
Δβ — with the apparatus's `ValidationTier` capping its empirical strength.

This is the methylation analog of Phase 2a's `stats::mean_diff` over `dose_response.csv`, but it (a)
reads the **content-addressed SE-Contract** (CES-1) instead of a bare CSV, (b) binds a **versioned
`AnalysisProfile`** as the apparatus (CES-0) instead of an ad-hoc oracle, and (c) computes a
**region Δβ over a methylation matrix** instead of a one-column mean.

---

## 1. Architecture & boundaries

Umbrella-only, mirroring `exec_adapters.py`. **Grammar and protocol are untouched; Corpus stays 4.**
Reuses, without modification:
- CES-1 `load_contract(ref) -> SEContractRef` (the data seam) + the bundled fixture mechanism.
- CES-0 `CANONICAL_EPICV2_V1`, `profile_oracle_id`, `profile_oracle_registry`, `substrate_tier`.
- The #5 `AdapterRegistry` air-gap gate, earned-strength (`verify_stage`), and `run_cycle`.
- `numpy` (already an umbrella `[embed]`/dev dep) for the least-squares leg.

New umbrella files: a generic SE-Contract fixture under `contracts/`, and `methyl_adapters.py`
(the betas reader + the two adapters + the claim builder + the registries). Nothing is re-exported
in a way that pulls numpy into the base import path unless already so (the adapters import numpy;
they are imported only by the CES-2 test/harness, not by the core CLI — same containment as
`embedding.py`).

---

## 2. The generic fixture (`contracts/epicv2_casectrl_demo`)

A neutral case/control EPICv2 SE-Contract, same shape as CES-1's fixture (manifest JSON + sidecar
betas TSV), built by a deterministic no-RNG generator (`contracts/_make_casectrl_fixture.py`, or a
generalized `_make_fixture`). **Synthetic** values, real structure:

- ~24 EPICv2 `cg########`-format probes on one chromosome/region, hg38 coordinates.
- ~10 samples, `Sample_Group ∈ {level1, level2}` (5/5), matching the canonical profile's contrast
  `level2 - level1`. (`col_data` also carries the covariate columns the canonical design references,
  even though the v1 reduction ignores them — see §6.)
- **A planted region effect:** over a contiguous probe block (the "signal region", ~5 probes),
  `level2` betas are shifted **+0.20** vs `level1`; the rest of the array has **no** group difference
  (the negative-control region).
- `metadata.genome_assembly = "hg38"`, `array = "EPICv2"`.

Resolved by the existing `load_contract("se:epicv2_casectrl_demo@1")` with no loader change (it is
generic by stem). The CES-1 fixture is left in place (CES-1's tests use it); CES-2 does not
reference it.

---

## 3. The two methodologically-independent adapters (`methyl_adapters.py`)

A shared **betas reader** resolves a node's `DataHandle` via `load_contract`, reads the betas matrix
(probe × sample) from the SE-Contract assay file, reads `Sample_Group` from the manifest `col_data`,
and selects the **region probes** named by the node params. It computes, per sample, the mean β over
the region's probes → one scalar per sample, grouped by `level1` / `level2`. (Shared data-access
layer, exactly as Phase 2a shares `_resolve`.)

Two adapters then compute the **same scalar — region Δβ = mean(level2) − mean(level1)** — by
genuinely different methods, so their agreement is a real two-implementation check:

- **`methyl-meandiff-beta`** (impl owner A): direct group means, `mean(level2_means) −
  mean(level1_means)`.
- **`methyl-lm-coef`** (impl owner B): the group coefficient of an ordinary least-squares fit of the
  per-sample region-mean β on a `level2` indicator (numpy `lstsq` on `[1, indicator]`). For a
  two-group design this coefficient **equals** the mean difference exactly, so the two legs agree
  within tolerance — but `lstsq` is a methodologically distinct estimator (the path to the live
  `limma`/regression world), so this is not air-gap theater.

Both implement the existing `Adapter` protocol (`execute(node, upstream, ctx) -> ExecValue`); impl
key `methyl::region_delta_beta`. A bad impl / missing handle / missing region probe / empty group
**raises** (the evaluator degrades a raise to a node error — never crashes the run), matching Phase
2a.

**Why the value agrees but the method differs** is the load-bearing design point: the air gap
requires two *independent* implementations to agree on the licensed value (CES §4 "no air-gap
theater"). Direct-mean-difference vs regression-coefficient is that, minimally and honestly.

---

## 4. The claim builder (`region_delta_beta_claim`)

Analog of `mean_diff_claim`. Builds a PENDING `Claim` with:

- terminal `OperationNode`: `impl="methyl::region_delta_beta"`,
  `inputs=(DataHandle(ref="se:epicv2_casectrl_demo@1"),)`, `params` carrying the region's probe ids as
  one delimited string (e.g. `("region_probes", "cg00000001,cg00000002,…")` — the reader splits it and
  selects those matrix rows) plus the group column + the two levels
  (`("group_col","Sample_Group")`, `("level_a","level1")`, `("level_b","level2")`), and
  `oracle_ref = profile_oracle_id(CANONICAL_EPICV2_V1)` (= `"canonical_epicv2_hg38_v1@1"`).
- `EvaluationPlan` with `SatisfactionCriterion(comparator=GT, threshold=0.10)` (the planted effect is
  ~0.20, so a true claim clears it; the negative-control region's ~0.0 does not).
- **`subject = GenomicRegion(chrom=…, start=…, end=…)`** spanning the signal region. **Load-bearing:**
  `profile_oracle_dossier`'s default applicability domain is bounded to `{genomic_region, cohort}`, so
  a claim with `subject=None` resolves **out-of-domain → UNVALIDATED → capped to 0.0**. The
  `genomic_region` subject is what makes the profile-as-apparatus actually apply (this is the exact
  CES-0 follow-up: "CES-1/2 methylation claims carry a genomic_region subject").
- `strength=None` → **earned at verify** from the computed value's margin over the threshold (the 2c
  earned-strength path), then capped by the apparatus tier.
- `pattern = adjusted_effect`, a `CategoricalLeaf` ontology term (a generic methylation term, e.g.
  `differential_methylation`).

---

## 5. Registries & wiring

- **`methyl_independent_registry()`** — an `AdapterRegistry` with two credentials asserting distinct
  owners + implementation hashes for `methyl-meandiff-beta` / `methyl-lm-coef`, so the #5 gate
  licenses on their agreement (twin of `independent_registry()`).
- **`profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))`** — a BENCHMARKED (0.6)
  dossier for `oracle_id="canonical_epicv2_hg38_v1@1"`, bounded to the default `{genomic_region,
  cohort}` domain (the claim's `GenomicRegion` subject matches).

`run_cycle(corpus, adapters=(meandiff, lmcoef), registry=methyl_independent_registry(),
oracles=profile_oracle_registry(...), ...)` executes the claim, the air gap mints the L2
`Satisfaction` on the two legs' agreement, earned strength is scored and tier-capped, and the claim
licenses.

---

## 6. Tests — the deliverable

A static end-to-end test (`tests/test_methyl_licensing.py`), no live node:

1. **Licenses on the computed Δβ** — the signal-region claim reaches `LICENSED`; the recorded
   terminal value ≈ 0.20 (within tolerance); both legs agree.
2. **Tier cap fires** — the licensed claim's empirical strength axes are capped at **0.6**
   (BENCHMARKED), via the profile-as-apparatus over `recomputable_public`.
3. **Air gap bites** — supplying a non-independent credential pair (same owner) for the two legs
   holds the claim PENDING with `ADAPTER_NOT_INDEPENDENT` (the #5 gate), verified through `run_cycle`.
4. **Negative control** — a claim over the no-shift region (Δβ ≈ 0) does **not** license (criterion
   `> 0.10` fails); it stays PENDING/UNTESTED, no false license.
5. **Subject precondition** — a variant claim with `subject=None` resolves the apparatus oracle
   **out-of-domain → UNVALIDATED**, capping its empirical strength to 0.0 (documents why the
   `genomic_region` subject is required; it may still license structurally but renders zero-strength).
6. **Adapter unit tests** — both legs return the same Δβ on the region; `methyl-lm-coef`'s coefficient
   equals `methyl-meandiff-beta`'s mean difference (the agreement is mathematical, not coincidental);
   a missing region probe / empty group raises.
7. **`check-all.sh` ALL GREEN** — grammar / protocol / umbrella / isolation / viewer unaffected.

---

## 7. Scope fences & honesty caveat

- **Static only** — not wired into `serve --real-data` / the live node (a later enrichment; the
  Phase-2b `serve` seam exists when wanted).
- **Region Δβ only** — n-DMPs-at-FDR (per-probe limma + BH count) is the richer reduction, deferred;
  the canonical profile already declares `dmp_method=limma`/`fdr_threshold=0.05` for that later slice.
- **Synthetic betas** — the substrate is labeled `recomputable_public` (→ BENCHMARKED) to **exercise**
  the tier-cap machinery, but the data is synthetic, so the tier is *exercised, not earned*. Swapping
  in a real public GEO EPICv2 subset is a deferred, self-contained sourcing slice (the
  `load_contract` fixture seam is identical — only the bytes change). This is the same honesty caveat
  carried by Phase 2a/2b, scoped to the data, not the machinery.
- **No grammar/protocol change; Corpus stays 4.** The covariate columns in the fixture are recorded
  but the v1 reduction ignores them (the canonical design formula's covariate adjustment is a later
  reduction, like n-DMPs).
- **Pinned-design material untouched** — the CES-0 pinned-design profile and CES-1 fixture remain (CES-1
  tests use the fixture); CES-2 simply does not build on them.

---

## 8. What CES-2 delivers vs defers

**Delivers:** the generic case/control EPICv2 fixture + generator; `methyl_adapters.py` (betas reader,
two independent region-Δβ adapters, `region_delta_beta_claim`, `methyl_independent_registry`); the
end-to-end licensing test (§6). The first claim that licenses on a **computed methylation value**
under a **pinned, content-addressed apparatus**.

**Defers:** live `serve` wiring; n-DMPs-at-FDR reduction; covariate-adjusted models; **real public
data** (the substrate-honesty swap); CES-3 (recording `dimnames_hash`/`profile_hash`/`semantic_run_id`
on `MaterializationContext` through `run_cycle` + drift wiring).

---

## 9. Invariants preserved

- **Grammar domain-agnostic & untouched;** the methylation vocabulary lives umbrella-side.
- **Air gap is real** — two distinct `(owner, impl-hash)` identities computing the same value by
  different methods; the #5 gate enforces independence.
- **Content-address + apparatus** — the claim reads a content-addressed SE-Contract (CES-1) and binds
  a versioned profile whose tier caps strength (CES-0), so "licensed" means "this tool, under this
  pinned profile, over this dataset, beat θ."
- **Determinism / purity** — adapters are pure given their inputs; the only impurity is file I/O via
  `load_contract`, exactly as Phase 2a.
