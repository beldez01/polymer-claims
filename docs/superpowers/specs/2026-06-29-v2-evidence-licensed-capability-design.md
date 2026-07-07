# V2.0 Slice 1 — Evidence-licensed capability via an in-cycle gated executor

**Date:** 2026-06-29
**Author:** Z. Belden (synthesized with Claude)
**Status:** ✅ **SHIPPED — Slice 1 merged (`9b8848c`, 2026-06-29).** `eval::benchmark_advantage@v1`, the `EvidenceExecutor`, `EVIDENCE_LICENSED` route, and the in-cycle gated dispatch are all in `main`. Slice-1 detail below is historical (authoritative record: `git log` + `CONTINUE.md`). **Pending:** Slice 2 (full attestation chain + certificate/SLSA `resolvedDependencies`) and Slice 3 (defeat/drift/reinstatement/replay-over-time) — see the roadmap. Kept in-tree only for that pending Slice-2/3 design.
**Roadmap item:** V2.0 (`docs/superpowers/2026-06-23-remaining-roadmap.md`)
**Depends on:** Capability Cell + Registry V1 (`b058d3c`)

> **Revision history.** v1–v2 statistically unsound; v3 out-of-cycle; v4 in-cycle (architecture approved,
> 4th review); v5 contract; v6 unified decision rule; v7 honesty fixes + concrete descriptor. **This v8**
> (7th review) finalizes wiring/registry/status details: a typed `EvidenceExecutor` that *owns* its
> components; an `ExecutorTrustEntry` registry wired into the trust binding; per-gate status that respects
> existing defeat semantics; two distinct baseline refs; `result_rule="evalue_discovery"`; a
> pydantic-2.6-safe `model_serializer`; and validator/migration details. **Slice 1 of Path A** (§13).

---

## 1. Purpose, lesson & trust model

Register one genuinely-new capability — licensed *not* by two pure-Python recompute legs — to find where
V1's abstraction breaks, and build the minimal honest machinery. **Lesson** (gating V2.1–V2.3 +
closed-world execution): *a capability can be executed and licensed by an in-cycle, registered,
content-addressed executor running through the same eligibility gates as the recompute path — the gate
stack, not the adapter count, is the trust boundary.*

**Non-goals:** the wedge (H1.A2 → H2 critical path); closed-world *enforcement*; V2.1–V2.3; networked
calls; certificate/SLSA evidence integration (Slice 2); defeat/drift/reinstatement (Slice 3).

**Trust model (honest, narrow).** Guarantee: **a result cannot bypass the protocol gates** (selection,
commit, mandatory pre-registration, grounded extension, e-LOND, commitment match). Validity still depends
on the configured executor + trust roots. v8 makes the executor's **code + configuration**, the
**baseline rule**, the **cell descriptor**, and the full execution contract content-addressed and
pre-registered, so none can be swapped after the α-slot locks.

---

## 2. Architecture — in-cycle, post-commit, gated

`run_cycle` order: REPRESENT → GENERATE → CANONICALIZE → SAFETY → SELECT → COMMIT → EXECUTE → VERIFY →
INTEGRATE → LEDGER.¹

1. **Identification + contract binding.** `EvaluationPlan` carries optional **`execution_contract`**
   (omit-when-`None`, §8) = `ExecutionContract{capability_id, capability_version, evidence_policy_ref,
   capability_descriptor_ref}`. `commitment_hash` hashes the whole plan², so these are
   pre-registration-bound; the rest is bound transitively through the content-addressed `EvidencePolicy`
   (§4 chain). `capability_descriptor_ref == cell.content_hash` (detects a registry swap under the same
   key). Dispatch resolves by the explicit versioned key; `cell.operation_impl == node.impl`.
2. **Pre-registration mandatory + enforced.** Caller `register_hypotheses` **before** `run_cycle` locks
   the α-slot + `commitment_hash`.³ Dispatch **refuses** any evidence claim not `selected ∧ committed ∧
   pending registered FDR test ∧ commitment matches`. **In-cycle GENERATE'd evidence claims are
   ineligible this cycle** (eligible only in a later cycle after the caller registers them).
