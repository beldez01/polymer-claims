"""EXECUTE/GROUND: run the Phase-8 air-gapped gate over committed, non-gated claims.

Reuses evaluate.verify() — the two-implementation agreement gate that mints a Satisfaction
only on cross-adapter agreement + SATISFIED (no self-licensing). Produces evidence
(ExecRecords); writes no status (VERIFY decides). Caller must supply >=2 distinct-identity
adapters or verify() raises SelfLicensingError. Spec §6.5.

Evidence claims (verification_policy.execution == "single") are dispatched to the
EvidenceExecutor instead of the 2-adapter verify() gate. They go through a pre-dispatch
check sequence; failures produce an EvidenceExecution with failure_reason set.
"""
from __future__ import annotations

from polymer_grammar import (
    Adapter,
    Claim,
    MaterializationContext,
    Status,
    requires_safety_review,
    verify,
)
from polymer_grammar.capability import validate_claim_shape
from polymer_grammar.commitment import commitment_hash
from polymer_grammar.evaluate import EvaluationResult, ExecValue, SatisfactionVerdict, VerifiedEvaluation

from .corpus import Corpus, ExecRecord, is_locked
from .evidence_executor import EvidenceExecution, EvidenceRuntime, ExecutionFailure


def _is_executable(claim: Claim) -> bool:
    if claim.status != Status.PENDING or claim.evaluation_plan is None:
        return False
    # committed: carries a preregistration lock (from COMMIT)
    if not is_locked(claim):
        return False
    # not safety-gated (same predicate SAFETY uses)
    if claim.governance is not None and requires_safety_review(claim.governance):
        return False
    return True


def _pre_dispatch_failure(claim_id: str, reason: str, adapter_identity: str = "") -> tuple[ExecRecord, EvidenceExecution]:
    """Build a pre-dispatch FAILURE ExecRecord + EvidenceExecution pair."""
    result = EvaluationResult(
        verdict=SatisfactionVerdict.UNDETERMINED,
        terminal=ExecValue(value=None),
        nodes=(),
        adapter_identity=adapter_identity,
        status="error",
    )
    ev = VerifiedEvaluation(results=(result,), agreement=True, satisfaction=None)
    record = ExecRecord(claim_id=claim_id, evaluation=ev)
    ee = EvidenceExecution(
        record=record,
        e_value=None,
        licensing_info=None,
        failure_reason=ExecutionFailure(stage="pre_dispatch", reason=reason),
    )
    return record, ee


