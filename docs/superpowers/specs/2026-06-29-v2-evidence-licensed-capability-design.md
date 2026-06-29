# V2.0 Slice 1 — Evidence-licensed capability via an in-cycle gated executor

**Date:** 2026-06-29
**Author:** Z. Belden (synthesized with Claude)
**Status:** DESIGN (v6, post-5th-review — architecture approved, contract + decision rule finalized) → `writing-plans`
**Roadmap item:** V2.0 (`docs/superpowers/2026-06-23-remaining-roadmap.md`)
**Depends on:** Capability Cell + Registry V1 (`b058d3c`)

> **Revision history.** v1–v2 statistically unsound; v3 out-of-cycle (forge/multiplicity); v4 moved
> execution **in-cycle, post-commit** (architecture approved, 4th review); v5 hardened the execution
> contract. **This v6** finalizes the decision rule and four runtime/commitment details from the 5th
> review: **the e-LOND discovery is the licensing decision** (no separate observed-advantage threshold —
> resolving the terminal-REFUTED conflict and the discovery/license divergence at once); a single
> concrete `ExecutionContract` bound by an explicit hash chain; a typed whole-`ExecutorCredential`
> including model/preprocessing config, verified before scoring; and per-field serializers preserving
> existing hashes. **Slice 1 of Path A** (§13).

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
(selection, commit, mandatory pre-registration, grounded extension, BH bar, e-LOND, commitment match).
Validity still depends on the configured executor + trust roots — a party controlling executor, registry,
benchmark and adapters can construct internally-consistent false evidence, as with adapters today. What
v6 adds: the executor's code **and configuration** and the full execution contract are content-addressed
and pre-registered, so they cannot be swapped after the α-slot locks.

---

## 2. Architecture — in-cycle, post-commit, gated; discovery = license

`run_cycle` order: REPRESENT → GENERATE → CANONICALIZE → SAFETY → SELECT → COMMIT → EXECUTE → VERIFY →
INTEGRATE → LEDGER.¹

