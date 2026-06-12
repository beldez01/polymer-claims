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


def test_refresh_world_tracks_current_address(monkeypatch):
    r = methyl_node()  # content_address=True -> __init__ set self.current
    real = r.current.dimnames_hash
    assert real is not None and real.startswith("sha256:")
    # unchanged disk -> same address
    assert r.refresh_world().dimnames_hash == real

    # simulate a re-published dataset: a contract with a moved dimnames_hash, valid betas path
    import polymer_claims.materialization as mat_mod
    from polymer_claims.contracts import load_contract as real_load

    moved = "sha256:" + "b" * 64
    monkeypatch.setattr(
        mat_mod, "load_contract",
        lambda ref: real_load(ref).model_copy(update={"dimnames_hash": moved}),
    )
    assert r.refresh_world().dimnames_hash == moved


def test_refresh_world_off_when_not_content_addressed():
    r = methyl_node(content_address=False)
    # self.current falls back to the seed ctx (no content-address fields)
    assert r.current.dimnames_hash is None
