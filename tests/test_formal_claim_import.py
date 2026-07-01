"""Tests for the formal-claim-IR ingestion route (foreign claims -> polymer-claims Corpus).

The load-bearing behavior is the WITNESSED discipline: imported claims enter the universe but
NEVER as `licensed` — they have not passed this system's gate.
"""
import json

from polymer_grammar.claim import Status

from polymer_claims.formal_claim_import import import_formal_claim_ir


def _write_claim(dir_path, stem, *, outcome, value, statname="rho",
                 depends_on=None, title="a claim"):
    (dir_path / f"{stem}.json").write_text(json.dumps({
        "schema_version": "v1.2",
        "title": title,
        "conclusion": {"outcome": outcome},
        "statistics": [{"name": statname, "value": value}],
        "depends_on": depends_on or [],
    }))


def test_imported_claims_are_never_licensed_and_falsified_is_rejected(tmp_path):
    d = tmp_path / "claims"
    d.mkdir()
    _write_claim(d, "base", outcome="positive", value=0.7)
    _write_claim(d, "falsified", outcome="negative", value=0.1)

    corpus = import_formal_claim_ir([d])

    assert len(corpus.claims) == 2
    by = {c.id: c for c in corpus.claims}
    # WITNESSED discipline — the whole point: nothing earns belief on import.
    assert all(c.status != Status.LICENSED for c in corpus.claims)
    assert by["falsified"].status == Status.REJECTED
    assert by["base"].status == Status.CONJECTURED


def test_headline_stat_becomes_quantity_leaf_and_depends_on_becomes_equivalence(tmp_path):
    d = tmp_path / "claims"
    d.mkdir()
    _write_claim(d, "base", outcome="positive", value=0.702)
    _write_claim(d, "synth", outcome="positive", value=0.71, depends_on=["base"])

    corpus = import_formal_claim_ir([d])
    by = {c.id: c for c in corpus.claims}

    leaf = by["base"].leaves[0]
    assert leaf.kind == "quantity"
    assert leaf.value == 0.702

    assert any({e.left, e.right} == {"synth", "base"} for e in corpus.equivalences)


def test_cli_ingest_formal_claims_writes_loadable_corpus(tmp_path):
    from polymer_claims.cli import main
    from polymer_claims.io import load_corpus

    d = tmp_path / "claims"
    d.mkdir()
    _write_claim(d, "base", outcome="positive", value=0.7)
    _write_claim(d, "falsified", outcome="negative", value=0.1)
    out = tmp_path / "corpus.json"

    rc = main(["ingest-formal-claims", "--source", str(d), "--out", str(out)])

    assert rc == 0
    corpus = load_corpus(str(out))
    assert len(corpus.claims) == 2
