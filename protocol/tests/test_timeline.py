"""Tests for export_timeline — the warm-started TopologyTimeline across run_cycle iterations."""
from __future__ import annotations

import pytest
from polymer_grammar import Direction, Proposition, Status

from polymer_protocol.corpus import Corpus
from polymer_protocol.proposers import rival_generation
from polymer_protocol.timeline import (
    TopologyTimeline,
    export_timeline,
)

from .conftest import make_claim, make_plan


@pytest.fixture
def seed_corpus(empty_ledger) -> Corpus:
    """A small corpus that grows + licenses over cycles: a PENDING-with-plan claim that
    licenses on cycle 1, plus a planless POSITIVE-conclusion claim that the rival_generation
    proposer elaborates into new CONJECTURED nodes."""
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    src = make_claim(
        "src",
        conclusion=Proposition(direction=Direction.POSITIVE, estimand="beta", descriptor="X on Y"),
    )
    return Corpus(claims=(a, src), fdr_ledger=empty_ledger)


def _proposers():
    return (rival_generation,)


def test_timeline_grows_and_licenses_with_stable_positions(seed_corpus, adapters, ctx):
    tl = export_timeline(seed_corpus, adapters, ctx, n_cycles=4, proposers=_proposers())
    assert tl.n_cycles == 4 and len(tl.frames) == 5
    # licensing rises across frames
    lic = [f.stats.n_licensed for f in tl.frames]
    assert lic[-1] >= lic[0]
    # warm-started: a node present in consecutive frames moves only a little
    for a, b in zip(tl.frames, tl.frames[1:]):
        pa = {n.id: n.position for n in a.topology.nodes}
        for n in b.topology.nodes:
            if n.id in pa:
                d = sum((x - y) ** 2 for x, y in zip(n.position, pa[n.id])) ** 0.5
                assert d < 0.75
    # frame 1+ layout is warm
    assert "seed=warm" in tl.frames[1].topology.layout_id


def test_timeline_frame0_is_unseeded(seed_corpus, adapters, ctx):
    tl = export_timeline(seed_corpus, adapters, ctx, n_cycles=2, proposers=_proposers())
    assert "seed=sha256" in tl.frames[0].topology.layout_id
    assert tl.frames[0].stats.cycle_index == 0
    assert tl.frames[0].stats.n_added == 0
    assert tl.frames[0].stats.n_newly_licensed == 0


def test_timeline_stats_track_growth_and_licensing(seed_corpus, adapters, ctx):
    tl = export_timeline(seed_corpus, adapters, ctx, n_cycles=4, proposers=_proposers())
    # the PENDING claim "a" licenses on cycle 1 -> frame 1 reports a newly-licensed delta
    assert tl.frames[1].stats.n_newly_licensed >= 1
    # node count never shrinks (generation only adds)
    counts = [f.stats.n_nodes for f in tl.frames]
    assert all(b >= a for a, b in zip(counts, counts[1:]))
    # each frame's n_nodes matches the actual topology
    for f in tl.frames:
        assert f.stats.n_nodes == len(f.topology.nodes)


def test_timeline_is_deterministic(seed_corpus, adapters, ctx):
    a = export_timeline(seed_corpus, adapters, ctx, n_cycles=3, proposers=_proposers())
    b = export_timeline(seed_corpus, adapters, ctx, n_cycles=3, proposers=_proposers())
    assert a == b


def test_timeline_json_roundtrips(seed_corpus, adapters, ctx):
    tl = export_timeline(seed_corpus, adapters, ctx, n_cycles=2, proposers=_proposers())
    assert TopologyTimeline.model_validate_json(tl.model_dump_json()) == tl


def test_timeline_public_surface():
    import polymer_protocol as pp

    for name in ("export_timeline", "TopologyTimeline", "TimelineFrame", "FrameStats"):
        assert hasattr(pp, name), name
        assert name in pp.__all__, name


def test_public_frame_stat_helpers_exported():
    from polymer_protocol import frame_stats, n_licensed
    # they are the same callables the timeline module uses internally
    from polymer_protocol import timeline as _tl
    assert _tl.frame_stats is frame_stats
    assert _tl.n_licensed is n_licensed
    # back-compat private aliases still resolve to the same objects
    assert _tl._frame_stats is frame_stats
    assert _tl._n_licensed is n_licensed
