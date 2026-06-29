# V2.0 Slice 1 — Evidence-licensed capability via an in-cycle gated executor

**Date:** 2026-06-29
**Author:** Z. Belden (synthesized with Claude)
**Status:** DESIGN (v5, post-4th-review — architecture APPROVED, contract hardened) → `writing-plans`
**Roadmap item:** V2.0 (`docs/superpowers/2026-06-23-remaining-roadmap.md`)
**Depends on:** Capability Cell + Registry V1 (`b058d3c`)

> **Revision history.** v1 (cassette + likelihood ratio) — no sampling distribution. v2 (accuracy vs
> base-rate) — marginal bound ≠ sequential null; data-dependent `p₀`. v3 (out-of-cycle precompute +
> injected DTO) — unsound (multiplicity leak, forge surface, broke pre-registration). v4 moved execution
> **in-cycle, post-commit** behind the gate stack — *architecture approved in 4th review*. **This v5**
> hardens the execution contract per the 4th review (binds the full execution contract into
> pre-registration; requires a locked FDR slot; credentials the whole executor; preserves existing
> content hashes; computed fixture). **Slice 1 of Path A** (§13).

---

## 1. Purpose & the generalization lesson

Register one genuinely-new capability — licensed *not* by two pure-Python recompute legs — to find
where V1's abstraction breaks, and build the minimal honest machinery. The lesson (gating V2.1–V2.3 +
closed-world execution): **a capability can be executed and licensed by an in-cycle, registered,
content-addressed *executor* running through the same eligibility gates as the recompute path — the
gate stack, not the adapter count, is the trust boundary.**

**Non-goals:** the wedge (H1.A2 → H2 stays critical path); closed-world *enforcement*; V2.1–V2.3;
networked calls; certificate/SLSA evidence integration (Slice 2); defeat/drift/reinstatement (Slice 3).

