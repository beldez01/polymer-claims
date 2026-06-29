# V2.0 Slice 1 — Evidence-licensed capability via an in-cycle gated executor

**Date:** 2026-06-29
**Author:** Z. Belden (synthesized with Claude)
**Status:** DESIGN (v7, post-6th-review — architecture approved; contract, decision rule, descriptor finalized) → `writing-plans`
**Roadmap item:** V2.0 (`docs/superpowers/2026-06-23-remaining-roadmap.md`)
**Depends on:** Capability Cell + Registry V1 (`b058d3c`)

> **Revision history.** v1–v2 statistically unsound; v3 out-of-cycle (forge/multiplicity); v4 in-cycle
> (architecture approved, 4th review); v5 hardened contract; v6 unified the decision rule. **This v7**
> (6th review) fixes two honesty over-claims and fills specification gaps: e-LOND discovery is the
> *statistical* decision but **not coextensive** with licensing (license = discovery + eligibility, as
> for every route); the **BH bar does not constrain** evidence claims (e-LOND is their multiplicity
> mechanism — stated, not hand-waved); the baseline predictor is credentialed; the **concrete 4th cell
> descriptor** is specified; the cell descriptor itself is committed; and the None-omit mechanism is
> pinned to a verified `Field(exclude_if=…)`. **Slice 1 of Path A** (§14).

---

## 1. Purpose, lesson & trust model

Register one genuinely-new capability — licensed *not* by two pure-Python recompute legs — to find where
V1's abstraction breaks, and build the minimal honest machinery. **Lesson** (gating V2.1–V2.3 +
closed-world execution): *a capability can be executed and licensed by an in-cycle, registered,
content-addressed executor running through the same eligibility gates as the recompute path — the gate
stack, not the adapter count, is the trust boundary.*

**Non-goals:** the wedge (H1.A2 → H2 critical path); closed-world *enforcement*; V2.1–V2.3; networked
calls; certificate/SLSA evidence integration (Slice 2); defeat/drift/reinstatement (Slice 3).