1. **Identification + contract binding (audit-4 #1/#3, audit-5 #1/#5).** The `EvaluationPlan` carries an
   optional **`execution_contract`** (omit-when-`None`, §8) = `ExecutionContract{capability_id,
   capability_version, evidence_policy_ref}`. `commitment_hash` hashes the whole plan², so these are
   pre-registration-bound; everything else is bound **transitively through the content-addressed
   `EvidencePolicy`** (§4 hash chain), each link re-checked at verify. Dispatch resolves the cell by the
   **explicit versioned key** (not ambiguous `node.impl`); the resolved `cell.operation_impl` must equal
   the terminal node impl, and `cell.verification_policy.evidence_policy_ref ==
   contract.evidence_policy_ref == resolved EvidencePolicy.content_hash` (audit-5 #5).
2. **Pre-registration is mandatory + enforced (audit-4 #2, audit-5 #8).** The caller
   `register_hypotheses` **before** `run_cycle`, locking the α-slot + `commitment_hash`.³ The dispatcher
   **refuses** any evidence claim not `selected ∧ committed ∧ has a pending registered FDR test ∧
   commitment matches`. **In-cycle GENERATE'd evidence claims are *not* eligible this cycle** — they have
   no prior registration; they become eligible only in a later cycle after the caller registers them.
3. **Execution branch.** `run_cycle` gains injected `evidence_executor` (umbrella; numpy) +
   `capability_registry` (grammar). In `execute_ground`'s per-claim chokepoint⁴, a claim whose resolved
   cell is `verification_policy.execution == "single"`, that passes **claim-shape conformance** (§6 L2)
   and §2.2, is dispatched to `evidence_executor` instead of the two-adapter `verify()`. **Before any
   prediction or label exposure (audit-5 #7)** the executor verifies Layer-3 bindings (artifact/baseline
   digests + live whole-executor credential incl. config). It returns a typed **`EvidenceExecution`**
   (audit-4 #16): `{record: ExecRecord, e_value: float | None, licensing_info: EvidenceLicensingInfo |
   None, failure_reason: ExecutionFailure | None}`. The `record`'s `EvaluationResult` carries
   **`verdict = UNDETERMINED`** with `agreement = True` — *never* `SATISFIED` or `REFUTED`⁵ — so the
   executor never itself licenses or terminally refutes; the license decision is deferred to e-LOND in
   verify_stage. A **successfully-scored** execution emits an `e_value`; a **structural failure**
   (empty/malformed/dup/missing/order/credential/digest mismatch) emits `e_value=None` + `failure_reason`.
4. **Data flow.** `execute_ground` returns `(corpus, records, evidence_executions)`; `run_cycle` merges
   e-values into the existing `evidence=` map and threads `evidence_licensing` + `evidence_failures`
   dicts into `verify_stage`. `ExecRecord` is the universal bridge⁶.
5. **Decision rule — discovery = license (audit-5 #3/#10; audit-4 #9/#14).** There is **no separate
   observed-advantage criterion**; the e-LOND discovery on the τ-null *is* the decision. The existing
   Phase-D resolution (iterating `exec_records`) resolves the locked test⁷. Then the **evidence-route
   licensing block** in verify_stage (reusing the precomputed gate sets — grounded-extension, provenance,
   BH bar `_permitted_by_bar`, commitment, PENDING⁸):
   - **failure** (`evidence_failures[c.id]`) → PENDING `EXECUTION_ERROR`; the locked α-slot stays
     consumed + unresolved (audit-5 #15; retry only under the identical committed contract — §7/#9).
   - **discovery ∧ gates B–G** → mint `Satisfaction(verdict=SATISFIED, materialization,
     credential_ids=(executor_credential_ref,))` + `Licensing(route=EVIDENCE_LICENSED,
     independence_tier=None, verification_standing, evidence_provenance)` → **LICENSED**.
   - **no discovery** → the `UNDETERMINED` record falls through the existing passthrough → **PENDING**
     (insufficient evidence, *non-terminal*; never REFUTED).
   Ledger-discovery is thus **coextensive** with the license (audit-5 #10) — one decision rule.

This is **not** "two localized edits" (v5 overstated — audit-5 #4): it is **one route-specific
licensing/status block** in verify_stage, plus skipping the independent-pair gate for single-source. It
reuses the gate *computations* (B–G) but owns the evidence-route status mapping (license / PENDING /
EXECUTION_ERROR).

> ¹ `cycle.py:62-183`. ² `commitment.py:13-18`. ³ `register.py:15`, `fdr.py:111`. ⁴ `execute.py:51-60`.
> ⁵ verdict mechanics: `SatisfactionVerdict{SATISFIED,REFUTED,UNDETERMINED}` `licensing.py:23`;
> `agreed_refuted` terminal `verify.py:224-228,316-321`; UNDETERMINED+agreement → `satisfaction=None` →
> passthrough PENDING `verify.py:327-328`. ⁶ `ExecRecord` `corpus.py:86`. ⁷ Phase-D `verify.py:169-186`.
> ⁸ gates `verify.py:231-233` + `_permitted_by_bar:80-115` + `_e_ok:197-201`.

---

## 3. Statistical core

**Inferential claim.** Under declared **IID** sampling of examples from a target population — with model,
baseline, preprocessing and decision rules **fixed independently of the evaluation sample** (recorded in
the `EvidencePolicy` commitment, audit-4 #14) — the model's expected per-example accuracy **advantage
over a precommitted baseline exceeds τ ≥ 0**.

**Paired increments / sequential null.** `Wᵢ = 1(model correctᵢ) − 1(baseline correctᵢ) ∈ {−1,0,+1}`;
`H0: E[Wᵢ − τ | history] ≤ 0`. The policy's `theta0 = τ`. **The licensing decision is the e-LOND
discovery on this τ-null** (§2.5) — there is no second observed-advantage threshold to diverge from
(audit-5 #10).

**E-value (committed order).** `paired_advantage_evalue(w, theta0=τ)` runs the existing GRAPA core⁹ over
`Wᵢ − τ` in the benchmark's **single committed order** (not the seed-averaged permutations of
`betting_evalue`). `lam_max = _C/(1+τ)` keeps factors `≥ 1−_C > 0`. **Validity (Ville proof
obligation):** under the IID null with `θ₀=τ`, `e = Πᵢ(1+λᵢ(Wᵢ−τ))` is a non-negative test
supermartingale (predictable past-only λ, positive factors), so `E_H0[e] ≤ 1`.

**No outcome-dependent filtering (audit-3 #1).** Only structurally degenerate inputs are rejected;
all-tie/negative streams are valid → `e ≤ 1` → no discovery → PENDING. **Typed `SamplingRegime`**
(one member `IID_EXAMPLES`, disclosed assumption in the policy).

> ⁹ `_grapa_capital` `evidence.py:28-46`.

---

## 4. Typed objects & the hash chain

- **`ExecutionContract`** (on `EvaluationPlan`, the *committed* contract): `capability_id`,
  `capability_version`, `evidence_policy_ref`. Small + sufficient: everything else hangs off the
  content-addressed policy (below). Omit-when-`None` (§8).
- **`EvidencePolicy`** (pure grammar `_Model`; explicit `content_hash` property — `_Model` has none free¹⁰
  — `ref = content_hash`): `policy_id`, `version`, `null_family:"paired_bounded_mean_betting"`,
  `theta0(=τ)`, `statistic`, `support`, `sampling_regime:SamplingRegime`, `baseline_ref`,
  `calibration_population_ref`, `predictor_config_ref` (model weights/prompt/decoding/preprocessing
  digest — audit-5 #2), `executor_credential_ref`, `evalue_transform`. Validators (audit-3 #23):
  non-empty ids/refs; `theta0` finite, `≥0`; family↔transform compatible.
  `EvidencePolicyRegistry.resolve(ref)` recomputes `content_hash`.
- **The hash chain (audit-5 #1/#5)** — checked **at dispatch, before any execution** (so untrusted
  config never runs — audit-5 #7), and the *committed* root (`plan.execution_contract`) is additionally
  pre-registration-bound and re-enforced at verify by the existing `commitment_hash` F-gate. Every link:
  `plan.execution_contract.evidence_policy_ref` **==** `cell.verification_policy.evidence_policy_ref`
  **==** `resolve(evidence_policy_ref).content_hash`; then within the resolved policy:
  `calibration_population_ref == BenchmarkArtifact.content_hash`, `baseline_ref == baseline digest`,
  `predictor_config_ref == live predictor config digest`, `executor_credential_ref ==
  ExecutorCredential.content_hash`; and `criterion.threshold == policy.theta0`,
  `cell.operation_impl == terminal node.impl`. Any broken link → claim not dispatched / not licensed.
- **`ExecutorCredential`** (typed, content-addressed — audit-5 #6): `components: tuple[Component, ...]`
  where `Component{role: Literal["predictor","scorer","evidence_transform"], identity: str,
  implementation_hash: str, config_hash: str}`, in canonical role order; `content_hash` = `_sha` over
  the ordered components. Registry lookup key = `content_hash` = `policy.executor_credential_ref`. (A new
  type, not an extension of `AdapterCredential`, which is recompute-pair-shaped.)
- **`EvidenceProvenance`** (on `Licensing`): `executor_credential_ref`, `evidence_policy_ref`,
  `benchmark_ref`, `baseline_ref`, `predictor_config_ref`, `oracle_dossier_ref | None`,
  `observed_advantage`, `theta0`, `e_value`, `execution_contract_digest`, `fdr_test_index`,
  `alpha_allocated` (audit-4 #17). Invariant: `e_value` equals the resolved `FDRTest.e_value` (audit-4
  #24).
- **`EvidenceExecution`** (transient return — audit-4 #16): `record`, `e_value: float | None`,
  `licensing_info: EvidenceLicensingInfo | None`, `failure_reason: ExecutionFailure | None`.
- **`EvidenceLicensingInfo`** (transient executor→verify_stage): `route`, `verification_standing`,
  `evidence_provenance`, `materialization`.
- **`verification_standing`** on `Licensing`: `Literal["single_source_baseline"]` (audit-4 #22).

> ¹⁰ per-model `content_hash` `@property` convention, e.g. `operations.py:153-160`.

---

## 5. Benchmark interface (the generalization lesson — audit-3 #6)

- **`BenchmarkArtifact`** (content-addressed over ordered `example_ids`, per-example `features`,
  `labels`, `target_population`, `sampling_regime`, `version`); `policy.calibration_population_ref ==
  content_hash`.
- **`BenchmarkAdapter.predict(examples_without_labels) -> PredictionVector`** — labels structurally
  absent. Baseline predictions content-addressed → `policy.baseline_ref`.
- **`Scorer`** (separate; holds labels): joins by `example_id` in committed order; missing/dup/extra/
  order-mismatch → structural failure (§2.3). **All Layer-3 verification (incl. the whole-executor
  credential + `predictor_config_ref`) runs before predict/score (audit-5 #7).**

---

## 6. Trust binding & validation — three layers (audit-4 #5/#7/#8/#9)

**Layer 1 — cell trust binding** (claim-independent). A 4th cell needs a `CAPABILITY_CELLS` entry **and**
a `_bindings()` entry¹¹. `min_executing_adapters` is reconciled with the policy: `2` for
`recompute_pair`, `1` for `single` (the validator forcing `== 2`¹² is relaxed accordingly).
`validate_trust_binding` gains `evidence_policy_registry`¹³ + a single-mode branch: skip the
independent-pair requirement; require the `ExecutorCredential` resolvable + trusted, and the
`EvidencePolicy` resolvable + digest-verified. **Oracle guarantee, accurate (audit-4 #8):** `OracleDossier`
has no `trusted` field; this layer only confirms the oracle **id exists** — it does **not** call
`in_domain` (no subject here).

**Layer 2 — claim-to-capability binding** (before dispatch — audit-4 #9). `validate_claim_shape(claim,
cell)` (pattern/subject/params/output/data-ref/criterion); a non-conforming claim is **not** dispatched.
Oracle `in_domain(subject)` is checked **here**.

**Layer 3 — runtime artifact/executor binding** (execution-time, **before scoring** — audit-5 #7).
Verify `BenchmarkArtifact.content_hash == policy.calibration_population_ref`; baseline digest ==
`policy.baseline_ref`; live `predictor_config_ref` == policy's; and the **live whole-executor combined
hash == the registered `ExecutorCredential`** (predictor + scorer + evidence-transform impl hashes +
config hashes, audit-5 #5/#6 — `implementation_hash_for_*` generalized to take the relevant method, since
`BenchmarkAdapter` exposes `predict`, not `execute`¹⁴). Comparison is live-vs-registered, never a returned
identity string.

> ¹¹ `bind()` `capabilities.py:105-111`. ¹² `min_executing_adapters` validator `capability.py:146-152`.
> ¹³ `validate_trust_binding` `capabilities.py:114-116`. ¹⁴ `adapter_identity.py:13`.

---

## 7. Lifecycle / status

| Outcome | Status |
|---|---|
| e-LOND **discovery** ∧ gates B–G | **LICENSED** (`EVIDENCE_LICENSED`, `single_source_baseline`) |
| no discovery (incl. all-tie/negative, `e ≤ 1`) | **PENDING** (UNDETERMINED passthrough; non-terminal) |
| structural failure (digest/credential/order/dup/missing/empty) | **PENDING** `EXECUTION_ERROR`; e_value=None; **locked α consumed + unresolved** |

`PendingReason.EXECUTION_ERROR` is additive. **Retry (audit-5 #9):** a failed claim may re-execute
against the *same locked α-slot* **only under the identical committed `execution_contract`** — enforced
because any change to capability/policy/baseline changes the plan and trips `HYPOTHESIS_ALTERED` via
`commitment_hash`; a test pins this invariant. No terminal REFUTED on this route (a low e-value is
insufficient evidence, not refutation).

---

## 8. Schema deltas & compatibility (audit-4 #10/#11, audit-5 #11/#12)

**Grammar (pure):** `LicenseRoute.EVIDENCE_LICENSED`; `Licensing.independence_tier: IndependenceTier |
None`; `Licensing.verification_standing` + `evidence_provenance`; `PendingReason.EXECUTION_ERROR`;
`SamplingRegime`; `EvidencePolicy`(+registry); `ExecutorCredential`(+registry); `VerificationPolicy`;
optional `CapabilityCell.verification_policy`; optional `EvaluationPlan.execution_contract`.

**Protocol:** `run_cycle`/`execute_ground` gain `evidence_executor` + `capability_registry`;
`execute_ground` returns `evidence_executions`; `verify_stage` gains `evidence_licensing` +
`evidence_failures` + the evidence-route block (§2.5). Executor typed as a `Callable` in protocol.

**Compatibility — preserve existing hashes (audit-4 #10/#11, audit-5 #11/#12).** Three models gain
optional fields hashed (directly or transitively) into committed digests, so each needs **explicit
serialization that omits the new field when `None`** — Pydantic does not omit `None` by default:
- `Licensing.{verification_standing, evidence_provenance}` — hashed into the whole-claim attestation
  subject digest (`attestation.py:194`, no `exclude_none`¹⁵).
- `EvaluationPlan.execution_contract` — hashed by `commitment_hash` (and the field sits on the plan, not
  in the graph, so `ComputeGraph.content_hash`/commit-lock are untouched).
- `CapabilityCell.verification_policy` — not currently hashed, but omit-when-`None` keeps the dump
  **byte-identical** (audit-4 #11).
**Prefer field-specific serialization exclusion** over a wrapping `model_serializer` where the installed
Pydantic supports it (audit-5 #12); if a `model_serializer` is used, the plan's tests must cover nested
serialization, JSON-schema generation, `model_dump_json()`, commitment hashes, attestation hashes, and
round-trip validation. **Result:** existing recompute-license subject digests + the three existing cells
+ all commitment hashes are **byte-identical** (no golden re-bless); only evidence-licensed claims (whose
fields are populated) digest differently, as they should.

> ¹⁵ `_subject()` `attestation.py:194`.

---

## 9. Honest, powered fixture (audit-4 #12/#13, audit-5 #13/#14)

- **Feature-dependent label DGP** `y = f(features) ⊕ noise` with independently-sampled noise; a **model
  rule fixed before the draws** that is genuinely more accurate than a **weaker precommitted baseline**;
  the random draws independent of *implementation choices* (not labels independent of features).
- **Powered by construction, not seed-shopped (audit-5 #13):** the DGP is chosen so the *expected*
  advantage `E[1(model correct) − 1(baseline correct)] > τ` analytically/by construction, **then** a seed
  is pinned whose realized stream clears the locked threshold — distinguishing a powered fixture from
  seed-shopping under a null DGP.
- **Test reads the actual α (audit-5 #14):** the end-to-end test reads `alpha_allocated` from the
  registered `FDRTest` and asserts `e_value ≥ 1/alpha_allocated` (correct even if the fixture is not the
  ledger's first test). A 15/20-vs-10/20 sketch (e≈13.03 < 32.9) would not license; the fixture must
  clear the *actual* locked α.

---

## 10. Tests

1. **E-value regression:** exact small-stream values; all-tie/negative → `e ≤ 1` (no exception);
   documented Ville argument.
2. **Structural-only degeneracy** → `EXECUTION_ERROR`, e_value=None, test left unresolved.
3. **Label withholding:** `predict` has no label param; scorer is sole label holder.
4. **Paired alignment:** join by `example_id` in committed order; model==baseline → `e ≤ 1`.
5. **Hash-chain binding:** altering policy/baseline/capability/benchmark changes `commitment_hash` /
   policy `content_hash` → `HYPOTHESIS_ALTERED` / link mismatch; dispatch refuses a claim with no pending
   registered test; an in-cycle-GENERATE'd evidence claim is not executed this cycle.
6. **Whole-executor credential:** swapping the **scorer**, **evidence-transform**, or **predictor
   config** (not just the model) changes `ExecutorCredential` and fails Layer-3 **before** scoring.
7. **Three-layer validation:** non-conforming claim not dispatched; oracle `in_domain` at Layer 2;
   single-mode binding passes with one credential, `recompute_pair` still needs the pair.
8. **Gate reuse + decision rule:** an evidence claim not selected / not committed / not in grounded
   extension / altered-plan / **sub-threshold e-value** → not licensed (PENDING, never REFUTED);
   discovery ∧ gates → LICENSED. A discovery is coextensive with the license.
9. **Bookkeeping:** evidence execution updates stage-audit counts, selection-ledger outcome,
   Goodhart/operator credit, integrate(); a failure leaves the registered test unresolved (α consumed);
   retry under the **identical** contract is permitted, a varied contract trips `HYPOTHESIS_ALTERED`.
10. **Standing serialization:** evidence license `independence_tier=None`, standing literal; never
    `reproduced`.
11. **Compatibility:** existing recompute-license attestation subject digests **byte-identical**
    (`_golden_bundle.json` unchanged); `CapabilityCell` dump byte-identical; all `commitment_hash`es of
    existing claims unchanged; (if `model_serializer` used) the audit-5 #12 serialization battery.
12. **Powered-fixture license:** the DGP's expected advantage `> τ` is documented; the pinned seed's
    `e_value ≥ 1/alpha_allocated` (read from the registered test) before the LICENSED assertion.
13. **Protocol-test purity:** protocol tests inject a tiny **grammar-DTO** executor stub; no
    `polymer_claims` import.
Validity/contract tests (2,5,6,7,9,11) precede the end-to-end license test; `scripts/check-all.sh` is the
**final** task.

---

## 11. Acceptance criteria

1. `eval::benchmark_advantage@v1` registered (cell + `_bindings()` + whole-`ExecutorCredential` +
   `EvidencePolicy`), `min_executing_adapters` reconciled with the policy.
2. Licenses an inferential model-vs-precommitted-baseline claim **offline, in-cycle, post-commit**, the
   **e-LOND discovery being the sole decision**, gated by the full stack (A folded into discovery; B–G
   reused) — no out-of-cycle precompute, no gate-bypass, no separate criterion threshold.
3. The execution contract is pre-registration-bound (plan `commitment_hash`) with the full **hash chain**
   re-checked at verify; dispatch requires a locked FDR slot; in-cycle-generated evidence claims are
   ineligible until a later cycle's registration; provenance records the contract digest + FDR index +
   locked α, its e-value equals the ledger's.
4. License carries `route=EVIDENCE_LICENSED`, `independence_tier=None`, standing literal, durable
   provenance; weak evidence → PENDING (never REFUTED); failure → `EXECUTION_ERROR` with the α-slot
   consumed and retry only under the identical contract.
5. Three-layer validation enforced (executor + config verified before scoring); content-addressed
   artifacts + whole-executor credential reject every tamper/mismatch before licensing.
6. **Existing recompute-license attestation digests, the three cells, and all existing commitment hashes
   are byte-identical** (per-field None-exclusion; no re-bless); `grammar/`+`protocol/` pure + numpy-free;
   `Corpus` stays 4; `check-all.sh` green.

---

## 12. Audit-5 resolution map

#1 one `ExecutionContract` + explicit hash chain (§2.1/§4) · #2 `predictor_config_ref` committed +
verified (§4/§6 L3) · #3 discovery=license; UNDETERMINED→PENDING, no REFUTED (§2.5/§7) · #4 evidence-route
block owns EXECUTION_ERROR; "two edits" corrected (§2.5) · #5 cross-validated hash chain (§4) ·
#6 typed `ExecutorCredential` (§4) · #7 Layer-3 verified before scoring (§5/§6) · #8 generated claims
ineligible until later registration (§2.2) · #9 retry only under identical contract (§7) · #10 discovery
coextensive with license (§2.5) · #11 per-field serializers named for all three models (§8) · #12 prefer
field-specific; serialization battery if `model_serializer` (§8/§10) · #13 powered DGP then pinned seed
(§9) · #14 test reads `alpha_allocated` (§9).

---

## 13. Decomposition (Path A) & rhythm

- **Slice 1 (this spec):** in-cycle gated executor + discovery-as-decision + corrected statistics +
  content-addressed artifacts + whole-executor credential + three-layer validation + powered fixture.
- **Slice 2:** meaningful benchmark + full attestation chain + certificate/SLSA.
- **Slice 3:** defeat/drift/reinstatement/replay-over-time + tamper/boundary depth + downgraded-oracle.

Each slice: `writing-plans` → `subagent-driven-development` (TDD) → whole-branch review → merge `--no-ff`
→ update `CONTINUE.md` + memory.
