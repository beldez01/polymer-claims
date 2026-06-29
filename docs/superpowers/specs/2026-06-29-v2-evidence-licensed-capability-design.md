# V2.0 Slice 1 — Evidence-licensed capability: benchmark-accuracy (generalization test)

**Date:** 2026-06-29
**Author:** Z. Belden (synthesized with Claude)
**Status:** DESIGN (v2, post-review) — awaiting review → `writing-plans`
**Roadmap item:** V2.0 (`docs/superpowers/2026-06-23-remaining-roadmap.md`, "Vision-derived additions")
**Depends on:** Capability Cell + Registry V1 (merged `b058d3c`, 2026-06-27)

> **Supersedes the v1 draft of this file.** The v1 design (a neutral cassette score licensed by a
> single-observation likelihood ratio) was rejected in review: a deterministic model on a fixed input
> has no sampling distribution, so `L_alt/L_null` was an invented transform, not an e-value. This v2
> pivots to a **benchmark-backed** capability whose null and calibration population are concrete, and
> whose e-value is the project's *existing, proven* betting supermartingale. It is **Slice 1** of a
> decomposed Path A (see §10).

---

## 1. Purpose

V2.0 is the capability-cell **generalization test**: register **one** genuinely-new capability — not a
re-expression of the three existing reductions — to discover where the V1 abstraction does not fit.
What it teaches gates the V2.1–V2.3 menu fan-out and the vision's closed-world agent execution.

All three V1 cells share one hidden shape: *licensed by exactly two independent pure-Python recompute
legs* (`grammar/.../evaluate.py:391` raises `SelfLicensingError` on <2 distinct adapter identities, and
`verify()` is the **sole** minter of `Satisfaction`). This slice registers a capability licensed a
different, honest way — **a single model evaluated against independent committed ground truth, with a
betting e-value gating discovery** — and builds the minimal IR + runtime seam that makes that route
first-class and auditable.

**Non-goals:** the wedge (H1.A2 → H2 stays the critical path); closed-world *enforcement*; the
V2.1–V2.3 fan-out; networked calls. One capability, one honest licensing route, the structural lesson.

---

## 2. The capability

Register one cell:

- **`capability_id` / `capability_version`:** `eval::benchmark_accuracy` / `v1`
- **`operation_impl`:** `eval::benchmark_accuracy`
- **What it claims:** a fixed-protocol predictor achieves per-example accuracy on a **committed labeled
  benchmark** exceeding a pre-specified base-rate null.
- **Subject / data:** the committed benchmark (sequence of `(example, gold_label)`) + a single model
  adapter that emits one prediction per example. `data_ref_kind`: a content-addressed benchmark ref
  (reuse `SE_CONTRACT`-style addressing or a new `BENCHMARK` ref kind — decided in §5).
- **Produces / claim leaf:** `quantity` node output (the accuracy), `categorical` claim leaf — the same
  convention as the three existing cells (`produced=_Q`, `claim_leaf_kinds=("categorical",)`).
- **Verification policy:** single-execution, ground-truth independence, betting evidence (§3, §4).

This meets the vision's "Start Narrow" bar — schema + fixture + typed output + comparison rule + ≥1
adapter + verifiable artifacts — with a **concrete null and calibration population** (the benchmark),
which the neutral-cassette vehicle lacked.

---

## 3. Honest licensing semantics (the epistemic heart — fully specified)

**Observation regime.** The benchmark is a committed sequence of `n` examples with gold labels. The
model adapter emits a prediction per example; scoring yields a **correctness stream** `cᵢ ∈ {0,1}`.

**Null hypothesis H0 (concrete, pre-specified, committed).**
`H0: E[cᵢ] ≤ p₀`, where `p₀` is the **base-rate** — the accuracy of the constant majority-class
predictor on the committed benchmark. `p₀` is a fixed, content-addressed property of the benchmark
labels, **not estimated from the model's outputs** (resolves review #19: the null parameter is known/
committed, not fit from the evaluated data).

