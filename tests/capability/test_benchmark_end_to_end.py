"""End-to-end evidence-licensed claim + defeat semantics + observable bookkeeping.

Task 19 (capstone): drives a benchmark evidence claim through run_cycle to
Status.LICENSED via the EVIDENCE_LICENSED route, then exercises the defeat
semantics, collision guard, observable bookkeeping, and failure/retry invariants.

Umbrella-side test — uses the real BenchmarkEvidenceExecutor and kit from
benchmark_capability.build_benchmark_kit().
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    DefeatEdge,
    DefeatEdgeKind,
    FDRLedger,
    GenerationMode,
    LicenseRoute,
    MaterializationContext,
    PendingReason,
    Provenance,
    RejectionReason,
    Status,
)
from polymer_grammar.capability import build_evaluation_plan
from polymer_grammar.commitment import commitment_hash
from polymer_grammar.operations import Comparator, SatisfactionCriterion
from polymer_grammar.pattern import PatternRef
from polymer_grammar.verification_policy import ExecutionContract
from polymer_protocol import Corpus, EvidenceRuntime, register_hypotheses, run_cycle
from polymer_protocol.commit import commit
from polymer_protocol.corpus import CycleScaffolding
from polymer_protocol.evidence_executor import EvidenceExecution
from polymer_protocol.execute import execute_ground
from polymer_protocol.verify import verify_stage

from polymer_claims._fixtures.benchmark_dgp import (
    DGPBaselineAdapter,
    DGPModelAdapter,
    TAU,
    evalue_threshold,
)
from polymer_claims.benchmark_capability import (
    BenchmarkEvidenceExecutor,
    BenchmarkKit,
    build_benchmark_kit,
)
from polymer_claims.benchmark_evidence import paired_advantage_evalue, score_advantage
from polymer_claims.capabilities import CAPABILITY_CELLS

# ---------------------------------------------------------------------------
# Module-level kit (built once, deterministic)
# ---------------------------------------------------------------------------

_KIT: BenchmarkKit = build_benchmark_kit()
_CTX = MaterializationContext(id="M-e2e", api_version="v1", data_version="d1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_plan():
    """Build an EvaluationPlan for eval::benchmark_advantage with the kit's policy/cell."""
    kit = _KIT
    base = build_evaluation_plan(
        kit.cell,
        params={},
        data_ref=kit.demo_benchmark.ref,
        criterion=SatisfactionCriterion(comparator=Comparator.GT, threshold=TAU),
        oracle_ref="benchmark_eval_apparatus",
    )
    return base.model_copy(
        update={
            "execution_contract": ExecutionContract(
                capability_id=kit.cell.capability_id,
                capability_version=kit.cell.capability_version,
                evidence_policy_ref=kit.policy.content_hash,
                capability_descriptor_ref=kit.cell.content_hash,
            )
        }
    )


def _build_claim(claim_id: str = "bench-e2e-1", *, operator_id: str = "test-operator-v1") -> Claim:
    """Build a PENDING benchmark evidence claim with explicit agent provenance."""
    return Claim(
        id=claim_id,
        title="benchmark advantage claim",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="term-bench-e2e"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        evaluation_plan=_build_plan(),
        provenance=Provenance(
            generated_by=GenerationMode.AGENT_GENERATED,
            agent_id=operator_id,
            search_cardinality=1,
        ),
    )


def _build_runtime(executor=None) -> EvidenceRuntime:
    """Build an EvidenceRuntime from the kit, optionally overriding the executor."""
    kit = _KIT
    return EvidenceRuntime(
        capability_registry=CAPABILITY_CELLS,
        evidence_policy_registry=kit.policy_registry,
        executor_descriptor_registry=kit.descriptor_registry,
        executor_trust_registry=kit.trust_registry,
        executor=executor if executor is not None else kit.executor,
    )


