from polymer_protocol import TopologyTimeline
from polymer_claims.node import NodeRunner
from tests.conftest import licensing_corpus


def test_node_runner_ticks_and_accumulates():
    r = NodeRunner.from_seed(licensing_corpus())
    for _ in range(5):
        r.tick()
    tl = r.snapshot()
    assert isinstance(tl, TopologyTimeline)
    assert len(tl.frames) >= 6                       # frame 0 + 5 ticks
    assert tl.frames[-1].stats.n_licensed >= tl.frames[0].stats.n_licensed
    # warm-start stability: a node present in consecutive frames moves only a little
    for a, b in zip(tl.frames, tl.frames[1:]):
        pa = {n.id: n.position for n in a.topology.nodes}
        for n in b.topology.nodes:
            if n.id in pa:
                d = sum((x - y) ** 2 for x, y in zip(n.position, pa[n.id])) ** 0.5
                assert d < 0.75
    # the timeline round-trips as JSON (frozen models)
    assert TopologyTimeline.model_validate_json(tl.model_dump_json()) == tl


def test_node_runner_snapshot_is_valid_before_ticks():
    r = NodeRunner.from_seed(licensing_corpus())
    tl = r.snapshot()
    assert len(tl.frames) == 1
    assert tl.frames[0].stats.cycle_index == 0