**Trust model (honest, narrow — audit-4 #6).** Guarantee: **a result cannot bypass the protocol gates**
(selection, commit, mandatory pre-registration, grounded extension, e-LOND, commitment match). Validity
still depends on the configured executor + trust roots — a party controlling executor, registry,
benchmark and adapters can construct internally-consistent false evidence, as with adapters today. What
v7 adds: the executor's **code + configuration**, the **baseline rule**, the **cell descriptor**, and the
full execution contract are content-addressed and pre-registered, so none can be swapped after the α-slot
locks.

---

## 2. Architecture — in-cycle, post-commit, gated

`run_cycle` order: REPRESENT → GENERATE → CANONICALIZE → SAFETY → SELECT → COMMIT → EXECUTE → VERIFY →
INTEGRATE → LEDGER.¹

1. **Identification + contract binding.** The `EvaluationPlan` carries an optional **`execution_contract`**
   (omit-when-`None`, §8) = `ExecutionContract{capability_id, capability_version, evidence_policy_ref,
   capability_descriptor_ref}`. `commitment_hash` hashes the whole plan², so these are
   pre-registration-bound; everything else is bound **transitively through the content-addressed
   `EvidencePolicy`** (§4 hash chain). `capability_descriptor_ref` is the resolved cell's `content_hash`
   (audit-6 #7) so a registry swap under the same key is detected. Dispatch resolves by the explicit
   versioned key; `cell.operation_impl == terminal node.impl`, `cell.content_hash ==
   capability_descriptor_ref`, and `cell.verification_policy.evidence_policy_ref ==
   contract.evidence_policy_ref == EvidencePolicy.content_hash`.
2. **Pre-registration mandatory + enforced (audit-4 #2, audit-5 #8).** Caller `register_hypotheses`
   **before** `run_cycle` locks the α-slot + `commitment_hash`.³ The dispatcher **refuses** any evidence
   claim not `selected ∧ committed ∧ has a pending registered FDR test ∧ commitment matches`. **In-cycle
   GENERATE'd evidence claims are ineligible this cycle** (no prior registration); eligible only in a
   later cycle after the caller registers them.
3. **Execution branch.** `run_cycle` gains injected `evidence_executor` (umbrella; numpy) +
   `capability_registry` (grammar). In `execute_ground`'s per-claim chokepoint⁴, a `single`-policy cell
   claim passing claim-shape conformance (§6 L2) + §2.2 is dispatched to `evidence_executor`. **Before any
   prediction or label exposure (audit-5 #7)** the executor verifies Layer-3 bindings (§6 L3: artifact +
   baseline + whole-executor credential + config). It returns a typed **`EvidenceExecution`**:
   `{record: ExecRecord, e_value: float | None, licensing_info: EvidenceLicensingInfo | None,
   failure_reason: ExecutionFailure | None}` (§4). The `record`'s `EvaluationResult` carries
   **`verdict=UNDETERMINED`, `agreement=True`** — never `SATISFIED`/`REFUTED`⁵ — so the executor never
   itself licenses or terminally refutes. A successfully-scored execution emits an `e_value`; a structural
   failure emits `e_value=None` + `failure_reason`.
4. **Data flow.** `execute_ground` returns `(corpus, records, evidence_executions)`; `run_cycle` merges
   e-values into the existing `evidence=` map and threads `evidence_licensing` + `evidence_failures` into
   `verify_stage`. `ExecRecord` is the universal bridge⁶.
5. **Decision rule — statistical decision vs license (audit-6 #1, the honesty fix).** There is **no
   separate observed-advantage criterion**: the **e-LOND discovery on the τ-null is the *statistical*
   decision**, exactly as the recompute route's e-value gates discovery. Phase-D resolution resolves the
   locked test⁷. The **evidence-route licensing block** in verify_stage then maps status:
   - **failure** → PENDING `EXECUTION_ERROR`; the α-slot stays consumed + unresolved (§7).
   - **discovery ∧ eligibility (grounded-extension B ∧ provenance C ∧ commitment F ∧ PENDING G)** → mint
     `Satisfaction(verdict=SATISFIED, materialization, credential_ids=(executor_credential_ref,))` +
     `Licensing(route=EVIDENCE_LICENSED, independence_tier=None, verification_standing, evidence_provenance)`
     → **LICENSED**.
   - **discovery but ineligible**, **or no discovery** → **PENDING** (UNDETERMINED passthrough; never
     REFUTED).
   **License ≠ discovery (honest):** a claim can record a ledger discovery yet fail eligibility and not
   license — true for *every* route. The "single decision rule" claim is narrowed to: *the evidence route
   has no second criterion; its statistical test is the e-LOND discovery, and a license additionally
   requires the standard eligibility gates.* (The v6 "coextensive" wording was wrong.)
6. **The BH selective-inference bar does not constrain this route (audit-6 #4, honestly).**
   `_permitted_by_bar` derives earned strength only from satisfied records⁸; an UNDETERMINED evidence
   record has `strength=None` → treated as exempt. This is **correct and intentional, not an oversight**:
   **e-LOND (mandatory pre-registration + locked α) is the evidence route's multiplicity-control
   mechanism**, in place of the BH bar the recompute path uses. The spec does **not** claim Gate D
   constrains evidence claims.

This is **one route-specific licensing/status block** in verify_stage (plus skipping the
independent-pair gate for single-source) — not "two localized edits" (v5's overstatement).

> ¹ `cycle.py:62-183`. ² `commitment.py:13-18`. ³ `register.py:15`, `fdr.py:111`. ⁴ `execute.py:51-60`.
> ⁵ `SatisfactionVerdict{SATISFIED,REFUTED,UNDETERMINED}` `licensing.py:23`; `agreed_refuted` terminal
> `verify.py:224-228,316-321`; UNDETERMINED+agreement → `satisfaction=None` → passthrough PENDING
> `verify.py:327-328`. ⁶ `ExecRecord` `corpus.py:86`. ⁷ Phase-D `verify.py:169-186`. ⁸ `_permitted_by_bar`
> `verify.py:80-115`.

---

## 3. Statistical core

**Inferential claim.** Under declared **IID** sampling of examples from a target population — model,
baseline, preprocessing, decision rules **fixed independently of the evaluation sample** (recorded in the
policy commitment) — the model's expected per-example accuracy **advantage over a precommitted baseline
exceeds τ**, with **0 ≤ τ < 1** (advantage ∈ [−1,1]; τ ≥ 1 is impossible — audit-6 #15).

**Paired increments / sequential null.** `Wᵢ = 1(model correctᵢ) − 1(baseline correctᵢ) ∈ {−1,0,+1}`;
`H0: E[Wᵢ − τ | history] ≤ 0`; `policy.theta0 = τ`. The **licensing statistical decision is the e-LOND
discovery on this τ-null** (§2.5).

**E-value (committed order).** `paired_advantage_evalue(w, theta0=τ)` runs the existing GRAPA core⁹ over
`Wᵢ − τ` in the benchmark's single committed order. `lam_max = _C/(1+τ)` keeps factors `≥ 1−_C > 0`.
**Validity:** under the IID null with `θ₀=τ`, `e = Πᵢ(1+λᵢ(Wᵢ−τ))` is a non-negative test supermartingale
(predictable past-only λ, positive factors) → `E_H0[e] ≤ 1` by Ville.

**No outcome-dependent filtering.** Only structurally degenerate inputs are rejected; all-tie/negative →
`e ≤ 1` → no discovery → PENDING. **Typed `SamplingRegime`** (`IID_EXAMPLES`).

> ⁹ `_grapa_capital` `evidence.py:28-46`.

---

## 4. Typed objects, modules & the hash chain

**Module placement (audit-6 #8).** The pure DTOs live in grammar: `EvidencePolicy`(+registry),
`ExecutorCredential`(+registry), `ExecutionContract`, `EvidenceProvenance`, `EvidenceLicensingInfo`,
`ExecutionFailure`, `VerificationPolicy`, `SamplingRegime` under `grammar/src/polymer_grammar/`
(`evidence_policy.py`, `executor_credential.py`, `verification_policy.py`). The `evidence_executor` is a
`Callable` *typed in protocol* (no numpy/umbrella import); its implementation is umbrella.

**`evidence_executor` signature (audit-6 #9):** `(claim, cell, policy, benchmark_artifact, ctx,
executor_credential, fdr_test) -> EvidenceExecution` — all immutable, resolved inputs, so no hidden
lookups inside the executor.

- **`ExecutionContract`** (committed on `EvaluationPlan`): `capability_id`, `capability_version`,
  `evidence_policy_ref`, `capability_descriptor_ref`. Omit-when-`None` (§8).
- **`EvidencePolicy`** (explicit `content_hash` property; `ref = content_hash`): `policy_id`, `version`,
  `null_family:"paired_bounded_mean_betting"`, `theta0(=τ)`, `statistic`, `support`,
  `sampling_regime:SamplingRegime`, `baseline_ref`, `calibration_population_ref`, `predictor_config_ref`,
  `executor_credential_ref`, `evalue_transform`. **Validators:** non-empty ids/refs; **`0 ≤ theta0 < 1`**
  (audit-6 #15); family↔transform compatible.
- **Hash chain**, checked **at dispatch before execution** (so untrusted code never runs — audit-5 #7),
  the committed root re-enforced at verify by `commitment_hash`: `contract.evidence_policy_ref ==
  cell.verification_policy.evidence_policy_ref == EvidencePolicy.content_hash`; `contract.
  capability_descriptor_ref == cell.content_hash`; within the policy: `calibration_population_ref ==
  BenchmarkArtifact.content_hash`, `baseline_ref == baseline component config_hash`, `predictor_config_ref
  == live predictor config digest`, `executor_credential_ref == ExecutorCredential.content_hash`; and
  `criterion.threshold == theta0`, `cell.operation_impl == node.impl`. Broken link → not dispatched.
- **`ExecutorCredential`** (typed; **trusted-state-bearing, audit-6 #5**): `components: tuple[Component,
  ...]` with `Component{role: Literal["predictor","baseline_predictor","scorer","evidence_transform"],
  identity, implementation_hash, config_hash}` in canonical role order (**includes the baseline
  predictor — audit-6 #2**); `owner`, `version`, `trusted: bool`; `content_hash` = `_sha` over the
  ordered components + version. Registry lookup key = `content_hash` = `policy.executor_credential_ref`.
  A **new type**, not an `AdapterCredential` extension. **`config_hash` canonical semantics (audit-6 #6):**
  the sha over a canonical-JSON dict of the component's declared config — for `predictor`: model
  id/version (or weights digest), prompt/system text, decoding params, preprocessing spec; for
  `baseline_predictor`: its rule + params; for `scorer`/`evidence_transform`: their parameters. Not an
  arbitrary caller string.
- **`EvidenceProvenance`** (on `Licensing`): `executor_credential_ref`, `evidence_policy_ref`,
  `benchmark_ref`, `baseline_ref`, `predictor_config_ref`, `capability_descriptor_ref`,
  `oracle_dossier_ref | None`, `observed_advantage`, `theta0`, `e_value`, `execution_contract_digest`,
  `fdr_test_index`, `alpha_allocated`. Invariant: `e_value == resolved FDRTest.e_value`.
- **`EvidenceExecution`**: `record`, `e_value: float | None`, `licensing_info | None`,
  `failure_reason: ExecutionFailure | None`. **Failure record shape (audit-6 #10):** `record =
  ExecRecord(claim_id, VerifiedEvaluation(results=(EvaluationResult(verdict=UNDETERMINED,
  terminal=ExecValue(value=None), nodes=(), adapter_identity=executor_credential.content_hash,
  status="error"),), agreement=True, satisfaction=None))` — `status="error"` distinguishes it; UNDETERMINED
  keeps it PENDING; it carries no earned strength (so `_build_earned`/integration treat it inertly).
- **`verification_standing`** on `Licensing`: `Literal["single_source_baseline"]`.

---

## 5. Concrete 4th cell descriptor (audit-6 #3)

`eval::benchmark_advantage@v1` — exact `CapabilityCell` values so `validate_claim_shape` is implementable:

- `capability_id="eval::benchmark_advantage"`, `capability_version="v1"`,
  `operation_impl="eval::benchmark_advantage"`, `title="model-vs-baseline benchmark advantage"`.
- `pattern=PatternRef(id="adjusted_effect", version="v1")` (reuse the existing pattern the stats cells
  use).
- `subject=SubjectRequirement(mode="forbidden")` — the benchmark is the content-addressed data-ref, not
  a claim subject; this avoids a new `SubjectKind`. (Oracle applicability is then checked at the
  apparatus level, not against a subject kind.)
- `param_schema=(ParamCodec(name="tau", codec="float"),)` only (τ; benchmark/policy refs live in
  `execution_contract`, not params).
- `produced=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=DERIVED)` (the advantage estimate);
  `claim_leaf_kinds=("categorical",)` (same convention as the three existing cells).
- `allowed_comparators=(GT,)`; `criterion_target="threshold"` (criterion `advantage GT τ`, recorded but
  **not** a second decision — §2.5).
- `data_ref_kind=DataRefKind.BENCHMARK` — **a new ref kind** (audit-6 #3): the benchmark is content-
  addressed (`bench:<hash>`), distinct from `OPAQUE` and `SE_CONTRACT`; the matcher validates the
  `bench:` form.
- `eligible_adapter_identities=("benchmark-model",)` (single); `min_executing_adapters=1` (reconciled
  with `verification_policy.execution="single"` — §6 L1).
- `oracle=OracleRequirement(default_oracle_id="benchmark_eval_apparatus", required=True)`.
- `verification_policy=VerificationPolicy(execution="single", result_rule="criterion",
  independence_requirement="baseline_ground_truth", evidence_policy_ref=<policy ref>, min_adapters=1)`.
- **Graph shape:** one `OperationNode(id="n0", impl="eval::benchmark_advantage",
  inputs=(DataHandle(ref="bench:<hash>"),), produces=…)`, `terminal="n0"`.
- `CapabilityCell` gains an explicit **`content_hash`** property (over its fields) so
  `capability_descriptor_ref` can bind it (§2.1).

---

## 6. Trust binding & validation — three layers

**Layer 1 — cell trust binding** (claim-independent). A 4th cell needs a `CAPABILITY_CELLS` entry **and**
a `_bindings()` entry¹⁰. `min_executing_adapters` validator¹¹ relaxed: `2` for `recompute_pair`, `1` for
`single`. `validate_trust_binding` gains `evidence_policy_registry`¹² + a single-mode branch: skip the
independent-pair requirement; require the `ExecutorCredential` resolvable **+ `trusted`** (§4) and the
`EvidencePolicy` resolvable + digest-verified. **Oracle (accurate):** `OracleDossier` has no `trusted`
field; this layer only confirms the oracle **id exists** — `in_domain` is Layer 2.

**Layer 2 — claim-to-capability binding** (before dispatch). `validate_claim_shape(claim, cell)`; a
non-conforming claim is not dispatched. Oracle `in_domain(subject)` checked here.

**Layer 3 — runtime artifact/executor binding** (execution-time, **before scoring** — audit-5 #7).
Verify the full hash chain's runtime links (§4): artifact, baseline-config, predictor-config, and the
**live whole-executor combined hash == registered `ExecutorCredential`** — including the **baseline
predictor** component (audit-6 #2). `implementation_hash_for_*` is generalized to take the relevant
method (`BenchmarkAdapter` exposes `predict`, not `execute`¹³). Live-vs-registered, never a returned
identity string.

> ¹⁰ `bind()` `capabilities.py:105-111`. ¹¹ `capability.py:146-152`. ¹² `validate_trust_binding`
> `capabilities.py:114-116`. ¹³ `adapter_identity.py:13`.

---

## 7. Lifecycle / status

| Outcome | Status |
|---|---|
| e-LOND **discovery** ∧ eligibility (B,C,F,G) | **LICENSED** (`EVIDENCE_LICENSED`, `single_source_baseline`) |
| discovery but ineligible, **or** no discovery (incl. all-tie/negative) | **PENDING** (UNDETERMINED; non-terminal) |
| structural failure | **PENDING** `EXECUTION_ERROR`; e_value=None; **locked α consumed + unresolved** |

A discovered-but-ineligible claim leaves a ledger discovery without a license (honest — §2.5).
**Retry (audit-6 #11):** a failed claim may re-execute against the *same unresolved test* only when
**`commitment_hash`, `FDRTest.index`, `alpha_allocated`, and `execution_contract_digest` all match** —
not merely "any pending test for this claim id". No terminal REFUTED on this route.

---

## 8. Schema deltas & compatibility (verified mechanism)

**Grammar (pure):** `LicenseRoute.EVIDENCE_LICENSED`; `Licensing.independence_tier: IndependenceTier |
None`; `Licensing.verification_standing` + `evidence_provenance`; `PendingReason.EXECUTION_ERROR`;
`SamplingRegime`; `DataRefKind.BENCHMARK`; `EvidencePolicy`(+registry);
`ExecutorCredential`(+registry); `VerificationPolicy`; `ExecutionContract`; `CapabilityCell.content_hash`
property + optional `CapabilityCell.verification_policy`; optional `EvaluationPlan.execution_contract`.

**Protocol:** `run_cycle`/`execute_ground` gain `evidence_executor` + `capability_registry`;
`execute_ground` returns `evidence_executions`; `verify_stage` gains `evidence_licensing` +
`evidence_failures` + the evidence-route block (§2.5).

**Compatibility — verified `Field(exclude_if=…)` mechanism (audit-6 #11/#12).** The three optional fields
hashed (directly/transitively) into committed digests use **`Field(default=None, exclude_if=lambda v: v
is None)`** — confirmed in pydantic 2.13.4 to **omit the key entirely** when `None`, keep it when set, and
deserialize historical JSON lacking it:
- `Licensing.{verification_standing, evidence_provenance}` (hashed into the attestation subject digest¹⁴);
- `EvaluationPlan.execution_contract` (hashed by `commitment_hash`; on the plan, not the graph, so
  `ComputeGraph.content_hash`/commit-lock untouched);
- `CapabilityCell.verification_policy` (keeps the cell dump byte-identical).
This is **field-level** (not a `model_serializer`), so no nested/schema risk. **Tests (audit-6 #12)**
cover: omitted-when-None output, present-when-set, `model_dump_json`, **deserializing historical JSON
without the fields**, commitment hashes, and attestation hashes. **Result:** existing recompute-license
subject digests, the three existing cells, and all existing commitment hashes are **byte-identical** — no
golden re-bless.

> ¹⁴ `_subject()` `attestation.py:194` (no exclude_none).

---

## 9. Honest, powered fixture (audit-6 #13/#14)

- **Feature-dependent label DGP** `y = f(features) ⊕ noise`, noise independently sampled; a **model rule
  fixed before the draws** genuinely more accurate than a **weaker precommitted baseline**; the random
  draws independent of *implementation choices*.
- **Powered by a power calculation, not seed search (audit-6 #13):** choose the sample size `n` from a
  power calculation so the *expected* advantage `E[1(model correct) − 1(baseline correct)] > τ` clears the
  locked threshold in expectation; then use the **first fixed seed**. If it does not clear, **increase the
  predeclared `n`** — never search seeds. The fixture is labeled as **demonstrating execution mechanics,
  not independent empirical validation.**
- **Provenance (audit-6 #14):** the `BenchmarkArtifact` records the **sampling seed and DGP digest**.
- **Test reads actual α (audit-5 #14):** reads `alpha_allocated` from the registered `FDRTest`; asserts
  `e_value ≥ 1/alpha_allocated` (correct even if not the ledger's first test).

---

## 10. Tests

1. E-value regression: exact small-stream values; all-tie/negative → `e ≤ 1` (no exception); Ville note.
2. Structural-only degeneracy → `EXECUTION_ERROR`, e_value=None, test left unresolved; failure
   `VerifiedEvaluation` shape (§4) is `status="error"`, UNDETERMINED, inert to `_build_earned`.
3. Label withholding: `predict` has no label param; scorer is sole label holder.
4. Paired alignment: join by `example_id` in committed order; model==baseline → `e ≤ 1`.
5. Hash-chain binding: altering policy/baseline/capability/benchmark **or the cell descriptor** changes a
   committed hash → not dispatched / `HYPOTHESIS_ALTERED`; dispatch refuses a claim with no pending test;
   an in-cycle-GENERATE'd evidence claim is not executed this cycle.
6. Whole-executor credential: swapping the **baseline predictor**, scorer, evidence-transform, or
   predictor **config** changes `ExecutorCredential` and fails Layer-3 **before** scoring.
7. Three layers + trust state: non-conforming claim not dispatched; oracle `in_domain` at L2; an
   **untrusted** `ExecutorCredential` fails L1; single-mode binding passes with one credential.
8. Decision rule + honest distinctness: sub-threshold e-value → PENDING (never REFUTED); a **discovered
   but non-grounded** claim is **not licensed** yet **does** record a ledger discovery (the distinct-state
   reality); discovery ∧ eligibility → LICENSED.
9. BH-bar exemption: an evidence claim is exempt from `_permitted_by_bar` (e-LOND is its control) — a test
   documents this rather than asserting false constraint.
10. Bookkeeping: stage-audit counts, selection-ledger outcome, Goodhart/operator credit, integrate();
    failure leaves the test unresolved (α consumed); retry under the **identical** `(commitment_hash,
    test index, α, contract digest)` is permitted, a varied contract trips `HYPOTHESIS_ALTERED`.
11. Standing serialization: evidence license `independence_tier=None`, standing literal; never `reproduced`.
12. Compatibility: existing recompute-license attestation digests **byte-identical** (`_golden_bundle.json`
    unchanged); cell dump byte-identical; all existing `commitment_hash`es unchanged; **historical JSON
    without the new fields deserializes**.
13. Powered fixture: documented power calc + first-seed; `e_value ≥ 1/alpha_allocated` (read from the test)
    before the LICENSED assertion.
14. Protocol-test purity: protocol tests inject a tiny **grammar-DTO** executor stub; no `polymer_claims`
    import.
Validity/contract tests (2,5,6,7,9,12) precede the end-to-end license test; `scripts/check-all.sh` is the
**final** task.

---

## 11. Acceptance criteria

1. `eval::benchmark_advantage@v1` registered with the **concrete descriptor** of §5 (incl. new
   `DataRefKind.BENCHMARK`, subject forbidden), `_bindings()` entry, whole-`ExecutorCredential`
   (incl. baseline, `trusted`), `EvidencePolicy`; `min_executing_adapters` reconciled.
2. Licenses an inferential model-vs-precommitted-baseline claim **offline, in-cycle, post-commit**; the
   **e-LOND discovery is the statistical decision** and the license additionally requires eligibility
   (B,C,F,G) — license **not** claimed coextensive with discovery; BH bar exemption documented, not
   hand-waved.
3. Execution contract (capability id/version, `evidence_policy_ref`, `capability_descriptor_ref`)
   pre-registration-bound; full **hash chain** checked at dispatch; dispatch requires a locked FDR slot;
   in-cycle-generated claims ineligible; provenance records contract digest + FDR index + locked α; its
   e-value equals the ledger's.
4. License carries `route=EVIDENCE_LICENSED`, `independence_tier=None`, standing literal, durable
   provenance; weak evidence → PENDING (never REFUTED); failure → `EXECUTION_ERROR`, α consumed, retry only
   under identical `(commitment, test index, α, contract digest)`.
5. Three-layer validation (executor + **baseline** + config verified before scoring); content-addressed
   artifacts + whole-executor credential reject every tamper/mismatch before licensing.
6. **Existing recompute-license attestation digests, the three cells, and all existing commitment hashes
   byte-identical** (verified `Field(exclude_if=…)`; historical JSON deserializes); `grammar/`+`protocol/`
   pure + numpy-free; `Corpus` stays 4; `check-all.sh` green.

---

## 12. Audit-6 resolution map

#1 discovery is the statistical decision, **not** coextensive with license (§2.5) · #2 baseline credentialed
(§4/§6) · #3 concrete cell descriptor + `DataRefKind.BENCHMARK` (§5) · #4 BH bar exemption stated, e-LOND
is the control (§2.6) · #5 `ExecutorCredential` has `trusted`/`owner`/`version` (§4) · #6 canonical
`config_hash` semantics (§4) · #7 `capability_descriptor_ref` committed (§2.1/§4) · #8 DTO module placement
(§4) · #9 executor callable signature (§4) · #10 failure `VerifiedEvaluation` shape (§4) · #11 retry binds
test index + α + contract digest (§7) · #12 verified `Field(exclude_if=…)` + historical-JSON test (§8) ·
#13 power-calc + first-seed fixture (§9) · #14 benchmark seed + DGP digest in artifact (§9) · #15
`0 ≤ theta0 < 1` (§3/§4).

---

## 13. Decomposition (Path A) & rhythm

- **Slice 1 (this spec):** in-cycle gated executor + statistical decision (e-LOND) + corrected statistics
  + concrete descriptor + content-addressed artifacts + whole-executor credential (incl. baseline) +
  three-layer validation + powered fixture.
- **Slice 2:** meaningful benchmark + full attestation chain + certificate/SLSA.
- **Slice 3:** defeat/drift/reinstatement/replay-over-time + tamper/boundary depth + downgraded-oracle.

Each slice: `writing-plans` → `subagent-driven-development` (TDD) → whole-branch review → merge `--no-ff`
→ update `CONTINUE.md` + memory.
