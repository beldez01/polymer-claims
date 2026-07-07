from __future__ import annotations

import math

import numpy as np

from polymer_claims.methyl_ndmp import (
    _n_dmps,
    _rank_sum_p,
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


def test_two_legs_agree_within_tau_on_count():
    # The two legs are now GENUINELY different procedures (pooled-t vs rank-sum), so exact
    # equality is not expected -- but on this real (non-adversarial) fixture they still land on
    # the same integer count (rel diff 0.0). (The capability gate itself no longer requires
    # numeric closeness for n-DMP -- see agreement_mode="both_satisfy_criterion" -- this
    # assertion is just a sanity check on the raw adapter outputs.)
    from polymer_claims.methyl_ndmp import NDmpRankAdapter, NDmpTTestAdapter
    probes = tuple(f"cg{i:08d}" for i in range(1, 25))
    node = _ndmp_node(probes)
    va = NDmpTTestAdapter().execute(node, (), None).value
    vb = NDmpRankAdapter().execute(node, (), None).value
    assert va == vb == 10.0
    rel = abs(va - vb) / max(va, vb, 1.0)
    assert rel <= 0.10


# ---------------------------------------------------------------------------
# TDD (b): the rank leg's Mann-Whitney U / Wilcoxon rank-sum p-value
# ---------------------------------------------------------------------------


def _pairwise_u(a, b):
    """Independent (brute-force, O(n^2)) reference implementation of the Mann-Whitney U
    statistic for group b: counts pairs (a_i, b_j) with b_j > a_i, +0.5 per exact tie."""
    u = 0.0
    for ai in a:
        for bj in b:
            if bj > ai:
                u += 1.0
            elif bj == ai:
                u += 0.5
    return u


def _rank_sum_u_and_p(a, b):
    """Re-derive (U_b, mean_U, var_U) the same way _rank_sum_p does internally, so tests can
    cross-check the U statistic independently of the final p-value formula."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na, nb = len(a), len(b)
    combined = np.concatenate([a, b])
    n = na + nb
    order = np.argsort(combined, kind="mergesort")
    sorted_vals = combined[order]
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    r_b = ranks[na:].sum()
    return r_b - nb * (nb + 1) / 2.0


def test_rank_u_statistic_matches_independent_pairwise_count_no_ties():
    a, b = [1.0, 2.0], [3.0, 4.0]
    assert _rank_sum_u_and_p(a, b) == _pairwise_u(a, b) == 4.0


def test_rank_u_statistic_matches_independent_pairwise_count_with_ties():
    a, b = [1.0, 2.0, 2.0, 3.0], [2.0, 3.0, 4.0, 5.0, 5.0, 6.0]
    assert _rank_sum_u_and_p(a, b) == _pairwise_u(a, b) == 21.5


def test_rank_p_known_value_small_no_ties():
    # a=[1,2], b=[3,4]: U_b=4, mean_U=2, var_U=5/3, z=(2-0.5)/sqrt(5/3) -> p ~ 0.2453 (hand-computed
    # via the normal CDF, independent of this module at pin-authoring time). Regression pin.
    p = _rank_sum_p(np.array([1.0, 2.0]), np.array([3.0, 4.0]))
    assert abs(p - 0.2453) < 5e-4


def test_rank_p_degenerate_all_equal_is_one():
    # Every pooled value tied (identical groups) -> not a DMP, mirroring _pooled_t's se==0 branch.
    a = np.full(18, 0.3)
    b = np.full(18, 0.3)
    assert _rank_sum_p(a, b) == 1.0


def test_rank_p_complete_separation_is_tiny():
    a = np.arange(1, 19, dtype=float)
    b = np.arange(100, 118, dtype=float)
    assert _rank_sum_p(a, b) < 1e-6


def test_rank_p_two_sided_symmetric_in_group_order():
    rng = np.random.default_rng(7)
    a = rng.normal(0.3, 0.05, 20)
    b = rng.normal(0.32, 0.05, 20)
    assert abs(_rank_sum_p(a, b) - _rank_sum_p(b, a)) < 1e-9


# ---------------------------------------------------------------------------
# TDD (c): a constructed shared-assumption failure where the two legs genuinely DISAGREE
# (one leg's own p-value crosses alpha, the other's doesn't)
# ---------------------------------------------------------------------------


def test_pooled_t_and_rank_disagree_on_an_outlier_laden_probe():
    """An outlier IN one group inflates the pooled t-test's variance enough to kill significance,
    while the rank-sum test (insensitive to the outlier's magnitude, only its rank) stays
    significant. This is exactly the "shared-assumption failure" the OLS-mirror leg could never
    catch (it was forced to equal the t-test algebraically) -- the new rank leg genuinely can."""
    a = np.array([0.2030, 0.1896, 0.2075, 0.2094, 0.1805, 0.1870, 0.2013, 0.1968, 0.1998, 0.9900])
    b = np.array([0.2415, 0.2588, 0.2578, 0.2507, 0.2613, 0.2547, 0.2414, 0.2537, 0.2404, 0.2588])
    from polymer_claims.methyl_ndmp import _pooled_t

    t, df = _pooled_t(a, b)
    p_ttest = 0.0 if math.isinf(t) else _t_two_sided_p(t, df)
    p_rank = _rank_sum_p(a, b)
    assert p_ttest > 0.05   # t-test: NOT a DMP (outlier-inflated variance)
    assert p_rank < 0.05    # rank-sum: IS a DMP (robust to the outlier's magnitude)


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
    assert ids == {"methyl-ndmp-ttest", "methyl-ndmp-rank"}
    owners = {cr.owner for cr in reg.credentials}
    hashes = {cr.implementation_hash for cr in reg.credentials}
    assert len(owners) == 2  # distinct owners -> registry-independent
    assert len(hashes) == 2
    assert all(h.startswith("sha256:") for h in hashes)


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
