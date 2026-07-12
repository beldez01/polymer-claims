"""merge_universes: union preserves per-arm statuses + tags arms/modalities; dedup collapses
a claim re-observed by two arms; a same-id-different-content collision keeps the first arm's
claim (logged, not silently dropped). All synthetic — no real data, fast."""
from __future__ import annotations

import logging

from polymer_grammar import (
    Claim,
    DefeatEdge,
    EquivalenceClaim,
    MeasurementBasis,
    PatternRef,
    PendingReason,
    QuantityLeaf,
    Status,
)
from polymer_grammar.fdr import FDRTest

from polymer_claims.merge_universes import ArmSource, merge_universes

_PATTERN = PatternRef(id="synthetic", version="v1")


def _claim(id_: str, status: Status, value: float = 1.0):
    return Claim(
        id=id_,
        title=f"synthetic claim {id_}",
        pattern=_PATTERN,
        leaves=(QuantityLeaf(value=value, measurement_basis=MeasurementBasis.DERIVED, formula="f"),),
        status=status,
        pending_reason=PendingReason.UNTESTED if status == Status.PENDING else None,
    )


def test_union_preserves_statuses_and_tags_arms():
    alpha = ArmSource(
        arm="alpha", modality="modA",
        claims=(_claim("a1", Status.LICENSED), _claim("a2", Status.PENDING)),
    )
    beta = ArmSource(arm="beta", modality="modB", claims=(_claim("b1", Status.REJECTED),))

    merged, facets = merge_universes([alpha, beta])

    by_id = merged.by_id()
    assert len(merged.claims) == 3
    # statuses preserved exactly — never re-derived/re-licensed
    assert by_id["a1"].status is Status.LICENSED
    assert by_id["a2"].status is Status.PENDING
    assert by_id["b1"].status is Status.REJECTED
    # arm + modality facets tagged per surviving claim
    assert facets["a1"].arm == "alpha" and facets["a1"].modality == "modA"
    assert facets["a2"].arm == "alpha" and facets["a2"].modality == "modA"
    assert facets["b1"].arm == "beta" and facets["b1"].modality == "modB"


def test_dedup_same_atom_observed_by_two_arms():
    shared = _claim("shared-1", Status.LICENSED, value=42.0)
    alpha = ArmSource(arm="alpha", modality="modA", claims=(shared,))
    beta = ArmSource(arm="beta", modality="modB", claims=(shared,))  # byte-identical re-observation

    merged, facets = merge_universes([alpha, beta])

    assert len(merged.claims) == 1
    assert merged.claims[0].id == "shared-1"
    # first arm in source order wins the facet tag
    assert facets["shared-1"].arm == "alpha"


def test_conflicting_content_same_id_keeps_first_arm_and_logs(caplog):
    alpha = ArmSource(arm="alpha", modality="modA", claims=(_claim("x1", Status.LICENSED, value=1.0),))
    beta = ArmSource(arm="beta", modality="modB", claims=(_claim("x1", Status.LICENSED, value=999.0),))

    with caplog.at_level(logging.WARNING, logger="polymer_claims.merge_universes"):
        merged, facets = merge_universes([alpha, beta])

    assert len(merged.claims) == 1
    by_id = merged.by_id()
    assert by_id["x1"].leaves[0].value == 1.0  # first arm's content wins
    assert facets["x1"].arm == "alpha"
    assert any("collides" in r.message for r in caplog.records)


def test_defeat_edges_equivalences_and_fdr_tests_union():
    a1 = _claim("a1", Status.LICENSED)
    a2 = _claim("a2", Status.CONJECTURED)
    b1 = _claim("b1", Status.REJECTED)
    alpha = ArmSource(
        arm="alpha", modality="modA", claims=(a1, a2),
        equivalences=(EquivalenceClaim(id="eq1", left="a1", right="a2", severity=0.5, status=Status.STRUCTURAL),),
        fdr_tests=(FDRTest(index=1, claim_id="a1", e_value=10.0, alpha_allocated=0.01, discovery=True),),
    )
    beta = ArmSource(
        arm="beta", modality="modB", claims=(b1,),
        defeat_edges=(DefeatEdge(source="b1", target="a1", kind="rebut", provisional=True),),
        fdr_tests=(FDRTest(index=1, claim_id="b1", e_value=0.1, alpha_allocated=0.01, discovery=False),),
    )

    merged, _ = merge_universes([alpha, beta], target_fdr=0.1)

    assert len(merged.equivalences) == 1
    assert len(merged.defeat_edges) == 1
    assert len(merged.fdr_ledger.tests) == 2
    assert merged.fdr_ledger.target_fdr == 0.1
    assert {t.claim_id for t in merged.fdr_ledger.tests} == {"a1", "b1"}


def test_empty_sources_yields_empty_corpus():
    merged, facets = merge_universes([])
    assert merged.claims == ()
    assert facets == {}


def test_synbio_arm_named_by_subject_with_topic_facet():
    from polymer_claims.merge_universes import collect_synbio, merge_universes
    src = collect_synbio()
    assert src.arm == "synthetic-biology"
    merged, facets = merge_universes([src])
    assert any(f.arm == "synthetic-biology" for f in facets.values())
    assert any(f.topic for f in facets.values())         # topic facet populated
