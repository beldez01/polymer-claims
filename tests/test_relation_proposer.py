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

from polymer_claims.relation_proposer import propose_relations

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


class FakeAgent:
    def judge(self, a, b):
        return {"tier": "biological", "kind": "coheres", "severity": 0.7, "rationale": "same pathway"}


class WeakAgent:
    def judge(self, a, b):
        return {"tier": "biological", "kind": "tension", "severity": -0.1, "rationale": "weak"}


class DecliningAgent:
    def judge(self, a, b):
        return None


def test_emits_conjectured_relation(corpus_two_arms_tp53):
    rels = propose_relations(corpus_two_arms_tp53, FakeAgent(), max_pairs=10, threshold=0.3)
    assert rels
    for r in rels:
        assert r.status.value == "conjectured"
        assert r.leaves[0].kind == "relation"
        assert r.leaves[0].relation_kind == RelationKind.COHERES


def test_below_threshold_declined(corpus_two_arms_tp53):
    assert propose_relations(corpus_two_arms_tp53, WeakAgent(), max_pairs=10, threshold=0.3) == []


def test_none_judgment_declined(corpus_two_arms_tp53):
    assert propose_relations(corpus_two_arms_tp53, DecliningAgent(), max_pairs=10, threshold=0.3) == []


def test_emitted_relation_ids_and_source_target(corpus_two_arms_tp53):
    rels = propose_relations(corpus_two_arms_tp53, FakeAgent(), max_pairs=10, threshold=0.3)
    ids = {r.id for r in rels}
    assert "rel:pharmaco:tp53_meth~synbio:tp53_expr" in ids
