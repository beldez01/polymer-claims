from __future__ import annotations

from polymer_claims.cli import _build_parser


def test_serve_has_tcga_laml_flag():
    parser = _build_parser()
    args = parser.parse_args(["serve", "--tcga-laml"])
    assert args.tcga_laml is True


def test_real_ndmp_seed_corpus_builds_one_real_claim():
    import polymer_claims.contracts as contracts_mod
    try:
        contracts_mod.load_contract("se:tcga_laml_idh@1")
    except Exception:
        import pytest
        pytest.skip("run `polymer-claims ingest tcga-laml` first")
    from polymer_claims.exec_adapters import real_ndmp_seed_corpus
    corpus, kwargs = real_ndmp_seed_corpus()
    assert len(corpus.claims) == 1
    assert corpus.claims[0].evaluation_plan.graph.nodes[0].impl == "methyl::n_dmps"