def execute_ground(
    corpus: Corpus,
    adapters: tuple[Adapter, ...],
    ctx: MaterializationContext,
    only: frozenset[str] | None = None,
    materializations: dict[str, MaterializationContext] | None = None,
    evidence_runtime: EvidenceRuntime | None = None,
) -> tuple[Corpus, tuple[ExecRecord, ...], tuple[EvidenceExecution, ...]]:
    """Run verify() over executable claims, optionally gated to this cycle's selection.

    When ``only`` is provided, a claim additionally must be in that set to execute: the
    permanent preregistration lock alone is no longer sufficient (it stays for anti-HARKing,
    but execution is gated to the selected set). ``only=None`` runs all executable claims.

    ``materializations`` (when supplied) gives a per-claim MaterializationContext: a claim
    present in the map is verified against its own ctx, absent → falls back to ``ctx``; None →
    every claim uses ``ctx`` (byte-identical to before). The core only reads the dict — no I/O.

    ``evidence_runtime`` (when supplied) enables the evidence dispatch pathway. Claims whose
    capability cell has ``verification_policy.execution == "single"`` are dispatched to the
    EvidenceExecutor instead of the 2-adapter verify() gate. When None, all claims use the
    standard verify() path and the third return element is always an empty tuple.

    Returns ``(corpus, records, evidence_executions)``. The third element is always present
    (even when evidence_runtime is None — it is then an empty tuple).
    """
    records: list[ExecRecord] = []
    evidence_executions: list[EvidenceExecution] = []

    # Build lookup of the most-recent pending FDR test per claim_id
    # (needed for the evidence pre-registration gate).
    pending_by_claim: dict[str, object] = {}
    if evidence_runtime is not None:
        for t in corpus.fdr_ledger.tests:
            if t.e_value is None and not t.retracted:
                pending_by_claim[t.claim_id] = t

    for c in corpus.claims:
        if only is not None and c.id not in only:
            continue
        if not _is_executable(c):
            continue
        ctx_c = materializations.get(c.id, ctx) if materializations else ctx

        # ── Evidence-dispatch path ────────────────────────────────────────────
        if (
            evidence_runtime is not None
            and c.evaluation_plan is not None
            and c.evaluation_plan.execution_contract is not None
        ):
            contract = c.evaluation_plan.execution_contract
            cell = evidence_runtime.capability_registry.resolve(
                contract.capability_id, contract.capability_version
            )
            if (
                cell is not None
                and cell.verification_policy is not None
                and cell.verification_policy.execution == "single"
            ):
                # This is an evidence claim — bypass the 2-adapter verify() gate.

                # Gate 1: find a pending FDR test with matching commitment hash.
                fdr_test = pending_by_claim.get(c.id)
                if fdr_test is None:
                    # No registered (or matching) test → skip entirely (no record).
                    continue
                ch = commitment_hash(c)
                if fdr_test.commitment_hash != ch:
                    # Commitment hash mismatch → hypothesis was altered → skip.
                    continue

                er = evidence_runtime

                # Pre-dispatch check 1: resolve policy.
                policy = er.evidence_policy_registry.resolve(contract.evidence_policy_ref)
                if policy is None:
                    rec, ee = _pre_dispatch_failure(c.id, "policy_mismatch")
                    records.append(rec)
                    evidence_executions.append(ee)
                    continue

                # Pre-dispatch check 2: policy ref consistency.
                vp = cell.verification_policy
                if (
                    contract.evidence_policy_ref != vp.evidence_policy_ref
                    or vp.evidence_policy_ref != policy.content_hash
                ):
                    rec, ee = _pre_dispatch_failure(c.id, "policy_mismatch", policy.executor_descriptor_ref)
                    records.append(rec)
                    evidence_executions.append(ee)
                    continue

                # Pre-dispatch check 3: capability descriptor ref.
                if contract.capability_descriptor_ref != cell.content_hash:
                    rec, ee = _pre_dispatch_failure(c.id, "digest_mismatch", policy.executor_descriptor_ref)
                    records.append(rec)
                    evidence_executions.append(ee)
                    continue

                # Pre-dispatch check 4: resolve executor descriptor.
                descriptor = er.executor_descriptor_registry.resolve(policy.executor_descriptor_ref)
                if descriptor is None:
                    rec, ee = _pre_dispatch_failure(c.id, "credential_mismatch", policy.executor_descriptor_ref)
                    records.append(rec)
                    evidence_executions.append(ee)
                    continue

                # Pre-dispatch check 5: credential check.
                cred = er.executor.credential()
                if (
                    cred != policy.executor_descriptor_ref
                    or policy.executor_descriptor_ref != descriptor.content_hash
                ):
                    rec, ee = _pre_dispatch_failure(c.id, "credential_mismatch", cred)
                    records.append(rec)
                    evidence_executions.append(ee)
                    continue

                # Pre-dispatch check 6: trust check.
                trust_entry = er.executor_trust_registry.resolve(policy.executor_descriptor_ref)
                if trust_entry is None or not trust_entry.trusted:
                    rec, ee = _pre_dispatch_failure(c.id, "untrusted_executor", cred)
                    records.append(rec)
                    evidence_executions.append(ee)
                    continue

                # Pre-dispatch check 7: validate claim shape.
                conformance = validate_claim_shape(c, cell)
                if not conformance.ok:
                    rec, ee = _pre_dispatch_failure(c.id, "malformed", cred)
                    records.append(rec)
                    evidence_executions.append(ee)
                    continue

                # Pre-dispatch check 8: criterion.threshold == policy.theta0 (spec §4 chain link).
                # A None threshold is treated as a mismatch — evidence claims must have a numeric
                # threshold, and it must equal the policy null exactly.
                ct = (
                    c.evaluation_plan.criterion.threshold
                    if c.evaluation_plan.criterion is not None
                    else None
                )
                if ct is None or ct != policy.theta0:
                    rec, ee = _pre_dispatch_failure(c.id, "policy_mismatch", cred)
                    records.append(rec)
                    evidence_executions.append(ee)
                    continue

                # All checks pass — dispatch to executor.
                result = er.executor.execute(c, cell, policy, ctx_c, fdr_test)
                records.append(result.record)
                evidence_executions.append(result)
                continue

        # ── Standard 2-adapter verify() path ─────────────────────────────────
        evaluation = verify(c.evaluation_plan, ctx_c, adapters, claim_leaves=c.leaves)
        records.append(ExecRecord(claim_id=c.id, evaluation=evaluation))

    return corpus, tuple(records), tuple(evidence_executions)
