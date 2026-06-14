from __future__ import annotations

from polymer_grammar import FDRLedger, MaterializationContext
from polymer_protocol import Corpus

from polymer_claims.contracts import load_contract
from polymer_claims.evidence import betting_evalue, evidence_map
from polymer_claims.methyl_adapters import _region_group_means, region_delta_beta_claim
from polymer_claims.replication import build_replication_inputs

_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
_REF_B = "se:epicv2_casectrl_demo_b@1"


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_cohort_b_resolves_with_distinct_dimnames():
    a = load_contract("se:epicv2_casectrl_demo@1")
    b = load_contract("se:epicv2_casectrl_demo_b@1")
    assert b.contract_uid == "epicv2_casectrl_demo_b@1"
    assert b.dimnames_hash != a.dimnames_hash  # different cohort -> different content-address


def test_replication_produces_satisfaction_and_product_evalue():
    claim = region_delta_beta_claim("c1")  # cohort A = epicv2_casectrl_demo@1
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE, bindings={"c1": _REF_B})

    # one extra satisfaction, carrying cohort B's dimnames_hash
    assert "c1" in rep.replications
    (sat_b,) = rep.replications["c1"]
    assert sat_b.materialization.dimnames_hash == load_contract(_REF_B).dimnames_hash

    # evidence for c1 is the PRODUCT e1 * e2 (computed independently here)
    node = claim.evaluation_plan.graph.nodes[0]
    comparator = claim.evaluation_plan.criterion.comparator
    a1, b1 = _region_group_means(node)
    e1 = betting_evalue(a1, b1, threshold=0.10, comparator=comparator)
    node_b = node.model_copy(update={"inputs": tuple(
        type(i)(ref=_REF_B) if hasattr(i, "ref") else i for i in node.inputs)})
    a2, b2 = _region_group_means(node_b)
    e2 = betting_evalue(a2, b2, threshold=0.10, comparator=comparator)
    assert rep.evidence["c1"] == e1 * e2


def test_same_cohort_binding_is_not_replication():
    claim = region_delta_beta_claim("c2")  # cohort A = epicv2_casectrl_demo@1
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE, bindings={"c2": "se:epicv2_casectrl_demo@1"})
    assert "c2" not in rep.replications  # same dimnames_hash -> no replication
    # evidence falls back to the single-cohort e-value
    assert "c2" in rep.evidence


def test_no_binding_leaves_evidence_unchanged():
    claim = region_delta_beta_claim("c3")
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE, bindings={})
    assert rep.replications == {}
    assert rep.evidence == evidence_map(corpus)
