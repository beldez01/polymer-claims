# V2.0 Slice 1 — Evidence-licensed capability (in-cycle gated executor) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Source spec:** `docs/superpowers/specs/2026-06-29-v2-evidence-licensed-capability-design.md` (v8, architecture approved over 7 reviews). Read it first.

**Goal:** Register `eval::benchmark_advantage@v1` — a capability licensed by an in-cycle, post-commit, content-addressed executor whose paired sequential betting e-value, gated by e-LOND through the existing verify gates, mints an honest `EVIDENCE_LICENSED` license — without the two-adapter recompute air-gap.

**Architecture:** Umbrella `EvidenceExecutor` runs at EXECUTE (post-COMMIT); `execute_ground` branches single-policy claims to it; it returns a normal `ExecRecord` (verdict `UNDETERMINED`) + an e-value via the existing `evidence=` map; `verify_stage`'s minimal evidence-route block mints the Satisfaction + license **only on e-LOND discovery + eligibility**, with all other outcomes falling through to existing branches. Pure DTOs live in grammar; `EvidenceExecution`/`EvidenceExecutor` (wrap `ExecRecord`) live in protocol; the executor implementation + benchmark machinery + e-value live in the umbrella.

**Tech Stack:** Python 3, Pydantic 2.13 frozen `_Model`, numpy (umbrella only), pytest, ruff, `uv`.

## Global Constraints

- `grammar/` + `protocol/` stay **pure + deterministic + numpy-free**; numpy only umbrella-side.
- `grammar/` never imports `polymer_formalclaim`; `protocol/` depends one-way on `grammar/` (isolation-tested).
- `Corpus` = exactly 4 collections. Models subclass `_Model` (frozen, `extra="forbid"`); collections are tuples, never `dict`/`list` model fields (function params may be dict/tuple).
- New cross-cutting fields land additive/optional with present-only-when validators; opt-in defaults to byte-identical behavior.
- **Pydantic floor stays `>=2.6`** — use `@model_serializer(mode="wrap")` for None-omission, NOT `Field(exclude_if=…)`.
- Per-package gate: `uv run pytest -q` + `uv run ruff check src tests` in `grammar/`, `protocol/`, umbrella. Full gate: `scripts/check-all.sh`. TDD: failing test first. Branch `feat/v2-evidence-capability`, merge `--no-ff`.

## Known risks (carried from review)

- The whole-executor trust depends on byte-derived hashes of `predict`/score/transform + canonical config hashes; a party controlling all trust roots can still construct false evidence (the guarantee is gate-non-bypass, not absolute validity).
- The compat `model_serializer` must be proven not to perturb existing attestation subject digests / commitment hashes — Task 18 is a hard golden gate.

---

## File structure

**Phase 1a — pure objects + umbrella primitives (no protocol dispatch; licenses nothing):**
- Grammar: `evidence_policy.py` (`EvidencePolicy`, `EvidencePolicyRegistry`), `executor_credential.py` (`ExecutorDescriptor`, `Component`, `ExecutorTrustEntry`, `ExecutorTrustRegistry`), `verification_policy.py` (`VerificationPolicy`, `ExecutionContract`, `SamplingRegime`, `EvidenceProvenance`, `EvidenceLicensingInfo`); edits to `licensing.py`, `status.py`, `operations.py` (DataRefKind, EvaluationPlan), `capability.py` (CapabilityCell), `__init__.py`.
- Protocol: `evidence_executor.py` (`EvidenceExecutor` Protocol, `EvidenceExecution`, `ExecutionFailure`).
- Umbrella: `benchmark_evidence.py` (paired e-value, `PredictionVector`, `Scorer`), `benchmark_adapter.py` (`BenchmarkArtifact`, `BenchmarkAdapter`, fixture predictors), `benchmark_capability.py` (the `EvidenceExecutor` impl + cell + `_bindings()` + hash-chain checks).