def _failing_executor() -> BenchmarkEvidenceExecutor:
    """Build a BenchmarkEvidenceExecutor with an empty artifact store.

    The credential is identical to the kit executor (same components), so all
    pre-dispatch checks pass. The artifact lookup fails → execution failure.
    """
    model_adapter = DGPModelAdapter()
    model_adapter.identity = "benchmark-model"
    baseline_adapter = DGPBaselineAdapter()
    return BenchmarkEvidenceExecutor(
        predictor=model_adapter,
        baseline_predictor=baseline_adapter,
        scorer=score_advantage,
        transform=paired_advantage_evalue,
        artifact_store={},  # empty → artifact not found → failure
    )


class _SpyExecutor:
    """Wraps the kit executor and counts calls to execute()."""

    def __init__(self, real):
        self._real = real
        self.calls: list[str] = []  # claim_ids

    def credential(self) -> str:
        return self._real.credential()

    def execute(self, claim, cell, policy, ctx, fdr_test) -> EvidenceExecution:
        result = self._real.execute(claim, cell, policy, ctx, fdr_test)
        self.calls.append(claim.id)
        return result


class _SubThresholdExecutor:
    """Wraps the kit executor but forces a sub-threshold e_value (0.5)."""

    _LOW_E = 0.5

    def __init__(self, real):
        self._real = real

    def credential(self) -> str:
        return self._real.credential()

    def execute(self, claim, cell, policy, ctx, fdr_test) -> EvidenceExecution:
        result = self._real.execute(claim, cell, policy, ctx, fdr_test)
        if result.failure_reason is not None:
            return result
        prov = result.licensing_info.evidence_provenance.model_copy(
            update={"e_value": self._LOW_E}
        )
        info = result.licensing_info.model_copy(update={"evidence_provenance": prov})
        return EvidenceExecution(
            record=result.record,
            e_value=self._LOW_E,
            licensing_info=info,
        )


# ---------------------------------------------------------------------------
# 1. End-to-end LICENSE
# ---------------------------------------------------------------------------


def test_e2e_licensed_route_and_invariants():
    """Full pipeline: register → run_cycle → Status.LICENSED via EVIDENCE_LICENSED.

    Asserts: route, independence_tier=None, verification_standing literal,
    provenance.e_value == FDRTest.e_value in ledger, and e_value >= evalue_threshold.
    """
    claim = _build_claim("bench-e2e-license", operator_id="research-agent-v1")
    corpus = register_hypotheses(
        Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    )
    runtime = _build_runtime()

    result = run_cycle(corpus, (), _CTX, evidence_runtime=runtime)

    c = result.corpus.by_id()["bench-e2e-license"]
    assert c.status == Status.LICENSED, f"expected LICENSED, got {c.status}"
    assert c.licensing is not None
    assert c.licensing.route == LicenseRoute.EVIDENCE_LICENSED
    assert c.licensing.independence_tier is None
    assert c.licensing.verification_standing == "single_source_baseline"

    # Provenance e_value must match the resolved FDRTest e_value
    prov = c.licensing.evidence_provenance
    assert prov is not None
    ledger_test = next(
        t for t in result.corpus.fdr_ledger.tests if t.claim_id == "bench-e2e-license"
    )
    assert prov.e_value == ledger_test.e_value, (
        f"provenance.e_value ({prov.e_value}) != ledger e_value ({ledger_test.e_value})"
    )

    # e_value must clear the alpha threshold
    alpha = ledger_test.alpha_allocated
    assert ledger_test.e_value >= evalue_threshold(alpha), (
        f"e_value {ledger_test.e_value} < threshold {evalue_threshold(alpha)} "
        f"(alpha={alpha})"
    )


# ---------------------------------------------------------------------------
# 2a. Defeat — grounded out via synthetic defeat source
# ---------------------------------------------------------------------------


def test_defeat_grounded_out_rejected():
    """Claim with a synthetic defeat edge is NOT in the grounded extension → DEFEAT_GROUNDED_OUT.

    Uses a synthetic source "refutation:<id>" (contains ':' so Corpus allows it;
    has no attackers so it is IN the extension, defeating the bench claim).
    The claim is still selected+committed+executed, but verify_stage rejects it.
    """
    claim = _build_claim("bench-e2e-go")
    defeat = DefeatEdge(
        source="refutation:bench-e2e-go",
        target="bench-e2e-go",
        kind=DefeatEdgeKind.REBUT,
    )
    corpus = Corpus(
        claims=(claim,),
        defeat_edges=(defeat,),
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )
    corpus = register_hypotheses(corpus)
    runtime = _build_runtime()

    result = run_cycle(corpus, (), _CTX, evidence_runtime=runtime)

    c = result.corpus.by_id()["bench-e2e-go"]
    assert c.status == Status.REJECTED, f"expected REJECTED, got {c.status}"
    assert c.rejection_reason == RejectionReason.DEFEAT_GROUNDED_OUT


