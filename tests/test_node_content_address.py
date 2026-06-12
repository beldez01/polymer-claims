from __future__ import annotations

from polymer_grammar import Status

from tests.conftest import methyl_node


def test_content_addressed_node_records_address_on_license():
    r = methyl_node()  # content_address=True
    for _ in range(3):
        r.tick()
    c = next(x for x in r.corpus.claims if x.id == "c-true")
    assert c.status == Status.LICENSED
    m = c.licensing.satisfactions[0].materialization
    assert m.dimnames_hash is not None
    assert m.profile_hash is not None
    assert m.semantic_run_id is not None and m.semantic_run_id.startswith("sha256:")


def test_node_without_content_address_records_no_address():
    r = methyl_node(content_address=False)
    for _ in range(3):
        r.tick()
    c = next(x for x in r.corpus.claims if x.id == "c-true")
    assert c.status == Status.LICENSED
    m = c.licensing.satisfactions[0].materialization
    assert m.dimnames_hash is None
    assert m.profile_hash is None
    assert m.semantic_run_id is None