**Phase 1b — protocol dispatch + end-to-end:**
- Protocol edits: `cycle.py` (`run_cycle`), `execute.py` (`execute_ground` branch), `verify.py` (evidence-route block).
- Umbrella: `capabilities.py` (register cell, `_bindings()`, `validate_trust_binding`), fixture `data/demo/benchmark_advantage_fixture.json`.
- Tests under `grammar/tests/`, `protocol/tests/`, `tests/capability/`.

---

## Phase 1a — pure objects + umbrella primitives

### Task 1: Paired betting e-value primitive

**Files:** Create `src/polymer_claims/benchmark_evidence.py`; Test `tests/capability/test_benchmark_evidence.py`

**Interfaces:** Produces `paired_advantage_evalue(w: Sequence[float], *, theta0: float) -> float` — deterministic GRAPA betting e-value over `Wᵢ − θ₀` in committed order, `Wᵢ∈[−1,1]`. Empty → `ValueError`. Consumes `_grapa_capital`, `_C` from `evidence.py`.

- [ ] **Step 1: failing test**
```python
# tests/capability/test_benchmark_evidence.py
import itertools, pytest
from polymer_claims.benchmark_evidence import paired_advantage_evalue

def test_strong_advantage_large_evalue():
    assert paired_advantage_evalue([1.0]*40, theta0=0.0) > 32.9   # clears e-LOND alpha1

def test_all_ties_evalue_one():
    assert paired_advantage_evalue([0.0]*10, theta0=0.0) == pytest.approx(1.0)

def test_all_negative_is_valid_low_evalue():   # audit: NO outcome filtering
    assert paired_advantage_evalue([-1.0]*10, theta0=0.0) <= 1.0

def test_empty_raises():
    with pytest.raises(ValueError):
        paired_advantage_evalue([], theta0=0.0)

def test_null_mean_not_exceeding_one_enumeration():
    n, q = 4, 0.5  # boundary null E[W]=0, P(-1)=P(+1)=0.5
    total = sum(
        (q**c.count(-1.0))*(q**c.count(1.0)) * paired_advantage_evalue(list(c), theta0=0.0)
        for c in itertools.product((-1.0,1.0), repeat=n))
    assert total <= 1.0 + 1e-9
```
- [ ] **Step 2:** `uv run pytest tests/capability/test_benchmark_evidence.py -q` → FAIL (ModuleNotFound).
- [ ] **Step 3: implement**
```python
# src/polymer_claims/benchmark_evidence.py
from __future__ import annotations
from collections.abc import Sequence
import numpy as np
from .evidence import _C, _grapa_capital

def paired_advantage_evalue(w: Sequence[float], *, theta0: float) -> float:
    """WSR betting e-value for H0: E[W_i - theta0 | history] <= 0 over W_i in [-1,1], in
    committed order (NO permutation). Valid by Ville (positive factors)."""
    arr = np.asarray(w, dtype=float)
    if arr.size == 0:
        raise ValueError("paired_advantage_evalue: empty stream")
    if np.any(arr < -1.0) or np.any(arr > 1.0):
        raise ValueError("increments must lie in [-1, 1]")
    W = arr - float(theta0)
    lam_max = _C / (1.0 + abs(float(theta0)))   # positivity cap for support [-1-θ0, 1-θ0]
    return _grapa_capital(W, lam_max)
```
- [ ] **Step 4:** rerun → PASS.
- [ ] **Step 5: commit** `git add -A && git commit -m "feat(capability): paired-advantage betting e-value (committed order)"`

### Task 2: PredictionVector + Scorer (label-withholding)

**Files:** Modify `benchmark_evidence.py`; Test `tests/capability/test_benchmark_scorer.py`

**Interfaces:** `PredictionVector(predictions: tuple[tuple[str,str],...])`; `score_advantage(model: PredictionVector, baseline: PredictionVector, labels: Mapping[str,str], order: Sequence[str]) -> list[float]` (Wᵢ in order); `ScoringError(ValueError)`. Missing/dup/extra/order-mismatch → `ScoringError`.

