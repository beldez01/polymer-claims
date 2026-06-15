# n-DMPs-at-FDR — a second methylation reduction

> **Design spec, 2026-06-14.** Tier-1 safe slice from `docs/superpowers/2026-06-13-overnight-deferred-analysis.md`.
> CES-2 built the first scalar reduction (region-Δβ). This adds the second: the **count of
> differentially-methylated probes (DMPs)** passing a per-probe significance threshold, as a scalar
> reduction with its own **count-enrichment e-value**. Umbrella-only (grammar + protocol untouched),
> exactly like CES-2.
>
> Rhythm: this spec → `superpowers:writing-plans` → `superpowers:subagent-driven-development` →
> merge `--no-ff` → update `CONTINUE.md`.

## Problem

The apparatus currently licenses one methylation reduction: region-Δβ (a two-group mean difference over
a region's probes, CES-2). A richer, standard methylation statistic is **n-DMPs**: how many individual
probes are differentially methylated between the two groups. It is a *count* (not a group mean), so it
needs its own statistic, its own air-gap legs, and — critically — its own **e-value**: the Phase-2.1
`betting_evalue` is a *two-sample group-mean* e-value and does not apply to a count.

## Decision

- **A probe is a DMP iff its per-probe two-group pooled t-test p-value < α** (decided). Under the
  per-probe null a valid test's p is Uniform, so P(p < α) = α exactly — making the null DMP-rate p0 = α
  *by construction*, which gives a clean, parameter-free enrichment e-value (no hand-set noise rate).
  This is the literal "DMPs at a significance/FDR threshold."
- **The e-value is a count-enrichment e-value**: over the M probes, the DMP-indicators X_i ∈ {0,1} are
  Bernoulli; H0: E[X] ≤ p0 (= α; "no enrichment beyond chance"). A **one-sample betting e-value**
  (WSR/Ville, predictable-λ GRAPA) tests it — the same anytime-valid family as `betting_evalue`, on
  bounded {0,1} data. Observing N ≫ α·M of M probes passing yields a large e-value.
- **Single-cohort REPRODUCED.** n-DMPs as a §2E REPLICATED second reduction (across cohorts) is a
  deferred follow-up; this slice ships the reduction itself.

## Approach (chosen: A)

- **A (chosen) — a new `methyl::n_dmps` apparatus, umbrella-only.** Mirrors region-Δβ: two independent
  legs, a claim builder, a content-addressed oracle, wired through the existing `evidence=` /
  earned-strength / air-gap / e-LOND verify path. No grammar/protocol change.
- **B — overload region-Δβ with a different threshold.** Rejected: a count is a categorically different
  statistic from a group mean; conflating them corrupts both.
- **C — literal BH-FDR rejection count.** Rejected: a BH-rejection count has no clean anytime-valid
  martingale e-value. The chosen per-probe-significance + binomial-enrichment e-value *is* FDR-style
  control (the e-value bounds false enrichment) and stays in the e-value family the system already uses.

## Components (all umbrella — `src/polymer_claims/`)

### `methyl_adapters.py` (extend; extract shared I/O)

- **Extract `_load_betas(node) -> (beta, sample_ids, group_of, params)`** — the manifest + betas-TSV
  parse currently inlined in `_region_group_means`. Refactor `_region_group_means` to call it (DRY; the
  region path stays byte-equivalent). `beta` is the `{probe: {sample_id: float}}` matrix.
- **`_per_probe_pvalues(node) -> dict[str, float]`** — for each probe in the node's `probes` param
  (default = all contract probes), split betas by `group_col`/`level_a`/`level_b`, compute the **pooled
  two-sample t-statistic** and its two-sided p-value (Student's t, equal-variance — equals the OLS
  group-coefficient t, so the two legs agree exactly). Uses numpy/`statistics`; degenerate probes
  (zero pooled variance) → p = 0.0 if the means differ else 1.0 (deterministic, no NaN).
- **`_n_dmps(node, alpha) -> int`** — `sum(p < alpha for p in _per_probe_pvalues(node).values())`.
- **Two legs** (the air-gap): `NDmpTTestAdapter` (identity `methyl-ndmp-ttest`, manual pooled-t) and
  `NDmpOlsCoefAdapter` (identity `methyl-ndmp-ols`, per-probe OLS coefficient t via numpy `lstsq`).
  Both `.execute(...) -> ExecValue(value=float(_n_dmps(node, alpha)))`; they return the **same count** by
  construction (the pooled-t and the OLS-coef t are identical for a two-group design).
- **`n_dmps_claim(claim_id, *, ref, probes=None, group_col, level_a, level_b, alpha=0.05, k,
  comparator=Comparator.GE, oracle_ref=None, …) -> Claim`** — mirrors `region_delta_beta_claim`. `k`
  (the DMP-count criterion) is a required caller arg (the demo passes `k=3`). When `probes is None` the
  builder resolves **all** contract feature-ids by calling `load_contract(ref)` + reading the manifest
  `row_data` (impure builder, fine umbrella-side). Builds
  `OperationNode(impl="methyl::n_dmps", inputs=(DataHandle(ref),), params=(("probes", ",".join(probes)),
  ("group_col",…), ("level_a",…), ("level_b",…), ("alpha", str(alpha))), oracle_ref=
  profile_oracle_id(CANONICAL_EPICV2_V1), produces=ProducedLeafSpec(leaf_kind="quantity",
  measurement_basis=DERIVED))`; criterion `SatisfactionCriterion(comparator=GE, threshold=float(k))`;
  subject = a `GenomicRegion` spanning the probe set (reuse the region-Δβ subject construction). The
  `probes` param is always materialized to an explicit comma-joined list in the node (so the apparatus
  is content-addressable and deterministic — no "all" sentinel reaches the adapter).
- **Registry credentials** for the two legs (distinct owners + implementation hashes) — add to (or a
  sibling of) `methyl_independent_registry` so the air-gap licenses their agreement.

### `evidence.py` (extend)

- **`count_enrichment_evalue(indicators, *, p0) -> float`** — a one-sample betting e-value for
  H0: E[X] ≤ p0 over X ∈ {0,1}^M. `W_i = X_i − p0` (E[W] ≤ 0 under H0); predictable past-only GRAPA
  λ_i ≥ 0 capped at `λ_max = c/(1−p0)` for factor positivity; `e = ∏(1 + λ_i W_i)`; seed-averaged over
  the existing fixed `_SEEDS` for determinism. Mirrors `_capital` but one-sample. Empty / all-zero
  indicators → ~1.0.
- **`evidence_map` branch** — add `elif node.impl == "methyl::n_dmps":` computing the per-probe
  indicators (probe is DMP iff p < alpha, via the methyl helper) and
  `count_enrichment_evalue(indicators, p0=alpha)`. The region-Δβ branch (`node.impl == _IMPL`) is
  unchanged.

### No grammar/protocol change

The claim rides the existing `Claim`/`EvaluationPlan`/`SatisfactionCriterion`(GE)/quantity-leaf; the
e-value flows through the existing `run_cycle(evidence=)` threading; verify's earned-strength (margin of
N over K), air-gap, and e-LOND gate apply unchanged. numpy stays behind the non-re-exported methyl seam
(base import numpy-free). Corpus = 4.

