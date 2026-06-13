from __future__ import annotations

import pytest
from polymer_grammar import FDRLedger, Status

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus, CycleScaffolding
from polymer_protocol.execute import execute_ground
from polymer_protocol.verify import verify_stage
from tests.conftest import make_claim, make_plan


def _setup(ctx, adapters):
    """Build (corpus, scaffolding, exec_records) for claim 'a':
    agreed + SATISFIED + grounded + provenance -> licenses under the 3-way gate.
    Starts with a fresh FDRLedger so n_tests assertions are exact."""
    empty_ledger = FDRLedger(target_fdr=0.05)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    return corpus, scaffolding, records


@pytest.fixture
def ctx():
    from polymer_grammar import MaterializationContext
    return MaterializationContext(id="M1", api_version="v1", data_version="d1")


@pytest.fixture
def adapters():
    from polymer_grammar import IdentityAdapter, ReferenceAdapter
    return (IdentityAdapter(), ReferenceAdapter(identity="reference"))


def test_evalue_discovery_allows_license(ctx, adapters):
    corpus, scaffolding, records = _setup(ctx, adapters)
    out = verify_stage(corpus, scaffolding, records, evidence={"a": 1e6})  # huge e -> discovery
    c = next(x for x in out.claims if x.id == "a")
    assert c.status == Status.LICENSED
    assert out.fdr_ledger.n_tests == 1 and out.fdr_ledger.n_discoveries == 1


def test_evalue_below_bar_blocks_license(ctx, adapters):
    corpus, scaffolding, records = _setup(ctx, adapters)
    out = verify_stage(corpus, scaffolding, records, evidence={"a": 0.0})  # e=0 -> never a discovery
    c = next(x for x in out.claims if x.id == "a")
    assert c.status != Status.LICENSED
    assert out.fdr_ledger.n_tests == 1 and out.fdr_ledger.n_discoveries == 0


def test_no_evidence_licenses_as_before(ctx, adapters):
    corpus, scaffolding, records = _setup(ctx, adapters)
    out = verify_stage(corpus, scaffolding, records)  # evidence=None -> 3-way gate, no e-test
    c = next(x for x in out.claims if x.id == "a")
    assert c.status == Status.LICENSED
    assert out.fdr_ledger.n_tests == 0
