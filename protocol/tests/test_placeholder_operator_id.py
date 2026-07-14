"""§3 — no path emits a proposal with the placeholder operator_id intact.

Reference proposers emit PLACEHOLDER_OPERATOR_ID relying on bridge_proposer to force the real
identity; the bridge now also REFUSES an adapter that (mis)uses the placeholder as an identity — the
one way the un-forced sentinel could reach a credit-governed path. Byte-identical (the sentinel value
is unchanged, just named).
"""
from __future__ import annotations

import pytest
from polymer_grammar import FDRLedger

from polymer_protocol import TemplateGenerationAdapter, bridge_proposer
from polymer_protocol.corpus import Corpus
from polymer_protocol.generation_adapter import PLACEHOLDER_OPERATOR_ID
from polymer_protocol.red_team import RepresentationRedTeamAdapter


def _corpus(make_quantity_claim) -> Corpus:
    return Corpus(claims=(make_quantity_claim("c1", 1.0),), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_reference_adapters_emit_the_placeholder(make_quantity_claim):
    corpus = _corpus(make_quantity_claim)
    for adapter in (TemplateGenerationAdapter(), RepresentationRedTeamAdapter()):
        props = adapter.propose(corpus, ())
        assert props
        assert all(p.operator_id == PLACEHOLDER_OPERATOR_ID for p in props)


def test_bridge_forces_the_placeholder_away(make_quantity_claim):
    corpus = _corpus(make_quantity_claim)
    proposer = bridge_proposer((TemplateGenerationAdapter(), RepresentationRedTeamAdapter()))
    out = proposer(corpus, ())
    assert out  # at least the template elaboration survives compile_untrusted
    assert all(p.operator_id != PLACEHOLDER_OPERATOR_ID for p in out)
    assert {p.operator_id for p in out} <= {"template-ref", "representation-red-team"}


def test_bridge_refuses_an_adapter_whose_identity_is_the_placeholder():
    class _BadAdapter:
        identity = PLACEHOLDER_OPERATOR_ID

        def propose(self, corpus, frontier):
            return ()

    with pytest.raises(ValueError, match="placeholder"):
        bridge_proposer((_BadAdapter(),))
