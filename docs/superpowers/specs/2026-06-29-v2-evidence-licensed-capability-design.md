# V2.0 Slice 1 — Evidence-licensed capability: model-vs-baseline benchmark advantage

**Date:** 2026-06-29
**Author:** Z. Belden (synthesized with Claude)
**Status:** DESIGN (v3, post-2nd-review) — awaiting review → `writing-plans`
**Roadmap item:** V2.0 (`docs/superpowers/2026-06-23-remaining-roadmap.md`, "Vision-derived additions")
**Depends on:** Capability Cell + Registry V1 (merged `b058d3c`, 2026-06-27)

> **Revision history.** v1 (neutral cassette + single-observation likelihood ratio) — rejected: a
> deterministic model on a fixed input has no sampling distribution. v2 (benchmark accuracy vs a
> majority-class base-rate) — rejected: a marginal mean bound `E[cᵢ]≤p₀` does not supply the *sequential*
> null a betting supermartingale requires, and `p₀` (majority-class rate from the eval labels) is
> data-dependent. **This v3** adopts the second review's recommended correction: an **inferential**
> claim of expected advantage over a **precommitted baseline**, paired increments, an explicit
> **sequential null**, a generic bounded-mean betting e-value, and a typed benchmark-adapter + protocol
> seam. It is **Slice 1** of a decomposed Path A (§12).

---

## 1. Purpose

V2.0 is the capability-cell **generalization test**: register one genuinely-new capability — not a
re-expression of the three existing reductions — to discover where the V1 abstraction does not fit, and
build the minimal honest machinery to license it. What it teaches gates V2.1–V2.3 and closed-world
agent execution.

The three V1 cells are all *licensed by two independent pure-Python recompute legs*: `evaluate.py:394`
raises `SelfLicensingError` on <2 distinct adapter identities, and `execute_ground` (`execute.py:58`) is
the only licensing path — it calls `verify()`, which licenses only with ≥2 distinct adapters.
(`Satisfaction` itself is also minted outside `verify()` in `replication.py:103,118`, so minting a
single-source `Satisfaction` in the new orchestrator is not unprecedented — it is the *licensing route*,
not the minting, that is new.) This slice adds a **second, honest licensing route**: a model evaluated against
a precommitted baseline on held-out examples, licensed by a betting e-value on the per-example advantage,
gated by e-LOND. Building it forces (and is the lesson of) a typed per-example adapter interface and a
typed verification seam the V1 single-node/scalar model cannot express.

**Non-goals:** the wedge (H1.A2 → H2 stays critical path); closed-world *enforcement*; V2.1–V2.3;
networked calls; the certificate/SLSA integration (Slice 2); defeat/drift/reinstatement (Slice 3).

---

## 2. The capability & exactly what it licenses (resolves #2)

Register `eval::benchmark_advantage@v1`.

It licenses an **inferential** claim, stated precisely:

> *Under a declared exchangeable/IID sampling of benchmark examples from a target population, the model's
> expected per-example 0/1 accuracy **advantage over a precommitted baseline predictor** is strictly
> positive.*

It does **not** license the deterministic fact "accuracy on this exact benchmark is X" (that needs no
e-value). The population, the sampling regime, and the baseline are all declared and content-addressed
(§4). The IID/exchangeability of the examples is a **disclosed assumption** — the same honesty posture
the project already takes for DEFINITIONAL calibration (validated under a disclosed generating model).

- **Produces / claim leaf:** `quantity` node output (the estimated advantage), `categorical` claim leaf
  — same convention as the three existing cells.
- **Verification policy:** single execution, ground-truth+baseline evidence (§3–§4).

---

## 3. Statistical core (the epistemic heart — fully specified) (resolves #1/#3/#4)

**Paired increments.** For each held-out example `i` with gold label `yᵢ`, the model prediction `mᵢ`
and the **precommitted baseline** prediction `bᵢ`:

```
Wᵢ = 1(mᵢ = yᵢ) − 1(bᵢ = yᵢ)   ∈ {−1, 0, +1}
```

**Sequential null (explicit, conditional).**

```
H0:  E[Wᵢ | W₁,…,Wᵢ₋₁]  ≤  0      (the model is, on average, no better than the baseline)
```

This is the predictable-process null a betting supermartingale actually requires — not a marginal mean
bound. `θ₀ = 0` is **fixed by construction**, eliminating the data-dependent `p₀` of v2: the baseline is
committed before label access, so no null parameter is selected from the evaluation sample.

