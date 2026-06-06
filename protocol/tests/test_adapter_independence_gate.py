"""Adapter-independence gate at the verify_stage license seam.

An executed claim can only LICENSE if SOME pair of its producing adapters is registry-
independent (different owner, different implementation lineage, both trusted). With no
registry (or an empty one) the gate is skipped — byte-identical back-compat.
"""
from __future__ import annotations

from polymer_grammar import PendingReason, Status
from polymer_protocol import AdapterCredential, AdapterRegistry, Corpus, run_cycle
from tests.conftest import make_claim, make_plan


def _licensing_corpus(empty_ledger):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    return Corpus(claims=(c,), fdr_ledger=empty_ledger)


def _registry(owner_a="alice", owner_b="bob", h_a="h1", h_b="h2", trusted_b=True):
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="identity", owner=owner_a, implementation_hash=h_a),
        AdapterCredential(identity="reference", owner=owner_b, implementation_hash=h_b, trusted=trusted_b),
    ))


def test_no_registry_licenses_as_before(empty_ledger, adapters, ctx):   # back-compat
    res = run_cycle(_licensing_corpus(empty_ledger), adapters, ctx)
    assert res.corpus.by_id()["a"].status == Status.LICENSED


def test_independent_registry_licenses(empty_ledger, adapters, ctx):
    res = run_cycle(_licensing_corpus(empty_ledger), adapters, ctx, adapter_registry=_registry())
    assert res.corpus.by_id()["a"].status == Status.LICENSED


def test_same_owner_holds_pending(empty_ledger, adapters, ctx):
    res = run_cycle(_licensing_corpus(empty_ledger), adapters, ctx, adapter_registry=_registry(owner_b="alice"))
    a = res.corpus.by_id()["a"]
    assert a.status == Status.PENDING
    assert a.pending_reason == PendingReason.ADAPTER_NOT_INDEPENDENT
    assert a.licensing is None


def test_same_lineage_holds_pending(empty_ledger, adapters, ctx):
    res = run_cycle(_licensing_corpus(empty_ledger), adapters, ctx, adapter_registry=_registry(h_b="h1"))
    assert res.corpus.by_id()["a"].pending_reason == PendingReason.ADAPTER_NOT_INDEPENDENT


def test_untrusted_holds_pending(empty_ledger, adapters, ctx):
    res = run_cycle(_licensing_corpus(empty_ledger), adapters, ctx, adapter_registry=_registry(trusted_b=False))
    assert res.corpus.by_id()["a"].pending_reason == PendingReason.ADAPTER_NOT_INDEPENDENT


def test_unregistered_adapter_holds_pending(empty_ledger, adapters, ctx):
    reg = AdapterRegistry(credentials=(AdapterCredential(identity="identity", owner="alice", implementation_hash="h1"),))
    res = run_cycle(_licensing_corpus(empty_ledger), adapters, ctx, adapter_registry=reg)
    assert res.corpus.by_id()["a"].pending_reason == PendingReason.ADAPTER_NOT_INDEPENDENT


def test_audit_note_reports_held_count(empty_ledger, adapters, ctx):
    res = run_cycle(_licensing_corpus(empty_ledger), adapters, ctx, adapter_registry=_registry(owner_b="alice"))
    vnote = next(a.note for a in res.audit if a.stage == "verify_stage")
    assert "held" in vnote


def test_gate_is_deterministic(empty_ledger, adapters, ctx):
    reg = _registry(owner_b="alice")
    a = run_cycle(_licensing_corpus(empty_ledger), adapters, ctx, adapter_registry=reg)
    b = run_cycle(_licensing_corpus(empty_ledger), adapters, ctx, adapter_registry=reg)
    assert a.model_dump_json() == b.model_dump_json()
