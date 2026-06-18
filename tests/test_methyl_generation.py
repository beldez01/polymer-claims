from __future__ import annotations

import json

from polymer_grammar import Comparator, FDRLedger
from polymer_protocol import Corpus

from polymer_claims.llm_adapter import MethylGenerationAdapter

_DSL = {
    "proposals": [
        {
            "kind": "region_delta_beta",
            "title": "fixture signal region is hypermethylated",
            "ref": "se:epicv2_casectrl_demo@1",
            "region_probes": ["cg00000001", "cg00000002", "cg00000003"],
            "group_col": "Sample_Group",
            "level_a": "level1",
            "level_b": "level2",
            "comparator": "gt",
            "threshold": 0.10,
            "rationale": "fixture signal probes carry the known positive shift",
        },
        {
            "kind": "n_dmps",
            "title": "powered fixture has enriched DMP count",
            "ref": "se:epicv2_casectrl_powered@1",
            "group_col": "Sample_Group",
            "level_a": "level1",
            "level_b": "level2",
            "alpha": 0.05,
            "k": 3,
            "comparator": "ge",
            "rationale": "the fixture contains planted DMPs",
        },
    ]
}


def _empty_corpus():
    return Corpus(claims=(), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_proposes_region_and_ndmp_methylation_claims_from_dsl():
    adapter = MethylGenerationAdapter(lambda _p: json.dumps(_DSL))
    props = adapter.propose(_empty_corpus(), ())
    assert len(props) == 2

    region = props[0].claim
    assert region.id.startswith("gen-methyl-region-")
    rnode = region.evaluation_plan.graph.nodes[0]
    assert rnode.impl == "methyl::region_delta_beta"
    assert dict(rnode.params)["region_probes"] == "cg00000001,cg00000002,cg00000003"
    assert region.evaluation_plan.criterion.comparator is Comparator.GT
    assert region.provenance.rationale == "fixture signal probes carry the known positive shift"

    ndmp = props[1].claim
    assert ndmp.id.startswith("gen-methyl-ndmp-")
    nnode = ndmp.evaluation_plan.graph.nodes[0]
    assert nnode.impl == "methyl::n_dmps"
    assert dict(nnode.params)["alpha"] == "0.05"
    assert ndmp.evaluation_plan.criterion.threshold == 3.0
    assert ndmp.provenance.rationale == "the fixture contains planted DMPs"


def test_methyl_generation_drops_unknown_contract():
    bad = {"proposals": [{**_DSL["proposals"][0], "ref": "se:missing_contract@1"}]}
    adapter = MethylGenerationAdapter(lambda _p: json.dumps(bad))
    assert adapter.propose(_empty_corpus(), ()) == ()


def test_methyl_generation_drops_missing_region_probe():
    bad = {"proposals": [{**_DSL["proposals"][0], "region_probes": ["cg99999999"]}]}
    adapter = MethylGenerationAdapter(lambda _p: json.dumps(bad))
    assert adapter.propose(_empty_corpus(), ()) == ()


def test_methyl_generation_drops_bad_kind_and_comparator():
    bad = {
        "proposals": [
            {**_DSL["proposals"][0], "kind": "free_text"},
            {**_DSL["proposals"][1], "comparator": "approx"},
        ]
    }
    adapter = MethylGenerationAdapter(lambda _p: json.dumps(bad))
    assert adapter.propose(_empty_corpus(), ()) == ()


def test_methyl_generation_prompt_mentions_asset_and_allowed_ops():
    adapter = MethylGenerationAdapter(lambda _p: json.dumps({"proposals": []}))
    prompt = adapter._build_prompt(_empty_corpus(), ())
    assert "se:epicv2_casectrl_demo@1" in prompt
    assert "EPICv2 synthetic case/control demo" in prompt
    assert "levels=level1,level2" in prompt
    assert "region_delta_beta" in prompt
    assert "n_dmps" in prompt
    assert "Sample_Group" in prompt
