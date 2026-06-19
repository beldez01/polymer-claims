"""§E: shared-cause gate tests for build_replication_inputs.

Tests the grammar predicate (cohorts_error_independent) directly, then exercises
build_replication_inputs via monkeypatching load_contract to inject shared_cause_factors
so the gate can be triggered inside the umbrella.
"""
from __future__ import annotations

from polymer_grammar import (
    FDRLedger,
    MaterializationContext,
    Satisfaction,
    SatisfactionVerdict,
    cohorts_error_independent,
)
from polymer_protocol import Corpus

from polymer_claims.contracts import load_contract as _real_load_contract
from polymer_claims.evidence import betting_evalue
from polymer_claims.methyl_adapters import _region_group_means, region_delta_beta_claim
from polymer_claims.replication import build_replication_inputs

_REF_B = "se:epicv2_casectrl_demo_b@1"
_BASE_NO_FACTORS = MaterializationContext(id="M", api_version="v1", data_version="d1")
_BASE_WITH_FACTORS = MaterializationContext(
    id="M",
    api_version="v1",
    data_version="d1",
    dimnames_hash="cohort-a-dimnames",  # required for cohorts_error_independent to resolve
    shared_cause_factors=("manifest:HM450", "norm:noob", "ref:GRCh38"),
)


def _sat(dimnames, factors):
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=MaterializationContext(
            id=f"M-{dimnames}",
            api_version="v1",
            data_version="d1",
            dimnames_hash=dimnames,
            shared_cause_factors=factors,
        ),
    )


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


# ---------------------------------------------------------------------------
# Predicate unit tests (grammar layer)
# ---------------------------------------------------------------------------


def test_gate_predicate_high_overlap_denies():
    """High Jaccard (2/4 = 0.5 >= tau) -> cohorts_error_independent is False -> do NOT multiply."""
    a = _sat("A", ("manifest:HM450", "norm:noob", "ref:GRCh38"))
    b = _sat("B", ("manifest:HM450", "norm:noob", "lib:numpy"))  # jaccard 2/4 = 0.5 -> False
    assert cohorts_error_independent((a, b)) is False


def test_gate_predicate_low_overlap_allows():
    """Disjoint factor sets -> cohorts_error_independent is True -> multiply."""
    a = _sat("A", ("manifest:HM450", "norm:noob", "ref:GRCh38"))
    b = _sat("B", ("manifest:EPIC", "norm:funnorm", "ref:GRCh37"))  # disjoint -> True
    assert cohorts_error_independent((a, b)) is True


def test_gate_predicate_no_factors_returns_none():
    """No shared_cause_factors -> None -> multiply (byte-identical path)."""
    a = _sat("A", ())
    b = _sat("B", ())
    assert cohorts_error_independent((a, b)) is None


# ---------------------------------------------------------------------------
# Integration: multiply-skip path (high-overlap factors on both sides)
# ---------------------------------------------------------------------------


def test_umbrella_skips_multiply_when_shared_cause_overlap_high(monkeypatch):
    """When base_ctx carries overlapping factors AND contract_b exposes overlapping factors,
    cohorts_error_independent returns False -> evidence stays at e1 (NOT e1*e2),
    but replications[cid] is still populated with sat_b.
    """
    real_contract_b = _real_load_contract(_REF_B)

    # Wrap the real contract to add shared_cause_factors with enough overlap
    # for Jaccard(base_ctx factors, contract_b factors) >= tau (0.5).
    # base_ctx has ("manifest:HM450", "norm:noob", "ref:GRCh38") — 3 factors.
    # contract_b gets ("manifest:HM450", "norm:noob", "lib:numpy") — 2 shared -> Jaccard 2/4 = 0.5 -> False.
    class _WrappedContract:
        """Thin proxy that delegates everything to the real contract but adds shared_cause_factors."""

        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        @property
        def shared_cause_factors(self):
            return ("manifest:HM450", "norm:noob", "lib:numpy")

    wrapped_b = _WrappedContract(real_contract_b)

    def _patched_load(ref):
        if ref == _REF_B:
            return wrapped_b
        return _real_load_contract(ref)

    monkeypatch.setattr("polymer_claims.replication.load_contract", _patched_load)

    claim = region_delta_beta_claim("c1")
    corpus = _corpus(claim)

    rep = build_replication_inputs(corpus, _BASE_WITH_FACTORS, bindings={"c1": _REF_B})

    # sat_b still recorded (replications always set before gate)
    assert "c1" in rep.replications
    (sat_b,) = rep.replications["c1"]
    assert sat_b.materialization.dimnames_hash == real_contract_b.dimnames_hash

    # e-value NOT multiplied — gate fires and blocks the product
    node = claim.evaluation_plan.graph.nodes[0]
    comparator = claim.evaluation_plan.criterion.comparator
    a1, b1 = _region_group_means(node)
    e1 = betting_evalue(a1, b1, threshold=0.10, comparator=comparator)
    assert rep.evidence["c1"] == e1  # e1 only, NOT e1 * e2


# ---------------------------------------------------------------------------
# Integration: byte-identical path (factors absent -> None -> product applied)
# ---------------------------------------------------------------------------


def test_umbrella_still_multiplies_when_no_factors():
    """When neither base_ctx nor contract_b carries shared_cause_factors,
    cohorts_error_independent returns None -> gate NOT blocked -> product e1*e2 applied.
    Byte-identical with the existing test_replication_inputs.py behaviour.
    """
    claim = region_delta_beta_claim("c2")
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE_NO_FACTORS, bindings={"c2": _REF_B})

    node = claim.evaluation_plan.graph.nodes[0]
    comparator = claim.evaluation_plan.criterion.comparator
    a1, b1 = _region_group_means(node)
    e1 = betting_evalue(a1, b1, threshold=0.10, comparator=comparator)
    node_b = node.model_copy(update={"inputs": tuple(
        type(i)(ref=_REF_B) if hasattr(i, "ref") else i for i in node.inputs
    )})
    a2, b2 = _region_group_means(node_b)
    e2 = betting_evalue(a2, b2, threshold=0.10, comparator=comparator)

    assert rep.evidence["c2"] == e1 * e2  # product still applied
