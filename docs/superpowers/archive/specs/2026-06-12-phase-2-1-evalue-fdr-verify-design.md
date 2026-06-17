# Phase 2.1 — the e-value / FDR / VERIFY unification

**Status:** Design / phase spec. v0.1
**Date:** 2026-06-12
**Author:** Z. Belden
**Anchor:** `docs/vision/2026-06-12-phase-2-north-star.md` — Phase 2 arc 1, the keystone. This slice
realizes North Star §2(B) (e-value evidence atom + FDR-as-dependence-robust online process) and
§2(E) (the independence / no-double-counting discipline), and begins §2(A) (licensing as the
thresholded view of one error-controlled ledger).
**Depends on:** the existing `FDRLedger` (LOND, `grammar/fdr.py`), the VERIFY licensing gate
(`protocol/verify.py`: `LICENSED ⇔ agreement ∧ SATISFIED ∧ grounded`), `integrate.py`'s FDR advance,
the CES-2 methylation apparatus (`methyl_adapters.py`, `region_delta_beta_claim`,
`CANONICAL_EPICV2_V1`), and the CES-3 pre-stamped-map pattern (`materializations=`).

**Decided this session:** **native** e-values per apparatus (not p→e calibration); **replace** the
`FDRLedger` internals with an e-value online process (keep the entity, Corpus stays 4); **hard-gate
VERIFY now** (licensing requires crossing the e-LOND bar). The native e-value tests the **shifted
severe-test null** H₀: effect ≤ θ₀ (the criterion threshold), not effect = 0. The two reproducibility
adapters yield **one** effective e-value (no multiplication — that is conceptual replication, a
follow-up).

---

## 0. Goal

Today three subsystems decide a claim's fate independently:

