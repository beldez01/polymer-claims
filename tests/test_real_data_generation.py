import json

from polymer_grammar import FDRLedger
from polymer_protocol import Corpus

from polymer_claims.llm_adapter import MeanDiffGenerationAdapter

_DSL = {"proposals": [{
    "title": "high dose lifts response", "value_col": "response", "group_col": "dose",
    "group_a": "high", "group_b": "low", "comparator": "gt", "threshold": 10.0,
    "rationale": "dose drives response",
}]}


def _empty_corpus():
    return Corpus(claims=(), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_proposes_a_mean_diff_claim_from_dsl():
    adapter = MeanDiffGenerationAdapter(lambda _p: json.dumps(_DSL))
    props = adapter.propose(_empty_corpus(), ())
    assert len(props) == 1
    claim = props[0].claim
    assert claim.id.startswith("gen-md-")
    node = claim.evaluation_plan.graph.nodes[0]
    assert node.impl == "stats::mean_diff"
    assert dict(node.params)["value_col"] == "response"
    assert claim.provenance.rationale == "dose drives response"


def test_invalid_column_is_dropped():
    bad = {"proposals": [{**_DSL["proposals"][0], "value_col": "__nope__"}]}
    adapter = MeanDiffGenerationAdapter(lambda _p: json.dumps(bad))
    assert adapter.propose(_empty_corpus(), ()) == ()


def test_bad_comparator_is_dropped():
    bad = {"proposals": [{**_DSL["proposals"][0], "comparator": "approx"}]}
    adapter = MeanDiffGenerationAdapter(lambda _p: json.dumps(bad))
    assert adapter.propose(_empty_corpus(), ()) == ()


def test_prompt_mentions_dataset_and_op():
    adapter = MeanDiffGenerationAdapter(lambda _p: json.dumps({"proposals": []}))
    prompt = adapter._build_prompt(_empty_corpus(), ())
    assert "dose_response" in prompt
    assert "mean" in prompt.lower()
    assert "response" in prompt and "dose" in prompt