- [ ] **Step 1: failing test** (assert paired Wᵢ in order `[0,1,1]` for a 3/3 model vs 1/3 baseline; missing id → `ScoringError`; duplicate id → `ScoringError`).
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: implement** `PredictionVector` (frozen dataclass with `as_map()` raising `ScoringError` on dup), `score_advantage` (validate both prediction sets' ids == `set(order)`; compute `float(m[e]==labels[e]) - float(b[e]==labels[e])`).
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5: commit** `"feat(capability): PredictionVector + label-withholding scorer"`

### Task 3: BenchmarkArtifact (content-addressed) + BenchmarkAdapter + fixture predictors

**Files:** Create `src/polymer_claims/benchmark_adapter.py`; Test `tests/capability/test_benchmark_adapter.py`

**Interfaces:**
- `BenchmarkExample(example_id: str, features: tuple[tuple[str,str],...])` (no label field).
- `BenchmarkArtifact` frozen: `example_ids: tuple[str,...]`, `features: tuple[...]`, `labels: tuple[tuple[str,str],...]`, `target_population: str`, `sampling_regime: str`, `version: str`, `sampling_seed: int`, `dgp_digest: str`; `content_hash` property via `canonical_sha256` (`_hashing.py`); `ref` = `"bench:" + content_hash`.
- `BenchmarkAdapter` Protocol: `identity: str`, `config: dict`, `predict(examples: Sequence[BenchmarkExample]) -> PredictionVector` (NO labels).
- Fixture `FixtureModelAdapter`, `FixtureBaselineAdapter` (deterministic, label-independent seed).

- [ ] **Step 1: failing test** — `predict` signature has no `labels` param (audit #20); two artifacts with different labels have different `content_hash`; `ref` starts `bench:`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: implement** per interfaces; `content_hash = canonical_sha256(self.model_dump(mode="json"))` (artifact is a frozen `_Model`-style dataclass or a pydantic model in the umbrella).
- [ ] **Step 4:** run → PASS; `uv run ruff check src tests`.
- [ ] **Step 5: commit** `"feat(capability): content-addressed BenchmarkArtifact + label-free adapters"`

### Task 4: Grammar — `SamplingRegime` + `DataRefKind.BENCHMARK`

**Files:** Modify `grammar/src/polymer_grammar/{operations.py (DataRefKind + bench: matcher), __init__.py}`; Create `grammar/src/polymer_grammar/sampling.py` (`SamplingRegime`); Test `grammar/tests/test_sampling_and_dataref.py`

- [ ] **Step 1: failing test** — `SamplingRegime.IID_EXAMPLES.value == "iid_examples"`; a `DataRefKind.BENCHMARK` matcher accepts `"bench:<hex>"` and rejects `"se:x@1"`/`"opaque"`.
- [ ] **Step 2–4:** implement enum + extend the data-ref matcher for the `bench:` form (mirror the existing `se:`/OPAQUE matchers); run → PASS; grammar suite green.
- [ ] **Step 5: commit** `"feat(grammar): SamplingRegime + DataRefKind.BENCHMARK"`

### Task 5: Grammar — `EvidencePolicy` (+registry, content_hash, validators)

**Files:** Create `grammar/src/polymer_grammar/evidence_policy.py`; Modify `__init__.py`; Test `grammar/tests/test_evidence_policy.py`

**Interfaces:** `EvidencePolicy(_Model)` fields per spec §4 (incl. `baseline_config_ref`, `predictor_config_ref`, `executor_descriptor_ref`); `content_hash` `@property` via the grammar `_sha` helper over a canonical dict of fields; `ref` returns it. Validators: non-empty ids/refs; `0 <= theta0 < 1`; `null_family`↔`evalue_transform` compatible. `EvidencePolicyRegistry(_Model){policies: tuple[...]; resolve(ref) -> EvidencePolicy | None}` (recompute hash).

- [ ] **Step 1: failing test** — `ref == content_hash`; registry `resolve` round-trips; `theta0=1.0` → `ValidationError`; `theta0=-0.1` → error; changing `baseline_config_ref` changes `ref`.
- [ ] **Step 2:** run → FAIL (`cd grammar && uv run pytest tests/test_evidence_policy.py -q`).
- [ ] **Step 3: implement.** Import base via `from .base import _Model`; reuse the package's `_sha` (grep `def _sha` in `operations.py`) for `content_hash`.
- [ ] **Step 4:** run → PASS; grammar suite + isolation green.
- [ ] **Step 5: commit** `"feat(grammar): content-addressed EvidencePolicy + registry + validators"`

### Task 6: Grammar — `ExecutorDescriptor` / `ExecutorTrustEntry` (+registries, validators)

**Files:** Create `grammar/src/polymer_grammar/executor_credential.py`; Modify `__init__.py`; Test `grammar/tests/test_executor_credential.py`

**Interfaces:** `Component(_Model){role: Literal["predictor","baseline_predictor","scorer","evidence_transform"], identity, implementation_hash, config_hash}`; `ExecutorDescriptor(_Model){components: tuple[Component,...], version}` + `content_hash` property; validators (audit #15): exactly one of each role, canonical role order, unique identities, non-empty `sha256:`-prefixed hashes. `ExecutorTrustEntry(_Model){descriptor_ref, owner, trusted: bool, version}`; `ExecutorTrustRegistry(_Model){entries: tuple[...]; resolve(descriptor_ref) -> ExecutorTrustEntry | None}`.

- [ ] **Step 1: failing test** — valid descriptor has stable `content_hash`; missing the baseline role → `ValidationError`; wrong role order → error; duplicate identity → error; non-`sha256:` hash → error; trust registry resolves by `descriptor_ref`.
- [ ] **Step 2–4:** implement + validators; run → PASS; grammar suite green.
- [ ] **Step 5: commit** `"feat(grammar): ExecutorDescriptor (content) + ExecutorTrustEntry (trust) split"`

### Task 7: Grammar — `VerificationPolicy`, `ExecutionContract`, `EvidenceProvenance`, `EvidenceLicensingInfo`

**Files:** Create `grammar/src/polymer_grammar/verification_policy.py`; Modify `__init__.py`; Test `grammar/tests/test_verification_policy.py`

**Interfaces:**
- `VerificationPolicy(_Model){execution: Literal["recompute_pair","single"]="recompute_pair", result_rule: Literal["criterion","evalue_discovery"]="criterion", independence_requirement: Literal["implementation","baseline_ground_truth"]="implementation", evidence_policy_ref: str|None=None, min_adapters: int=2}`; validator `single` ⇒ `evidence_policy_ref` set ∧ `min_adapters==1`.
- `ExecutionContract(_Model){capability_id, capability_version, evidence_policy_ref, capability_descriptor_ref}`.
- `EvidenceProvenance(_Model)` per spec §4 (all refs + `observed_advantage`, `theta0`, `e_value`, `execution_contract_digest`, `fdr_test_index`, `alpha_allocated`).
- `EvidenceLicensingInfo(_Model){route: LicenseRoute, verification_standing: str, evidence_provenance: EvidenceProvenance}`.

- [ ] **Step 1: failing test** — `single` policy without `evidence_policy_ref` → error; `recompute_pair` default round-trips; `EvidenceProvenance`/`ExecutionContract` construct + round-trip.
- [ ] **Step 2–4:** implement; run → PASS; grammar suite + isolation green (no numpy).
- [ ] **Step 5: commit** `"feat(grammar): VerificationPolicy + ExecutionContract + EvidenceProvenance + LicensingInfo"`

### Task 8: Grammar — `Licensing` route/standing/provenance + `PendingReason.EXECUTION_ERROR`

**Files:** Modify `grammar/src/polymer_grammar/{licensing.py, status.py}`; Test `grammar/tests/test_licensing_evidence_route.py`

**Interfaces:** `LicenseRoute.EVIDENCE_LICENSED="evidence_licensed"`; `Licensing.independence_tier: IndependenceTier | None = IndependenceTier.REPRODUCED` (default unchanged); `Licensing.verification_standing: Literal["single_source_baseline"] | None = None`; `Licensing.evidence_provenance: EvidenceProvenance | None = None`; validator: standing/provenance non-None **iff** `route==EVIDENCE_LICENSED`. `PendingReason.EXECUTION_ERROR="execution_error"`.

- [ ] **Step 1: failing test** — evidence-route `Licensing` with standing+provenance + `independence_tier=None` round-trips; standing on a `SEVERE_TEST` route → error; `Licensing(satisfactions=())` still rejected (`_all_satisfied`); `PendingReason.EXECUTION_ERROR` exists.
- [ ] **Step 2–4:** implement; run → PASS; full grammar suite green.
- [ ] **Step 5: commit** `"feat(grammar): EVIDENCE_LICENSED route + standing + provenance + EXECUTION_ERROR"`

### Task 9: Grammar — `CapabilityCell.content_hash` + optional `verification_policy`; `min_executing_adapters` migration

**Files:** Modify `grammar/src/polymer_grammar/capability.py`; Test `grammar/tests/test_capability_descriptors.py`

**Interfaces:** add `CapabilityCell.content_hash` `@property`; add optional `verification_policy: VerificationPolicy | None = None`; relax the cardinality validator: `verification_policy is None` or `execution=="recompute_pair"` ⇒ require `min_executing_adapters == 2`; `execution=="single"` ⇒ `== 1`.

- [ ] **Step 1: failing test** — the three existing cells (None policy, `min=2`) stay valid + their `content_hash` is stable; a `single`-policy cell with `min_executing_adapters=2` → error; with `=1` → valid.
- [ ] **Step 2–4:** implement (None-omit serializer for `verification_policy` comes in Task 18); run → PASS; full grammar suite green.
- [ ] **Step 5: commit** `"feat(grammar): CapabilityCell content_hash + optional VerificationPolicy + cardinality migration"`

### Task 10: Grammar — optional `EvaluationPlan.execution_contract`

**Files:** Modify `grammar/src/polymer_grammar/operations.py`; Test `grammar/tests/test_operations_contract.py`

**Interfaces:** `EvaluationPlan.execution_contract: ExecutionContract | None = None` (on the plan, NOT the graph). None-omit serializer in Task 18.

- [ ] **Step 1: failing test** — a plan with `execution_contract` round-trips; an existing plan without one is unchanged; **`ComputeGraph.content_hash` is unaffected** by adding the field (assert two graphs equal hash regardless of plan-level contract).
- [ ] **Step 2–4:** implement; run → PASS; grammar suite green.
- [ ] **Step 5: commit** `"feat(grammar): optional EvaluationPlan.execution_contract"`

### Task 11: Protocol — `EvidenceExecutor` protocol + `EvidenceExecution` + `ExecutionFailure`

**Files:** Create `protocol/src/polymer_protocol/evidence_executor.py`; Modify `__init__.py`; Test `protocol/tests/test_evidence_executor_types.py`

**Interfaces:**
```python
class ExecutionFailure(_Model):
    reason: Literal["empty","malformed","duplicate","missing","order_mismatch",
                    "credential_mismatch","digest_mismatch"]
    detail: str = ""
class EvidenceExecution(_Model):
    record: ExecRecord
    e_value: float | None = None
    licensing_info: EvidenceLicensingInfo | None = None
    failure_reason: ExecutionFailure | None = None
class EvidenceExecutor(Protocol):
    def credential(self) -> str: ...
    def execute(self, claim, cell, policy, benchmark_artifact, ctx, fdr_test) -> EvidenceExecution: ...
```

- [ ] **Step 1: failing test** — construct an `EvidenceExecution` wrapping an `ExecRecord`; a trivial stub satisfying `EvidenceExecutor` (grammar/protocol DTOs only, no umbrella import) returns one. Confirms protocol-test purity (audit #14).
- [ ] **Step 2–4:** implement; run → PASS (`cd protocol && uv run pytest -q`); isolation green.
- [ ] **Step 5: commit** `"feat(protocol): EvidenceExecutor protocol + EvidenceExecution + ExecutionFailure"`

### Task 12: Umbrella — `EvidenceExecutor` implementation + hash-chain checks

**Files:** Create `src/polymer_claims/benchmark_capability.py`; Test `tests/capability/test_benchmark_executor.py`

**Interfaces:** `BenchmarkEvidenceExecutor` implementing the protocol: owns `predictor`, `baseline_predictor`, `scorer`, `evidence_transform`(=`paired_advantage_evalue`); `credential()` recomputes the live `ExecutorDescriptor.content_hash` from component impl+config hashes; `execute(...)` runs Layer-3 link checks, scores `Wᵢ`, computes the e-value, builds `EvidenceProvenance` + `EvidenceLicensingInfo`, returns `EvidenceExecution`. Structural failures → `failure_reason` + `e_value=None`. **No outcome filtering.**

- [ ] **Step 1: failing test** — a strong fixture → `EvidenceExecution` with `e_value > 32.9`, `licensing_info.route == EVIDENCE_LICENSED`, provenance populated, record verdict `UNDETERMINED`; a tampered benchmark digest → `failure_reason="digest_mismatch"`, `e_value=None`; `credential()` matches the registered descriptor and changes when the **baseline** swaps.
- [ ] **Step 2–4:** implement; run → PASS; `uv run ruff check src tests`.
- [ ] **Step 5: commit** `"feat(capability): umbrella EvidenceExecutor + hash-chain verification"`

---

## Phase 1b — protocol dispatch + end-to-end

### Task 13: Protocol — thread executor + registry through `run_cycle`; gate evidence claims out of two-adapter `verify()`

**Files:** Modify `protocol/src/polymer_protocol/cycle.py`; Test `protocol/tests/test_evidence_dispatch.py`

**Interfaces:** `run_cycle(..., evidence_executor: EvidenceExecutor | None = None, capability_registry: CapabilityRegistry | None = None)`; forward both into `execute_ground`; exclude evidence-claim ids from the two-adapter set.

- [ ] **Step 1: failing test** — a cycle with one evidence claim + an injected stub executor does **not** raise (the claim is not sent to two-adapter `verify()`); a non-evidence cycle with both params `None` is byte-identical to today.
- [ ] **Step 2–4:** implement signature + pass-through; run → PASS; full protocol suite green.
- [ ] **Step 5: commit** `"feat(protocol): thread evidence_executor + capability_registry through run_cycle"`

### Task 14: Protocol — `execute_ground` dispatch branch + precondition + return `evidence_executions`

**Files:** Modify `protocol/src/polymer_protocol/execute.py`; Test `protocol/tests/test_evidence_dispatch.py`

**Interfaces:** `execute_ground(...) -> (Corpus, tuple[ExecRecord,...], tuple[EvidenceExecution,...])`. For a claim whose resolved cell is `execution=="single"`, passing §2.2 precondition (`selected ∧ committed ∧ pending registered test ∧ commitment matches`) + claim-shape conformance + the dispatch-time hash-chain + `credential()` compare: call `evidence_executor.execute(...)`, append its `record` to records and the `EvidenceExecution` to a new list; on precondition/chain failure → refuse (no dispatch). Non-evidence claims unchanged.

- [ ] **Step 1: failing test** — evidence claim with a pending registered test → produces an `EvidenceExecution` + an `ExecRecord`; an **unregistered** evidence claim is refused (not executed); an in-cycle-GENERATE'd evidence claim is not executed.
- [ ] **Step 2–4:** implement; run → PASS; protocol suite green.
- [ ] **Step 5: commit** `"feat(protocol): execute_ground evidence dispatch + locked-slot precondition"`

### Task 15: Protocol — `verify_stage` evidence-route block (license-on-discovery; EXECUTION_ERROR; fall-through)

**Files:** Modify `protocol/src/polymer_protocol/verify.py`; Test `protocol/tests/test_evidence_dispatch.py`

**Interfaces:** `verify_stage(..., evidence_licensing: dict[str, EvidenceLicensingInfo] | None = None, evidence_failures: dict[str, ExecutionFailure] | None = None)`. For an evidence claim: (a) if in `evidence_failures` → `_with_status(PENDING, EXECUTION_ERROR)`; (b) elif e-LOND discovery (`_e_ok` true after Phase-D resolution) **and** eligible (`c.id in in_ext`, provenance present, not altered, status PENDING) → mint `Satisfaction(SATISFIED, materialization, credential_ids=(descriptor_ref,))` + `Licensing(EVIDENCE_LICENSED, independence_tier=None, verification_standing, evidence_provenance)` → LICENSED; (c) else **fall through** to the existing per-claim branches (grounded-out → REJECTED `DEFEAT_GROUNDED_OUT`, altered → REJECTED `HYPOTHESIS_ALTERED`, else passthrough PENDING). Skip the independent-pair gate for evidence claims.

- [ ] **Step 1: failing tests** — discovery+eligible → LICENSED (route/standing/`independence_tier=None`/provenance.e_value == ledger); **discovered but non-grounded → REJECTED `DEFEAT_GROUNDED_OUT`** (audit #5, not PENDING); sub-threshold → PENDING (not REFUTED); failure → PENDING `EXECUTION_ERROR`.
- [ ] **Step 2–4:** implement; run → PASS; **full protocol suite green** (inert when both dicts `None`).
- [ ] **Step 5: commit** `"feat(protocol): verify_stage evidence-route licensing block (discovery=decision)"`

### Task 16: Umbrella — register cell + `_bindings()` + `validate_trust_binding` single-mode

**Files:** Modify `src/polymer_claims/capabilities.py`; Test `tests/capability/test_cells.py`, `tests/capability/test_binding.py`

**Interfaces:** add `EVAL_BENCHMARK_ADVANTAGE_CELL` (the §5 descriptor) to `CAPABILITY_CELLS`; add a `_bindings()` entry whose `CapabilityTrustBinding` gains an `executor_trust_registry: ExecutorTrustRegistry` field; `validate_trust_binding(cell, adapter_registry, oracle_registry, *, evidence_policy_registry=None, executor_trust_registry=None)` single-mode branch: skip pair requirement; require `EvidencePolicy` resolvable+digest-verified and `ExecutorTrustEntry` resolvable+`trusted`; unbounded oracle apparatus.

- [ ] **Step 1: failing tests** — `CAPABILITY_CELLS.resolve("eval::benchmark_advantage","v1")` is `single`; `validate_trust_binding` passes with one credential + a trusted descriptor; an **untrusted** entry fails; the three existing cells still require the pair.
- [ ] **Step 2–4:** implement (`CapabilityTrustBinding` gains the field — additive); run → PASS.
- [ ] **Step 5: commit** `"feat(capability): register eval::benchmark_advantage + single-mode trust binding"`

### Task 17: Powered fixture

**Files:** Create `data/demo/benchmark_advantage_fixture.json`; `src/polymer_claims/_fixtures/benchmark_dgp.py` (generator); Test `tests/capability/test_benchmark_fixture.py`

**Interfaces:** a generator with a declared feature-dependent DGP `y=f(features)⊕noise`, a fixed model rule + weaker baseline, a **predeclared** `n` chosen for `P_alt(E≥1/α)≥0.8`, and the **first fixed seed**. Emits a `BenchmarkArtifact` JSON (with `sampling_seed` + `dgp_digest`).

- [ ] **Step 1: failing test** — load the fixture; compute `Wᵢ` via the scorer; assert `paired_advantage_evalue(W, theta0=τ) ≥ 32.9` (α₁) AND document the power target in the test; assert labels are independent of the model rule's seed.
- [ ] **Step 2–4:** generate the fixture with one predeclared `n`/seed (escalate `n` only via the predeclared schedule if needed — never seed-search); run → PASS.
- [ ] **Step 5: commit** `"test(capability): powered benchmark fixture (declared power target, first seed)"`

### Task 18: Compatibility — `model_serializer` None-omission + golden battery

**Files:** Modify `grammar/src/polymer_grammar/{licensing.py, capability.py, operations.py}`; Test `grammar/tests/test_compat_serialization.py`, `tests/attestation/test_golden_unchanged.py`

**Interfaces:** add `@model_serializer(mode="wrap")` to `Licensing`, `CapabilityCell`, `EvaluationPlan` that calls the handler then pops `verification_standing`/`evidence_provenance` / `verification_policy` / `execution_contract` when `None`.

- [ ] **Step 1: failing tests (the hard gate)** — for each model: None → key absent in `model_dump`/`model_dump_json`; set → present; **historical JSON lacking the field deserializes**; a `ComputeGraph.content_hash` / `commitment_hash` over an existing plan is unchanged; **`tests/attestation/_golden_bundle.json` subject digests (`fb81e5a2…`, `2426880d…`) are byte-identical**; the three existing cells' `model_dump_json` unchanged; JSON-schema generation succeeds; nested round-trip holds.
- [ ] **Step 2–4:** implement the three serializers; run → PASS (this proves "no golden re-bless").
- [ ] **Step 5: commit** `"feat(grammar): None-omit model_serializers preserve existing digests (no re-bless)"`

### Task 19: End-to-end + defeat-semantics + bookkeeping + final gate

**Files:** Test `tests/capability/test_benchmark_end_to_end.py`; Modify `data`/wiring as needed

- [ ] **Step 1: failing tests** — full pipeline (`register_hypotheses` → `run_cycle(..., evidence_executor=BenchmarkEvidenceExecutor(...), capability_registry=CAPABILITY_CELLS, ...)`) on the powered fixture: claim LICENSED, `route=EVIDENCE_LICENSED`, `independence_tier=None`, standing literal, `evidence_provenance.e_value == registered FDRTest.e_value`, `e_value ≥ 1/alpha_allocated`. **Defeat semantics:** a non-grounded discovered claim → REJECTED `DEFEAT_GROUNDED_OUT`; an altered-plan claim → REJECTED `HYPOTHESIS_ALTERED`; sub-threshold → PENDING. **Bookkeeping:** the claim appears in `executed_ids`, the verify stage-audit counts, the selection-ledger outcome, and Goodhart credit; a failure leaves the registered test unresolved (α consumed); retry under the identical `(commitment, index, α, contract digest)` permitted, varied contract trips `HYPOTHESIS_ALTERED`. **BH exemption** documented.
- [ ] **Step 2–4:** make them pass.
- [ ] **Step 5: final gate** — `scripts/check-all.sh` ALL GREEN (grammar + protocol + umbrella + ruff + isolation; viewer unaffected); commit `"test(capability): end-to-end evidence license + defeat semantics + bookkeeping"`

---

## Self-review (spec → task coverage)

§2 architecture → 11,13,14,15. §3 statistics → 1,17. §4 objects/modules/executor/chain → 5,6,7,11,12. §5 descriptor → 9,16. §6 three-layer binding → 12,16. §7 lifecycle/status → 8,15,19. §8 schema+compat → 4,8,9,10,18. §9 fixture → 17. §10 tests → every task + 19. §11 acceptance → 16,18,19. §12 audit-7 map → 6 (trust split), 7 (result_rule via cell in 16), 15 (status), 18 (serializer), 17 (fixture).

**Type-consistency check:** `executor_descriptor_ref` (not `executor_credential_ref`) used in Tasks 5,7,12,15. `paired_advantage_evalue(w, *, theta0)` consistent in 1,12,17. `EvidenceExecution`/`EvidenceExecutor` in protocol (11) consumed by 13,14,15. `validate_trust_binding` extra params keyword-only, consistent in 16.

## Optional internal split

- **1a = Tasks 1–12** (pure objects + umbrella primitives + executor impl; no protocol dispatch; licenses nothing; fully unit-tested) — mergeable alone.
- **1b = Tasks 13–19** (dispatch + verify block + cell registration + fixture + compat goldens + end-to-end).

## Execution

`subagent-driven-development` (fresh subagent per task + two-stage review) → whole-branch review → merge `--no-ff` → update `CONTINUE.md` + memory.
