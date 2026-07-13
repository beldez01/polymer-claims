"""Task 8: the umbrella spectral embedder honors signed cross-arm relation weights.

`build_graph` aggregates two channels per unordered pair: a legacy MAX over typed edges
(pre-Task-8 behavior) plus a SUM over signed relation edges, combined and clamped to
[-1, 1]. A tension relation contributes negatively and can drive a pair's weight below
zero (repulsion via the unchanged signed-Laplacian `_embed_component`); a coheres
relation adds attraction. A relation-free corpus stays byte-identical to the old MAX-only
graph (the byte-identity guard below + the existing spectral goldens).
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    DefeatEdge,
    DefeatEdgeKind,
    FDRLedger,
    PatternRef,
    RelationKind,
    Status,
    Tier,
    make_relation_claim,
)
from polymer_protocol.corpus import Corpus

from polymer_claims._synthetic_corpus import POLAR_PAIR, planted_corpus
from polymer_claims.embedding import KIND_WEIGHT, build_graph

_LEDGER = FDRLedger(target_fdr=0.05)
_PATTERN = PatternRef(id="adjusted_effect", version="v1")


def _claim(cid: str) -> Claim:
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=Status.EXPLORATORY,
    )


def _rebut(a: str, b: str) -> DefeatEdge:
    # A same-/no-direction rebut is a WEAK positive legacy attraction (KIND_WEIGHT["rebut"] = 0.4)
    # and — with no opposite-direction conclusions — is NOT flagged polar.
    return DefeatEdge(source=a, target=b, kind=DefeatEdgeKind.REBUT)


def test_tension_nets_negative():
    """A weak positive legacy edge (rebut, 0.4) plus CONJECTURED tension relations whose signed
    weights SUM below it drives the pair's aggregated weight negative — behavior that does not
    exist under the old MAX-only collapse (which would have kept +0.4).

    A single conjectured tension caps at severity(-1.0) * factor(0.3) = -0.3 (severity is bounded
    to [-1, 1] by RelationLeaf), which cannot outweigh the 0.4 floor of any legacy edge; two of
    them sum to -0.6, so the pair nets clamp(0.4 - 0.6) = -0.2 < 0 — this also exercises the
    relation channel's SUM (multiple signed edges on one pair)."""
    a, b = _claim("a"), _claim("b")
    r1 = make_relation_claim(
        "r1", ["a"], ["b"], Tier.BIOLOGICAL, RelationKind.TENSION, -1.0,
        rationale="tension one", status=Status.CONJECTURED,
    )
    r2 = make_relation_claim(
        "r2", ["a"], ["b"], Tier.BIOLOGICAL, RelationKind.TENSION, -1.0,
        rationale="tension two", status=Status.CONJECTURED,
    )
    corpus = Corpus(
        claims=(a, b, r1, r2), defeat_edges=(_rebut("a", "b"),), fdr_ledger=_LEDGER
    )
    _, W, _ = build_graph(corpus)
    assert W[frozenset(("a", "b"))] < 0


def test_coheres_adds_attraction():
    """A coheres relation adds positive weight on top of the legacy attraction, so the pair is
    strictly MORE attractive than the legacy-only baseline."""
    base = Corpus(
        claims=(_claim("a"), _claim("b")),
        defeat_edges=(_rebut("a", "b"),),
        fdr_ledger=_LEDGER,
    )
    coh = make_relation_claim(
        "rc", ["a"], ["b"], Tier.BIOLOGICAL, RelationKind.COHERES, 1.0,
        rationale="coheres", status=Status.CONJECTURED,
    )
    augmented = Corpus(
        claims=(_claim("a"), _claim("b"), coh),
        defeat_edges=(_rebut("a", "b"),),
        fdr_ledger=_LEDGER,
    )
    key = frozenset(("a", "b"))
    _, w_base, _ = build_graph(base)
    _, w_aug, _ = build_graph(augmented)
    assert w_aug[key] > w_base[key]
    assert w_base[key] == KIND_WEIGHT["rebut"]  # baseline is exactly the legacy weight


def test_relation_free_graph_is_byte_identical():
    """Byte-identity guard: for a relation-free corpus every aggregated weight is EXACTLY a
    KIND_WEIGHT value (legacy MAX, no clamp/sum artifact) and the polar set is preserved — so the
    channel split cannot have perturbed the existing spectral goldens."""
    _, W, polar = build_graph(planted_corpus())
    assert W  # non-trivial
    for w in W.values():
        assert w in set(KIND_WEIGHT.values())
    assert frozenset(POLAR_PAIR) in polar  # opposite-direction rebut still flagged
