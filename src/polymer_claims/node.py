"""Live node runner — the IMPURE driver layer.

`NodeRunner` is a stateful, mutable loop driver that ticks the #5d budget
scheduler, executes the recommended pure-engine action, and accumulates
warm-started topology frames into a `TopologyTimeline`.

This module is the ONLY impure piece: it owns the mutable live state
(`corpus`, `ledger`, accumulated frames, prior node positions). Every value it
derives comes from a PURE engine call (`run_cycle`, `next_action`,
`export_topology`) — the grammar and protocol packages stay untouched. It
reuses the protocol's own private `_frame_stats`/`_n_licensed` helpers so the
runner's per-frame stats are byte-identical to `export_timeline`'s.

No web/HTTP here — a streaming server is a later task.
"""
from __future__ import annotations

from polymer_grammar import IdentityAdapter, MaterializationContext, ReferenceAdapter
from polymer_protocol import (
    ActionKind,
    Corpus,
    Layout,
    SchedulerConfig,
    SchedulerState,
    SelectionLedger,
    TimelineFrame,
    TopologyTimeline,
    export_topology,
    next_action,
    run_cycle,
)
from polymer_protocol.timeline import _frame_stats, _n_licensed

_ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="d1")


class NodeRunner:
    """Stateful driver that warm-starts a live claims-universe timeline.

    `max_frames` caps retained `frames` to a newest-N ring window (oldest
    frames are trimmed once the cap is exceeded) so a long-running node does
    not leak memory; `None` disables the cap (unbounded, the historical
    behavior). The cap touches ONLY the retained frame window: `frame_index`
    stays the monotonic TRUE total of ticks (and `snapshot().n_cycles`), while
    `frames` is just the newest-N slice of that history. Warm-start
    (`prev_positions`) is unaffected — it always derives from the latest frame.
    """

    def __init__(
        self,
        corpus: Corpus,
        *,
        adapters=_ADAPTERS,
        ctx: MaterializationContext = _CTX,
        config: SchedulerConfig | None = None,
        scheduler_budget: float = 1e9,
        max_frames: int | None = 10000,
        **run_cycle_kwargs,
    ) -> None:
        self.corpus = corpus
        self.ledger = SelectionLedger()
        self.adapters = adapters
        self.ctx = ctx
        self.config = config if config is not None else SchedulerConfig()
        # `scheduler_budget` gates whether RUN_CYCLE fires (threaded into
        # `next_action`). A `budget` inside `run_cycle_kwargs` is a DIFFERENT
        # quantity — run_cycle's own SELECT budget — and flows straight through
        # to `run_cycle`, where it spreads licensing progressively across cycles.
        self.scheduler_budget = scheduler_budget
        self.max_frames = max_frames
        self.run_cycle_kwargs = run_cycle_kwargs
        self._proposers_available = bool(run_cycle_kwargs.get("proposers"))
        self.frame_index = 0
        self.prev_positions: dict[str, tuple] = {}
        self.running = True

        # Frame 0 — the seed snapshot (no warm-start positions yet).
        topo = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
        stats = _frame_stats(
            corpus,
            topo,
            cycle_index=0,
            n_frontier=0,
            n_added=0,
            n_newly_licensed=0,
        )
        self.frames: list[TimelineFrame] = [TimelineFrame(topology=topo, stats=stats)]
        if self.max_frames is not None and len(self.frames) > self.max_frames:
            self.frames = self.frames[-self.max_frames:]
        self.prev_positions = {n.id: n.position for n in topo.nodes}
        self._licensed_prev = _n_licensed(corpus)

    @classmethod
    def from_seed(
        cls,
        corpus: Corpus,
        *,
        adapters=_ADAPTERS,
        ctx: MaterializationContext = _CTX,
        config: SchedulerConfig | None = None,
        scheduler_budget: float = 1e9,
        max_frames: int | None = 10000,
        **run_cycle_kwargs,
    ) -> "NodeRunner":
        return cls(
            corpus,
            adapters=adapters,
            ctx=ctx,
            config=config,
            scheduler_budget=scheduler_budget,
            max_frames=max_frames,
            **run_cycle_kwargs,
        )

    def tick(self) -> TimelineFrame:
        """Advance one scheduler-driven step; emit and accumulate a frame."""
        state = SchedulerState(
            corpus=self.corpus,
            ledger=self.ledger,
            proposers_available=self._proposers_available,
        )
        action = next_action(state, budget=self.scheduler_budget, config=self.config)

        if action is not None and action.kind == ActionKind.RUN_CYCLE:
            result = run_cycle(
                self.corpus,
                self.adapters,
                self.ctx,
                ledger=self.ledger,
                **self.run_cycle_kwargs,
            )
            self.corpus = result.corpus
            self.ledger = result.ledger
            n_frontier = len(result.frontier)
            n_added = len(result.generation.admitted)
        else:
            # IDLE tick: action is None, or a daemon kind from_seed never
            # enables in v1. Corpus/ledger unchanged, but still emit a frame so
            # the timeline has a heartbeat.
            n_frontier = 0
            n_added = 0

        self.frame_index += 1
        topo = export_topology(
            self.corpus,
            layout=Layout.FORCE_DIRECTED,
            seed_positions=self.prev_positions,
        )
        licensed_now = _n_licensed(self.corpus)
        n_newly_licensed = max(0, licensed_now - self._licensed_prev)
        self._licensed_prev = licensed_now

        stats = _frame_stats(
            self.corpus,
            topo,
            cycle_index=self.frame_index,
            n_frontier=n_frontier,
            n_added=n_added,
            n_newly_licensed=n_newly_licensed,
        )
        frame = TimelineFrame(topology=topo, stats=stats)
        self.frames.append(frame)
        if self.max_frames is not None and len(self.frames) > self.max_frames:
            self.frames = self.frames[-self.max_frames:]
        self.prev_positions = {n.id: n.position for n in topo.nodes}
        return frame

    def snapshot(self) -> TopologyTimeline:
        """Immutable view of the accumulated timeline so far."""
        return TopologyTimeline(frames=tuple(self.frames), n_cycles=self.frame_index)