**Calibration population (review #16).** The benchmark itself is the calibration/evaluation population.
The labels are independent ground truth; the model's predictions are the observations under test. The
"air gap" here is **model-vs-ground-truth**, a different (and stronger) independence than
model-vs-model recompute.

**E-value (existing, proven machinery — review #1/#2/#3).** Use the project's WSR betting
supermartingale `betting_evalue` / `count_enrichment_evalue` (`src/polymer_claims/evidence.py:62,94`)
to test `H0: mean(c) ≤ p₀` over the correctness stream (`cᵢ ∈ {0,1} ⊂ [0,1]`, `threshold=p₀`,
`comparator=GT`). Because `cᵢ` are bounded in `[0,1]` and the betting fraction `λ` is already capped
for positivity, this is a valid test supermartingale with `E_H0[e] ≤ 1` **by the existing proof** —
no invented transform, no ad-hoc clipping.

**Discovery / licensing gate.** The e-value is submitted through the **existing** e-LOND intake
(`process_test`/`elond_decisions`, `grammar/.../fdr.py:60,93`, already called at `verify.py:195`):
discovery iff `e ≥ 1/αₜ`. A claim **licenses iff BOTH** (review #23/#24): its `SatisfactionCriterion`
is satisfied (observed accuracy vs the criterion threshold) **and** the e-value clears e-LOND. The four
status outcomes are defined explicitly in §6.

**Trust basis, stated truthfully.** Single model credential + committed benchmark digest + the
`EvidencePolicy` digest + the e-value clearing e-LOND. **No second adapter, no air-gap-independence
claim.** The standing is `SINGLE_SOURCE` (§5), never `REPRODUCED`.

**Shared-dependence note (review #20).** Reusing the same `EvidencePolicy`/benchmark across claims
creates dependence between their e-values; e-LOND controls FDR under arbitrary dependence between
**valid** e-values, and each capability's e-value is individually valid (WSR). The slice does not
construct e-values adaptively from prior outcomes.

**Boundary behavior (review #18/#27).** `p₀` is clamped to `(0,1)`; empty/degenerate streams →
`e = 0.0` (the existing functions already return `0.0` on empty input) → PENDING, never licensed; NaN/
out-of-support predictions are an **execution error**, distinct from evidential failure (§6).

---

## 4. The three explicit objects (review's recommended redesign)

1. **`VerificationPolicy`** (on the cell; structured, replacing the coarse-enum idea — review #8).
   Minimal fields sufficient for the two modes we have:
   - `execution: "recompute_pair" | "single"`
   - `result_rule: "criterion"` (how a successful grounding is produced)
   - `independence_requirement: "implementation" | "ground_truth"`
   - `evidence_policy_ref: str | None` (content-address of an `EvidencePolicy`; required for `single`)
   - `min_adapters: int` (2 for `recompute_pair`, 1 for `single`)
   The three existing cells map to `{execution:"recompute_pair", result_rule:"criterion",
   independence_requirement:"implementation", evidence_policy_ref:None, min_adapters:2}` — the default,
   so they are behaviorally unchanged.

2. **`EvidencePolicy`** (typed, immutable, content-addressed — review #4 separates this from the oracle
   dossier). Fields: `id/version`, `null_family:"bounded_mean_betting"`,
   `null_param:{statistic:"accuracy", null_value_rule:"base_rate_majority_class"}`,
   `support:"{0,1}"`, `evalue_transform:"wsr_betting_one_sample"`,
   `calibration_population_ref` (benchmark digest), `fitting_provenance:"committed-null (not fit)"`,
   and a `digest`. The **oracle dossier may still attest the apparatus/model credibility and cap
   strength**, but does **not** become the e-value calibration source.

3. **Licensing provenance record** (durable, content-addressed, in claim/licensing state — review #13).
   An additive frozen DTO on `Licensing` (route-level provenance), set only for the `EVIDENCE_LICENSED`
   route: `execution_credential_ids`, `evidence_policy_digest`, `benchmark_digest`,
   `oracle_dossier_ref | None`, `observed_statistic`, `e_value`, `criterion_verdict`,
   `independence_standing="single_source"`. Because it is recorded in durable state (not recomputed
   from a mutable registry), the certificate can later read it without violating content-addressed
   auditability.

---

## 5. Schema + runtime delta (Seam B: umbrella orchestration)

**Grammar layer (pure, numpy-free):**

- Add `IndependenceTier.SINGLE_SOURCE` and `LicenseRoute.EVIDENCE_LICENSED`
  (`grammar/.../licensing.py:53,65`). `independence_tier_of` is bypassed for this route; the route sets
  `SINGLE_SOURCE` explicitly so a single-source license **never serializes as `reproduced`** (review #7).
- Add the optional `VerificationPolicy` to `CapabilityCell` and the optional evidence-provenance DTO to
  `Licensing`. Both default to None / the recompute-pair default so existing cells are behaviorally
  unchanged.
- Decide `data_ref_kind`: prefer reusing content-addressed `SE_CONTRACT`-style addressing for the
  benchmark; add a `BENCHMARK` ref kind only if the existing matcher cannot express it.

**Umbrella layer (impure; numpy allowed):**

- A capability orchestrator: resolve the cell + `VerificationPolicy`, run the single model adapter over
  the committed benchmark, score correctness, compute the betting e-value, build the licensing
  provenance record, and **mint a single-source `Satisfaction`**. This is the new Satisfaction-minting
  path (review #6) — it does **not** call grammar `verify()` (which mandates 2 adapters); its guard
  replacing no-self-licensing is **ground-truth independence**: the benchmark labels must be attested
  independent of the model (provenance flag + benchmark digest; review #17/#34).
- Feed the minted Satisfaction + the e-value through the **existing** evidence/verify seam
  (`evidence=` → `elond_decisions`), mirroring the methyl `evidence_map` precedent.
- A small, localized `verify_stage` branch (`protocol/.../verify.py:252`): when the satisfaction is
  single-source, construct `Licensing(route=EVIDENCE_LICENSED,
  independence_tier=SINGLE_SOURCE, …, evidence_provenance=…)` instead of the SEVERE_TEST default.
  Protocol stays capability-agnostic (it consumes a resolved result, not the registry).

**Four-layer validation split (review #9):**
1. **cell-schema validation** — the `VerificationPolicy`/`EvidencePolicy` are well-formed.
2. **claim-shape conformance** (`validate_claim_shape`) — unchanged shape checks; it does **not**
   inspect executing-adapter count.
3. **trust-binding validation** (`validate_trust_binding`, `capabilities.py:130`) — for `single`, do
   **not** require an independent credential pair; require the single execution credential + (if the
   cell binds one) a resolvable, in-domain, trusted oracle. (Removes the unconditional
   `BINDING_NO_INDEPENDENT_PAIR` for this mode — review #10.)
4. **runtime execution-policy enforcement** — the orchestrator refuses to take the single-evidence path
   for a claim whose resolved cell is not `execution:"single"` (review #30: an unregistered/mismatched
   claim cannot accidentally select it).

**Compatibility (replaces the imprecise "byte-identical" claim — review #11).** Acceptance is stated at
four levels for the three existing cells + all existing suites: (a) behaviorally backward-compatible;
(b) JSON-schema compatible; (c) canonical-serialization identical; (d) content-address identical.
Adding optional defaulted fields can change `model_dump()`, so the plan must either exclude
unset/default fields in the canonical serializer or accept + document a one-time content-address bump.
**A golden test pins the canonical serialization of the three existing cells before/after** (review
#32); the target is (c)+(d) identical, and any deviation is an explicit, documented decision.

---

## 6. Lifecycle / status semantics (review #22/#23/#24)

| Criterion satisfied? | e-LOND discovery? | Status |
|---|---|---|
| yes | yes | **LICENSED** (`EVIDENCE_LICENSED`, `SINGLE_SOURCE`) |
| yes | no | **PENDING** (insufficient evidence; re-testable) |
| no | yes | **PENDING** (effect detected but criterion unmet; not licensed) |
| no | no | **PENDING** |
| execution error (NaN/out-of-support/adapter failure) | — | **PENDING** with an execution-error reason — *distinct from evidential failure* |

Sub-threshold evidence is **PENDING, never terminal REJECTED** (matches the existing core's
re-testability). Oracle present-but-unresolved / out-of-domain / untrusted / downgraded → trust-binding
fails → claim does not license (review #21).

---

## 7. Fixtures & tests

**Slice-1 fixture:** a **tiny, hand-checkable** committed benchmark (e.g. n=20, base-rate 0.5, model
correct on 18/20) so the betting e-value is verifiable by inspection and a known multiple of `1/α`.

**Tests (TDD; failing test first):**

1. **E-value null regression (review #26):** over the declared null (correctness drawn at the base
   rate), empirical mean of the e-value ≤ ~1 across seeds — a regression guard against transform
   mistakes.
2. **Boundary (review #18/#27):** `p₀→{0,1}` clamping; empty/degenerate stream → `e=0`; one-sided
   `GT` only (EQ/NE → 0). Upper behavior sane.
3. **Honest license:** tiny benchmark → criterion satisfied + e clears e-LOND → LICENSED with
   `route=EVIDENCE_LICENSED`, `independence_tier=SINGLE_SOURCE`, and a populated provenance record.
4. **Honest non-license:** model at base-rate → e below threshold → PENDING (each off-diagonal row of
   §6).
5. **Standing serialization (review #31):** a single-source license does **not** serialize as
   `reproduced`; `SINGLE_SOURCE` round-trips.
6. **Runtime guard (review #30):** a claim whose resolved cell is not `single` cannot select the
   evidence path.
7. **Four-layer validation:** cell-schema, claim-shape, trust-binding (single-mode accepts 1 credential;
   `recompute_pair` still requires the independent pair), runtime enforcement.
8. **Compat goldens (review #32):** canonical serialization of the three existing cells unchanged;
   full grammar/protocol/umbrella suites green.

---

## 8. Acceptance criteria

1. `eval::benchmark_accuracy@v1` is registered with `VerificationPolicy{execution:"single", …}` and a
   content-addressed `EvidencePolicy`.
2. It licenses a claim **offline** from the committed benchmark via a single model adapter and an
   **honest betting e-value** gated by e-LOND — no synthetic corroborator, no air-gap claim.
3. The license carries `route=EVIDENCE_LICENSED`, `independence_tier=SINGLE_SOURCE`, and a durable
   content-addressed provenance record; it never reads `REPRODUCED`.
4. The four-layer validation split holds; `validate_trust_binding` no longer demands an independent
   pair for `single`.
5. The three existing cells + all suites meet compatibility levels (a)–(d) (or a documented bump);
   `grammar/`+`protocol/` stay pure + numpy-free; `Corpus` stays 4; `scripts/check-all.sh` green.
6. The design records the discovered misfit + the structured-policy lesson (input to V2.1–V2.3).

---

## 9. Explicitly deferred (with review-point tags)

- **Slice 2:** a *meaningful* committed benchmark; full attestation provenance — request/response/
  model-version/endpoint/capture/signer/calibration digests (review #12) — flowing into the
  certificate/SLSA `resolvedDependencies` and subject digest (review #13/#25); `build_certificate`
  gaining the evidence basis.
- **Slice 3:** defeat / drift / reinstatement / replay coverage for this route (review #33/#34);
  cassette/benchmark tamper + model-version-mismatch + calibration-digest-mismatch tests (review #28);
  out-of-domain / downgraded-oracle behavioral tests (review #21).
- **Later (not this feature):** closed-world *enforcement*; a capability-ref on the claim (Seam A);
  quorum/agreement verification policies; the V2.1–V2.3 capabilities.

---

## 10. Decomposition (Path A) & rhythm

- **Slice 1 (this spec):** the honest evidence-licensing route + IR + standing + tiny benchmark.
- **Slice 2:** meaningful benchmark + full provenance/attestation + certificate/SLSA.
- **Slice 3:** lifecycle hardening (defeat/drift/reinstatement/replay) + tamper/boundary depth.

Each slice: `writing-plans` → `superpowers:subagent-driven-development` (TDD per task) → whole-branch
review → merge `--no-ff` → update `CONTINUE.md` + memory.
