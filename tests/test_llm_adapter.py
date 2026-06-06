"""Tests for the LLMGenerationAdapter: a DSL -> executable PENDING+plan claim mapper
backed by an injected `complete` (no network in tests)."""
from __future__ import annotations

import json

from polymer_grammar import FDRLedger, PendingReason, Status
from polymer_protocol import Corpus, Proposal

from polymer_claims.llm_adapter import LLMGenerationAdapter

from tests.conftest import licensing_corpus

_DSL = {
    "proposals": [
        {
            "title": "Adjusted effect is small",
            "pattern_id": "adjusted_effect",
            "ontology_term": "HP:0001250",
            "value": 0.02,
            "comparator": "lt",
            "threshold": 0.05,
            "rationale": "extends the corpus",
        }
    ]
}


def _stub(payload) -> LLMGenerationAdapter:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return LLMGenerationAdapter(lambda prompt: text)


def test_builds_executable_pending_claim():
    adapter = _stub(_DSL)
    proposals = adapter.propose(licensing_corpus(), frontier=())
    assert len(proposals) == 1
    p = proposals[0]
    assert isinstance(p, Proposal)
    assert p.operator_id == adapter.identity
    claim = p.claim
    assert claim.status == Status.PENDING
    assert claim.pending_reason == PendingReason.UNTESTED
    assert claim.id.startswith("gen-llm-")
    # executable plan: a builtin::const node + comparison criterion
    plan = claim.evaluation_plan
    assert plan is not None
    assert plan.graph.terminal == "n0"
    node = plan.graph.nodes[0]
    assert node.impl == "builtin::const"
    assert ("value", "0.02") in node.params


def test_malformed_json_yields_empty():
    adapter = _stub("this is not json at all")
    assert adapter.propose(licensing_corpus(), frontier=()) == ()


def test_codefence_tolerated():
    fenced = "Here you go:\n```json\n" + json.dumps(_DSL) + "\n```\nthanks"
    adapter = _stub(fenced)
    proposals = adapter.propose(licensing_corpus(), frontier=())
    assert len(proposals) == 1


def test_bad_proposal_dropped_others_kept():
    payload = {
        "proposals": [
            {  # bad: missing comparator
                "title": "broken",
                "pattern_id": "adjusted_effect",
                "ontology_term": "HP:0000001",
                "value": 0.1,
                "threshold": 0.5,
            },
            {  # good
                "title": "good one",
                "pattern_id": "adjusted_effect",
                "ontology_term": "HP:0002222",
                "value": 0.03,
                "comparator": "gt",
                "threshold": 0.01,
            },
        ]
    }
    adapter = _stub(payload)
    proposals = adapter.propose(licensing_corpus(), frontier=())
    assert len(proposals) == 1
    assert proposals[0].claim.title == "good one"


def test_content_addressed_ids_stable():
    a = _stub(_DSL).propose(licensing_corpus(), frontier=())
    b = _stub(_DSL).propose(licensing_corpus(), frontier=())
    assert a[0].claim.id == b[0].claim.id


def test_skip_own_output_already_in_corpus():
    # First produce the claim, then seed a corpus that already contains it.
    base = _stub(_DSL).propose(licensing_corpus(), frontier=())
    existing_claim = base[0].claim
    seed = licensing_corpus()
    corpus = Corpus(
        claims=(*seed.claims, existing_claim), fdr_ledger=FDRLedger(target_fdr=0.05)
    )
    proposals = _stub(_DSL).propose(corpus, frontier=())
    assert proposals == ()


def test_allowed_patterns_filter():
    adapter = LLMGenerationAdapter(
        lambda prompt: json.dumps(_DSL), allowed_patterns=("some_other_pattern",)
    )
    assert adapter.propose(licensing_corpus(), frontier=()) == ()
