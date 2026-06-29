# V2.0 Slice 1 — Evidence-licensed capability via an in-cycle gated executor

**Date:** 2026-06-29
**Author:** Z. Belden (synthesized with Claude)
**Status:** DESIGN (v4, post-3rd-review) — awaiting review → `writing-plans`
**Roadmap item:** V2.0 (`docs/superpowers/2026-06-23-remaining-roadmap.md`)
**Depends on:** Capability Cell + Registry V1 (`b058d3c`)

> **Revision history.** v1 (cassette + likelihood ratio) — no sampling distribution. v2 (accuracy vs
> base-rate) — marginal mean bound ≠ sequential null; data-dependent `p₀`. v3 (paired baseline,
> **out-of-cycle** precompute injected as `ResolvedVerification`) — *unsound*: computing evidence before
> commit/α-lock is a multiplicity leak, the injected DTO is a license-forging surface, and removing
> evidence claims from `exec_records` breaks pre-registration resolution + all bookkeeping. **This v4**
> keeps the v2/v3 *statistics* (corrected) but moves execution **in-cycle, post-commit**, behind the
> protocol's existing gate stack, via an injected executor. Architecture grounded in a full pipeline +
> content-address map (see "Grounding" footnotes). **Slice 1 of Path A** (§13).

---

## 1. Purpose & the generalization lesson

V2.0 registers one genuinely-new capability — licensed *not* by two pure-Python recompute legs — to
find where V1's abstraction breaks, and to build the minimal honest machinery. The lesson V2.0 teaches
(and that gates V2.1–V2.3 + closed-world execution): **a capability can be executed and licensed by an
in-cycle, registered, content-addressed *executor* that runs through the same eligibility gates as the
recompute path — the gate stack, not the adapter count, is the trust boundary.**

**Non-goals:** the wedge (H1.A2 → H2 stays critical path); closed-world *enforcement*; V2.1–V2.3;
networked calls; certificate/SLSA evidence integration (Slice 2); defeat/drift/reinstatement (Slice 3).

---

## 2. Architecture — in-cycle, post-commit, gated (the v3→v4 fix)

`run_cycle`'s order is REPRESENT → GENERATE → CANONICALIZE → SAFETY → **SELECT** → **COMMIT** →
**EXECUTE** → **VERIFY** → INTEGRATE → LEDGER.¹ The evidence route plugs into the **existing** pipeline:

1. **Identification.** An evidence claim's terminal `OperationNode.impl` is the capability's
   `operation_impl` (e.g. `eval::benchmark_advantage`). It is already covered by `commitment_hash`
   (which hashes `evaluation_plan` only²), so the capability + criterion are locked at COMMIT — swapping
   them post-registration trips `HYPOTHESIS_ALTERED`.