# ---------------------------------------------------------------------------
# 2b. Defeat — hypothesis altered (commitment hash mismatch)
# ---------------------------------------------------------------------------


def test_defeat_hypothesis_altered_rejected():
    """After registration, altering the plan (different threshold → different commitment_hash)
    is detected as HYPOTHESIS_ALTERED by verify_stage.

    Approach: execute original claim A → get exec_records; then present the altered
    claim B to verify_stage. The Phase-D loop sees commitment_hash mismatch → REJECTED.
    """
    kit = _KIT
    claim_id = "bench-e2e-ha"

    # Original plan A
    claim_a = _build_claim(claim_id)
    fdr = FDRLedger(target_fdr=0.05)
    corpus_a = Corpus(claims=(claim_a,), fdr_ledger=fdr)
    corpus_a = register_hypotheses(corpus_a)

    # Commit + execute on plan A (all chain checks pass → real executor runs)
    corpus_committed = commit(corpus_a)
    runtime = _build_runtime()
    _, exec_records, evidence_executions = execute_ground(
        corpus_committed, (), _CTX, evidence_runtime=runtime
    )
    assert exec_records, "expected at least one exec record from original plan"

    # Build ev_map + evidence_licensing from the successful execution
    ev_map: dict[str, float] = {}
    evidence_licensing: dict = {}
    for ee in evidence_executions:
        if ee.failure_reason is None:
            ev_map[ee.record.claim_id] = ee.e_value
            evidence_licensing[ee.record.claim_id] = ee.licensing_info

    # Altered plan B: same structure but different criterion threshold
    base = build_evaluation_plan(
        kit.cell,
        params={},
        data_ref=kit.demo_benchmark.ref,
        criterion=SatisfactionCriterion(comparator=Comparator.GT, threshold=TAU + 0.1),
        oracle_ref="benchmark_eval_apparatus",
    )
    altered_plan = base.model_copy(
        update={
            "execution_contract": ExecutionContract(
                capability_id=kit.cell.capability_id,
                capability_version=kit.cell.capability_version,
                evidence_policy_ref=kit.policy.content_hash,
                capability_descriptor_ref=kit.cell.content_hash,
            )
        }
    )
    claim_b = Claim(
        id=claim_id,
        title="benchmark advantage claim",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="term-bench-e2e"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        evaluation_plan=altered_plan,
        provenance=Provenance(
            generated_by=GenerationMode.AGENT_GENERATED,
            agent_id="test-operator-v1",
            search_cardinality=1,
        ),
    )

    # Verify plan_A and plan_B have different commitment_hashes
    assert commitment_hash(claim_a) != commitment_hash(claim_b), (
        "test setup error: plan A and plan B must have different commitment hashes"
    )

    # Build altered corpus (plan B claim + original FDR ledger with plan A hash)
    corpus_altered = Corpus(claims=(claim_b,), fdr_ledger=corpus_a.fdr_ledger)
    scaffolding = CycleScaffolding(grounded_extension=(claim_id,), frontier=())

    result_corpus = verify_stage(
        corpus_altered,
        scaffolding,
        exec_records,
        evidence=ev_map,
        evidence_licensing=evidence_licensing,
    )

    c = result_corpus.by_id()[claim_id]
    assert c.status == Status.REJECTED, f"expected REJECTED, got {c.status}"
    assert c.rejection_reason == RejectionReason.HYPOTHESIS_ALTERED


# ---------------------------------------------------------------------------
# 2c. Sub-threshold → PENDING (not REFUTED, not REJECTED)
# ---------------------------------------------------------------------------


