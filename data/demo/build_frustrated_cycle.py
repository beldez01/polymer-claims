"""Build a frustrated-cycle seed corpus and write it to frustrated_cycle_corpus.json.

The corpus contains three Quantity-leaf LICENSED claims (A, B, C) with:
  - A ≡ B  (EquivalenceClaim, LICENSED)
  - B ≡ C  (EquivalenceClaim, LICENSED)
  - C ⊣ A  (DefeatEdge, kind=REBUT, effective — attacker has no strength so target
             cannot Pareto-dominate, so the attack stands)
  - Disagreeing values: A=1.0, B=1.0, C=4.0  →  B≡C edge is frustrated (values differ)
  - Same Dimension (mass^1) and same unit=None/DERIVED basis → commensurable

This produces exactly ONE H¹ obstruction over {A, B, C} with inconsistency_energy > 0.

Usage (from the repo root):
    uv run --project '.[embed]' python data/demo/build_frustrated_cycle.py
    uv run --project '.[embed]' polymer-claims export-consistency data/demo/frustrated_cycle_corpus.json
"""
from __future__ import annotations

import json
from pathlib import Path

from polymer_grammar import (
    DefeatEdge,
    DefeatEdgeKind,
    Dimension,
    EquivalenceClaim,
    FDRLedger,
    FDRTest,
    MeasurementBasis,
    PatternRef,
    QuantityLeaf,
    Status,
    Claim,
)
from polymer_protocol.corpus import Corpus

_PATTERN = PatternRef(id="adjusted_effect", version="v1")
_DIM = Dimension(exponents=(("mass", 1),))

# --- Three LICENSED Quantity-leaf claims with same Dimension (mass^1), no unit (DERIVED basis).
# Values: A=1.0, B=1.0, C=4.0.
# A≡B agrees (both 1.0, zero tension).
# B≡C disagrees (1.0 vs 4.0, energy > 0).
# C⊣A adds a sign-flipped defeat edge, completing the frustrated cycle.


def _make_claim(cid: str, value: float) -> Claim:
    leaf = QuantityLeaf(
        value=value,
        measurement_basis=MeasurementBasis.DERIVED,
        formula="test::const",
        dimension=_DIM,
    )
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=_PATTERN,
        leaves=(leaf,),
        status=Status.LICENSED,
    )


claim_a = _make_claim("A", 1.0)
claim_b = _make_claim("B", 1.0)
claim_c = _make_claim("C", 4.0)

# EquivalenceClaims: A≡B, B≡C (both LICENSED, severity=0.8 so weight > 0)
equiv_ab = EquivalenceClaim(id="eq_ab", left="A", right="B", severity=0.8, status=Status.LICENSED)
equiv_bc = EquivalenceClaim(id="eq_bc", left="B", right="C", severity=0.8, status=Status.LICENSED)

# DefeatEdge: C attacks A (REBUT kind).
# To make it effective, C must be in licensed_ids and not strength-dominated by A.
# Neither claim has a StrengthVector (strength=None on both), so the attack stands
# (effective_defeats: "when either strength is absent ... the attack stands").
defeat_ca = DefeatEdge(source="C", target="A", kind=DefeatEdgeKind.REBUT)

# FDR ledger: give attacker C a registered e-value so its defeat edge carries a weight.
# The extract_sheaf code does: weight = _attacker_evalue(latest, "C") = e_value = 5.0 here.
fdr_ledger = FDRLedger(
    target_fdr=0.05,
    tests=(
        FDRTest(index=1, claim_id="C", e_value=5.0, alpha_allocated=0.05, discovery=True),
    ),
)

corpus = Corpus(
    claims=(claim_a, claim_b, claim_c),
    equivalences=(equiv_ab, equiv_bc),
    defeat_edges=(defeat_ca,),
    fdr_ledger=fdr_ledger,
)

out_path = Path(__file__).parent / "frustrated_cycle_corpus.json"
out_path.write_text(corpus.model_dump_json())
print(f"Wrote {out_path}")
print(f"  claims: {[c.id for c in corpus.claims]}")
print(f"  equivalences: {[(e.left, e.right) for e in corpus.equivalences]}")
print(f"  defeat_edges: {[(d.source, d.target, d.kind.value) for d in corpus.defeat_edges]}")
