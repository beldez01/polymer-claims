# tests/test_evidence_map.py
from __future__ import annotations

from polymer_grammar import FDRLedger
from polymer_protocol import Corpus

from polymer_claims.evidence import evidence_map
from polymer_claims.methyl_adapters import region_delta_beta_claim


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_evidence_map_computes_evalue_for_signal_region():
    c = region_delta_beta_claim("c-true", threshold=0.10)  # planted +0.20 Δβ (existing noiseless fixture)
    m = evidence_map(_corpus(c))
    assert "c-true" in m
    assert m["c-true"] > 1.0  # a real effect above threshold -> e-value > 1 (modest on the noiseless fixture)


def test_evidence_map_skips_unresolvable_contract():
    c = region_delta_beta_claim("c-bad", ref="se:does_not_exist@1")
    assert "c-bad" not in evidence_map(_corpus(c))


def test_evidence_map_skips_non_apparatus_claim():
    from tests.conftest import make_claim, make_plan
    c = make_claim("plain", plan=make_plan(0.01, 0.05))
    assert "plain" not in evidence_map(_corpus(c))
