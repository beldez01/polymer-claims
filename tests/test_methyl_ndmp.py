from __future__ import annotations

from polymer_claims.methyl_ndmp import (
    _n_dmps,
    _t_two_sided_p,
    dmp_indicators,
)


def test_t_pvalue_zero_t_is_one():
    assert abs(_t_two_sided_p(0.0, 98) - 1.0) < 1e-9


def test_t_pvalue_large_t_is_tiny():
    assert _t_two_sided_p(30.0, 98) < 1e-6


def test_t_pvalue_known_value():
    # t=2.0, df=98 two-sided p ~ 0.0483 (close to the normal 0.0455). Regression pin.
    assert abs(_t_two_sided_p(2.0, 98) - 0.0483) < 5e-4


def test_n_dmps_counts_below_alpha():
    pvals = {"a": 0.001, "b": 0.04, "c": 0.20, "d": 0.049}
    assert _n_dmps(pvals, 0.05) == 3  # a, b, d


def test_dmp_indicators_on_powered_fixture():
    # n-DMP node over all 24 powered probes; signal probes (1-10) should be DMPs, controls mostly not.
    probes = tuple(f"cg{i:08d}" for i in range(1, 25))
    node = _ndmp_node(probes)
    ind = dmp_indicators(node)
    assert len(ind) == 24
    assert sum(ind) >= 8  # ~10 true DMPs (5 strong + 5 weak), few/no control false positives
    assert set(ind) <= {0, 1}


def _ndmp_node(probes):
    from polymer_grammar import DataHandle, MeasurementBasis, OperationNode, ProducedLeafSpec
    return OperationNode(
        id="n0", impl="methyl::n_dmps",
        inputs=(DataHandle(ref="se:epicv2_casectrl_powered@1"),),
        params=(("probes", ",".join(probes)), ("group_col", "Sample_Group"),
                ("level_a", "level1"), ("level_b", "level2"), ("alpha", "0.05")),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_two_legs_agree_on_count():
    from polymer_claims.methyl_ndmp import NDmpOlsCoefAdapter, NDmpTTestAdapter
    probes = tuple(f"cg{i:08d}" for i in range(1, 25))
    node = _ndmp_node(probes)
    va = NDmpTTestAdapter().execute(node, (), None).value
    vb = NDmpOlsCoefAdapter().execute(node, (), None).value
    assert va == vb            # the air-gap: same integer count two ways
    assert va >= 8.0


def test_n_dmps_claim_builds_over_all_probes():
    from polymer_claims.methyl_ndmp import _NDMP_IMPL, n_dmps_claim
    c = n_dmps_claim("c-ndmp", ref="se:epicv2_casectrl_powered@1", k=3)
    node = c.evaluation_plan.graph.nodes[0]
    assert node.impl == _NDMP_IMPL
    assert c.evaluation_plan.criterion.threshold == 3.0
    probes = dict(node.params)["probes"].split(",")
    assert len(probes) == 24
    assert c.subject is not None  # GenomicRegion spanning the probes
    assert c.subject.start == 1_000_000 and c.subject.end == 1_004_800


def test_ndmp_registry_has_two_independent_legs():
    from polymer_claims.methyl_ndmp import ndmp_independent_registry
    reg = ndmp_independent_registry()
    ids = {cr.identity for cr in reg.credentials}
    assert ids == {"methyl-ndmp-ttest", "methyl-ndmp-ols"}
    owners = {cr.owner for cr in reg.credentials}
    assert len(owners) == 2  # distinct owners -> registry-independent


def test_evidence_map_scores_n_dmps_claim():
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus

    from polymer_claims.evidence import evidence_map
    from polymer_claims.methyl_ndmp import n_dmps_claim

    claim = n_dmps_claim("c-ndmp", ref="se:epicv2_casectrl_powered@1", k=3)
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    m = evidence_map(corpus)
    assert "c-ndmp" in m
    assert m["c-ndmp"] > 32.0  # strong enrichment (~10/24 DMPs vs p0=0.05) clears a typical e-LOND bar
