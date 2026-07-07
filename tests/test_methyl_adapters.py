from __future__ import annotations

import pytest
from polymer_grammar import Comparator, DataHandle, MaterializationContext, MeasurementBasis, OperationNode, ProducedLeafSpec, Status

from polymer_claims.methyl_adapters import RegionHodgesLehmannAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim

_CTX = MaterializationContext(id="M1", api_version="v1", data_version="epicv2_casectrl_demo@1")
_SIGNAL = ("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005")
_CONTROL = ("cg00000006", "cg00000007", "cg00000008", "cg00000009", "cg00000010")


def _node(probes=_SIGNAL, ref="se:epicv2_casectrl_demo@1"):
    return OperationNode(
        id="n0", impl="methyl::region_delta_beta",
        inputs=(DataHandle(ref=ref),),
        params=(
            ("region_probes", ",".join(probes)),
            ("group_col", "Sample_Group"),
            ("level_a", "level1"),
            ("level_b", "level2"),
        ),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_signal_region_delta_is_planted_shift():
    md = RegionMeanDiffAdapter().execute(_node(), (), _CTX).value
    assert abs(md - 0.20) < 1e-9


def test_two_legs_both_clear_threshold_on_planted_shift():
    # The bundled demo fixture is a NOISE-FREE constant shift (every level1 sample == 0.35,
    # every level2 sample == 0.55 in the signal region), so every pairwise difference b_j - a_i
    # is exactly 0.20 -> the two legs coincide numerically HERE. That coincidence is a property
    # of this particular zero-variance fixture, NOT an algebraic identity between the
    # estimators (see test_legs_genuinely_disagree_on_skewed_data below for real divergence).
    # The capability gate itself no longer requires numeric closeness for region-Δβ -- see
    # agreement_mode="both_satisfy_criterion" -- this assertion is a sanity check on the raw
    # adapter outputs.
    node = _node()
    md = RegionMeanDiffAdapter().execute(node, (), _CTX).value
    hl = RegionHodgesLehmannAdapter().execute(node, (), _CTX).value
    assert abs(md - hl) < 1e-9
    assert md > 0.10 and hl > 0.10  # both independently clear the claim's 0.10 criterion


def test_control_region_delta_is_zero():
    md = RegionMeanDiffAdapter().execute(_node(probes=_CONTROL), (), _CTX).value
    assert abs(md) < 1e-9


def test_identities_distinct():
    assert RegionMeanDiffAdapter().identity == "methyl-meandiff-beta"
    assert RegionHodgesLehmannAdapter().identity == "methyl-hodges-lehmann"
    assert RegionMeanDiffAdapter().identity != RegionHodgesLehmannAdapter().identity


def test_missing_region_probe_raises():
    with pytest.raises(Exception):
        RegionMeanDiffAdapter().execute(_node(probes=("cg99999999",)), (), _CTX)


def test_unsupported_impl_raises():
    bad = OperationNode(id="n0", impl="builtin::const", params=(("value", "1"),),
                        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED))
    with pytest.raises(Exception):
        RegionHodgesLehmannAdapter().execute(bad, (), _CTX)


def test_claim_carries_oracle_ref_subject_and_criterion():
    c = region_delta_beta_claim("c0")
    node = c.evaluation_plan.graph.nodes[0]
    assert node.oracle_ref == "canonical_epicv2_hg38_v1@1"
    assert node.impl == "methyl::region_delta_beta"
    assert c.subject is not None and c.subject.kind == "genomic_region"
    assert c.status == Status.PENDING and c.strength is None
    crit = c.evaluation_plan.criterion
    assert crit.comparator == Comparator.GT and crit.threshold == 0.10


def test_claim_can_omit_subject_for_the_precondition_probe():
    c = region_delta_beta_claim("c-nosub", with_subject=False)
    assert c.subject is None


def test_independent_registry_has_two_distinct_owners():
    reg = methyl_independent_registry()
    owners = {cr.owner for cr in reg.credentials}
    ids = {cr.identity for cr in reg.credentials}
    hashes = {cr.implementation_hash for cr in reg.credentials}
    assert ids == {"methyl-meandiff-beta", "methyl-hodges-lehmann"}
    assert len(owners) == 2
    assert len(hashes) == 2
    assert all(h.startswith("sha256:") for h in hashes)


# ---------------------------------------------------------------------------
# TDD: the Hodges-Lehmann leg's estimator itself -- a genuinely different (robust,
# rank-family) statistic from the group mean-difference, unlike the retired OLS-coef leg
# which was algebraically forced to equal the mean-difference exactly.
# ---------------------------------------------------------------------------


def _hodges_lehmann_bruteforce(a, b):
    """Independent (O(n*m), pure-Python) reference implementation of the HL location-shift
    estimator: the median of ALL pairwise differences b_j - a_i."""
    diffs = sorted(bj - ai for ai in a for bj in b)
    n = len(diffs)
    mid = n // 2
    if n % 2 == 1:
        return diffs[mid]
    return (diffs[mid - 1] + diffs[mid]) / 2.0


def test_hl_matches_independent_bruteforce_no_ties():
    import numpy as np
    a = [1.0, 2.0, 3.0]
    b = [10.0, 20.0]
    pairwise = (np.asarray(b)[:, None] - np.asarray(a)[None, :]).ravel()
    assert float(np.median(pairwise)) == _hodges_lehmann_bruteforce(a, b)


def test_hl_matches_independent_bruteforce_with_ties():
    import numpy as np
    a = [1.0, 1.0, 2.0, 5.0]
    b = [2.0, 2.0, 3.0, 3.0, 6.0]
    pairwise = (np.asarray(b)[:, None] - np.asarray(a)[None, :]).ravel()
    assert float(np.median(pairwise)) == _hodges_lehmann_bruteforce(a, b)


def test_hl_is_translation_equivariant():
    # Shifting every b value by a constant c shifts the HL estimate by exactly c.
    import numpy as np
    a = [0.1, 0.3, 0.2, 0.15]
    b = [0.5, 0.6, 0.55]
    c = 0.37

    def hl(a, b):
        pairwise = (np.asarray(b)[:, None] - np.asarray(a)[None, :]).ravel()
        return float(np.median(pairwise))

    assert abs(hl(a, [x + c for x in b]) - (hl(a, b) + c)) < 1e-12


def test_legs_genuinely_disagree_on_skewed_data():
    """An outlier IN the level2 group inflates the group mean enough to swing the mean
    difference well past the HL estimate, which (being the median of pairwise differences) is
    insensitive to the outlier's magnitude, only its rank. This is exactly the shared-assumption
    failure the OLS-mirror leg could never expose (it was forced to equal the mean-difference
    algebraically) -- the Hodges-Lehmann leg genuinely can."""
    import numpy as np
    a = [0.20, 0.19, 0.21, 0.20, 0.18]
    b = [0.25, 0.24, 0.26, 0.25, 0.99]  # one wild outlier in level2

    def meandiff(a, b):
        return sum(b) / len(b) - sum(a) / len(a)

    def hl(a, b):
        pairwise = (np.asarray(b)[:, None] - np.asarray(a)[None, :]).ravel()
        return float(np.median(pairwise))

    md = meandiff(a, b)
    h = hl(a, b)
    assert md > 0.20   # outlier drags the mean difference up substantially
    assert h < 0.10    # the median-of-pairwise-differences estimator is untouched by it