## Demo & money-shot (powered fixture, `epicv2_casectrl_powered@1`)

- **Licenses (REPRODUCED):** an n-DMPs claim over all 24 probes (5 strong + 5 weak signal probes — both
  clear p<α at n=50/group — plus 14 ~null controls) with `k=3` licenses — `_n_dmps ≈ 10 ≥ 3`, both legs
  agree (air-gap holds), and the enrichment e-value (≈10/24 passing vs p0=0.05) clears the e-LOND bar.
- **Money-shot (does NOT license):** an n-DMPs claim over only the **null/control** probes — count ≈
  α·M (chance), enrichment e-value below the bar → withheld. The corpus error control working on a count.
- **Air-gap bites:** a same-owner credential pair is held PENDING.

## Invariants preserved

- grammar + protocol **untouched, pure + numpy-free** at base import; **Corpus = 4**; the n-DMP e-value
  threads through the existing `evidence=` seam (default None → byte-identical).
- The two legs **agree on the integer count** by construction (pooled-t = OLS-coef t). Caveat: on real
  noisy data a borderline probe (p ≈ α) could flip between legs; the powered fixture has clean separation
  (signal p ≈ 0, controls p ≫ α), so no flips — flagged as a real-data caveat, not a demo risk.
- Synthetic-betas caveat carries forward (the recomputable tier is exercised, not earned).

## Acceptance criteria

1. `n_dmps_claim` over the powered fixture's full probe set licenses at REPRODUCED, recording an earned
   strength from the count margin, with the count-enrichment e-value clearing the e-LOND discovery bar.
2. The two legs return the **same** integer count on the fixture (air-gap agreement); a same-owner pair
   is held PENDING (`ADAPTER_NOT_INDEPENDENT`).
3. A null-only-probe n-DMPs claim does **not** license (enrichment e-value below the e-LOND bar).
4. `count_enrichment_evalue` is a valid e-value (deterministic; ≈1.0 under no enrichment; large under
   strong enrichment; monotone in N) — unit-tested directly.
5. The region-Δβ path is byte-identical (the `_load_betas` refactor doesn't change its output; existing
   CES-2 / evidence_map tests stay green); `run_cycle(evidence=None)` byte-identical.
6. grammar/protocol untouched + numpy-free at base import; Corpus = 4; `scripts/check-all.sh` ALL GREEN.

## Out of scope (deferred)

- n-DMPs as a §2E **REPLICATED** second reduction across cohorts (a natural follow-up — a second cohort's
  n-DMP e-value multiplies in).
- Welch (unequal-variance) per-probe tests; per-probe BH-FDR exact (vs the chosen significance +
  enrichment-e-value framing); empirical-Bayes moderation (limma-style).
- Real public GEO data (the synthetic-betas caveat is unchanged).
- Viewer surfacing of the n-DMP count.

## Anchored file map (for the plan)

- `src/polymer_claims/methyl_adapters.py` — `_load_betas` extraction, `_per_probe_pvalues`, `_n_dmps`,
  `NDmpTTestAdapter`, `NDmpOlsCoefAdapter`, `n_dmps_claim`, registry credentials.
- `src/polymer_claims/evidence.py` — `count_enrichment_evalue`, the `methyl::n_dmps` branch in
  `evidence_map`.
- Reference precedents: `region_delta_beta_claim` / `RegionMeanDiffAdapter` (the apparatus pattern to
  mirror), `betting_evalue` / `_capital` (the e-value family to mirror one-sample),
  `docs/specs/2026-06-12-ces-2-methylation-licensing-design.md`,
  `docs/specs/2026-06-12-phase-2-1-evalue-fdr-verify-design.md` (§3.2 e-value rationale),
  `src/polymer_claims/contracts/_make_powered_fixture.py` (the demo fixture: 5 strong + 5 weak + 14 null).
