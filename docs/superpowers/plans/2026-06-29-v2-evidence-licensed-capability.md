# V2.0 Slice 1 — Evidence-licensed capability (in-cycle gated executor) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Source spec:** `docs/superpowers/specs/2026-06-29-v2-evidence-licensed-capability-design.md` (v8). Read it first. **Plan rev:** v2 (post-8th-review — data-flow contract, validators, and serializer sequencing fixed).

**Goal:** Register `eval::benchmark_advantage@v1` — a capability licensed by an in-cycle, post-commit, content-addressed executor whose paired sequential betting e-value, gated by e-LOND through the existing verify gates, mints an honest `EVIDENCE_LICENSED` license — without the two-adapter recompute air-gap.

**Architecture:** Umbrella `EvidenceExecutor` runs at EXECUTE (post-COMMIT). The protocol resolves the **grammar-pure** registries (policy/descriptor/trust) and does the precondition + hash-chain + credential + trust checks; it passes the resolved `EvidencePolicy` to `executor.execute(...)`, which resolves the **umbrella** `BenchmarkArtifact` internally (package direction preserved), scores, and returns a normal `ExecRecord` (verdict `UNDETERMINED`) + e-value. `verify_stage`'s minimal evidence-route block mints the license **only on e-LOND discovery + eligibility**, all other outcomes falling through to existing branches.

**Tech Stack:** Python 3, Pydantic 2.13 frozen `_Model`, numpy (umbrella only), pytest, ruff, `uv`.

## Global Constraints

- `grammar/` + `protocol/` stay **pure + numpy-free**; numpy only umbrella-side. `grammar/` never imports `polymer_formalclaim`; `protocol/` depends one-way on `grammar/`.
- `Corpus` = exactly 4 collections. Models subclass `_Model` (frozen, `extra="forbid"`); collections are tuples; no `dict`/`list` model fields (function params may be).
- New fields additive/optional with present-only-when validators; default byte-identical behavior.
- **Pydantic floor stays `>=2.6`** — None-omission via `@model_serializer(mode="wrap")`, NOT `Field(exclude_if=…)`.
- Per-package: `uv run pytest -q` + `uv run ruff check src tests`. Full gate `scripts/check-all.sh`. TDD: failing test first. Branch `feat/v2-evidence-capability`, merge `--no-ff`.

## Data-flow contract (resolves 8th-review #1–#4)