**Trust model (stated honestly — audit-4 #6).** This is a *local injected-executor* model. The
guarantee is narrow: **a result cannot bypass the protocol gates** (selection, commit, pre-registration,
grounded extension, BH bar, e-LOND, commitment match). Scientific validity still depends on the
configured executor and trust roots — a party controlling the executor, registry, benchmark and adapter
registry can construct internally-consistent false evidence, exactly as a party controlling the adapters
can today. What v5 adds is that the executor's code and the execution contract are **content-addressed
and pre-registered**, so they cannot be silently swapped after the α-slot is locked.

---

## 2. Architecture — in-cycle, post-commit, gated

`run_cycle`'s order: REPRESENT → GENERATE → CANONICALIZE → SAFETY → **SELECT** → **COMMIT** →
**EXECUTE** → **VERIFY** → INTEGRATE → LEDGER.¹ The evidence route uses the existing pipeline.

1. **Identification + execution-contract binding (audit-4 #1/#3/#14).** The `EvaluationPlan` carries an
   optional **`execution_contract`** field (omitted-when-`None`, §8) holding the **explicit
   `capability_id` + `capability_version`**, `evidence_policy_ref`, and `baseline_ref` (τ already lives
   in the criterion). Because `commitment_hash` hashes the whole `evaluation_plan`², these are bound by
   pre-registration: a caller cannot register the claim and then resolve a *different* cell/policy/
   baseline under the same `operation_impl` without changing the plan and tripping `HYPOTHESIS_ALTERED`.
   Dispatch resolves the cell by the **explicit versioned capability key in `execution_contract`** (not
   by inferring from `node.impl`, which is ambiguous across versions). The contract field is placed on
   the plan (not on a graph node) so existing claims' **graph hashes** are untouched (§8).
2. **Pre-registration is mandatory and enforced (audit-4 #2).** The caller `register_hypotheses(...)`
   **before** `run_cycle`, locking the e-LOND α-slot + `commitment_hash`.³ The evidence dispatcher
   **refuses to execute** a claim that is not `selected ∧ committed ∧ has a pending registered FDR test
   ∧ commitment matches` — so "the outcome cannot be observed before the slot is locked" is *enforced*,
   not convention. (Charge-at-verify is disallowed for the evidence route.)
3. **Execution branch.** `run_cycle` gains injected `evidence_executor` (umbrella; numpy) + the pure
   `capability_registry` (grammar). In `execute_ground`'s single per-claim chokepoint⁴, a claim whose
   resolved cell has `verification_policy.execution == "single"` — **and** that passes claim-shape
   conformance to that cell (§6, audit-4 #9) and the §2.2 precondition — is dispatched to
   `evidence_executor` instead of the two-adapter `verify()`. The executor returns a typed
   **`EvidenceExecution`** DTO (audit-4 #16):
   `{record: ExecRecord, e_value: float | None, licensing_info: EvidenceLicensingInfo | None,
   failure_reason: ExecutionFailure | None}`. The `record` carries an honest `SATISFIED` Satisfaction
   **iff** the criterion is met (else a non-satisfied verdict → no Satisfaction → Gate A withholds).
   **A successfully-scored execution always emits an `e_value`** (resolving the locked test regardless of
   criterion verdict); a **structural failure** (empty/malformed/dup/missing/credential mismatch) emits
   `e_value=None` + a `failure_reason` → the claim is PENDING `EXECUTION_ERROR` and **its locked α-slot
   stays consumed and unresolved** (a deliberate, tested consequence — audit-4 #15).
4. **Data flow.** `execute_ground` returns `(corpus, records, evidence_executions)`; `run_cycle` merges
   the e-values into the existing `evidence=` map and threads an `evidence_licensing: dict[claim_id,
   EvidenceLicensingInfo]` into `verify_stage`. `ExecRecord` stays the universal bridge⁶.
5. **Gating + licensing (reuse).** Because the output is a normal `ExecRecord` + an `evidence=` e-value,
   the **entire existing `verify_stage` gate stack applies unchanged**: A minted-Satisfaction,
   B grounded-extension, C provenance, D BH bar, E e-LOND, F commitment-hash, G PENDING.⁵ Phase-D
   resolution (iterating `exec_records`) resolves the locked test; `executed_ids`, audit counts, and
   Goodhart/selection credit accrue because the claim went through SELECT and produced a record.⁷

**Two localized `verify_stage` edits only:** skip the independent-pair gate (`verify.py:235-245`) for
evidence claims (single-source by design); and at `Licensing` construction (`verify.py:252-258`), when
`c.id ∈ evidence_licensing`, build `Licensing(route=EVIDENCE_LICENSED, independence_tier=None,
verification_standing=…, evidence_provenance=…, satisfactions=(sat,), …)` instead of the `SEVERE_TEST`
default. This only **labels** an already-gated license; it cannot license anything that fails A–G.

> ¹ `cycle.py:62-183`. ² `commitment.py:13-18`. ³ `register.py:15`, `fdr.py:111`. ⁴ `execute.py:51-60`.
> ⁵ `verify.py:231-233` + `_permitted_by_bar:80-115` + `_e_ok:197-201`. ⁶ `ExecRecord` `corpus.py:86`.
> ⁷ `cycle.py:125,130-168`.

---

## 3. Statistical core

**Inferential claim.** Under a declared **IID** sampling of benchmark examples from a target population —
*with the model, baseline, preprocessing and decision rules all fixed independently of the evaluation
sample* (recorded in the `EvidencePolicy` commitment — audit-4 #14) — the model's expected per-example
accuracy **advantage over a precommitted baseline exceeds τ ≥ 0**.

**Paired increments / sequential null.** `Wᵢ = 1(model correctᵢ) − 1(baseline correctᵢ) ∈ {−1,0,+1}`,
test `H0: E[Wᵢ − τ | history] ≤ 0`. The claim's `SatisfactionCriterion` tests observed advantage `> τ`;
the policy's `theta0 = τ` **must equal** that criterion threshold (validated) so criterion and null
address one statistic (audit #9/#14).

**E-value (committed order, no permutation).** `paired_advantage_evalue(w, theta0=τ)` runs the existing
GRAPA capital core⁸ over `Wᵢ − τ` in the benchmark's **single committed example order** (not the
seed-averaged permutations of `betting_evalue`, audit #6). `lam_max = _C/(1+τ)` keeps factors
`1+λ(Wᵢ−τ) ≥ 1−_C > 0`. **Validity (proof obligation, audit #8):** under the IID null with `θ₀=τ`,
`e = Πᵢ(1+λᵢ(Wᵢ−τ))` is a non-negative test supermartingale (predictable past-only λ, positive
factors), so `E_H0[e] ≤ 1` by Ville — the same WSR guarantee the methyl e-value relies on.

**No outcome-dependent filtering (audit #1).** Only *structurally* degenerate inputs are rejected
(empty / missing / dup / extra / malformed). All-tie or all-negative streams are **valid results** →
`e ≤ 1`, no discovery, PENDING. The decision to submit the test is made before scoring.

**Typed sampling regime (audit #7).** `SamplingRegime` enum, one member `IID_EXAMPLES`, a disclosed
assumption recorded in the `EvidencePolicy`.

> ⁸ `_grapa_capital` `evidence.py:28-46`.

---

## 4. Typed objects

- **`VerificationPolicy`** (optional on `CapabilityCell`): `execution: Literal["recompute_pair",
  "single"]`, `result_rule: Literal["criterion"]`, `independence_requirement: Literal["implementation",
  "baseline_ground_truth"]`, `evidence_policy_ref: str | None`, `min_adapters: int`. Validator: `single`
  ⇒ `evidence_policy_ref` set ∧ `min_adapters == 1`. Default `None` ⇒ existing cells unchanged.
- **`EvidencePolicy`** (pure grammar `_Model`; explicit `content_hash` property — `_Model` has none free⁹
  — over canonical `_sha` of its fields; `ref = content_hash`, no stored self-digest, audit #10):
  `policy_id`, `version`, `null_family: Literal["paired_bounded_mean_betting"]`, `theta0: float (=τ)`,
  `statistic`, `support`, `sampling_regime: SamplingRegime`, `baseline_ref`,
  `calibration_population_ref`, `evalue_transform`, and an `executor_credential_ref` (the digest of the
  registered executor credential, §6). **Validators (audit #23):** non-empty ids/refs; `theta0` finite,
  `≥0`; family↔transform compatible. `EvidencePolicyRegistry.resolve(ref)` recomputes `content_hash`.
- **`ExecutionContract`** (the composite bound into pre-registration — audit #1/#17): the tuple
  `(capability_id, capability_version, verification_policy, evidence_policy_ref, benchmark_ref,
  baseline_ref, executor_credential_ref)`, all present in the plan or resolved-and-checked at verify; its
  digest plus the `FDRTest` index + locked `alpha_allocated` are recorded in the provenance.
- **`EvidenceProvenance`** (on `Licensing`): `executor_credential_ref`, `evidence_policy_ref`,
  `benchmark_ref`, `baseline_ref`, `oracle_dossier_ref | None`, `observed_advantage`, `theta0`,
  `e_value`, `criterion_satisfied`, **`execution_contract_digest`**, **`fdr_test_index`**,
  **`alpha_allocated`** (audit #17). Invariant: its `e_value` equals the resolved `FDRTest.e_value` by
  construction (audit #24).
- **`EvidenceExecution`** (transient executor return DTO — audit #16): `record: ExecRecord`,
  `e_value: float | None`, `licensing_info: EvidenceLicensingInfo | None`,
  `failure_reason: ExecutionFailure | None`.
- **`EvidenceLicensingInfo`** (transient executor→`verify_stage`): `route`, `verification_standing`,
  `evidence_provenance`.
- **`verification_standing`** (on `Licensing`): `Literal["single_source_baseline"]` (audit #22).

> ⁹ per-model `content_hash` `@property` convention, e.g. `operations.py:153-160`.

---

## 5. Benchmark interface (the generalization lesson — audit #6)

V1's adapter returns a scalar `ExecValue`¹⁰; per-example evaluation cannot. Slice 1 adds:
- **`BenchmarkArtifact`** (content-addressed `content_hash` over canonical bytes binding ordered
  `example_ids`, per-example `features`, `labels`, `target_population`, `sampling_regime`, `version` —
  audit #16). `EvidencePolicy.calibration_population_ref == artifact.content_hash`.
- **`BenchmarkAdapter.predict(examples_without_labels) -> PredictionVector`** — labels structurally
  absent from the call. Baseline predictions content-addressed → `EvidencePolicy.baseline_ref` (#17).
- **`Scorer`** (separate, holds labels): joins predictions↔labels by `example_id` in committed order;
  missing/dup/extra/order-mismatch → structural failure (§2.3, `EXECUTION_ERROR`).

> ¹⁰ `ExecValue(value: float|str|None)` `evaluate.py:43`.

---

## 6. Trust binding & validation — three layers (audit-4 #5/#7/#8/#9)

The 4th review showed validation spans three distinct scopes; conflating them was a real error.

**Layer 1 — cell trust binding** (cell-level, claim-independent). A 4th cell needs a `CAPABILITY_CELLS`
entry **and** a `_bindings()` entry (else `bind()` raises¹¹). `min_executing_adapters` is reconciled
with the policy (audit #4): the cell validator that today forces `== 2`¹² becomes `2` for
`recompute_pair`, `1` for `single`. `validate_trust_binding` gains an `evidence_policy_registry`
parameter (absent today¹³) and a single-mode branch: skip the independent-pair requirement; require the
**executor credential** resolvable + trusted, and the `EvidencePolicy` resolvable + digest-verified.
**Oracle guarantee, stated accurately (audit #8):** `OracleDossier` has no `trusted` field and this layer
only confirms the oracle **id exists** in the registry — it does **not** call `in_domain` (no claim
subject here).

**Layer 2 — claim-to-capability binding** (claim-level, before dispatch — audit #9). The runtime runs
`validate_claim_shape(claim, cell)` (pattern/subject/params/output/data-ref/criterion) **before** taking
the single path. A non-conforming claim is not dispatched to the executor (this is *evidence-route*
enforcement, not general closed-world enforcement). Oracle `in_domain(subject)` is checked **here**,
where the subject exists.

**Layer 3 — runtime artifact/policy binding** (execution-time). The executor verifies: the
`BenchmarkArtifact.content_hash == policy.calibration_population_ref`; the baseline digest ==
`policy.baseline_ref`; and — critically — the **live executor implementation matches its registered
credential**.

**The executor is credentialed as a whole (audit #5).** Crediting only the model leaves the scorer and
e-value transform untrusted — an injected callable could emit arbitrary evidence under the model's
identity. So the **predictor, scorer, and evidence-transform implementations are each byte-hashed** (via
a generalization of `implementation_hash_for_adapter` that accepts the relevant method — the existing
one hashes `execute`¹⁴, and `BenchmarkAdapter` exposes `predict`, so the hasher takes the method
explicitly), combined into one **executor credential** whose digest is `policy.executor_credential_ref`.
Verification compares the **live** combined hash against the registered credential — not a returned
identity string.

> ¹¹ `bind()` `capabilities.py:105-111`. ¹² `min_executing_adapters` validator `capability.py:146-152`.
> ¹³ `validate_trust_binding` `capabilities.py:114-116`. ¹⁴ `adapter_identity.py:13`.

---

## 7. Lifecycle / status (audit #15)

| Outcome | Status |
|---|---|
| criterion satisfied ∧ e-LOND discovery ∧ gates B–G | **LICENSED** (`EVIDENCE_LICENSED`, `single_source_baseline`) |
| criterion satisfied, no discovery | **PENDING** |
| discovery, criterion unmet | **PENDING** |
| all-tie / negative advantage (valid) | **PENDING** (e ≤ 1) |
| structural failure (empty/dup/missing/order/credential/digest mismatch) | **PENDING** `EXECUTION_ERROR`; e_value=None; **locked α-slot consumed, test unresolved** |

A successfully-scored execution **always** emits an e-value (resolving the locked test regardless of
criterion verdict — audit #15); a structural failure emits none and leaves the registered test
unresolved (tested, §10). `PendingReason.EXECUTION_ERROR` is additive. The executor mints a `SATISFIED`
Satisfaction **only** when the criterion is met (audit #13) — `Licensing` requires every satisfaction be
`SATISFIED`¹⁵.

> ¹⁵ `Licensing._all_satisfied` `licensing.py:158-167`.

---

## 8. Schema deltas & compatibility (audit #10/#11 — preserve existing hashes)

**Grammar (pure):** `LicenseRoute.EVIDENCE_LICENSED`; `Licensing.independence_tier: IndependenceTier |
None`; `Licensing.verification_standing` + `Licensing.evidence_provenance` (optional, present-only-when
`route == EVIDENCE_LICENSED`); `PendingReason.EXECUTION_ERROR`; `SamplingRegime`; `EvidencePolicy`
(+registry); `VerificationPolicy`; optional `CapabilityCell.verification_policy`; an optional
`EvaluationPlan.execution_contract` field (`omitted-when-None`, so existing plans' `commitment_hash`,
graph hash, and commit lock are **byte-identical**; the field sits on the plan, not in the graph, so
`ComputeGraph.content_hash` is unaffected).

**Protocol:** `run_cycle`/`execute_ground` gain `evidence_executor` + `capability_registry`;
`execute_ground` returns `evidence_executions`; `verify_stage` gains `evidence_licensing` + the two
localized hooks (§2). The executor is a `Callable` typed in protocol (no numpy coupling).

**Compatibility — preserve existing content hashes (audit #10, the corrected answer).** `Licensing` is
hashed transitively into the whole-claim attestation **subject digest** (`attestation.py:194`, no
`exclude_none`¹⁶). To keep **existing recompute-license digests byte-stable**, add a `@model_serializer`
on `Licensing` that **omits `verification_standing` and `evidence_provenance` when they are `None`** (a
*targeted, field-specific* exclusion — it does not touch the other already-`None` optionals, so no other
claim's digest moves). Existing licensed claims therefore hash **identically**; evidence licenses (which
populate the fields) hash differently *because their semantics differ*. **No golden re-bless needed.**
`CapabilityCell.verification_policy` is similarly omitted-when-`None` in its dump so the cell is
**byte-identical**, not merely "not-currently-hashed" (audit #11). (A broader move to `exclude_none` in
the content-address convention is noted as out of scope.)

> ¹⁶ `_subject()` `attestation.py:194`.

---

## 9. Honest fixture (audit #12/#13 — corrected)

The contradiction in v4 ("labels independent of the model" yet "model better") is fixed. The fixture
declares:
- a **predeclared feature-dependent label DGP** `y = f(features) ⊕ noise` with independently-sampled
  noise;
- a **model rule fixed before the draws** that is genuinely (probabilistically) more accurate than a
  **weaker precommitted baseline**;
- the *random draws* are independent of *implementation choices* — **not** the labels independent of the
  features (audit #12).
**The fixture is sized by computation, not assertion (audit #13):** its `Wᵢ` stream, in committed order,
must yield `paired_advantage_evalue ≥ 1/α₁ ≈ 32.9` (q=0.05, γ₁=6/π²) against the **actual locked α** — a
15/20-vs-10/20 sketch gives e≈13.03 and would *not* license. The plan computes the exact fixture and a
test asserts the e-value clears the locked threshold before the end-to-end license test runs.

---

## 10. Tests (audit #18/#26/#27/#28)

1. **E-value regression** (renamed from "validity proof", #8): exact small-stream values; all-tie/
   negative → `e ≤ 1` (#1, **no exception**); a documented Ville argument in §3.
2. **Structural-only degeneracy:** empty/missing/dup/extra/order → `EXECUTION_ERROR` + e_value=None.
3. **Label withholding (#20):** `predict` has no label parameter; the scorer is the sole label holder.
4. **Paired alignment (#21):** `Wᵢ` joins by `example_id` in committed order; model==baseline → `e ≤ 1`.
5. **Execution-contract binding (#1/#3):** altering policy/baseline/capability changes `commitment_hash`
   → `HYPOTHESIS_ALTERED`; dispatch refuses a claim with no pending registered test (#2).
6. **Full-executor credential (#5):** swapping the **scorer** or **evidence-transform** (not just the
   model) changes the executor credential and fails Layer-3 verification.
7. **Three-layer validation (#7/#9):** a non-conforming claim is not dispatched; oracle `in_domain`
   checked at Layer 2; single-mode binding passes with one credential, `recompute_pair` still needs the
   pair.
8. **Gate reuse (core safety):** an evidence claim not selected / not committed / not in grounded
   extension / altered-plan / sub-threshold → **not licensed** (proves A–G apply).
9. **Bookkeeping (#18):** evidence execution updates stage-audit counts, selection-ledger outcome,
   Goodhart/operator credit, and integrate(); and an **execution failure leaves the registered test
   unresolved** with the α-slot consumed.
10. **Standing serialization:** evidence license has `independence_tier=None`, standing literal; never
    `reproduced`.
11. **Compatibility (#10/#11):** existing recompute-license attestation digests **byte-identical** (the
    `_golden_bundle.json` digests unchanged); `CapabilityCell` dump byte-identical; the three existing
    cells unchanged.
12. **Computed-fixture license (#13):** the fixture's e-value clears the locked α₁ before the end-to-end
    LICENSED assertion.
13. **Protocol-test purity (#28):** protocol tests inject a tiny **grammar-DTO** executor stub; no
    `polymer_claims` import.
Validity/contract tests (2,5,6,7,9,11) precede the end-to-end license test (#26); `scripts/check-all.sh`
is the **final** task (#27).

---

## 11. Acceptance criteria

1. `eval::benchmark_advantage@v1` registered (cell + `_bindings()` + **whole-executor** byte-derived
   credential + `EvidencePolicy`), `min_executing_adapters` reconciled with the policy.
2. Licenses an inferential model-vs-precommitted-baseline claim **offline, in-cycle, post-commit**,
   gated by the **full existing gate stack (A–G)** — no out-of-cycle precompute, no gate-bypass.
3. The **execution contract** (capability+policy+benchmark+baseline+executor credential) is bound into
   pre-registration (`commitment_hash`) and re-checked at verify; dispatch **requires a locked FDR
   slot**; provenance records the contract digest + FDR index + locked α, and its e-value equals the
   ledger's.
4. License carries `route=EVIDENCE_LICENSED`, `independence_tier=None`, standing literal, durable
   provenance.
5. Three-layer validation enforced; content-addressed artifacts + whole-executor credential reject every
   tamper/mismatch before licensing.
6. **Existing recompute-license attestation digests and the three existing cells are byte-identical**
   (targeted None-exclusion; no golden re-bless); `grammar/`+`protocol/` pure + numpy-free; `Corpus`
   stays 4; `check-all.sh` green.

---

## 12. Audit resolution map

**Audit-3 (all resolved in v4/v5):** see §3/§5/§6/§8/§12-prior.
**Audit-4:** #1 execution-contract in plan+`commitment_hash` (§2/§4) · #2 dispatch requires locked slot
(§2.2) · #3 explicit versioned capability key (§2.1) · #4 `min_executing_adapters` reconciled (§6 L1) ·
#5 whole-executor credential (§6 L3) · #6 narrowed trust claim (§1) · #7 three-layer validation (§6) ·
#8 accurate oracle guarantee (§6 L1/L2) · #9 claim-shape conformance before dispatch (§6 L2) ·
#10 targeted None-exclusion preserves existing hashes (§8) · #11 `CapabilityCell` byte-identical (§8) ·
#12 feature-dependent DGP fixture (§9) · #13 computed fixture e-value ≥ 32.9 (§9) · #14 IID binds
model/baseline (§3) · #15 successfully-scored emits e-value; failure consumes slot (§2.3/§7) ·
#16 `EvidenceExecution` DTO (§4) · #17 provenance binds contract digest + FDR index/α (§4) ·
#18 bookkeeping tests (§10).

---

## 13. Decomposition (Path A) & rhythm

- **Slice 1 (this spec):** in-cycle gated executor + corrected statistics + content-addressed artifacts
  + whole-executor credential + three-layer validation + computed honest fixture.
- **Slice 2:** meaningful benchmark + full attestation chain + certificate/SLSA.
- **Slice 3:** defeat/drift/reinstatement/replay-over-time + tamper/boundary depth + downgraded-oracle.

Each slice: `writing-plans` → `subagent-driven-development` (TDD) → whole-branch review → merge
`--no-ff` → update `CONTINUE.md` + memory.