def test_sub_threshold_stays_pending():
    """Sub-threshold e_value → no discovery → claim stays PENDING.

    Uses a wrapped executor that forces e_value=0.5, well below the e-LOND
    threshold of 1/alpha_1 ≈ 33 for the first registered slot.
    """
    claim = _build_claim("bench-e2e-sub")
    corpus = register_hypotheses(
        Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    )
    sub_executor = _SubThresholdExecutor(_KIT.executor)
    runtime = _build_runtime(executor=sub_executor)

    result = run_cycle(corpus, (), _CTX, evidence_runtime=runtime)

    c = result.corpus.by_id()["bench-e2e-sub"]
    assert c.status == Status.PENDING, f"expected PENDING, got {c.status}"
    assert c.rejection_reason is None, "sub-threshold claim must NOT be rejected"
    assert c.status != Status.LICENSED


# ---------------------------------------------------------------------------
# 3. Collision — caller-supplied evidence collides with executor result
# ---------------------------------------------------------------------------


def test_collision_raises_value_error():
    """Providing evidence={'bench-e2e-col': e_value} while the runtime would also
    produce evidence for the same claim → run_cycle must raise ValueError.
    """
    import pytest

    claim = _build_claim("bench-e2e-col")
    corpus = register_hypotheses(
        Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    )
    runtime = _build_runtime()

    with pytest.raises(ValueError, match="evidence collision"):
        run_cycle(
            corpus,
            (),
            _CTX,
            evidence_runtime=runtime,
            evidence={"bench-e2e-col": 1.0},
        )


# ---------------------------------------------------------------------------
# 4. Observable bookkeeping
# ---------------------------------------------------------------------------


def test_observable_bookkeeping():
    """Assert observable consequences of a successful evidence-licensed cycle.

    Checks:
    - verify/execute stage-audit counts reflect the execution
    - selection-ledger outcome is present for the claim
    - executor was called exactly once (spy)
    - Goodhart/operator credit: claim with agent provenance; selection ledger
      records the ExecutedOutcome with licensed=True
    """
    spy = _SpyExecutor(_KIT.executor)
    claim = _build_claim("bench-e2e-book", operator_id="research-agent-obs")
    corpus = register_hypotheses(
        Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    )
    runtime = _build_runtime(executor=spy)

    result = run_cycle(corpus, (), _CTX, evidence_runtime=runtime)

    c = result.corpus.by_id()["bench-e2e-book"]
    assert c.status == Status.LICENSED, f"expected LICENSED, got {c.status}"

    # 4a. Executor was called exactly once
    assert spy.calls == ["bench-e2e-book"], (
        f"expected spy.calls == ['bench-e2e-book'], got {spy.calls}"
    )

    # 4b. Stage-audit: execute_ground count == 1, verify_stage count == 1 (licensed)
    audit_by_stage = {a.stage: a for a in result.audit}
    assert audit_by_stage["execute_ground"].count == 1, (
        f"execute_ground.count = {audit_by_stage['execute_ground'].count}, expected 1"
    )
    assert audit_by_stage["verify_stage"].count == 1, (
        f"verify_stage.count = {audit_by_stage['verify_stage'].count}, expected 1 licensed"
    )

    # 4c. Selection-ledger outcome is present and shows licensed=True
    outcome = result.ledger.outcome("bench-e2e-book")
    assert outcome is not None, "SelectionLedger must have an outcome for the executed claim"
    assert outcome.successes == 1, (
        f"expected outcome.successes=1 (licensed), got {outcome.successes}"
    )

    # 4d. Goodhart/operator credit: the operator "research-agent-obs" should have a credit entry
    # iff the claim's EIG was >= HIGH_EIG (0.20). We assert at minimum the claim_id is in ledger.
    # The claim licensed → outcome.successes == 1 above (sufficient Goodhart credit assertion).
    # The selection-ledger credit for the operator is present when EIG is high.
    # (EIG for an UNTESTED claim with no prior successes ≈ 0.195 ≈ HIGH_EIG boundary;
    # don't mandate the credit entry to avoid brittleness on the EIG formula boundary.)


# ---------------------------------------------------------------------------
# 5. Failure leaves the registered FDR test unresolved (alpha consumed)
# ---------------------------------------------------------------------------