**E-value — a new generic paired bounded-mean betting function (resolves #4/#12).** The existing
`betting_evalue` independently *permutes* its two arrays (`ia = rng.permutation`, `ib = rng.permutation`)
→ it is **unpaired**, wrong for example-aligned comparison. Add `paired_betting_evalue(w)` over a single
stream `Wᵢ ∈ [−1,1]`, processed in the **committed example order**, testing `H0: E[Wᵢ|history] ≤ 0`,
built on the existing GRAPA capital core (`_grapa_capital`, predictable past-only λ capped for
positivity). It is a valid test supermartingale with `E_H0[E] ≤ 1` under the declared regime — no
invented transform, no ad-hoc clipping. **Degenerate inputs are rejected, not clamped (resolves
#13/#19):** empty stream, baseline already perfect (no possible advantage), or all-tie streams are
**invalid evidence-policy/benchmark inputs** → the claim does not license (an *invalid-input* outcome,
distinct from low-evidence PENDING). No epsilon clamp.

**Discovery / licensing gate.** The e-value enters the **existing** e-LOND ledger
(`process_test`/`elond_decisions`, `fdr.py:60,93`): discovery iff `E ≥ 1/αₜ`. A claim **licenses iff
BOTH** its `SatisfactionCriterion` is satisfied **and** the e-value clears e-LOND (§6).

**Criterion ↔ null relationship (resolves #14).** The criterion and the e-value must address the **same
statistic**: the criterion tests `advantage > τ` with `τ ≥ 0`; the e-value tests `advantage > 0`. Both
`τ` and `θ₀=0` are recorded in the provenance, so a weak criterion cannot quietly stand in for a
different scientific assertion than the one the e-value certifies.

**Independence framing (resolves #5).** This is a **different independence basis**, not a "stronger"
one. Ground-truth/baseline comparison assesses *predictive validity*; two-adapter recomputation detects
*implementation/execution error*. A single scorer can still mis-parse labels, mis-order examples, or
miscompute — so the scorer is a pure, exhaustively-tested component (a recompute-of-scorer leg is a
noted later hardening, not Slice 1).

---

## 4. The typed objects

**(a) `VerificationPolicy`** (on the cell; structured — resolves #8 partially):
`execution: "recompute_pair" | "single"`, `result_rule: "criterion"`,
`independence_requirement: "implementation" | "baseline_ground_truth"`,
`evidence_policy_ref: str | None` (required for `single`), `min_adapters: int`. The three existing cells
map to the `recompute_pair` default → behaviorally unchanged.

**(b) `EvidencePolicy`** (typed, immutable, content-addressed — resolves #4/#9/#10): fields
`id/version`, `null_family: "paired_bounded_mean_betting"`, `theta0: 0.0`,
`statistic: "accuracy_advantage_over_baseline"`, `support: "[-1,1]"`,
`sampling_regime: "exchangeable_iid (disclosed assumption)"`, `baseline_ref` (digest of the committed
baseline predictor/predictions), `calibration_population_ref` (benchmark digest),
`evalue_transform: "paired_wsr_betting"`, and `digest`.
- **Resolution contract (resolves #9):** an `EvidencePolicyRegistry` resolves `evidence_policy_ref` →
  `EvidencePolicy`, **verifies the digest on resolution**, and checks
  **policy↔benchmark compatibility** (`calibration_population_ref` == the bound benchmark digest;
  `baseline_ref` resolvable). An unresolved/mismatched ref fails trust-binding → no license.
- **Digest (resolves #10):** sha256 over the project's canonical serialization (`protocol/canonicalize.py`
  conventions) of the policy **excluding the `digest` field**; algorithm + canonicalization recorded in
  the policy.
- The **oracle dossier may still attest apparatus/model credibility and cap strength**, but is **not**
  the e-value calibration source.

**(c) Licensing provenance record** (durable, content-addressed, on `Licensing` — resolves #13-original):
`execution_credential_ids`, `evidence_policy_digest`, `benchmark_digest`, `baseline_digest`,
`oracle_dossier_ref | None`, `observed_advantage`, `criterion_threshold τ`, `theta0`, `e_value`,
`criterion_verdict`, `verification_standing`. Recorded in durable state so the certificate (Slice 2) can
read it without recomputing from a mutable registry.

**(d) `ResolvedVerification`** (typed protocol input — resolves #7/#8): the umbrella orchestrator builds,
per licensed claim, `{claim_id, route: EVIDENCE_LICENSED, verification_standing, satisfaction (single-
source), evidence_provenance, credential_ids, e_value, criterion_verdict}`. This — **not** the scalar
`evidence=` map — is what the protocol consumes. The **single-source discriminator lives here**, not
overloaded onto `Satisfaction` (which stays `{verdict, materialization, credential_ids}`).

---

## 5. The benchmark-adapter interface (the central generalization lesson — resolves #6)

V1's adapter executes one `OperationNode` and returns a **scalar** `ExecValue(value: float|str|None)`
(`evaluate.py:43`). A per-example evaluation cannot be expressed that way. Slice 1 introduces:

- **`BenchmarkAdapter` protocol:** input = example **inputs + example IDs** (gold labels **withheld** —
  structurally absent from this interface); output = a typed **`PredictionVector`** DTO: an ordered tuple
  of `(example_id, prediction)`. Supports the committed benchmark size (batched), deterministic.
- **`Scorer` (separate component, holds gold labels exclusively):** joins predictions to labels **by
  `example_id`**, computes `Wᵢ` in committed order, and treats **missing, duplicate, extra, or
  order-mismatched** predictions as **execution errors** (§6), not silent zeros.
- **Label withholding is structural:** the model `BenchmarkAdapter` type has no label parameter; only the
  scorer sees labels. A test asserts the adapter never receives labels (#20).

This typed input/result/scorer split is the reusable lesson V2.1–V2.3 inherit.

---

## 6. Lifecycle / status (resolves #15/#22/#23/#24)

| Outcome | Status |
|---|---|
| criterion satisfied **and** e-LOND discovery | **LICENSED** (`EVIDENCE_LICENSED`, `verification_standing="single_source_baseline"`) |
| criterion satisfied, no discovery | **PENDING** (insufficient evidence; re-testable) |
| discovery, criterion unmet | **PENDING** |
| neither | **PENDING** |
| invalid evidence-policy/benchmark (degenerate stream, digest/compat/order/dup/credential mismatch) | **rejected at validation/trust-binding → no `ResolvedVerification` emitted → not licensed** (claim stays in its prior status); the failure surfaces as a validation/binding error, not a silent zero |
| adapter failure / NaN / out-of-support prediction | **PENDING**, new `PendingReason.EXECUTION_ERROR` — *distinct from evidential failure* |

`PendingReason.EXECUTION_ERROR` is an additive enum member (schema delta + compat goldens). Sub-threshold
evidence is **PENDING, never terminal REJECTED**.

---

## 7. Schema + runtime delta (Seam B: umbrella orchestration, new protocol dispatch)

**Grammar (pure, numpy-free):**
- `LicenseRoute.EVIDENCE_LICENSED`; a new optional `verification_standing` field on `Licensing`;
  `independence_tier` becomes **optional (`None` for the evidence route)** rather than forcing a tier —
  so a single-source license **never serializes as `REPRODUCED`** and `SINGLE_SOURCE` is *not* misfiled as
  a degree of independence (resolves #7-original/#11).
- Optional `VerificationPolicy` on `CapabilityCell`; optional evidence-provenance DTO on `Licensing`;
  `PendingReason.EXECUTION_ERROR`. All additive, defaulting to current behavior.

**Umbrella (impure; numpy allowed):** the capability orchestrator resolves the cell + `EvidencePolicy`
(digest-verified), runs the `BenchmarkAdapter`, scores via the `Scorer`, computes `paired_betting_evalue`,
enforces the validity checks (§8), mints a single-source `Satisfaction`, and emits a `ResolvedVerification`.

**Protocol (new typed dispatch — the real change, given #7):** add a `resolved_verifications:
dict[str, ResolvedVerification] | None` input threaded through `run_cycle`→`verify_stage`. For a claim
with a `ResolvedVerification`, `verify_stage` licenses **from it** (route + standing + provenance + the
e-value into `elond_decisions`) **without** calling the two-adapter `verify()`; all other claims take the
existing path unchanged. Protocol stays capability-agnostic (it consumes a typed result, not the registry).

**Four-layer validation (resolves #9-orig):** cell-schema · claim-shape (`validate_claim_shape`,
unchanged, does **not** count adapters) · trust-binding (`validate_trust_binding`: for `single`, require
the one execution credential + a resolvable digest-verified `EvidencePolicy` + (if bound) an in-domain
trusted oracle; **drop** the unconditional `BINDING_NO_INDEPENDENT_PAIR`) · runtime execution-policy
enforcement (the orchestrator refuses the single path for a non-`single` resolved cell — #30).

**Compatibility (four levels, resolves #11-orig):** the three existing cells + all suites are (a)
behaviorally compatible, (b) JSON-schema compatible, (c) canonical-serialization identical, (d)
content-address identical — pinned by a golden over the existing cells; the canonical serializer excludes
unset/default fields, or a one-time content-address bump is documented.

---

## 8. Validity-protection checks — IN Slice 1 (resolves #16)

These protect the *initial* license's validity and are Slice-1 requirements (not deferred):
benchmark-digest mismatch · `EvidencePolicy`-digest mismatch · duplicate/missing example IDs ·
prediction-order mismatch · model-credential mismatch · **reuse of one evaluation result under a different
claim or benchmark**. Each → the invalid-input row of §6 (never licensed). The full attestation chain
(request/response/model-version/endpoint/signer/capture digests) and SLSA flow remain Slice 2 (#12/#25);
defeat/drift/reinstatement/replay-over-time and tamper depth remain Slice 3 (#28/#33/#34).

**Leakage provenance (resolves #4-provenance/#17):** the `EvidencePolicy`/binding records digest-bound
commitments — model/version committed **before** label access, train/tune/eval separation, benchmark
embargo/release status, preprocessing/prompt config, **baseline committed before labels**, predictions
generated before scoring. Slice 1 enforces the digest-bound, ordering-checkable subset; assertions that
cannot be digest-verified are recorded as *disclosed assumptions*, not treated as guarantees.

---

## 9. Fixture (resolves #17)

A **tiny, hand-checkable** benchmark whose predictions and baseline are **frozen before labels are
revealed**, via deterministic seeded generation that demonstrably does not see labels (separate fixture
construction history / a generator whose seed is label-independent). Sized so the paired e-value is a
known multiple of `1/α` and verifiable by inspection.

---

## 10. Tests (resolves #18/#19/#20/#21 + §8)

1. **E-value validity (#18):** exact enumeration of the betting e-value over **all** small `Wᵢ∈{−1,0,1}`
   streams confirming the null mean ≤ 1 — not a flaky "mean≈1 across seeds"; plus a documented validity
   argument; plus a test of the **conditional** null (a sequence violating exchangeability is not silently
   trusted).
2. **Degenerate rejection (#19):** empty / baseline-perfect / all-tie → invalid-input, not clamped, not
   licensed.
3. **Label withholding (#20):** the `BenchmarkAdapter` interface never receives gold labels.
4. **Paired model-vs-baseline (#21):** `Wᵢ` is example-aligned; a model that merely matches the baseline
   yields `E ≈ 1` and no license.
5. **Validity-protection (#16):** each mismatch in §8 → not-licensed.
6. **Standing serialization:** an evidence license has `independence_tier=None`,
   `verification_standing="single_source_baseline"`, and never serializes as `reproduced`.
7. **Runtime guard (#30):** a non-`single` resolved cell cannot select the evidence path.
8. **Honest end-to-end:** the §9 fixture → criterion satisfied + e clears e-LOND → LICENSED with a
   populated provenance record.
9. **Compat goldens:** canonical serialization of the three existing cells unchanged; full
   grammar/protocol/umbrella suites green.

---

## 11. Acceptance criteria

1. `eval::benchmark_advantage@v1` registered with `VerificationPolicy{execution:"single",…}` + a
   digest-verified `EvidencePolicy`.
2. Licenses an **inferential** model-vs-precommitted-baseline claim **offline** via a single model
   adapter + a **paired sequential** betting e-value gated by e-LOND — no synthetic corroborator, no
   air-gap claim, no data-dependent null.
3. The license carries `route=EVIDENCE_LICENSED`, `independence_tier=None`,
   `verification_standing="single_source_baseline"`, and a durable content-addressed provenance record;
   it never reads `REPRODUCED`.
4. The typed `BenchmarkAdapter`/`PredictionVector`/`Scorer` interface withholds labels from the model;
   the typed `ResolvedVerification` seam drives a new protocol dispatch that does **not** call the
   two-adapter `verify()`.
5. The §8 validity-protection checks reject every listed mismatch before licensing.
6. The four-layer validation holds; `validate_trust_binding` no longer demands an independent pair for
   `single`.
7. Existing cells + suites meet compatibility (a)–(d) (or a documented bump); `grammar/`+`protocol/`
   stay pure + numpy-free; `Corpus` stays 4; `scripts/check-all.sh` green.

---

## 12. Decomposition (Path A) & rhythm

- **Slice 1 (this spec):** the paired-baseline evidence-licensing route + statistical core + typed
  benchmark-adapter interface + typed protocol seam + validity-protection checks + standing + tiny
  honest fixture.
- **Slice 2:** a *meaningful* benchmark + full attestation chain + certificate/SLSA `resolvedDependencies`
  (#12/#25).
- **Slice 3:** defeat/drift/reinstatement/replay-over-time + tamper/boundary depth + out-of-domain/
  downgraded-oracle behavior (#21-orig/#28/#33/#34).

Each slice: `writing-plans` → `superpowers:subagent-driven-development` (TDD per task) → whole-branch
review → merge `--no-ff` → update `CONTINUE.md` + memory.

> **Scope note.** The two reviews grew Slice 1 from "register a cell + relax a constant" into a real
> subsystem: a new statistical primitive, a typed per-example adapter/scorer interface, a new protocol
> licensing dispatch, and an `EvidencePolicy` registry. That is the honest minimum for a *valid* evidence
> license — none of it can be deferred without making the license unsound. If this is too large for one
> build loop, the natural internal split is **1a** (statistical primitive + `EvidencePolicy` +
> benchmark-adapter/scorer, umbrella-only, no protocol change — licenses nothing yet) → **1b** (the
> `ResolvedVerification` protocol dispatch + standing + end-to-end license).