3. **Execution branch.** `run_cycle` gains injected `evidence_executor: EvidenceExecutor` (§4, umbrella;
   numpy) + `capability_registry` (grammar). In `execute_ground`'s per-claim chokepoint⁴, a `single`-policy
   cell claim passing claim-shape conformance (§6 L2) + §2.2 is dispatched. **Before any prediction or
   label exposure (audit-5 #7)** the dispatcher compares `evidence_executor.credential()` (the live whole-
   executor descriptor hash) against the registered `ExecutorDescriptor` (§4/§6 L3) and verifies the
   artifact/baseline-config links; only then `evidence_executor.execute(...)` runs. It returns a typed
   **`EvidenceExecution`** (§4). The `record`'s `EvaluationResult` carries **`verdict=UNDETERMINED`,
   `agreement=True`** — never `SATISFIED`/`REFUTED`⁵. A successfully-scored execution emits an `e_value`;
   a structural failure emits `e_value=None` + `failure_reason`.
4. **Data flow.** `execute_ground` returns `(corpus, records, evidence_executions)`; `run_cycle` merges
   e-values into the existing `evidence=` map and threads `evidence_licensing` + `evidence_failures` into
   `verify_stage`. `ExecRecord` is the universal bridge⁶.
5. **Decision rule + per-gate status (audit-6 #1, audit-7 #5 — respect existing semantics).** The e-LOND
   discovery on the τ-null is the **statistical** decision (no separate observed-advantage criterion);
   Phase-D resolves the locked test⁷. The evidence-route block in verify_stage is **minimal**: it owns
   only two outcomes and lets all others **fall through to the existing branches** so defeat semantics are
   unchanged:
   - **failure** (`evidence_failures[c.id]`) → PENDING `EXECUTION_ERROR` (α-slot consumed, unresolved).
   - **e-LOND discovery ∧ eligible** (in grounded extension, provenance present, commitment matched, status
     PENDING) → mint `Satisfaction(verdict=SATISFIED, materialization,
     credential_ids=(executor_descriptor_ref,))` + `Licensing(route=EVIDENCE_LICENSED,
     independence_tier=None, verification_standing, evidence_provenance)` → **LICENSED**.
   - **everything else falls through** to the existing per-claim mapping⁸: not in grounded extension →
     terminal **REJECTED `DEFEAT_GROUNDED_OUT`**; altered commitment → terminal **REJECTED
     `HYPOTHESIS_ALTERED`**; otherwise (eligible, no discovery) → **PENDING** (UNDETERMINED passthrough).
   **License ≠ discovery (honest):** a discovered-but-ineligible claim records a ledger discovery and is
   handled by the existing gate (e.g. grounded-out → REJECTED), not silently PENDING.
6. **The BH selective-inference bar does not constrain this route (audit-6 #4, honestly).**
   `_permitted_by_bar` derives strength only from satisfied records⁹; an UNDETERMINED evidence record has
   `strength=None` → exempt. This is **intentional**: **e-LOND (mandatory pre-registration + locked α) is
   the evidence route's multiplicity-control mechanism**, in place of the recompute path's BH bar. The
   spec does not claim Gate D constrains evidence claims.

> ¹ `cycle.py:62-183`. ² `commitment.py:13-18`. ³ `register.py:15`, `fdr.py:111`. ⁴ `execute.py:51-60`.
> ⁵ `SatisfactionVerdict{SATISFIED,REFUTED,UNDETERMINED}` `licensing.py:23`; verdict mechanics
> `verify.py:224-228,316-328`. ⁶ `ExecRecord` `corpus.py:86`. ⁷ Phase-D `verify.py:169-186`. ⁸ existing
> per-claim branches `verify.py:316-328` (REFUTED / DEFEAT_GROUNDED_OUT / passthrough PENDING).
> ⁹ `_permitted_by_bar` `verify.py:80-115`.

---

## 3. Statistical core

**Inferential claim.** Under declared **IID** sampling (model, baseline, preprocessing, decision rules
fixed independently of the evaluation sample) the model's expected per-example accuracy **advantage over a
precommitted baseline exceeds τ**, **0 ≤ τ < 1** (advantage ∈ [−1,1]).

**Paired increments / sequential null.** `Wᵢ = 1(model correctᵢ) − 1(baseline correctᵢ) ∈ {−1,0,+1}`;
`H0: E[Wᵢ − τ | history] ≤ 0`; `policy.theta0 = τ`. The **statistical decision is the e-LOND discovery on
this τ-null** (§2.5).

**E-value (committed order).** `paired_advantage_evalue(w, theta0=τ)` runs the existing GRAPA core¹⁰ over
`Wᵢ − τ` in committed order; `lam_max = _C/(1+τ)` keeps factors `≥ 1−_C > 0`. Ville → `E_H0[e] ≤ 1`.
**No outcome-dependent filtering**; all-tie/negative → `e ≤ 1` → no discovery. Typed
`SamplingRegime.IID_EXAMPLES`.

> ¹⁰ `_grapa_capital` `evidence.py:28-46`.

---

## 4. Typed objects, modules, executor & the hash chain

**Module placement (audit-6 #8, audit-7 #14).** *Grammar* (pure): `EvidencePolicy`(+registry),
`ExecutorDescriptor`, `ExecutorTrustEntry`(+registry), `ExecutionContract`, `EvidenceProvenance`,
`EvidenceLicensingInfo`, `VerificationPolicy`, `SamplingRegime`. *Protocol* (consumes `ExecRecord`):
`EvidenceExecution`, `ExecutionFailure`, and the **`EvidenceExecutor`** protocol type + the
`evidence_executor` param. The executor *implementation* is umbrella (numpy).

**`EvidenceExecutor` protocol (audit-7 #2 — owns its components).**
```
class EvidenceExecutor(Protocol):
    def credential(self) -> str: ...            # the live ExecutorDescriptor.content_hash
    def execute(self, claim, cell, policy, benchmark_artifact, ctx, fdr_test) -> EvidenceExecution: ...
```
It internally owns `predictor`, `baseline_predictor`, `scorer`, `evidence_transform`. `credential()`
recomputes the descriptor hash from the live components (not a stored string), so dispatch can compare it
to the registered `ExecutorDescriptor` **before** `execute()` — no hidden lookups, no closure trust.

- **`ExecutionContract`** (committed on the plan): `capability_id`, `capability_version`,
  `evidence_policy_ref`, `capability_descriptor_ref`.
- **`EvidencePolicy`** (explicit `content_hash`; `ref = content_hash`): `policy_id`, `version`,
  `null_family:"paired_bounded_mean_betting"`, `theta0(=τ)`, `statistic`, `support`,
  `sampling_regime:SamplingRegime`, **`baseline_config_ref`** (the precommitted baseline rule/config —
  audit-7 #4), `calibration_population_ref`, `predictor_config_ref`, **`executor_descriptor_ref`**,
  `evalue_transform`. Validators: non-empty ids/refs; **`0 ≤ theta0 < 1`**; family↔transform compatible.
- **Hash chain** (checked at dispatch, before execution; committed root re-enforced by `commitment_hash`):
  `contract.evidence_policy_ref == cell.verification_policy.evidence_policy_ref == EvidencePolicy.content_hash`;
  `contract.capability_descriptor_ref == cell.content_hash`; within the policy:
  `calibration_population_ref == BenchmarkArtifact.content_hash`, `baseline_config_ref == live baseline
  component config_hash`, `predictor_config_ref == live predictor config digest`, `executor_descriptor_ref
  == ExecutorDescriptor.content_hash`; and `criterion.threshold == theta0`, `cell.operation_impl ==
  node.impl`. Broken link → not dispatched.
- **`ExecutorDescriptor`** (content-addressed — audit-7 #9): `components: tuple[Component, ...]` with
  `Component{role: Literal["predictor","baseline_predictor","scorer","evidence_transform"], identity,
  implementation_hash, config_hash}`, `version`; `content_hash` = `_sha` over ordered components + version.
  **`config_hash` semantics (audit-6 #6):** sha over canonical-JSON of the component's declared config
  (predictor: model id/version or weights digest, prompt, decoding, preprocessing; baseline_predictor: its
  rule + params; scorer/evidence_transform: their params). **Validators (audit-7 #15):** exactly one of
  each required role; canonical role order; unique identities; non-empty hashes; `sha256:`-prefixed.
- **`ExecutorTrustEntry`** (registry entry, mutable trust — audit-7 #1/#9): `descriptor_ref` (==
  `ExecutorDescriptor.content_hash`), `owner`, `trusted: bool`, `version`. `ExecutorTrustRegistry.resolve(
  descriptor_ref) -> ExecutorTrustEntry | None`. Trust state lives here, *not* on the content-addressed
  descriptor.
- **`EvidenceProvenance`** (on `Licensing`): `executor_descriptor_ref`, `evidence_policy_ref`,
  `benchmark_ref`, **`baseline_config_ref`**, **`baseline_predictions_ref`** (realized predictions on this
  benchmark — audit-7 #4), `predictor_config_ref`, `capability_descriptor_ref`, `oracle_dossier_ref | None`,
  `observed_advantage`, `theta0`, `e_value`, `execution_contract_digest`, `fdr_test_index`,
  `alpha_allocated`. Invariant: `e_value == resolved FDRTest.e_value`.
- **`EvidenceExecution`** (protocol module): `record`, `e_value: float | None`, `licensing_info | None`,
  `failure_reason: ExecutionFailure | None`. **Failure record (audit-6 #10):** `ExecRecord(claim_id,
  VerifiedEvaluation(results=(EvaluationResult(verdict=UNDETERMINED, terminal=ExecValue(value=None),
  nodes=(), adapter_identity=executor_descriptor_ref, status="error"),), agreement=True,
  satisfaction=None))`.
- **`verification_standing`** on `Licensing`: `Literal["single_source_baseline"]`.

---

## 5. Concrete 4th cell descriptor (audit-6 #3)

`eval::benchmark_advantage@v1` — exact `CapabilityCell`:
- `capability_id/operation_impl="eval::benchmark_advantage"`, `capability_version="v1"`,
  `title="model-vs-baseline benchmark advantage"`.
- `pattern=PatternRef(id="adjusted_effect", version="v1")`.
- `subject=SubjectRequirement(mode="forbidden")` — the benchmark is the data-ref, not a subject (avoids a
  new `SubjectKind`); oracle applicability is apparatus-level (§6 L1/L2).
- `param_schema=()` — **τ lives only in the criterion** (audit-7 #6: no duplicate `tau` param to keep
  consistent); benchmark/policy refs live in `execution_contract`.
- `produced=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=DERIVED)`;
  `claim_leaf_kinds=("categorical",)`.
- `allowed_comparators=(GT,)`; `criterion_target="threshold"` (criterion `advantage GT τ`, **recorded; not
  a decision** — §2.5).
- `data_ref_kind=DataRefKind.BENCHMARK` (new; content-addressed `bench:<hash>`).
- `eligible_adapter_identities=("benchmark-model",)`; `min_executing_adapters=1`.
- `oracle=OracleRequirement(default_oracle_id="benchmark_eval_apparatus", required=True)`.
- `verification_policy=VerificationPolicy(execution="single", result_rule="evalue_discovery",
  independence_requirement="baseline_ground_truth", evidence_policy_ref=<ref>, min_adapters=1)` —
  **`result_rule="evalue_discovery"`** (audit-7 #3: a new value reflecting that satisfaction is minted from
  the e-LOND discovery, not a criterion comparison).
- **Graph:** one `OperationNode(id="n0", impl="eval::benchmark_advantage",
  inputs=(DataHandle(ref="bench:<hash>"),), produces=…)`, `terminal="n0"`.
- `CapabilityCell` gains an explicit `content_hash` property so `capability_descriptor_ref` binds it.

---

## 6. Trust binding & validation — three layers

**Layer 1 — cell trust binding.** `CapabilityTrustBinding` gains an **`executor_trust_registry:
ExecutorTrustRegistry`** field (alongside the existing `AdapterRegistry`/`OracleRegistry`/`trust_profile`
— audit-7 #1). `validate_trust_binding` gains `evidence_policy_registry` **and**
`executor_trust_registry` params + a single-mode branch: skip the independent-pair requirement; require the
`EvidencePolicy` resolvable + digest-verified, and the `ExecutorTrustEntry` for
`policy.executor_descriptor_ref` resolvable **+ `trusted`**. **`min_executing_adapters` migration (audit-7
#7):** the validator treats `verification_policy is None` **or** `execution=="recompute_pair"` as requiring
`min_executing_adapters == 2` (so the three existing `None`-policy cells stay valid unchanged);
`execution=="single"` requires `== 1`. **Oracle (audit-7 #8):** `benchmark_eval_apparatus` has an
**unbounded applicability domain**; with no subject, the apparatus-level check passes without a subject-kind
`in_domain` call (`OracleDossier` has no `trusted` field; this layer confirms the id exists).

**Layer 2 — claim-to-capability binding** (before dispatch). `validate_claim_shape(claim, cell)`; a
non-conforming claim is not dispatched. (No subject ⇒ no subject-`in_domain`; apparatus domain is
unbounded.)

**Layer 3 — runtime artifact/executor binding** (execution-time, **before scoring**). Dispatch compares
`evidence_executor.credential()` to the registered `ExecutorDescriptor` (incl. the **baseline_predictor**
component — audit-6 #2) and verifies the artifact + baseline-config + predictor-config links (§4 chain).
`implementation_hash_for_*` generalized to take the relevant method (`BenchmarkAdapter` exposes `predict`
not `execute`¹¹). Live-vs-registered.

> ¹¹ `adapter_identity.py:13`; `bind()` `capabilities.py:105-111`; `min_executing_adapters`
> `capability.py:146-152`; `validate_trust_binding` `capabilities.py:114-116`.

---

## 7. Lifecycle / status (respects existing semantics — audit-7 #5)

| Outcome | Status | Source |
|---|---|---|
| e-LOND discovery ∧ eligible (grounded, provenance, commitment, PENDING) | **LICENSED** (`EVIDENCE_LICENSED`) | evidence block |
| not in grounded extension | **REJECTED** `DEFEAT_GROUNDED_OUT` | existing branch⁸ |
| altered commitment | **REJECTED** `HYPOTHESIS_ALTERED` | existing branch |
| eligible, no discovery (incl. all-tie/negative) | **PENDING** (UNDETERMINED) | existing passthrough |
| structural failure | **PENDING** `EXECUTION_ERROR`; α consumed + unresolved | evidence block |

**Retry (audit-6 #11):** a failed claim re-executes against the same unresolved test only when
**`commitment_hash`, `FDRTest.index`, `alpha_allocated`, and `execution_contract_digest` all match**. No
terminal REFUTED on this route.

---

## 8. Schema deltas & compatibility (pydantic-2.6-safe — audit-7 #10)

**Grammar (pure):** `LicenseRoute.EVIDENCE_LICENSED`; `Licensing.independence_tier: IndependenceTier |
None`; `Licensing.verification_standing` + `evidence_provenance`; `PendingReason.EXECUTION_ERROR`;
`SamplingRegime`; `DataRefKind.BENCHMARK`; `EvidencePolicy`(+registry); `ExecutorDescriptor`;
`ExecutorTrustEntry`(+registry); `VerificationPolicy`; `ExecutionContract`; `CapabilityCell.content_hash`
property + optional `CapabilityCell.verification_policy`; optional `EvaluationPlan.execution_contract`.
`VerificationPolicy.result_rule` includes `"evalue_discovery"`.

**Protocol:** `run_cycle`/`execute_ground` gain `evidence_executor` + `capability_registry`;
`execute_ground` returns `evidence_executions`; `verify_stage` gains `evidence_licensing` +
`evidence_failures` + the minimal evidence-route block (§2.5); `CapabilityTrustBinding` +
`validate_trust_binding` gain the executor-trust registry.

**Compatibility — `model_serializer`, not `exclude_if` (audit-7 #10).** The repo declares `pydantic>=2.6`;
`Field(exclude_if=…)` is newer, so relying on it would silently raise the floor. Instead, the three models
with optional fields hashed (directly/transitively) into committed digests use a targeted
**`@model_serializer(mode="wrap")`** (available since 2.0) that calls the handler then **drops the named
fields when `None`** — `Licensing.{verification_standing, evidence_provenance}`,
`EvaluationPlan.execution_contract`, `CapabilityCell.verification_policy`. **Test battery (audit-6 #12):**
omitted-when-None, present-when-set, `model_dump_json`, JSON-schema generation, nested serialization,
**deserializing historical JSON lacking the fields**, commitment hashes, and attestation hashes. **Result:**
existing recompute-license subject digests, the three cells, and all existing commitment hashes are
**byte-identical** — no golden re-bless, no dependency-floor change.

> ¹² `_subject()` `attestation.py:194` (no exclude_none).

---

## 9. Honest, powered fixture (audit-7 #11/#12)

- **Feature-dependent label DGP** `y = f(features) ⊕ noise`, noise independently sampled; a model rule
  fixed before draws, genuinely more accurate than a weaker precommitted baseline; draws independent of
  implementation choices.
- **Power target, then fixed seed (audit-7 #11):** choose **one** sample size `n` before execution from a
  declared power target — `P_alt(E ≥ 1/alpha_allocated) ≥ 0.8` under the DGP — then use the **first fixed
  seed**. The escalation schedule (if any) is **predeclared** (e.g. `n ∈ {200,400,800}`, same seeded
  stream, first prefix meeting the target); no post-hoc seed search (audit-7 #12). The fixture
  **demonstrates execution mechanics, not independent empirical validation.**
- **Provenance:** `BenchmarkArtifact` records the sampling seed + DGP digest.
- **Test reads actual α:** reads `alpha_allocated` from the registered `FDRTest`; asserts `e_value ≥
  1/alpha_allocated`.

---

## 10. Tests

1. E-value regression: exact small-stream values; all-tie/negative → `e ≤ 1` (no exception).
2. Structural-only degeneracy → `EXECUTION_ERROR`, e_value=None, test unresolved; failure
   `VerifiedEvaluation` shape (§4) `status="error"`, UNDETERMINED, inert to `_build_earned`.
3. Label withholding: `predict` has no label param; scorer is sole label holder.
4. Paired alignment: join by `example_id` in committed order; model==baseline → `e ≤ 1`.
5. Hash-chain binding: altering policy/baseline-config/capability-descriptor/benchmark changes a committed
   hash → not dispatched / `HYPOTHESIS_ALTERED`; dispatch refuses a claim with no pending test; an
   in-cycle-GENERATE'd evidence claim is not executed this cycle.
6. Whole-executor credential via `credential()`: swapping **baseline predictor**, scorer, transform, or
   predictor **config** changes `ExecutorDescriptor` and fails the Layer-3 compare **before** scoring; an
   **untrusted** `ExecutorTrustEntry` fails L1.
7. Three layers: non-conforming claim not dispatched; unbounded-apparatus oracle passes with no subject;
   single-mode binding passes with one credential.
8. Decision rule + existing defeat semantics (audit-7 #5): sub-threshold e-value → PENDING; **discovered
   but non-grounded → REJECTED `DEFEAT_GROUNDED_OUT`** (not PENDING); altered → REJECTED
   `HYPOTHESIS_ALTERED`; discovery ∧ eligible → LICENSED. A discovered-but-rejected claim still records a
   ledger discovery.
9. BH-bar exemption documented (e-LOND is the control) — a test asserts the evidence claim is exempt, not
   falsely constrained.
10. Bookkeeping: stage-audit counts, selection-ledger outcome, Goodhart/operator credit, integrate();
    failure leaves the test unresolved (α consumed); retry under identical `(commitment, index, α, contract
    digest)` permitted, varied contract trips `HYPOTHESIS_ALTERED`.
11. Standing serialization: `independence_tier=None`, standing literal; never `reproduced`.
12. Compatibility battery (§8): existing attestation digests + cells + commitment hashes byte-identical;
    `model_dump_json`, schema-gen, nested, and **historical-JSON deserialization** all pass.
13. Powered fixture: documented power target + predeclared n/seed; `e_value ≥ 1/alpha_allocated` (read from
    the test) before the LICENSED assertion.
14. Protocol-test purity: protocol tests inject a tiny **protocol-DTO** executor stub (the
    `EvidenceExecutor` protocol lives in protocol); no `polymer_claims` import.
Validity/contract tests (2,5,6,7,9,12) precede the end-to-end license test; `scripts/check-all.sh` final.

---

## 11. Acceptance criteria

1. `eval::benchmark_advantage@v1` registered with §5's concrete descriptor (`DataRefKind.BENCHMARK`,
   subject forbidden, `param_schema=()`, `result_rule="evalue_discovery"`), `_bindings()` entry (incl.
   `ExecutorTrustRegistry`), `ExecutorDescriptor` (incl. baseline component) + trusted `ExecutorTrustEntry`,
   `EvidencePolicy`; `min_executing_adapters` migration leaves the three existing cells valid.
2. Licenses an inferential model-vs-precommitted-baseline claim **offline, in-cycle, post-commit**; e-LOND
   discovery is the statistical decision; license also requires eligibility; **per-gate status follows the
   existing protocol** (grounded-out → REJECTED, altered → REJECTED, no-discovery → PENDING); BH-bar
   exemption documented.
3. Execution contract (capability id/version, `evidence_policy_ref`, `capability_descriptor_ref`)
   pre-registration-bound; full hash chain checked at dispatch via `EvidenceExecutor.credential()`; dispatch
   requires a locked FDR slot; in-cycle-generated claims ineligible; provenance records contract digest +
   FDR index + α + both baseline refs; e-value equals the ledger's.
4. License carries `route=EVIDENCE_LICENSED`, `independence_tier=None`, standing literal, durable
   provenance; failure → `EXECUTION_ERROR`, α consumed, retry only under identical `(commitment, index, α,
   contract digest)`.
5. Three-layer validation (executor incl. baseline + config verified before scoring); content-addressed
   artifacts + whole-executor descriptor + trust entry reject every tamper/mismatch/untrusted before
   licensing.
6. **Existing recompute-license attestation digests, the three cells, and all existing commitment hashes
   byte-identical** (`model_serializer`, pydantic floor unchanged; historical JSON deserializes);
   `grammar/`+`protocol/` pure + numpy-free; `Corpus` stays 4; `check-all.sh` green.

---

## 12. Audit-7 resolution map

#1 `ExecutorTrustRegistry` in `CapabilityTrustBinding` + `validate_trust_binding` (§6/§4) · #2 typed
`EvidenceExecutor` owning components + `credential()` (§4) · #3 `result_rule="evalue_discovery"` (§5) ·
#4 split `baseline_config_ref` / `baseline_predictions_ref` (§4) · #5 per-gate status respects existing
defeat semantics (§2.5/§7) · #6 τ only in the criterion (`param_schema=()`) (§5) · #7
`min_executing_adapters` migration: `None`→recompute-pair==2 (§6) · #8 unbounded `benchmark_eval_apparatus`
domain, no subject `in_domain` (§5/§6) · #9 `ExecutorDescriptor` (content) / `ExecutorTrustEntry` (trust)
split (§4) · #10 `model_serializer` not `exclude_if`; floor unchanged (§8) · #11 power target
`P_alt(E≥1/α)≥0.8` (§9) · #12 predeclared n/escalation, no seed search (§9) · #13 header → §13 (fixed) ·
#14 `EvidenceExecution`/executor in protocol (§4) · #15 `ExecutorDescriptor.components` validators (§4).

---

## 13. Decomposition (Path A) & rhythm

- **Slice 1 (this spec):** in-cycle gated executor + e-LOND statistical decision + corrected statistics +
  concrete descriptor + content-addressed artifacts + whole-executor descriptor/trust split + three-layer
  validation + powered fixture.
- **Slice 2:** meaningful benchmark + full attestation chain + certificate/SLSA.
- **Slice 3:** defeat/drift/reinstatement/replay-over-time + tamper/boundary depth + downgraded-oracle.

Each slice: `writing-plans` → `subagent-driven-development` (TDD) → whole-branch review → merge `--no-ff`
→ update `CONTINUE.md` + memory.