`run_cycle` gains **one** keyword param `evidence_runtime: EvidenceRuntime | None = None` — a **protocol-level** dataclass (not a Corpus model; holds a callable) bundling: `capability_registry: CapabilityRegistry`, `evidence_policy_registry: EvidencePolicyRegistry`, `executor_descriptor_registry: ExecutorDescriptorRegistry`, `executor_trust_registry: ExecutorTrustRegistry` (all grammar), and `executor: EvidenceExecutor` (protocol type; umbrella impl). It threads into `execute_ground`. **No pre-filtering of evidence ids** (#4): the selected set is passed normally and the per-claim loop branches. The protocol resolves policy/descriptor/trust from the claim's `execution_contract` and does the precondition + hash-chain + credential + trust checks; only the umbrella `BenchmarkArtifact` is resolved inside `executor.execute(...)`. `executor.execute(claim, cell, policy, ctx, fdr_test) -> EvidenceExecution`.

## Compatibility sequencing (resolves #23/#24)

Each None-omit `@model_serializer(mode="wrap")` ships **in the same task as its field addition** so every intermediate commit has stable hashes: `Licensing` serializer in **Task 8**, `CapabilityCell` in **Task 9**, `EvaluationPlan` in **Task 10**. **Task 18** is regression goldens only.

## Known risks

- Task 18 (golden battery) is the make-or-break: prove no existing attestation subject digest / commitment hash moves.
- Whole-executor trust rests on byte-derived component hashes + canonical config hashes; the guarantee is gate-non-bypass, not absolute validity.

---

## Phase 1a — pure objects + umbrella primitives

### Task 1: Paired betting e-value primitive (with finite/range validation)

**Files:** Create `src/polymer_claims/benchmark_evidence.py`; Test `tests/capability/test_benchmark_evidence.py`

**Interfaces:** `paired_advantage_evalue(w: Sequence[float], *, theta0: float) -> float`. **Validates (8th-review #8):** `theta0` finite ∧ `0 ≤ theta0 < 1`; every `Wᵢ` finite ∧ ∈ [−1,1]; empty → `ValueError`. Committed order (no permutation). Consumes `_grapa_capital`, `_C`.

- [ ] **Step 1: failing test** — strong stream `[1.0]*40` → `> 32.9`; all-ties → `≈1.0`; all-negative → `≤1.0` (valid, no exception); empty → `ValueError`; `theta0=float("nan")` → `ValueError`; `theta0=1.0` → `ValueError`; a stream with `nan` → `ValueError`; exact null-mean enumeration over `{-1,1}^4` at the boundary null ≤ 1.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: implement**
```python
from __future__ import annotations
from collections.abc import Sequence
import numpy as np
from .evidence import _C, _grapa_capital

def paired_advantage_evalue(w: Sequence[float], *, theta0: float) -> float:
    t = float(theta0)
    if not np.isfinite(t) or not (0.0 <= t < 1.0):
        raise ValueError("theta0 must be finite and in [0, 1)")
    arr = np.asarray(w, dtype=float)
    if arr.size == 0:
        raise ValueError("empty stream")
    if not np.all(np.isfinite(arr)) or np.any(arr < -1.0) or np.any(arr > 1.0):
        raise ValueError("increments must be finite and in [-1, 1]")
    return _grapa_capital(arr - t, _C / (1.0 + abs(t)))
```
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5: commit** `"feat(capability): paired-advantage betting e-value (committed order + validation)"`

### Task 2: PredictionVector + Scorer (label-withholding, real order check)

**Files:** Modify `benchmark_evidence.py`; Test `tests/capability/test_benchmark_scorer.py`

**Interfaces:** `PredictionVector(predictions: tuple[tuple[str,str],...])`; `score_advantage(model, baseline, labels, order) -> list[float]`; `ScoringError(ValueError)`. **Order check (8th-review #7):** require each `PredictionVector`'s id sequence to **equal `order` exactly** (not just the set); missing/dup/extra/order-mismatch → `ScoringError`.

- [ ] **Step 1: failing test** — paired Wᵢ in order `[0,1,1]`; a vector with the same ids in **different order** → `ScoringError`; missing id → `ScoringError`; duplicate → `ScoringError`.
- [ ] **Step 2–3:** implement `as_map()` (dup → error) + `score_advantage` asserting `tuple(eid for eid,_ in pv.predictions) == tuple(order)` for both model and baseline.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5: commit** `"feat(capability): PredictionVector + scorer with exact-order check"`

### Task 3: Grammar — `SamplingRegime` + `DataRefKind.BENCHMARK` (BEFORE the artifact — #10)

**Files:** Create `grammar/src/polymer_grammar/sampling.py` (`SamplingRegime`); **Modify `grammar/src/polymer_grammar/capability.py`** (`DataRefKind` + `data_ref_ok`, at `capability.py:64` — **not** `operations.py`, 8th-review #5); Modify `__init__.py`; Test `grammar/tests/test_sampling_and_dataref.py`

**Canonical bench ref (8th-review #6):** the artifact's `content_hash` is `sha256:<hex>` (from `canonical_sha256`); the bench ref is **`"bench:" + content_hash` = `bench:sha256:<hex>`**. `data_ref_ok` for `DataRefKind.BENCHMARK` accepts exactly that shape.

- [ ] **Step 1: failing test** — `SamplingRegime.IID_EXAMPLES.value == "iid_examples"`; `data_ref_ok("bench:sha256:"+ "a"*64, DataRefKind.BENCHMARK)` is True; `bench:<hex-without-sha256>` and `se:x@1` are False.
- [ ] **Step 2–4:** add the enum member to `DataRefKind` + the matcher branch in `data_ref_ok`; run → PASS; grammar suite green.
- [ ] **Step 5: commit** `"feat(grammar): SamplingRegime + DataRefKind.BENCHMARK (bench:sha256:<hex>)"`

### Task 4: BenchmarkArtifact (frozen pydantic + validators) + BenchmarkAdapter + fixture predictors

**Files:** Create `src/polymer_claims/benchmark_adapter.py`; Test `tests/capability/test_benchmark_adapter.py`

**Interfaces (8th-review #9):** `BenchmarkArtifact` is a **frozen pydantic model**: `example_ids: tuple[str,...]`, `features: tuple[tuple[tuple[str,str],...],...]`, `labels: tuple[tuple[str,str],...]`, `target_population: str`, `sampling_regime: SamplingRegime` (typed), `version: str`, `sampling_seed: int`, `dgp_digest: str`; **validators:** unique example_ids; `features`/`labels` keys exactly cover `example_ids`; no malformed labels; non-empty `target_population`/`version`; `dgp_digest` `sha256:`-shaped. `content_hash` = `canonical_sha256(model_dump(mode="json"))`; `ref` = `"bench:" + content_hash`. `BenchmarkAdapter` Protocol: `identity`, `config: dict`, `predict(examples) -> PredictionVector` (no labels). `FixtureModelAdapter`/`FixtureBaselineAdapter` (deterministic, label-independent seed).

- [ ] **Step 1: failing test** — `predict` signature has no `labels`; two artifacts with different labels differ in `content_hash`; `ref` == `"bench:" + content_hash`; duplicate example_id → `ValidationError`; label not covering an id → `ValidationError`.
- [ ] **Step 2–4:** implement; run → PASS; `uv run ruff check src tests`.
- [ ] **Step 5: commit** `"feat(capability): validated content-addressed BenchmarkArtifact + adapters"`

### Task 5: Grammar — `EvidencePolicy` (+registry w/ uniqueness, content_hash, validators)

**Files:** Create `grammar/src/polymer_grammar/evidence_policy.py`; Modify `__init__.py`; Test `grammar/tests/test_evidence_policy.py`

**Interfaces:** `EvidencePolicy(_Model)` per spec §4 (`baseline_config_ref`, `predictor_config_ref`, `executor_descriptor_ref`, …); `content_hash` `@property` via `_sha`; `ref` returns it. **Validators:** non-empty ids/refs; **`0 ≤ theta0 < 1`**; family↔transform compatible. `EvidencePolicyRegistry{policies; resolve(ref)}` with a **duplicate-ref validator** (8th-review #12).

- [ ] **Step 1: failing test** — `ref == content_hash`; `resolve` round-trips; `theta0` 1.0/−0.1 → error; **two policies with the same `content_hash` in one registry → `ValidationError`**.
- [ ] **Step 2–4:** implement (`from .base import _Model`); run → PASS; grammar + isolation green.
- [ ] **Step 5: commit** `"feat(grammar): EvidencePolicy + registry (uniqueness, validators)"`

### Task 6: Grammar — `ExecutorDescriptor` + `ExecutorDescriptorRegistry` + `ExecutorTrustEntry` + `ExecutorTrustRegistry`

**Files:** Create `grammar/src/polymer_grammar/executor_credential.py`; Modify `__init__.py`; Test `grammar/tests/test_executor_credential.py`

**Interfaces (8th-review #2/#12/#15):** `Component{role: Literal["predictor","baseline_predictor","scorer","evidence_transform"], identity, implementation_hash, config_hash}`; `ExecutorDescriptor{components, version}` + `content_hash`; **validators:** exactly one of each role, canonical role order, unique identities, non-empty `sha256:`-prefixed hashes. **`ExecutorDescriptorRegistry{descriptors; resolve(content_hash)}`** (the descriptor content, needed to verify live hashes — #2) with uniqueness. `ExecutorTrustEntry{descriptor_ref, owner, trusted: bool, version}`; `ExecutorTrustRegistry{entries; resolve(descriptor_ref)}` with a **duplicate-`descriptor_ref` validator**.

- [ ] **Step 1: failing test** — valid descriptor stable hash; missing baseline role / wrong order / dup identity / non-`sha256:` hash → error; descriptor registry resolves by `content_hash`; duplicate descriptor_ref in trust registry → error.
- [ ] **Step 2–4:** implement; run → PASS; grammar green.
- [ ] **Step 5: commit** `"feat(grammar): ExecutorDescriptor(+registry) / ExecutorTrustEntry(+registry)"`

### Task 7: Grammar — `VerificationPolicy` (both-mode validation), `ExecutionContract`, `EvidenceProvenance` (numeric invariants), `EvidenceLicensingInfo` (literal standing)

**Files:** Create `grammar/src/polymer_grammar/verification_policy.py`; Modify `__init__.py`; Test `grammar/tests/test_verification_policy.py`

**Interfaces:**
- `VerificationPolicy` — **validate BOTH complete modes (8th-review #11):** `recompute_pair` ⇒ `result_rule="criterion"` ∧ `independence_requirement="implementation"` ∧ `evidence_policy_ref is None` ∧ `min_adapters==2`; `single` ⇒ `result_rule="evalue_discovery"` ∧ `independence_requirement="baseline_ground_truth"` ∧ `evidence_policy_ref is not None` ∧ `min_adapters==1`.
- `ExecutionContract{capability_id, capability_version, evidence_policy_ref, capability_descriptor_ref}`.
- `EvidenceProvenance` per §4 with **numeric validators (8th-review #16):** `observed_advantage ∈ [−1,1]`; `0 ≤ theta0 < 1`; `e_value ≥ 0` ∧ finite; `fdr_test_index > 0`; `0 < alpha_allocated ≤ 1`; refs non-empty/hash-shaped.
- `EvidenceLicensingInfo{route: LicenseRoute, verification_standing: Literal["single_source_baseline"], evidence_provenance: EvidenceProvenance, materialization}` — **literal, not str (8th-review #13)**.

- [ ] **Step 1: failing test** — `single` with `result_rule="criterion"` → error; `recompute_pair` with `evidence_policy_ref` set → error; provenance with `e_value=-1`/`alpha=0`/`observed_advantage=2` → error; standing literal rejects an arbitrary string.
- [ ] **Step 2–4:** implement; run → PASS; grammar + isolation green.
- [ ] **Step 5: commit** `"feat(grammar): VerificationPolicy(both modes) + ExecutionContract + Provenance(invariants) + LicensingInfo"`

### Task 8: Grammar — `Licensing` evidence fields + serializer + `PendingReason.EXECUTION_ERROR`

**Files:** Modify `grammar/src/polymer_grammar/{licensing.py, status.py}`; Test `grammar/tests/test_licensing_evidence_route.py`, `grammar/tests/test_compat_licensing.py`

**Interfaces:** `LicenseRoute.EVIDENCE_LICENSED`; `Licensing.independence_tier: IndependenceTier | None = IndependenceTier.REPRODUCED`; `Licensing.verification_standing: Literal["single_source_baseline"] | None = None`; `Licensing.evidence_provenance: EvidenceProvenance | None = None`; validator standing/provenance non-None **iff** `EVIDENCE_LICENSED`. `PendingReason.EXECUTION_ERROR`. **Serializer in THIS task (#24):** `@model_serializer(mode="wrap")` dropping `verification_standing`/`evidence_provenance` when `None`.

- [ ] **Step 1: failing tests** — evidence-route Licensing round-trips with `independence_tier=None`; standing on `SEVERE_TEST` → error; `Licensing(satisfactions=())` still rejected; **a non-evidence `Licensing` `model_dump` is byte-identical to before (no `verification_standing`/`evidence_provenance` keys)**; historical JSON without the fields deserializes.
- [ ] **Step 2–4:** implement field + serializer together; run → PASS; full grammar suite green.
- [ ] **Step 5: commit** `"feat(grammar): EVIDENCE_LICENSED route + standing/provenance (+None-omit serializer) + EXECUTION_ERROR"`

### Task 9: Grammar — `CapabilityCell.content_hash` + optional `verification_policy` + serializer + cardinality migration

**Files:** Modify `grammar/src/polymer_grammar/capability.py`; Test `grammar/tests/test_capability_descriptors.py`

**Interfaces:** `CapabilityCell.content_hash` `@property`; optional `verification_policy: VerificationPolicy | None = None` with a **same-task `@model_serializer(mode="wrap")`** dropping it when `None` (#24); cardinality validator: `None`/`recompute_pair` ⇒ `min_executing_adapters==2`, `single` ⇒ `==1`.

- [ ] **Step 1: failing test** — three existing cells valid + `content_hash` stable + **their `model_dump` byte-identical** (no `verification_policy` key); `single`-policy cell with `min=2` → error, `=1` → valid.
- [ ] **Step 2–4:** implement; run → PASS; full grammar suite green.
- [ ] **Step 5: commit** `"feat(grammar): CapabilityCell content_hash + optional VerificationPolicy(+serializer) + cardinality migration"`

### Task 10: Grammar — optional `EvaluationPlan.execution_contract` + serializer

**Files:** Modify `grammar/src/polymer_grammar/operations.py`; Test `grammar/tests/test_operations_contract.py`

**Interfaces:** `EvaluationPlan.execution_contract: ExecutionContract | None = None` (on the plan, not the graph) with a **same-task `@model_serializer(mode="wrap")`** dropping it when `None` (#24).

- [ ] **Step 1: failing test** — plan with contract round-trips; **existing plan's `model_dump`/`commitment_hash`/`ComputeGraph.content_hash` byte-identical** (no `execution_contract` key); a contract-bearing plan's `commitment_hash` includes it.
- [ ] **Step 2–4:** implement; run → PASS; grammar green.
- [ ] **Step 5: commit** `"feat(grammar): optional EvaluationPlan.execution_contract (+None-omit serializer)"`

### Task 11: Protocol — `EvidenceExecutor` protocol + `EvidenceExecution` (state validator) + broadened `ExecutionFailure`

**Files:** Create `protocol/src/polymer_protocol/evidence_executor.py`; Modify `__init__.py`; Test `protocol/tests/test_evidence_executor_types.py`

**Interfaces (8th-review #14/#15):**
```python
class ExecutionFailure(_Model):
    # distinguish pre-dispatch rejection from execution failure (#15)
    reason: Literal["empty","malformed","duplicate","missing","order_mismatch",
                    "nonfinite_prediction","out_of_support","predictor_error",
                    "policy_mismatch","credential_mismatch","digest_mismatch","untrusted_executor"]
    stage: Literal["pre_dispatch","execution"]
    detail: str = ""
class EvidenceExecution(_Model):
    record: ExecRecord
    e_value: float | None = None
    licensing_info: EvidenceLicensingInfo | None = None
    failure_reason: ExecutionFailure | None = None
    # validator (#14): success => e_value & licensing_info present, failure None, e_value>=0 & finite;
    #                   failure => failure present, e_value & licensing_info None;
    #                   record.claim_id == licensing_info.evidence_provenance fields' claim (when success)
class EvidenceExecutor(Protocol):
    def credential(self) -> str: ...
    def execute(self, claim, cell, policy, ctx, fdr_test) -> EvidenceExecution: ...
EvidenceRuntime = dataclass(capability_registry, evidence_policy_registry,
    executor_descriptor_registry, executor_trust_registry, executor)  # protocol-level, holds the callable
```

- [ ] **Step 1: failing test** — success/failure validators reject contradictory states; a tiny **grammar/protocol-DTO-only** stub executor returns a valid `EvidenceExecution` (no `polymer_claims` import — purity).
- [ ] **Step 2–4:** implement; run → PASS (`cd protocol && uv run pytest -q`); isolation green.
- [ ] **Step 5: commit** `"feat(protocol): EvidenceExecutor + EvidenceExecution(state validator) + ExecutionFailure(stages) + EvidenceRuntime"`

### Task 12: Umbrella — `EvidenceExecutor` impl + internal artifact resolution + Layer-3 checks

**Files:** Create `src/polymer_claims/benchmark_capability.py`; Test `tests/capability/test_benchmark_executor.py`

**Interfaces:** `BenchmarkEvidenceExecutor` owns predictor/baseline/scorer/transform + an artifact store; `credential()` recomputes the live `ExecutorDescriptor.content_hash`; `execute(claim, cell, policy, ctx, fdr_test)` resolves the `BenchmarkArtifact` from `policy.calibration_population_ref`, verifies artifact + baseline-config + predictor-config links (failure → `ExecutionFailure(stage="execution"|"pre_dispatch")`), scores `Wᵢ`, computes the e-value, builds `EvidenceProvenance` (`e_value`, `observed_advantage`, both baseline refs, contract digest, `fdr_test_index`, `alpha_allocated` from `fdr_test`) + `EvidenceLicensingInfo`, returns `EvidenceExecution`. **No outcome filtering.**

- [ ] **Step 1: failing test** — strong fixture → `e_value > 1/alpha`, `route==EVIDENCE_LICENSED`, provenance populated, record verdict `UNDETERMINED`; tampered benchmark → `failure_reason.reason=="digest_mismatch"`, `e_value=None`; `credential()` changes when the baseline component swaps.
- [ ] **Step 2–4:** implement; run → PASS; ruff clean.
- [ ] **Step 5: commit** `"feat(capability): umbrella EvidenceExecutor + internal artifact resolution + Layer-3"`

---

## Phase 1b — protocol dispatch + end-to-end

### Task 13: Protocol — thread `evidence_runtime` through `run_cycle` (NO pre-filtering)

**Files:** Modify `protocol/src/polymer_protocol/cycle.py`; Test `protocol/tests/test_evidence_dispatch.py`

**Interfaces:** `run_cycle(..., evidence_runtime: EvidenceRuntime | None = None)`; forward into `execute_ground`. **Do NOT exclude evidence ids from the selected set (#4)** — branching happens inside `execute_ground`.

- [ ] **Step 1: failing test** — a cycle with an evidence claim + a stub `evidence_runtime` does not raise; a normal cycle with `evidence_runtime=None` is byte-identical to today.
- [ ] **Step 2–4:** implement pass-through; run → PASS; full protocol suite green.
- [ ] **Step 5: commit** `"feat(protocol): thread evidence_runtime through run_cycle"`

### Task 14: Protocol — `execute_ground` branch: resolve, precondition (exact test index), checks, dispatch

**Files:** Modify `protocol/src/polymer_protocol/execute.py`; Test `protocol/tests/test_evidence_dispatch.py`

**Interfaces:** `execute_ground(...) -> (Corpus, tuple[ExecRecord,...], tuple[EvidenceExecution,...])`. Per-claim, if the resolved cell (via `evidence_runtime.capability_registry`, by the plan's `execution_contract` versioned key) is `execution=="single"`: resolve `EvidencePolicy`/`ExecutorDescriptor`/`ExecutorTrustEntry`; check the **hash chain** + `executor.credential()==descriptor.content_hash` + trust entry `trusted`; check the **precondition** — selected ∧ committed ∧ **a pending registered `FDRTest` located by the committed test index** with matching `claim_id`/`commitment_hash`/`alpha`/contract digest (8th-review #19) ∧ claim-shape conformance. Pass → `executor.execute(...)`, collect `ExecRecord` + `EvidenceExecution`; any check fails → **refuse** (no dispatch; or `ExecutionFailure(stage="pre_dispatch")`). Non-evidence claims unchanged.

- [ ] **Step 1: failing test** — registered evidence claim → `EvidenceExecution` + `ExecRecord`; unregistered → refused; in-cycle-GENERATE'd → not executed; a claim whose live `credential()` ≠ registered descriptor → `pre_dispatch` credential_mismatch.
- [ ] **Step 2–4:** implement; run → PASS; protocol suite green.
- [ ] **Step 5: commit** `"feat(protocol): execute_ground evidence dispatch + exact-index precondition + chain checks"`

### Task 15: Protocol — `verify_stage` evidence-route block (altered-first, ledger-equality, discovery, fall-through)

**Files:** Modify `protocol/src/polymer_protocol/verify.py`; Test `protocol/tests/test_evidence_dispatch.py`

**Interfaces:** `verify_stage(..., evidence_licensing=None, evidence_failures=None)`. Order (8th-review #17): **(1) altered commitment → existing REJECTED `HYPOTHESIS_ALTERED` (precedence preserved)**; (2) `evidence_failures[c.id]` → PENDING `EXECUTION_ERROR`; (3) e-LOND discovery (`_e_ok` after Phase-D) **and** eligible (`in_ext`, provenance present, status PENDING) → **locate the resolved `FDRTest` by `provenance.fdr_test_index` and assert `claim_id`/`commitment_hash`/`alpha_allocated`/`e_value` all equal the provenance (#18)**, then mint `Satisfaction(SATISFIED, materialization, credential_ids=(descriptor_ref,))` + `Licensing(EVIDENCE_LICENSED, independence_tier=None, verification_standing, evidence_provenance)` → LICENSED; (4) else **fall through** to existing branches (grounded-out → REJECTED `DEFEAT_GROUNDED_OUT`, else passthrough PENDING). Skip the independent-pair gate for evidence claims.

- [ ] **Step 1: failing tests** — discovery+eligible → LICENSED (route/standing/`independence_tier=None`/`provenance.e_value==FDRTest.e_value`); **altered AND failed → REJECTED `HYPOTHESIS_ALTERED`** (not EXECUTION_ERROR); discovered but non-grounded → REJECTED `DEFEAT_GROUNDED_OUT`; sub-threshold → PENDING; failure (not altered) → PENDING `EXECUTION_ERROR`.
- [ ] **Step 2–4:** implement; run → PASS; full protocol suite green (inert when dicts `None`).
- [ ] **Step 5: commit** `"feat(protocol): verify_stage evidence block (altered-first, ledger-equality, discovery=decision)"`

### Task 16: Umbrella — register cell + `_bindings()` (executor registries) + `validate_trust_binding` single-mode

**Files:** Modify `src/polymer_claims/capabilities.py`; Test `tests/capability/test_cells.py`, `tests/capability/test_binding.py`

**Interfaces:** add `EVAL_BENCHMARK_ADVANTAGE_CELL` (the §5 descriptor) to `CAPABILITY_CELLS`; `CapabilityTrustBinding` gains `executor_descriptor_registry` + `executor_trust_registry`; `_bindings()` entry supplies them; `validate_trust_binding(cell, adapter_registry, oracle_registry, *, evidence_policy_registry=None, executor_descriptor_registry=None, executor_trust_registry=None)` single-mode branch (skip pair; require policy resolvable+digest-verified, descriptor resolvable, trust entry `trusted`; unbounded oracle apparatus).

- [ ] **Step 1: failing tests** — cell is `single`; binding passes with one credential + trusted descriptor; untrusted entry fails; existing three cells still require the pair.
- [ ] **Step 2–4:** implement; run → PASS.
- [ ] **Step 5: commit** `"feat(capability): register eval::benchmark_advantage + single-mode trust binding"`

### Task 17: Powered fixture (Monte-Carlo power calc, separate RNG, ledger-derived threshold)

**Files:** Create `src/polymer_claims/_fixtures/benchmark_dgp.py`; `data/demo/benchmark_advantage_fixture.json`; Test `tests/capability/test_benchmark_fixture.py`

**Interfaces (8th-review #20/#21/#22):** the generator constructs the model rule + weaker baseline **before** label generation, using a **separate fixed RNG stream** for the feature-dependent DGP `y=f(features)⊕noise`. A **deterministic Monte-Carlo power estimate** (fixed sim seed) computes `P̂_alt(E ≥ 1/α) ` and selects the **predeclared `n`** meeting `≥ 0.8` with a conservative margin. A helper `evalue_threshold(alpha)` returns `1/alpha` (used by both fixture and Task 19 — #22).

- [ ] **Step 1: failing test** — the Monte-Carlo power estimate at the chosen `n` is `≥ 0.8` (fixed sim seed, conservative tolerance); the committed fixture's realized `paired_advantage_evalue(W, theta0=τ) ≥ evalue_threshold(α)` where α is read/derived (not hardcoded 32.9); a test asserts the DGP RNG stream is distinct from and precedes the rule construction (#21).
- [ ] **Step 2–4:** generate with the predeclared n/seed (escalate n only via the predeclared schedule); run → PASS.
- [ ] **Step 5: commit** `"test(capability): powered fixture (MC power calc, separate RNG, ledger-derived threshold)"`

### Task 18: Compatibility regression goldens (serializers already shipped in Tasks 8–10)

**Files:** Test `tests/attestation/test_golden_unchanged.py`, `grammar/tests/test_compat_serialization.py`

- [ ] **Step 1: failing tests (hard gate)** — **`tests/attestation/_golden_bundle.json` subject digests (`fb81e5a2…`, `2426880d…`) byte-identical**; all three existing cells' `model_dump_json` unchanged; representative existing `commitment_hash` unchanged; JSON-schema generation for `Licensing`/`CapabilityCell`/`EvaluationPlan` succeeds; nested round-trip; **historical JSON lacking the new fields deserializes**.
- [ ] **Step 2–4:** these should PASS given Tasks 8–10 shipped the serializers; if any digest moved, fix the serializer (do NOT re-bless).
- [ ] **Step 5: commit** `"test: compatibility regression goldens (existing digests byte-identical)"`

### Task 19: End-to-end + defeat-semantics + observable bookkeeping + final gate

**Files:** Test `tests/capability/test_benchmark_end_to_end.py`

**Interfaces (8th-review #25/#26):** assert **observable consequences**, not the internal `executed_ids` var: the verify/execute **stage-audit counts**, the **selection-ledger outcome**, the claim **status/provenance**, and an **executor call count** (spy). For Goodhart credit, construct the evidence claim with **explicit generated-by/operator provenance** (or limit to selection-ledger outcome).

- [ ] **Step 1: failing tests** — `register_hypotheses` → `run_cycle(..., evidence_runtime=EvidenceRuntime(...))` on the powered fixture: LICENSED, `route=EVIDENCE_LICENSED`, `independence_tier=None`, standing literal, `provenance.e_value == registered FDRTest.e_value`, `e_value ≥ evalue_threshold(alpha_allocated)`. **Defeat semantics:** non-grounded discovered → REJECTED `DEFEAT_GROUNDED_OUT`; altered → REJECTED `HYPOTHESIS_ALTERED`; sub-threshold → PENDING. **Bookkeeping (observable):** stage-audit counts reflect the execution; selection-ledger outcome present; executor called once; a failure leaves the registered test unresolved (α consumed); retry under identical `(commitment, index, α, contract digest)` permitted, varied contract → `HYPOTHESIS_ALTERED`. **BH exemption** documented.
- [ ] **Step 2–4:** make pass.
- [ ] **Step 5: final gate** — `scripts/check-all.sh` ALL GREEN; commit `"test(capability): end-to-end evidence license + defeat semantics + observable bookkeeping"`

---

## Self-review (spec → task coverage)

§2 architecture → 11,13,14,15. §3 statistics → 1,17. §4 objects/modules/executor/chain → 5,6,7,11,12. §5 descriptor → 9,16. §6 three-layer binding → 12,14,16. §7 lifecycle/status → 8,15,19. §8 schema+compat → 3,8,9,10,18 (serializers in 8/9/10; goldens in 18). §9 fixture → 17. §10 tests → all + 19. §11 acceptance → 16,18,19. §12 audit-7 map → 6,7,15,8–10,17.

**8th-review coverage:** #1–#4 data-flow/`EvidenceRuntime`/no-pre-filter (Data-flow contract + 13,14). #5 DataRefKind in capability.py (3). #6 `bench:sha256:` (3,4). #7 scorer order (2). #8 e-value validation (1). #9 frozen artifact + validators (4). #10 enum-before-artifact (3<4). #11 both-mode policy (7). #12 registry uniqueness (5,6). #13 literal standing (7). #14 EvidenceExecution validator (11). #15 ExecutionFailure stages (11). #16 provenance invariants (7). #17 altered-first (15). #18 ledger-equality step (15). #19 exact-index retry (14). #20 MC power calc (17). #21 RNG separation (17). #22 1/alpha helper (17,19). #23/#24 serializer sequencing (8,9,10; 18 goldens). #25 observable bookkeeping (19). #26 operator provenance (19).

**Type consistency:** `executor_descriptor_ref` throughout; `paired_advantage_evalue(w, *, theta0)` in 1,12,17; `EvidenceRuntime`/`EvidenceExecution`/`EvidenceExecutor` in protocol (11) used by 13,14,15; `evalue_threshold(alpha)` in 17,19.

## Optional internal split

- **1a = Tasks 1–12** (pure objects + umbrella primitives + executor; licenses nothing). **1b = Tasks 13–19**.

## Execution

`subagent-driven-development` → whole-branch review → merge `--no-ff` → update `CONTINUE.md` + memory.
