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


def test_sheaf_active_promotes_to_pending_with_dimensionless_magnitude_leaves(tmp_path):
    d = tmp_path / "claims"
    d.mkdir()
    _write_claim(d, "effect", outcome="positive", value=-0.71)
    _write_claim(d, "falsified", outcome="negative", value=0.1)

    corpus = import_formal_claim_ir([d], sheaf_active=True)
    by = {c.id: c for c in corpus.claims}

    # still never licensed — pending is the weakest sheaf-eligible standing.
    assert all(c.status != Status.LICENSED for c in corpus.claims)
    assert by["effect"].status == Status.PENDING
    assert by["falsified"].status == Status.REJECTED  # negatives stay rejected

    leaf = by["effect"].leaves[0]
    assert leaf.value == 0.71            # magnitude, not the signed -0.71
    assert leaf.dimension is not None    # dimensionless signature, not None (so it can wire)


def test_sheaf_active_makes_the_gauge_engage(tmp_path):
    from polymer_protocol import extract_sheaf

    d = tmp_path / "claims"
    d.mkdir()
    _write_claim(d, "base", outcome="positive", value=0.7)
    _write_claim(d, "synth", outcome="positive", value=0.71, depends_on=["base"])

    active = import_formal_claim_ir([d], sheaf_active=True)
    default = import_formal_claim_ir([d])

    s_active = extract_sheaf(active)     # DEFAULT filter {licensed, pending}
    s_default = extract_sheaf(default)

    # sheaf-active: pending + dimensionless + genuine depends_on edge -> the gauge sees structure.
    assert len(s_active.vertices) >= 2
    assert len(s_active.edges) >= 1
    # default import: conjectured -> filtered out entirely.
    assert len(s_default.vertices) == 0