2. **Pre-registration (multiplicity-safe).** The caller `register_hypotheses(...)` **before**
   `run_cycle` (today's pattern), locking the e-LOND α-slot + `commitment_hash`.³ The executor runs
   *inside* the cycle at EXECUTE (post-COMMIT), so the caller never observes the outcome before the slot
   is locked — closing the v3 multiplicity leak.
3. **Execution branch.** `run_cycle` gains injected `evidence_executor` (umbrella; numpy lives there)
   and the pure `capability_registry` (grammar). In `execute_ground`'s single per-claim chokepoint⁴,
   if `capability_registry` resolves the node's `impl` to a cell whose `verification_policy.execution
   == "single"`, the claim is dispatched to `evidence_executor` **instead of** the two-adapter
   `verify()`. The executor returns a normal `ExecRecord(claim_id, evaluation=VerifiedEvaluation(...))`
   carrying an **honest `SATISFIED` Satisfaction** *iff* the criterion is met (otherwise a non-satisfied
   verdict → no Satisfaction → Gate A withholds the license). It **always** emits an e-value (to resolve
   the locked FDR test even when the criterion is unmet) plus an `EvidenceLicensingInfo`
   (route/standing/provenance). **Data flow:** `execute_ground` returns these alongside `records`;
   `run_cycle` merges the e-values into the existing `evidence=` map and threads the
   `EvidenceLicensingInfo` dict into `verify_stage` as a new parameter (§8). `ExecRecord` stays the
   universal bridge⁶ — no new content-addressed structure is introduced.
4. **Gating + licensing (reuse).** Because the output is a normal `ExecRecord` + an `evidence=` e-value,
   the **entire existing `verify_stage` gate stack applies unchanged**: Gate A minted-Satisfaction,
   B grounded-extension, C provenance, D BH selective-inference bar, E e-LOND, F commitment-hash match,
   G PENDING.⁵ The Phase-D pre-registration resolution loop (which iterates `exec_records`) resolves the
   locked test automatically. `executed_ids`, audit counts, and Goodhart/selection-ledger credit all
   accrue because the claim went through SELECT and produced a record.⁶

This is the v3→v4 correction: **no out-of-cycle precompute, no injected-DTO licensing path, no
gate-bypass.** A malicious caller cannot forge a license — the executor runs in-cycle and its output
still must clear A–G; trust in the executor itself is the same model as adapters (byte-derived
credential, §6).

> ¹ `cycle.py:62-183`. ² `commitment.py:13-18` (hashes `evaluation_plan` only). ³ `register.py:15`,
> `fdr.py:111` `register_test`. ⁴ `execute.py:51-60`. ⁵ Gates quoted at `verify.py:231-233` +
> `_permitted_by_bar` `verify.py:80-115` + `_e_ok` `verify.py:197-201`. ⁶ `cycle.py:125,130-168`.

**Two localized `verify_stage` changes** (the only edits to the licensing block):
- **Skip the independent-pair gate** (`verify.py:235-245`) for evidence claims (single-source by
  design — else `ADAPTER_NOT_INDEPENDENT`).
- **Stamp route/standing/provenance**: at `Licensing` construction (`verify.py:252-258`), if the claim
  has `EvidenceLicensingInfo`, build `Licensing(route=EVIDENCE_LICENSED, independence_tier=None,
  verification_standing=..., evidence_provenance=..., satisfactions=(sat,), ...)` instead of the
  `SEVERE_TEST` default. This only **labels** an already-gated license; it cannot license anything that
  fails A–G.

---

## 3. Statistical core (corrected per audit-3)

**Inferential claim (unchanged from v3):** under a declared **IID** sampling of benchmark examples from
a target population, the model's expected per-example accuracy **advantage over a precommitted baseline
exceeds τ ≥ 0**.

**Paired increments / sequential null.** `Wᵢ = 1(model correctᵢ) − 1(baseline correctᵢ) ∈ {−1,0,+1}`.
Test `H0: E[Wᵢ − τ | history] ≤ 0`. The criterion (in the claim's `SatisfactionCriterion`) tests
observed advantage `> τ`; **the e-value tests the same τ** — the policy's `theta0 = τ` and the criterion
threshold must be equal (validated), so a weak criterion cannot diverge from the null (audit #9, #14).

**E-value (committed order, no permutation).** `paired_advantage_evalue(w, theta0=τ)` runs the existing
GRAPA capital core⁷ over `Wᵢ − τ` in the benchmark's **single committed example order** — *not* the
seed-averaged random permutations of `betting_evalue` (which assume exchangeability beyond the stated
sequential null; audit #6). Positivity: increments lie in `[−1−τ, 1−τ]`, so `lam_max = _C/(1+τ)` keeps
every factor `1 + λ(Wᵢ−τ) ≥ 1−_C > 0`. **Validity (the proof obligation, audit #8):** under the IID
null with `θ₀=τ`, `e = Πᵢ(1+λᵢ(Wᵢ−τ))` is a non-negative test supermartingale (predictable past-only
`λ`, positive factors), so `E_H0[e] ≤ 1` by Ville's inequality — exactly the WSR guarantee the existing
methyl e-value already relies on, transferred to the paired stream.

**No outcome-dependent filtering (audit #1, critical).** Only *structurally* degenerate inputs are
rejected (empty stream, missing/duplicate/extra predictions, malformed) — **never** based on the
observed advantage. All-tie or all-negative streams are *valid results*: they yield `e ≤ 1`, no e-LOND
discovery, and the claim stays PENDING. Submitting the test is decided before scoring, not after.

**Sampling regime is typed (audit #7).** `SamplingRegime` enum with one member for this slice,
`IID_EXAMPLES`; it is a *disclosed assumption* recorded in the `EvidencePolicy`, not a free string.

> ⁷ `_grapa_capital` `src/polymer_claims/evidence.py:28-46`.

---

## 4. Typed objects

- **`VerificationPolicy`** (optional on `CapabilityCell`; **byte-safe** — `CapabilityCell` is content-
  addressed nowhere⁸): `execution: Literal["recompute_pair","single"] = "recompute_pair"`,
  `result_rule: Literal["criterion"] = "criterion"`, `independence_requirement: Literal["implementation",
  "baseline_ground_truth"] = "implementation"`, `evidence_policy_ref: str | None = None`,
  `min_adapters: int = 2`. Validator: `single` ⇒ `evidence_policy_ref` set, `min_adapters == 1`. Default
  `None` ⇒ the three existing cells unchanged.
- **`EvidencePolicy`** (pure grammar `_Model`; content-addressed by an **explicit** `content_hash`
  property — `_Model` has none for free⁹, so define one over the canonical `_sha` of its fields; `ref`
  = `content_hash`, no stored self-referential digest, audit #10): `policy_id`, `version`,
  `null_family: Literal["paired_bounded_mean_betting"]`, `theta0: float` (= τ),
  `statistic: Literal["accuracy_advantage_over_baseline"]`, `support: Literal["[-1,1]"]`,
  `sampling_regime: SamplingRegime`, `baseline_ref: str`, `calibration_population_ref: str`,
  `evalue_transform: Literal["paired_wsr_betting"]`. **Validators (audit #23):** non-empty ids/refs;
  `theta0` finite and `≥ 0`; `null_family`↔`evalue_transform` compatible. `EvidencePolicyRegistry`:
  `resolve(ref) -> EvidencePolicy | None` by recomputing `content_hash` (digest-verified).
- **`EvidenceProvenance`** (on `Licensing`): `execution_credential_id`, `evidence_policy_ref`,
  `benchmark_ref`, `baseline_ref`, `oracle_dossier_ref | None`, `observed_advantage`, `theta0`,
  `e_value`, `criterion_satisfied`. **Invariant (audit #24):** its `e_value` equals the resolved
  `FDRTest.e_value` by construction (the executor produces one e-value used for both the ledger and the
  provenance; a `verify_stage` assertion enforces equality).
- **`EvidenceLicensingInfo`** (transient, executor→`verify_stage`, keyed by claim_id; *not* a stored
  model): `route`, `verification_standing`, `evidence_provenance`. Carries the *labels* for an
  already-gated license; it does not itself license.
- **`verification_standing`** (on `Licensing`): `Literal["single_source_baseline"]` — a constrained
  literal, not a free string (audit #22).

> ⁸ `CAPABILITY_CELLS` consumed only via `.resolve()`; no hash/golden serializes a cell. ⁹ per-model
> `content_hash` `@property` convention, e.g. `operations.py:153-160`.

---

## 5. The benchmark-adapter interface (the generalization lesson — audit #6)

V1's adapter returns a scalar `ExecValue`¹⁰; a per-example evaluation cannot. Slice 1 adds:
- **`BenchmarkArtifact`** (content-addressed; `content_hash` over canonical bytes binding *everything*
  — audit #16): ordered `example_ids`, per-example `features`, `labels`, `target_population`,
  `sampling_regime`, `version`. The `EvidencePolicy.calibration_population_ref` **==** the artifact's
  `content_hash`.
- **`BenchmarkAdapter`** Protocol: `predict(examples_without_labels) -> PredictionVector` — the model
  sees inputs + ids, **never** labels (structurally absent from the call). Its predictions are
  content-addressed → `EvidencePolicy.baseline_ref` for the baseline (audit #17).
- **`Scorer`** (separate; holds labels): joins predictions↔labels by `example_id` in the artifact's
  committed order; missing/duplicate/extra/order-mismatch → `ScoringError` (an *execution error*, §7).

> ¹⁰ `ExecValue(value: float|str|None)` `evaluate.py:43`.

---

## 6. Trust binding (single-execution) — audit #19/#20/#21

A 4th cell needs both a `CAPABILITY_CELLS` entry **and** a `_bindings()` entry (else `bind()` raises¹¹).
The binding's `AdapterRegistry` holds the model adapter's `AdapterCredential` with a **byte-derived
`implementation_hash`** (`implementation_hash_for_adapter`, hashing the adapter's `execute` bytecode¹²)
— so a swapped implementation is detected; identity-string matching is not the trust basis.

`validate_trust_binding` gains an `evidence_policy_registry: EvidencePolicyRegistry | None = None`
parameter (absent today¹³) and a **single-mode branch**: when `cell.verification_policy.execution ==
"single"`, do **not** require an independent pair (skip `BINDING_NO_INDEPENDENT_PAIR`); instead require
(a) the single execution credential resolvable + trusted, (b) the `EvidencePolicy` resolvable +
digest-verified + `calibration_population_ref`/`baseline_ref` matching the bound benchmark/baseline, and
(c) the oracle dossier if `cell.oracle.required`. `recompute_pair` cells are unchanged.

> ¹¹ `bind()` `capabilities.py:105-111`. ¹² `adapter_identity.py:13`. ¹³ `validate_trust_binding`
> `capabilities.py:114-116`.

---

## 7. Lifecycle / status (audit #15)

| Outcome | Status |
|---|---|
| criterion satisfied **and** e-LOND discovery (+ gates B–G) | **LICENSED** (`EVIDENCE_LICENSED`, `single_source_baseline`) |
| criterion satisfied, no discovery | **PENDING** (insufficient evidence) |
| discovery, criterion unmet | **PENDING** |
| all-tie / negative advantage (valid result) | **PENDING** (e ≤ 1, no discovery) |
| structurally-invalid input (digest/policy/order/dup/credential mismatch, empty stream) | not dispatched / **PENDING** with `EXECUTION_ERROR`; never licensed |
| adapter failure / NaN / out-of-support | **PENDING**, `PendingReason.EXECUTION_ERROR` |

`PendingReason.EXECUTION_ERROR` is an additive enum member (audit #15). The executor mints a `SATISFIED`
Satisfaction **only** when the criterion is met (audit #13) — an unsatisfied evaluation carries a
non-satisfied verdict and cannot enter `Licensing` (whose validator requires every satisfaction be
`SATISFIED`¹⁴).

> ¹⁴ `Licensing._all_satisfied` `licensing.py:158-167`.

---

## 8. Schema deltas & compatibility (audit #25 — decided, not deferred)

**Grammar (pure):** `LicenseRoute.EVIDENCE_LICENSED`; `Licensing.independence_tier: IndependenceTier |
None` (keep default `REPRODUCED` so existing routes are unchanged; the evidence branch sets `None`);
`Licensing.verification_standing` + `Licensing.evidence_provenance` (optional, present-only-when
`route == EVIDENCE_LICENSED`, validated); `PendingReason.EXECUTION_ERROR`; `SamplingRegime`;
`EvidencePolicy`(+registry); `VerificationPolicy`; optional `CapabilityCell.verification_policy`.

**Protocol:** `run_cycle` + `execute_ground` gain `evidence_executor` + `capability_registry`;
`verify_stage` gains `evidence_licensing: dict[str, EvidenceLicensingInfo] | None` and the two localized
hooks (§2). The injected executor is a **`Callable` typed in protocol** (no grammar/numpy coupling); its
umbrella implementation does the numpy work.

**Compatibility, concretely (audit #25):**
- `CapabilityCell.verification_policy` → **byte-identical** (cell serialized in no hash/golden⁸).
- `Licensing.verification_standing`/`evidence_provenance` → **NOT byte-identical**: `Licensing` is
  hashed transitively into the whole-claim attestation **subject digest** (`attestation.py:194`, **no**
  `exclude_none`¹⁵), so every LICENSED claim's digest gains `"verification_standing":null,
  "evidence_provenance":null`. **Decision:** re-bless `tests/attestation/_golden_bundle.json` (subject
  digests `fb81e5a2…`, `2426880d…`) once, with a documented rationale — semantically correct, since an
  evidence-licensed claim *should* digest differently from a recompute-licensed one. **Deferred (noted,
  not entangled here):** switching the content-address convention to `exclude_none` so future optional
  additions are byte-safe — a separate change touching every attested claim's digest.

Acceptance level (d) "content-address identical" is thus **explicitly relaxed**: identical for
non-LICENSED claims and the three existing cells; LICENSED-claim subject digests re-blessed once.

> ¹⁵ `_subject()` `attestation.py:194` (`canonical_sha256(claim.model_dump(mode="json"))`, no
> exclude_none).

---

## 9. Honest fixture (audit #5/#17)

A tiny benchmark whose **labels are generated independently of the model's decision rule** (seeded label
process), with the model genuinely — but not perfectly — better than the baseline (e.g. ~15/20 vs the
baseline's ~10/20), so the e-value is a real finite value, not `∞`-by-construction. Predictions are
frozen via a label-independent seed; the construction order (predictions fixed → labels assigned by an
independent process) is documented in the fixture file. No labels are chosen to favor the predictions.

---

## 10. Tests (audit #18/#19/#20/#21/#26/#27/#28)

1. **E-value arithmetic regression** (renamed from "validity proof", audit #8): exact small-stream
   values + a documented Ville argument in this spec (§3); a test that an all-tie/negative stream gives
   `e ≤ 1` (audit #1).
2. **No outcome filtering:** all-negative stream returns a valid low e-value (not an exception).
3. **Structural degeneracy** only: empty/missing/dup/extra → `ScoringError`/`EXECUTION_ERROR`.
4. **Label withholding (#20):** the `BenchmarkAdapter.predict` signature has no label parameter; a test
   asserts the scorer is the only label holder.
5. **Paired alignment (#21):** `Wᵢ` joins by `example_id` in committed order; a model == baseline gives
   `e ≤ 1`, no license.
6. **Content-address binding (#16/#17):** tampering any artifact/baseline byte changes its
   `content_hash` and fails policy resolution.
7. **Byte-derived credential (#21):** a swapped adapter implementation changes `implementation_hash` and
   fails trust-binding.
8. **Single-mode binding (#19):** `validate_trust_binding(..., evidence_policy_registry=…)` passes with
   one credential; `recompute_pair` cells still require the pair.
9. **Standing serialization:** evidence license has `independence_tier=None`,
   `verification_standing="single_source_baseline"`; never `reproduced`.
10. **Gate reuse (the core safety test):** an evidence claim that is **not** selected / not committed /
    not in the grounded extension / has an altered plan / sub-threshold e-value is **not** licensed —
    proving the evidence route is subject to all of A–G.
11. **Validity-protection BEFORE end-to-end (#26):** tests 3,6,7,8 precede the end-to-end license test
    in task order.
12. **Compat goldens:** the three existing cells byte-identical; attestation goldens re-blessed with a
    documented diff; full `scripts/check-all.sh` green **as the final task** (#27).
13. **Protocol-test purity (#28):** protocol tests inject a tiny **grammar-DTO** executor stub; they do
    **not** import `polymer_claims`.

---

## 11. Acceptance criteria

1. `eval::benchmark_advantage@v1` registered (cell + `_bindings()` entry + byte-derived credential +
   `EvidencePolicy`).
2. It licenses an inferential model-vs-precommitted-baseline claim **offline, in-cycle, post-commit**,
   via the paired sequential betting e-value gated by the **full existing gate stack** (A–G) — no
   out-of-cycle precompute, no gate-bypass, no synthetic corroborator.
3. License carries `route=EVIDENCE_LICENSED`, `independence_tier=None`,
   `verification_standing="single_source_baseline"`, and a durable provenance record whose `e_value`
   equals the ledger's.
4. The gate-reuse test (#10) proves the route is subject to selection, commit, grounded-extension,
   provenance, BH bar, e-LOND, commitment-hash, and PENDING gating.
5. Content-addressed benchmark/baseline + byte-derived credential + digest-verified policy reject every
   tamper/mismatch before licensing.
6. Compatibility per §8 (cells byte-identical; attestation goldens re-blessed once, documented);
   `grammar/`+`protocol/` stay pure + numpy-free; `Corpus` stays 4; `check-all.sh` green.

---

## 12. Audit-3 resolution map

#1 outcome-filtering removed (§3) · #2 in-cycle post-commit (§2) · #3 no inject path; gate reuse (§2) ·
#4 normal `ExecRecord` resolves Phase-D (§2) · #5 honest fixture (§9) · #6 committed order (§3) ·
#7 typed `SamplingRegime` (§3) · #8 regression test + Ville obligation (§3/§10) · #9 e-value tests τ
(§3) · #10 explicit `EvidencePolicy.content_hash` (§4) · #11 `from .base import _Model` (plan) ·
#12 Licensing needs ≥1 SATISFIED — executor mints SATISFIED only when satisfied (§7) · #13 same (§7) ·
#14 criterion==τ==θ₀ (§3) · #15 normal record feeds all bookkeeping (§2) · #16 `BenchmarkArtifact`
content hash (§5) · #17 baseline content-addressed + honest fixture (§5/§9) · #18 enumeration→regression
(§10) · #19 `validate_trust_binding` gains policy-registry arg (§6) · #20 `_bindings()` entry (§6) ·
#21 byte-derived credential (§6) · #22 `verification_standing` literal (§4) · #23 `EvidencePolicy`
validators (§4) · #24 provenance `e_value` == ledger invariant (§4) · #25 compat decided (§8) ·
#26 validity tests before e2e (§10) · #27 full gate last (§10) · #28 protocol tests use grammar DTOs
(§10).

---

## 13. Decomposition (Path A) & rhythm

- **Slice 1 (this spec):** the in-cycle gated executor + corrected statistics + content-addressed
  artifacts + binding + honest fixture.
- **Slice 2:** meaningful benchmark + full attestation chain + certificate/SLSA `resolvedDependencies`.
- **Slice 3:** defeat/drift/reinstatement/replay-over-time + tamper/boundary depth + downgraded-oracle.

Each slice: `writing-plans` → `subagent-driven-development` (TDD) → whole-branch review → merge
`--no-ff` → update `CONTINUE.md` + memory.