1. **VERIFY** licenses on `agreement ∧ SATISFIED ∧ grounded-extension` (`verify.py:3`); empirical
   strength is *earned* from the criterion margin via a hand-tuned saturating curve
   (`earned_strength.py`, whose own comment says "recalibrate against real test statistics … in the
   2d arc").
2. **The FDR ledger** (`fdr.py`) runs online-FDR via **LOND over p-values** (the terminal value fed
   in as a p-value) — but it is **advisory**: `is_discovery` is never consulted by the licensing gate.
3. **Defeat/AGM** (`integrate.py`) computes grounded-extension membership (which *is* in the gate).

Two problems. First, p-value LOND assumes a benign dependence structure; our defeat/equivalence edges
are **explicit dependence**, so the corpus-level error control is **unsound** as the corpus grows.
Second, the licensing decision and the corpus error budget are **disconnected** — a claim can license
without the FDR ledger ever gating it.

This slice fixes both by making the **evidence atom an e-value**, the ledger an **e-LOND online
process that controls FDR under arbitrary dependence**, and the **licensing gate a thresholded view
of that ledger** — one error-controlled mechanism instead of three.

---

## 1. Architecture & boundaries

The pure/impure split is the CES split, reused exactly:

- **Pure (grammar + protocol):** the e-value *scalar*, the e-LOND ledger arithmetic, the discovery
  rule, the licensing gate. An e-value, once computed, is a non-negative float — exactly as a p-value
  is today.
- **Impure (umbrella):** computing the native e-value *from the per-sample region-mean betas* (needs
  raw data + numpy). It flows into the pure core as a **pre-stamped `evidence` map**, mirroring CES-3's
  `materializations` map.

No new Corpus collection (stays 4). `FDRLedger` keeps its name; its internals change p-value → e-value.
`node.py` and the base import stay numpy-free (the e-value computation lives in the methyl umbrella
module, like the adapters).

---

## 2. The e-value evidence atom (grammar — `fdr.py`)

An **e-value** is a statistic `e ≥ 0` with `E[e] ≤ 1` under its null. `FDRLedger` swaps its p-value
internals for e-values:

- `FDRTest`: `e_value: float = Field(ge=0.0)` replaces `p_value`; `alpha_allocated` (the level α_t)
  stays; `discovery = e_value ≥ 1/alpha_allocated`.
- `process_test(ledger, claim_id, e_value) -> FDRLedger`: keep the LOND skeleton — `γ_j = (6/π²)/j²`,
  `α_t = target_fdr · γ_t · (D_{t-1}+1)` — but flip the rejection rule to **e-LOND**:

  ```
  discovery_t  ⇔  e_t ≥ 1 / α_t        (was: p_t ≤ α_t)
  ```

  This is the e-value analog of LOND (Xu & Ramdas 2024). Because the γ's sum to 1 and the e-values are
  valid, **e-LOND controls FDR ≤ target_fdr under ARBITRARY dependence** — no PRDS/positive-dependence
  assumption. That is the whole reason for the switch: defeat/equivalence edges are dependence.
- `process_stream(ledger, items)`: unchanged shape — fold `process_test` over `(claim_id, e_value)`
  pairs in order.
- New pure helper `elond_decisions(ledger, items) -> tuple[FDRLedger, dict[str, bool]]`: folds
  `process_test` over the cycle's `(claim_id, e_value)` pairs **in claim_id-sorted order**, returning
  the advanced ledger AND the per-claim discovery flags. **Single source of truth** for both the
  VERIFY gate and the committed ledger.
- `is_discovery(ledger, claim_id)` unchanged (reads recorded discoveries).

---

## 3. The native e-value (umbrella — `evidence.py` + methyl module)

New `src/polymer_claims/evidence.py`:

```python
def evidence_map(corpus) -> dict[str, float]:
    ...
```

mirrors `materialization_map`: for each executable apparatus claim whose terminal node is the methyl
apparatus and whose criterion is a one-sided numeric comparison (`GT/GE/LT/LE` with a numeric
threshold), it computes a native e-value via `region_evalue(...)`; claims with no apparatus, an
unresolvable contract, or a non-one-sided criterion (`EQ/NE/WITHIN_TOL`/None threshold) get **no
entry** (caller falls back to the existing gate). It needs neither `base_ctx` nor `profiles` — the
e-value is criterion + data only.

### 3.1 The e-value construction — the WSR betting e-value (the rigor crux)

Per-sample region-mean betas in group A (`n_A`) and B (`n_B`), each value in **[0,1]**. The criterion
threshold is `θ₀`. We test the **severe-test composite one-sided null** H₀: `d = μ_B − μ_A ≤ θ₀` vs
H₁: `d > θ₀` (mirrored for `LT/LE`).

We use the **betting / empirical-Bernstein e-value for bounded data** (Waudby-Smith & Ramdas, JRSS-B
2024, Eqs. 24–26) — chosen over the safe-t because its validity rests on **boundedness alone**
(β-values are bounded; no Gaussianity assumption — the honest call for small-n, often-skewed
methylation data), it is **variance-adaptive** (powerful when concentrated, never the Hoeffding
worst-case), and it **stays finite at zero variance**.

Construction:
1. **Pair** the groups by index (random pairing with a **fixed, data-independent seed** if
   `n_A ≠ n_B`, taking `n = min(n_A, n_B)`): `wᵢ = b_{π(i)} − a_{σ(i)} ∈ [−1, 1]`.
2. **Shift** to put the null boundary at zero: `Wᵢ = wᵢ − θ₀` (under H₀, `E[Wᵢ] = d − θ₀ ≤ 0`).
3. **Capital process** (one-sided, upward bets only): `e = ∏ᵢ (1 + λᵢ·Wᵢ)`, with `λᵢ ≥ 0`.
4. **Positivity cap:** `0 ≤ λᵢ ≤ λ_max = c/(1+θ₀)`, `c ∈ [0,1)` fixed (default `c = 0.9`), so every
   factor stays strictly positive.
5. **Predictable plug-in λ (past-only — the validity trap):** `λᵢ` uses only `W₁…W_{i−1}`:
   `λᵢ = clip( μ̂_{i−1} / (σ̂²_{i−1} + μ̂²_{i−1}), 0, λ_max )` (GRAPA), with WSR's padded running
   mean/variance (variance-1/4 prior at `i=1`). **λ must never see `Wᵢ` or any later point** — a
   leave-one-out λ silently breaks the supermartingale and inflates `E[e]` above 1.

**Validity (exact):** with `λᵢ` predictable and `≥ 0`, `Lₜ = ∏_{i≤t}(1+λᵢWᵢ)` is a nonnegative
supermartingale with `L₀ = 1` (since `E[Wᵢ | F_{i−1}] = d−θ₀ ≤ 0` under H₀), so by Ville's inequality
`E[e] ≤ 1` for **every** distribution in the composite null — needing **only boundedness**. MC-confirmed
(research pass): `E[e] ≤ 1` at every least-favorable boundary null (`d = θ₀`) across a grid of SDs and
for Bernoulli/Beta nulls.

**Determinism:** the pairing seed is fixed (e.g. averaged over a small fixed seed set — averaging
e-values preserves `E[e] ≤ 1` as a convex combination), so the e-value is a deterministic function of
the data. **Degenerate variance:** the `μ̂²` term in the denominator keeps `λ` finite at `σ̂² = 0`, and
`c < 1` keeps factors positive, so `e` is large-but-finite (e.g. identical near-noiseless groups at
`d = 0.22`, `θ₀ = 0.10` → `e ≈ 1.93`; identical groups at `d = 0` → `e = 1.0`).

**Power ⇒ a well-powered fixture.** Clearing the strict e-LOND bar (`≈ 33` for the first discovery at
FDR 0.05) needs real evidence — roughly `n ≈ 35–40` per group with tight within-group SD and a clear
effect. The synthetic licensing demonstration therefore uses a **new, realistic, well-powered**
SE-Contract fixture (realistic within-group biological noise + enough samples), separate from the
existing noiseless CES fixtures (which stay for the CES-2/3/4 tests).

### 3.2 One e-value, not a product (North Star §2(E))

The two adapters (`RegionMeanDiffAdapter`, `RegionLmCoefAdapter`) compute the **same estimand two
ways** — they are **reproducibility-independent** (catch implementation bugs) but **not
error-independent** (same data, same effect). Their agreement is still required (the air gap), but the
apparatus emits **one** effective e-value from the agreed `d̂`. Multiplying them would double-count
evidence. Genuine e-value multiplication is **conceptual replication** (a different cohort/assay,
low common-cause overlap) and belongs with the common-cause-graph follow-up.

---

## 4. The hard VERIFY gate (protocol)

The licensing predicate gains a fourth conjunct — **for apparatus claims that have an e-value only**:

```
LICENSED  ⇔  agreement ∧ SATISFIED ∧ grounded-extension ∧ e-LOND-discovery
```

- **`run_cycle(..., evidence: dict[str, float] | None = None)`** — a new keyword param (the umbrella
  `evidence_map` output), threaded to VERIFY. Default `None`/empty → today's behavior, byte-identical.
- **VERIFY** consults `evidence`, calls `elond_decisions(corpus.fdr_ledger, sorted (claim_id, e_value))`
  over this cycle's apparatus claims, **advances the ledger**, and adds the discovery flag as the
  fourth gate conjunct. The advanced ledger threads into the corpus update.
- **INTEGRATE** — its current p-value FDR advance is **removed**. Licensing now owns the ledger
  (`integrate.py` keeps AGM/defeat only). This is the "licensing = thresholded view of the ledger"
  thesis made literal.
- **Back-compat:** a claim with **no e-value** (no apparatus, unresolvable contract, or a
  non-one-sided criterion) is **not** subject to the e-discovery conjunct — it licenses on the
  existing three-way gate exactly as today. Empty `evidence` map → no-op (CES-3 pattern). The current
  FDR ledger already only processes apparatus claims with a valid statistic, so no claim that is
  FDR-gated today becomes un-gated, and none that is ungated today becomes gated.

### 4.1 Ordering note

Within a cycle, VERIFY processes apparatus claims through `elond_decisions` in **claim_id-sorted**
order (deterministic; same order INTEGRATE used for the old FDR advance). The grounded-extension flag
comes from the existing scaffolding; the e-value comes from the pre-stamped `evidence` map. The four
conjuncts are independent — no circularity.

---

## 5. Data flow (one cycle)

```
evidence_map(corpus, ctx)            # umbrella, before the cycle (needs raw betas)
        │
        ▼
SELECT → EXECUTE → VERIFY[ consult evidence → elond_decisions advances ledger → 4-way gate ]
                                                                              → INTEGRATE[ AGM only ]
```

`evidence=None`/empty → the e-discovery conjunct never fires → byte-identical to pre-2.1.

---

## 6. Components & files

- **Modify `grammar/src/polymer_grammar/fdr.py`** — `FDRTest.p_value → e_value`; e-LOND rejection
  (`e ≥ 1/α_t`); add `elond_decisions`. Update the module docstring (LOND-p → e-LOND). **[DONE]**
- **Create `src/polymer_claims/evidence.py`** — `betting_evalue(a, b, theta0, comparator)` (the WSR
  §3.1 e-value, numpy) + `region_evalue(node, criterion)` (reads betas via `_region_group_means`) +
  `evidence_map(corpus)`.
- **Create a new realistic, well-powered SE-Contract fixture** under
  `src/polymer_claims/contracts/` (a generator script + the bundled `.json`/`.betas.tsv`), separate
  from the existing noiseless `epicv2_casectrl_demo` (which stays for CES-2/3/4). ~35–40 samples/group,
  realistic within-group SD, a clear signal-region Δβ.
- **Modify `protocol/src/polymer_protocol/verify.py`** — `verify_stage(..., evidence=None)`: run
  `elond_decisions`, add the fourth gate conjunct, return the advanced ledger.
- **Modify `protocol/src/polymer_protocol/integrate.py`** — remove the p-value FDR advance.
- **Modify `protocol/src/polymer_protocol/cycle.py`** — `run_cycle(..., evidence=None)`; thread to
  VERIFY; fix the integrate audit note.
- **Tests** — grammar `fdr` (DONE); umbrella `betting_evalue` validity guard + `evidence_map` + the
  e2e methylation license on the realistic fixture; protocol verify gate + the e-LOND FDR-control
  deliverable.

---

## 7. Testing

**Grammar (`grammar/tests/`):**
- e-LOND step: `discovery ⇔ e ≥ 1/α_t`; α_t allocation unchanged (`target_fdr·γ_t·(D_{t-1}+1)`).
- `elond_decisions` determinism: sorted-order fold equals iterated `process_test`; returns the
  advanced ledger + correct per-claim flags.
- migrate existing `FDRLedger` tests from p-values to e-values (expected churn).

**Protocol (`protocol/tests/`):**
- **e-value validity guard:** Monte-Carlo under H₀ (effect = θ₀ on simulated bounded betas) →
  `mean(e) ≤ 1 + MC-tol`. (Lives wherever the e-value formula is unit-tested; if the formula is
  umbrella-side, this test is umbrella.)
- **e-LOND FDR control (headline deliverable):** a synthetic stream of nulls + non-nulls **with
  planted dependence** (a shared latent factor across hypotheses) → mean realized FDP ≤ target_fdr
  across many sims (MC-tol). Generate valid null e-values (e.g. `e = exp(λZ − λ²/2)`, `Z ~ N(0,1)`,
  `E[e]=1`) with the shared factor in `Z`; non-nulls shift `Z`'s mean > 0. *(Optional/illustrative,
  not required to pass: contrast with classical BH on `p = min(1, 1/e)` under the same dependence —
  include only if a clean failing construction is at hand; the mandatory assertion is e-LOND control.)*