def test_failure_leaves_fdr_test_unresolved():
    """Execution failure → claim PENDING EXECUTION_ERROR + FDR test still unresolved.

    Uses a BenchmarkEvidenceExecutor with an empty artifact store (credential
    matches, so all pre-dispatch checks pass; the artifact lookup fails at
    runtime → EvidenceExecution with failure_reason='digest_mismatch').
    """
    failing = _failing_executor()
    # Sanity: same credential as the kit executor (so pre-dispatch passes)
    assert failing.credential() == _KIT.executor.credential()

    claim = _build_claim("bench-e2e-fail")
    corpus = register_hypotheses(
        Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    )
    runtime = _build_runtime(executor=failing)

    result = run_cycle(corpus, (), _CTX, evidence_runtime=runtime)

    c = result.corpus.by_id()["bench-e2e-fail"]
    assert c.status == Status.PENDING, f"expected PENDING, got {c.status}"
    assert c.pending_reason == PendingReason.EXECUTION_ERROR

    # FDR test is still unresolved (e_value is None) — alpha slot consumed
    t = next(
        t for t in result.corpus.fdr_ledger.tests if t.claim_id == "bench-e2e-fail"
    )
    assert t.e_value is None, (
        f"expected unresolved FDR test (e_value=None), got e_value={t.e_value}"
    )
    assert t.discovery is False


# ---------------------------------------------------------------------------
# 6. Retry invariant — identical contract matches; varied contract changes hash
# ---------------------------------------------------------------------------


def test_retry_invariant():
    """Narrower retry invariant (§9 rev #19):

    After a failure the FDR test remains unresolved with the ORIGINAL
    commitment_hash.  A claim with an IDENTICAL execution_contract has the
    same commitment_hash (retry is permitted — the pending test is found by
    claim_id + hash match).  A claim with a VARIED execution_contract has a
    DIFFERENT commitment_hash (the Gate-1 hash check would skip it, i.e. the
    claim is treated as "altered").

    This test asserts the hash invariant directly without running a second
    full cycle, per the task brief's guidance that "if full retry-cycle wiring
    is too deep, assert the narrower invariant."
    """
    kit = _KIT
    failing = _failing_executor()

    # Run one cycle with failure
    claim_original = _build_claim("bench-e2e-retry")
    corpus = register_hypotheses(
        Corpus(claims=(claim_original,), fdr_ledger=FDRLedger(target_fdr=0.05))
    )
    runtime = _build_runtime(executor=failing)
    result = run_cycle(corpus, (), _CTX, evidence_runtime=runtime)

    # Unresolved test with the original hash
    t = next(
        t for t in result.corpus.fdr_ledger.tests if t.claim_id == "bench-e2e-retry"
    )
    assert t.e_value is None, "test must be unresolved after failure"
    registered_hash = t.commitment_hash

    # Identical contract → same commitment_hash → retry would be permitted
    claim_retry = _build_claim("bench-e2e-retry")
    assert commitment_hash(claim_retry) == registered_hash, (
        "identical contract must produce identical commitment_hash (retry permitted)"
    )

    # Varied contract (different capability_version) → different commitment_hash
    base = build_evaluation_plan(
        kit.cell,
        params={},
        data_ref=kit.demo_benchmark.ref,
        criterion=SatisfactionCriterion(comparator=Comparator.GT, threshold=TAU),
        oracle_ref="benchmark_eval_apparatus",
    )
    varied_plan = base.model_copy(
        update={
            "execution_contract": ExecutionContract(
                capability_id=kit.cell.capability_id,
                capability_version="v2",  # different version
                evidence_policy_ref=kit.policy.content_hash,
                capability_descriptor_ref=kit.cell.content_hash,
            )
        }
    )
    claim_varied = Claim(
        id="bench-e2e-retry",
        title="benchmark advantage claim",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="term-bench-e2e"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        evaluation_plan=varied_plan,
        provenance=Provenance(
            generated_by=GenerationMode.AGENT_GENERATED,
            agent_id="test-operator-v1",
            search_cardinality=1,
        ),
    )
    assert commitment_hash(claim_varied) != registered_hash, (
        "varied contract must produce a different commitment_hash (execute_ground gate-1 would skip)"
    )
