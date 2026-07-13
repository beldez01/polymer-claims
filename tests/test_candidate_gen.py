from __future__ import annotations

import pytest
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    FDRLedger,
    GeneOrProtein,
    GeneOrProteinIdentifiers,
    PatternRef,
    RelationKind,
    RelationLeaf,
    Status,
    Tier,
)
from polymer_protocol.corpus import Corpus

from polymer_claims.relation_proposer import candidate_pairs, entity_key

_PATTERN = PatternRef(id="adjusted_effect", version="v1")
_RELATION_PATTERN = PatternRef(id="relation", version="v1")


def _tp53_claim(cid: str) -> Claim:
    subject = GeneOrProtein(
        id=f"{cid}-subject", display="TP53 promoter methylation",
        identifiers=GeneOrProteinIdentifiers(hgnc="TP53"), entity_type="gene",
    )
    return Claim(
        id=cid, title=f"claim {cid}", pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term="term"),),
        status=Status.CONJECTURED, subject=subject,
    )


def _relation_claim(cid: str) -> Claim:
    subject = GeneOrProtein(
        id=f"{cid}-subject", display="TP53 promoter methylation",
        identifiers=GeneOrProteinIdentifiers(hgnc="TP53"), entity_type="gene",
    )
    return Claim(
        id=cid, title=f"relation {cid}", pattern=_RELATION_PATTERN,
        leaves=(RelationLeaf(tier=Tier.COMPUTATIONAL, relation_kind=RelationKind.COHERES, severity=0.5),),
        status=Status.CONJECTURED, subject=subject,
    )


@pytest.fixture
def corpus_two_arms_tp53() -> Corpus:
    claims = (
        _tp53_claim("pharmaco:tp53_meth"),
        _tp53_claim("synbio:tp53_expr"),
        _tp53_claim("pharmaco:tp53_other"),  # same arm as tp53_meth, shares entity -> must not pair
        _relation_claim("relation:tp53_link"),  # shares entity but must never be paired
    )
    return Corpus(claims=claims, fdr_ledger=FDRLedger(target_fdr=0.05))


def test_entity_key_none_subject_is_empty():
    claim = Claim(
        id="x:none", title="no subject", pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term="term"),),
        status=Status.CONJECTURED,
    )
    assert entity_key(claim) == frozenset()


def test_entity_key_hgnc_normalized():
    subject = GeneOrProtein(
        id="s1", display="TP53", identifiers=GeneOrProteinIdentifiers(hgnc="tp53"), entity_type="gene",
    )
    claim = Claim(
        id="x:tp53", title="tp53", pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term="term"),),
        status=Status.CONJECTURED, subject=subject,
    )
    keys = entity_key(claim)
    assert "hgnc:TP53" in keys
    assert "text:tp53" in keys


def test_pairs_share_entity_cross_arm(corpus_two_arms_tp53):
    pairs = candidate_pairs(corpus_two_arms_tp53, max_pairs=100)
    assert ("pharmaco:tp53_meth", "synbio:tp53_expr") in {tuple(sorted(p)) for p in pairs}


def test_capped_and_deterministic(corpus_two_arms_tp53):
    p1 = candidate_pairs(corpus_two_arms_tp53, max_pairs=1)
    p2 = candidate_pairs(corpus_two_arms_tp53, max_pairs=1)
    assert p1 == p2 and len(p1) == 1


def test_same_arm_claims_not_paired(corpus_two_arms_tp53):
    pairs = candidate_pairs(corpus_two_arms_tp53, max_pairs=100)
    assert ("pharmaco:tp53_meth", "pharmaco:tp53_other") not in pairs
    assert ("pharmaco:tp53_other", "pharmaco:tp53_meth") not in pairs


def test_relation_claim_never_paired(corpus_two_arms_tp53):
    pairs = candidate_pairs(corpus_two_arms_tp53, max_pairs=100)
    for a, b in pairs:
        assert a != "relation:tp53_link" and b != "relation:tp53_link"