- VERIFY 4-way gate: an apparatus claim with a large e-value (discovery) + agreement + grounded →
  LICENSED; the same claim with an e-value below `1/α_t` → **not** LICENSED (even with agreement +
  grounded). A non-apparatus claim (no e-value) → licenses exactly as today.
- back-compat: existing verify/cycle/integrate suites green with `evidence=None`.

**Umbrella (`tests/`):**
- **`betting_evalue` validity guard:** MC under the least-favorable boundary null (`d = θ₀`) across a
  grid of within-group SDs AND a non-Gaussian (Bernoulli) null → `mean(e) ≤ 1 + MC-tol`. The
  predictable-λ (past-only) discipline is what this guards.
- `evidence_map` computes the e-value for the methylation claim; an unresolvable contract or a
  non-one-sided criterion → no entry.
- **End-to-end:** a well-powered signal region (the **new realistic fixture**) run through
  `run_cycle(evidence=evidence_map(corpus))` → LICENSED with the e-discovery recorded; an
  under-powered / threshold-above-effect variant → e below the e-LOND bar → **not** licensed; the air
  gap (same-owner adapters) still holds a same-owner pair PENDING.
- `scripts/check-all.sh` ALL GREEN.

---

## 8. Scope fences & honesty

- **Delivers:** the e-value atom; the e-LOND ledger (FDR control under arbitrary dependence); the
  native methylation e-value (WSR betting, severe-test null, valid from boundedness alone,
  variance-adaptive); a new realistic well-powered fixture; the hard 4-way VERIFY gate; the
  FDR-control deliverable.
