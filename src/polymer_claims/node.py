"""Live node runner — the IMPURE driver layer.

`NodeRunner` is a stateful, mutable loop driver that ticks the #5d budget
scheduler, executes the recommended pure-engine action, and accumulates
warm-started topology frames into a `TopologyTimeline`.

This module is the ONLY impure piece: it owns the mutable live state
(`corpus`, `ledger`, accumulated frames, prior node positions). Every value it
derives comes from a PURE engine call (`run_cycle`, `next_action`,
`export_topology`) — the grammar and protocol packages stay untouched. It
reuses the protocol's public `frame_stats`/`n_licensed` helpers so the
runner's per-frame stats are byte-identical to `export_timeline`'s.

No web/HTTP here — a streaming server is a later task.
"""
from __future__ import annotations

import logging
from typing import Literal

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
    frame_stats,
    n_licensed,
    next_action,
    run_cycle,
)

from .contracts import clear_contract_cache
from .materialization import materialization_map
from .profiles import CANONICAL_EPICV2_V1
from polymer_protocol.drift import DriftRecord, drift_pass, reopen_drifted

_ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="d1")
logger = logging.getLogger(__name__)


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
        content_address: bool = False,
        profiles: tuple = (CANONICAL_EPICV2_V1,),
        evalue_gate: bool = False,
        layout: Literal["spectral", "force"] = "spectral",
        materializations: dict[str, MaterializationContext] | None = None,
        evidence: dict[str, float] | None = None,
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
        self.content_address = content_address
        self.profiles = profiles
        self.evalue_gate = evalue_gate
        self.run_cycle_kwargs = run_cycle_kwargs
        # Optional static overrides for materializations/evidence.  When provided,
        # these bypass the content_address / evalue_gate flag-based recomputation in
        # tick() (additive/optional: None → byte-identical existing behaviour).
        self._static_materializations = materializations
        self._static_evidence = evidence
        self._proposers_available = bool(run_cycle_kwargs.get("proposers"))
        self.frame_index = 0
        self.prev_positions: dict[str, tuple] = {}
        self.layout = layout
        # Previously DISPLAYED spectral positions — the Procrustes alignment target chain.
        self._prev_spectral: dict[str, tuple] = {}
        self._spectral_fallback_warned = False
        self.running = True

        # Frame 0 — the seed snapshot (no warm-start positions yet).
        topo = self._layout_topology(corpus)
        stats = frame_stats(
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
        self._licensed_prev = n_licensed(corpus)
        self.last_drift: DriftRecord | None = None
        self.n_reopened: int = 0
        if self.content_address:
            self.refresh_world()
        else:
            self.current = self.ctx

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
        content_address: bool = False,
        profiles: tuple = (CANONICAL_EPICV2_V1,),
        evalue_gate: bool = False,
        layout: Literal["spectral", "force"] = "spectral",
        materializations: dict[str, MaterializationContext] | None = None,
        evidence: dict[str, float] | None = None,
        **run_cycle_kwargs,
    ) -> "NodeRunner":
        return cls(
            corpus,
            adapters=adapters,
            ctx=ctx,
            config=config,
            scheduler_budget=scheduler_budget,
            max_frames=max_frames,
            content_address=content_address,
            profiles=profiles,
            evalue_gate=evalue_gate,
            layout=layout,
            materializations=materializations,
            evidence=evidence,
            **run_cycle_kwargs,
        )

    def refresh_world(self) -> MaterializationContext:
        """Re-read the live SE-Contracts/profile and recompute the current-world content-address.
        Operator/endpoint-triggered (not per-tick): busts the contract cache so a re-published
        dataset is actually re-read, then takes the v1 single-world representative (all entries of
        a single-dataset corpus share one address). Empty map -> the seed ctx (drift inert)."""
        clear_contract_cache()
        m = materialization_map(self.corpus, self.ctx, profiles=self.profiles)
        self.current = next(iter(m.values()), self.ctx)
        return self.current

    def tick(self) -> TimelineFrame:
        """Advance one scheduler-driven step; emit and accumulate a frame."""
        state = SchedulerState(
            corpus=self.corpus,
            ledger=self.ledger,
            proposers_available=self._proposers_available,
            current=self.current if self.content_address else None,
        )
        action = next_action(state, budget=self.scheduler_budget, config=self.config)

        if action is not None and action.kind == ActionKind.RUN_CYCLE:
            if self._static_materializations is not None:
                mats = self._static_materializations
            elif self.content_address:
                mats = materialization_map(self.corpus, self.ctx, profiles=self.profiles)
            else:
                mats = None
            if self._static_evidence is not None:
                ev = self._static_evidence
            elif self.evalue_gate:
                from .evidence import evidence_map   # lazy: keeps node.py base import numpy-free
                ev = evidence_map(self.corpus)
            else:
                ev = None
            result = run_cycle(
                self.corpus,
                self.adapters,
                self.ctx,
                ledger=self.ledger,
                materializations=mats,
                evidence=ev,
                **self.run_cycle_kwargs,
            )
            self.corpus = result.corpus
            self.ledger = result.ledger
            n_frontier = len(result.frontier)
            n_added = len(result.generation.admitted)
        elif action is not None and action.kind == ActionKind.DRIFT:
            _, record = drift_pass(self.corpus, current=self.current)
            self.corpus = reopen_drifted(self.corpus, record)
            self.last_drift = record
            self.n_reopened += sum(1 for f in record.drifted if f.re_executable)
            n_frontier = 0
            n_added = 0
        else:
            # IDLE tick: action is None, or a daemon kind from_seed never
            # enables in v1. Corpus/ledger unchanged, but still emit a frame so
            # the timeline has a heartbeat.
            n_frontier = 0
            n_added = 0

        self.frame_index += 1
        topo = self._layout_topology(self.corpus)
        licensed_now = n_licensed(self.corpus)
        n_newly_licensed = max(0, licensed_now - self._licensed_prev)
        self._licensed_prev = licensed_now

        stats = frame_stats(
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

    def _spectral_positions(self, corpus: Corpus) -> dict[str, tuple]:
        """Raw signed-Laplacian eigenmap positions, orthogonal-Procrustes-aligned to the previous
        displayed spectral frame (kills the per-frame eigenbasis sign/rotation thrash). The numpy
        embedder is LAZY-imported here so `node.py`'s base import stays numpy-free (mirrors the
        evalue_gate lazy methyl import). Frame 0 (empty `_prev_spectral`) → the raw reference.

        Raises ImportError if numpy / the `[embed]` extra is absent (caller handles fallback)."""
        from .embedding import procrustes_align, spectral_layout  # lazy: base import stays numpy-free

        raw = spectral_layout(corpus)
        aligned = procrustes_align(self._prev_spectral, raw)
        self._prev_spectral = aligned
        return aligned

    def _layout_topology(self, corpus: Corpus):
        """Export a topology frame for the chosen layout.

        - "spectral": inject Procrustes-aligned eigenmap positions through the protocol's
          `positions=` seam (`layout_id="external:spectral-v1"`). If the numpy embedder is
          unavailable (ImportError — numpy/`[embed]` absent) fall back to the force path for this
          frame (logged once); the frame's `layout_id` is self-describing.
        - "force": today's EXACT warm-started Fruchterman-Reingold path. `self.prev_positions` is
          `{}` at frame 0, which `export_topology` treats identically to `seed_positions=None`, so
          this is byte-identical to the historical behaviour."""
        if self.layout == "spectral":
            try:
                positions = self._spectral_positions(corpus)
            except ImportError:
                if not self._spectral_fallback_warned:
                    logger.warning(
                        "spectral layout unavailable (numpy/[embed] missing); "
                        "falling back to force-directed"
                    )
                    self._spectral_fallback_warned = True
            else:
                return export_topology(
                    corpus, layout=Layout.FORCE_DIRECTED, positions=positions
                )
        return export_topology(
            corpus, layout=Layout.FORCE_DIRECTED, seed_positions=self.prev_positions
        )

    def snapshot(self) -> TopologyTimeline:
        """Immutable view of the accumulated timeline so far."""
        return TopologyTimeline(frames=tuple(self.frames), n_cycles=self.frame_index)
