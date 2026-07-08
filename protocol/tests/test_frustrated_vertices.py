from polymer_protocol.sheaf import SheafEdge, SheafStructure, SheafVertex, frustration_obstructions
from polymer_protocol import frustrated_vertices


def _v(cid):
    return SheafVertex(claim_id=cid, value=0.0)


def _e(u, v, sign):
    return SheafEdge(kind="equivalence" if sign > 0 else "defeat", u=u, v=v, weight=1.0, sign=sign)


def _struct(vids, edges):
    return SheafStructure(vertices=tuple(_v(x) for x in vids), edges=tuple(edges))


def test_theta_includes_the_vertex_that_obstructions_miss():
    # a-b +, a-p2 +, p2-b +, a-p3 +, p3-b - : reviewer-verified witness
    s = _struct(("a", "b", "p2", "p3"), [
        _e("a", "b", 1), _e("a", "p2", 1), _e("p2", "b", 1), _e("a", "p3", 1), _e("p3", "b", -1),
    ])
    assert frustrated_vertices(s) == frozenset({"a", "b", "p2", "p3"})
    # the divergence that is the whole point: reported obstructions miss p2
    reported = frozenset().union(*(frozenset(o.claim_ids) for o in frustration_obstructions(s)))
    assert "p2" not in reported
    assert "p2" in frustrated_vertices(s)


def test_opposite_sign_parallel_edges_frustrate_both_endpoints():
    s = _struct(("u", "v"), [_e("u", "v", 1), _e("u", "v", -1)])
    assert frustrated_vertices(s) == frozenset({"u", "v"})


def test_same_sign_parallel_edges_are_balanced_both_signs():
    plus = _struct(("u", "v"), [_e("u", "v", 1), _e("u", "v", 1)])
    minus = _struct(("u", "v"), [_e("u", "v", -1), _e("u", "v", -1)])
    assert frustrated_vertices(plus) == frozenset()
    assert frustrated_vertices(minus) == frozenset()     # guards "any negative edge ⇒ unbalanced"


def test_self_loops():
    neg = _struct(("v",), [_e("v", "v", -1)])
    pos = _struct(("v",), [_e("v", "v", 1)])
    assert frustrated_vertices(neg) == frozenset({"v"})
    assert frustrated_vertices(pos) == frozenset()


def test_balanced_articulation_plus_unbalanced_block():
    # balanced triangle {a,b,c} sharing cut-vertex c with a frustrated triangle {c,d,e}
    s = _struct(("a", "b", "c", "d", "e"), [
        _e("a", "b", 1), _e("b", "c", 1), _e("a", "c", 1),          # balanced (all +)
        _e("c", "d", 1), _e("d", "e", 1), _e("c", "e", -1),         # frustrated
    ])
    assert frustrated_vertices(s) == frozenset({"c", "d", "e"})     # cut-vertex c included; a,b excluded


def test_disconnected_only_unbalanced_component_returned():
    s = _struct(("a", "b", "c", "x", "y", "z"), [
        _e("a", "b", 1), _e("b", "c", 1), _e("a", "c", 1),          # balanced component
        _e("x", "y", 1), _e("y", "z", 1), _e("x", "z", -1),         # frustrated component
    ])
    assert frustrated_vertices(s) == frozenset({"x", "y", "z"})


def test_simple_frustrated_cycle_equals_obstruction_union():
    s = _struct(("a", "b", "c"), [_e("a", "b", 1), _e("b", "c", 1), _e("a", "c", -1)])
    reported = frozenset().union(*(frozenset(o.claim_ids) for o in frustration_obstructions(s)))
    assert frustrated_vertices(s) == reported == frozenset({"a", "b", "c"})


def test_invalid_edge_endpoint_is_skipped_not_raised():
    s = _struct(("a",), [_e("a", "ghost", -1)])                     # ghost not a vertex
    assert frustrated_vertices(s) == frozenset()