- **Defers (documented):** **defeat-as-e-value-update + alpha-wealth refund** (the next slice — the
  literal "one mechanism" climax where a successful defeat lowers the e-value and refunds error
  budget); **independent e-value multiplication** via the common-cause graph (conceptual replication,
  North Star §2(E)); deriving `StrengthVector.evidence_against_null` from the e-value (retires the
  hand-tuned `_sat` curve); native e-values for **future** apparatus types (one apparatus exists
  today); the **safe-t** Gaussian alternative (kept as a documented fallback for data where
  Gaussianity is defensible).
- **Honesty:** the e-value is **exactly valid from boundedness of betas alone** (β ∈ [0,1]) — no
  Gaussianity. Validity holds for the composite one-sided null via Ville's inequality on a
  predictable-λ test supermartingale; the **leave-one-out λ trap** (λ must use only the strict past)
  is the one thing that silently breaks it, and the validity guard exists to catch it. Determinism via
  a fixed pairing seed. The licensing demonstration needs a **well-powered** synthetic fixture (the
  strict e-LOND bar is real); the synthetic-data caveat carries forward (CES-2) — the e-value is real
  and valid, but addresses synthetic betas until the real-public-data swap.

---

## 9. Invariants preserved

- **Purity:** grammar/protocol stay pure/deterministic; the e-value *scalar* + ledger + gate are
  pure; only the e-value *computation from data* is umbrella-side, threaded in via the pre-stamped
  `evidence` map (CES-3 pattern). No clock/random in the core (the FDR-control test's randomness is
  test-side).
- **The kernel stays small:** the e-value is evidence *for* the recomputation kernel, not inside it;
  licensing still requires the real, pinned, agreed computation — the e-value gates whether that
  computation cleared a corpus-error-controlled bar.
- **Back-compat:** `evidence=None`/empty + the no-e-value fallback keep every existing test
  byte-identical; only apparatus claims with a one-sided criterion gain the stricter gate.
- **Corpus stays 4; grammar entity names stable** (`FDRLedger` kept; internals e-value).
- **One mechanism:** the corpus error budget and the licensing decision are now the same ledger —
  the foundation the defeat-as-e-value-update slice completes.
