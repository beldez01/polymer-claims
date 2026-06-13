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
def evidence_map(corpus, base_ctx, *, profiles=(CANONICAL_EPICV2_V1,)) -> dict[str, float]:
    ...
```

mirrors `materialization_map`: for each executable apparatus claim whose criterion is a one-sided
numeric comparison (`GT/GE/LT/LE` with a numeric threshold), it computes a native e-value via
`region_evalue(...)` in the methyl module; claims with no apparatus, an unresolvable contract, or a
non-one-sided criterion (`EQ/NE/WITHIN_TOL`/None threshold) get **no entry** (caller falls back to the
existing gate).

### 3.1 The e-value construction (the rigor crux)

Per-sample region-mean betas in group A (`n_A`) and B (`n_B`), each value in **[0,1]**. The agreed
terminal value is the effect estimate `d̂` (= region Δβ). The criterion threshold is `θ₀`. Test the
**severe-test null**:

- `GT/GE`: H₀: μ_d ≤ θ₀ vs H₁: μ_d > θ₀, with `d̂` as estimated.
- `LT/LE`: the sign-flipped mirror (H₀: μ_d ≥ θ₀), `d̂ → −d̂`, `θ₀ → −θ₀`.

E-value (one-sided sub-Gaussian test statistic):

```
σ²_eff = ¼ · (1/n_A + 1/n_B)                       # Hoeffding sub-Gaussian proxy: betas ∈ [0,1]
λ      = (δ₁ − θ₀) / σ²_eff                          # predictable: δ₁, θ₀, n_A, n_B are design facts
e      = exp( λ·(d̂ − θ₀) − λ²·σ²_eff / 2 )          # valid e-value for H₀: μ_d ≤ θ₀
```

**Validity (why E[e] ≤ 1 under H₀):** each group mean is an average of `n` bounded-[0,1] values, hence
sub-Gaussian with proxy `¼/n` (Hoeffding); `d̂` has proxy `σ²_eff`. For any **fixed** λ,
`E[exp(λ(d̂−μ_d))] ≤ exp(λ²σ²_eff/2)`, so `E[e] ≤ exp(λ(μ_d−θ₀)) ≤ 1` whenever `μ_d ≤ θ₀`. Validity
needs **only boundedness of betas** — no Gaussianity. **λ must be predictable** (independent of the
random beta values): we set it from a fixed target alternative `δ₁` (default `δ₁ = 2·θ₀`) and the
sample sizes, all design facts. A method-of-mixtures / GRO λ (data-adaptive, still valid via mixing) is
a documented follow-up.

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
  (`e ≥ 1/α_t`); add `elond_decisions`. Update the module docstring (LOND-p → e-LOND).
- **Modify `protocol/src/polymer_protocol/verify.py`** — consult `evidence`, run `elond_decisions`,
  add the fourth gate conjunct, thread the advanced ledger.
- **Modify `protocol/src/polymer_protocol/integrate.py`** — remove the p-value FDR advance.
- **Modify `protocol/src/polymer_protocol/cycle.py`** — `run_cycle(..., evidence=None)`; thread to
  VERIFY; thread the advanced ledger into the corpus update.
- **Create `src/polymer_claims/evidence.py`** — `evidence_map(corpus, base_ctx, *, profiles)`.
- **Modify `src/polymer_claims/methyl_adapters.py`** (or a sibling) — `region_evalue(...)` computing
  the §3.1 e-value from the per-sample betas (numpy; umbrella).
- **Tests** — grammar `fdr` migration to e-values; protocol verify/cycle gate + the FDR-control
  deliverable; umbrella `evidence_map` + the end-to-end methylation license.

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
- `evidence_map` computes the §3.1 e-value for the methylation claim; a claim with an unresolvable
  contract or a non-one-sided criterion gets no entry.
- **End-to-end:** the planted Δβ=0.20 region run through `run_cycle(evidence=evidence_map(...))`
  → LICENSED with the e-discovery recorded; a null/negative-control region → e below bar → **not**
  licensed; the air gap (same-owner adapters) still holds it PENDING.
- `scripts/check-all.sh` ALL GREEN.

---

## 8. Scope fences & honesty

- **Delivers:** the e-value atom; the e-LOND ledger (FDR control under arbitrary dependence); the
  native methylation e-value (severe-test null, Hoeffding-valid); the hard 4-way VERIFY gate; the
  FDR-control deliverable.
- **Defers (documented):** **defeat-as-e-value-update + alpha-wealth refund** (the next slice — the
  literal "one mechanism" climax where a successful defeat lowers the e-value and refunds error
  budget); **independent e-value multiplication** via the common-cause graph (conceptual replication,
  North Star §2(E)); the **mixture/GRO λ** (v1 uses a fixed predictable λ); deriving
  `StrengthVector.evidence_against_null` from the e-value (retires the hand-tuned `_sat` curve);
  native e-values for **future** apparatus types (one apparatus exists today).
- **Honesty:** the e-value is valid under **boundedness of betas** (betas ∈ [0,1]) — stated, not
  hidden; the noise model is Hoeffding sub-Gaussian, not Gaussian. v1 λ is a fixed predictable choice
  (`δ₁ = 2θ₀`), recalibratable. Synthetic-data caveat carries forward (CES-2): the e-value is real and
  valid, but addresses synthetic betas until the real-public-data swap.

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
