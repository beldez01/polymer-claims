"""export_timeline — a pure, deterministic TopologyTimeline across run_cycle iterations.

One warm-started TopologyExport frame per cycle plus that cycle's FrameStats. Frame 0 is the
seed corpus (no seed positions); each subsequent frame runs one run_cycle, threading
corpus + ledger forward, and lays out warm-started from the PREVIOUS frame's node positions so
existing claims hold their place and only new structure perturbs locally.

Purity: no clock, no random, no IO. Determinism is inherited from run_cycle + export_topology —
identical `(corpus, adapters, ctx, n_cycles, ledger, run_cycle_kwargs)` → identical timeline.
Grammar untouched; the Corpus stays its 4 collections (Timeline models are NOT corpus fields).
"""
from __future__ import annotations

from polymer_grammar import Adapter, MaterializationContext, Status

from .base import _Model
from .corpus import Corpus
from .cycle import run_cycle
from .ledger import SelectionLedger
from .topology import Layout, TopologyExport, export_topology


class FrameStats(_Model):
    """Per-cycle summary derived from the CycleResult, the post-cycle corpus, and the new topology."""
    cycle_index: int
    n_nodes: int
    n_licensed: int
    n_pending: int
    n_conjectured: int
    n_rejected: int
    n_edges: int
    n_effective_edges: int
    n_provisional_edges: int
    n_frontier: int
    n_added: int  # claims generated this cycle (len of generation.admitted)
    n_newly_licensed: int  # licensed delta vs the prior frame


class TimelineFrame(_Model):
    topology: TopologyExport
    stats: FrameStats


class TopologyTimeline(_Model):
    frames: tuple[TimelineFrame, ...] = ()
    n_cycles: int


def _status_count(corpus: Corpus, status: Status) -> int:
    return sum(1 for c in corpus.claims if c.status == status)


def _n_licensed(corpus: Corpus) -> int:
    return _status_count(corpus, Status.LICENSED)


def _frame_stats(
    corpus: Corpus,
    topology: TopologyExport,
    *,
    cycle_index: int,
    n_frontier: int,
    n_added: int,
    n_newly_licensed: int,
) -> FrameStats:
    return FrameStats(
        cycle_index=cycle_index,
        n_nodes=len(topology.nodes),
        n_licensed=_status_count(corpus, Status.LICENSED),
        n_pending=_status_count(corpus, Status.PENDING),
        n_conjectured=_status_count(corpus, Status.CONJECTURED),
        n_rejected=_status_count(corpus, Status.REJECTED),
        n_edges=len(topology.edges),
        n_effective_edges=sum(1 for e in topology.edges if e.effective),
        n_provisional_edges=sum(1 for e in topology.edges if e.provisional),
        n_frontier=n_frontier,
        n_added=n_added,
        n_newly_licensed=n_newly_licensed,
    )


def export_timeline(
    corpus: Corpus,
    adapters: tuple[Adapter, ...],
    ctx: MaterializationContext,
    *,
    n_cycles: int,
    layout: Layout = Layout.FORCE_DIRECTED,
    ledger: SelectionLedger | None = None,
    **run_cycle_kwargs,
) -> TopologyTimeline:
    """Pure, deterministic corpus → TopologyTimeline over `n_cycles` run_cycle iterations.

    Frame 0 = `export_topology(corpus, layout)` (no seed) + stats from the seed corpus
    (cycle_index 0, n_added 0, n_newly_licensed 0). For i in 1..n_cycles: run one cycle (threading
    corpus + ledger forward), lay out warm-started from the previous frame's node positions, and
    derive FrameStats from the CycleResult + post-cycle corpus + new topology. `adapters`/`ctx` and
    any extra `run_cycle_kwargs` (proposers, injected, budget, …) follow run_cycle's contract.
    """
    led = ledger

    # frame 0 — the seed corpus, unseeded layout
    topo = export_topology(corpus, layout=layout)
    licensed_prev = _n_licensed(corpus)
    frames: list[TimelineFrame] = [
        TimelineFrame(
            topology=topo,
            stats=_frame_stats(
                corpus,
                topo,
                cycle_index=0,
                n_frontier=0,
                n_added=0,
                n_newly_licensed=0,
            ),
        )
    ]

    for i in range(1, n_cycles + 1):
        result = run_cycle(corpus, adapters, ctx, ledger=led, **run_cycle_kwargs)
        corpus = result.corpus
        led = result.ledger

        seed_positions = {n.id: n.position for n in frames[-1].topology.nodes}
        topo = export_topology(corpus, layout=layout, seed_positions=seed_positions)

        licensed_now = _n_licensed(corpus)
        stats = _frame_stats(
            corpus,
            topo,
            cycle_index=i,
            n_frontier=len(result.frontier),
            n_added=len(result.generation.admitted),
            n_newly_licensed=max(0, licensed_now - licensed_prev),
        )
        licensed_prev = licensed_now
        frames.append(TimelineFrame(topology=topo, stats=stats))

    return TopologyTimeline(frames=tuple(frames), n_cycles=n_cycles)
