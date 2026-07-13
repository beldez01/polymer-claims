from polymer_protocol.topology import TopologyEdge


def test_legacy_edge_has_no_new_keys():
    e = TopologyEdge(source="a", target="b", kind="defeat", effective=True, provisional=False)
    d = e.model_dump()
    assert "signed_weight" not in d and "tier" not in d and "relation_status" not in d


def test_relation_edge_keeps_new_keys():
    e = TopologyEdge(source="a", target="b", kind="tension", effective=True, provisional=False,
                     tier="biological", signed_weight=-0.3, relation_status="conjectured")
    d = e.model_dump()
    assert d["signed_weight"] == -0.3 and d["tier"] == "biological"
    assert d["relation_status"] == "conjectured"
