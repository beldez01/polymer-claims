from polymer_grammar import FDRLedger, Status
from polymer_protocol.corpus import Corpus
from polymer_protocol.topology import Layout, export_topology
from tests.conftest import make_claim

_LEDGER = FDRLedger(target_fdr=0.05)


def _corpus():
    a = make_claim("a", status=Status.PENDING)
    b = make_claim("b", status=Status.PENDING)
    return Corpus(claims=(a, b), fdr_ledger=_LEDGER)


def test_positions_override_used_verbatim():
    corpus = _corpus()
    pos = {"a": (0.1, 0.2, 0.3), "b": (-0.4, -0.5, -0.6)}
    export = export_topology(corpus, layout=Layout.FORCE_DIRECTED, positions=pos)
    by_id = {n.id: n.position for n in export.nodes}
    assert by_id["a"] == (0.1, 0.2, 0.3)
    assert by_id["b"] == (-0.4, -0.5, -0.6)
    assert export.layout_id == "external:spectral-v1"


def test_missing_position_falls_back_to_origin():
    corpus = _corpus()
    export = export_topology(corpus, layout=Layout.FORCE_DIRECTED, positions={"a": (1.0, 1.0, 1.0)})
    by_id = {n.id: n.position for n in export.nodes}
    assert by_id["b"] == (0.0, 0.0, 0.0)


def test_no_positions_is_unchanged_force_directed():
    corpus = _corpus()
    e1 = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    e2 = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    assert e1 == e2
    assert e1.layout_id.startswith("fruchterman-reingold")
