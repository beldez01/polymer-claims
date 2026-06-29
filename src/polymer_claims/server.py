"""FastAPI node server — streams a live NodeRunner over SSE. (Optional [serve] extra.)

This is an IMPURE driver host: it owns the clock (a cancellable background
ticker) and a broadcast hub. Each `/stream` subscriber receives an
`asyncio.Queue` of frame-JSON strings; the ticker publishes one payload per
tick. The pure engine (grammar + protocol) is never touched — every frame comes
from `runner.tick()`.

Imported only on the `[serve]` path: nothing in the core CLI import graph pulls
this module in, so `import polymer_claims` works without fastapi installed.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .node import NodeRunner

logger = logging.getLogger(__name__)

# Per-subscriber SSE queue cap: drop-oldest beyond this many buffered frames so a
# slow client can't grow an unbounded queue (memory leak).
_SSE_QUEUE_MAX = 1000


def _bounded_put(q, payload) -> None:
    try:
        q.put_nowait(payload)
    except asyncio.QueueFull:
        try:
            q.get_nowait()  # drop oldest
        except asyncio.QueueEmpty:
            pass
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass  # give up this frame rather than block the ticker


def _sse_event(json_str: str) -> bytes:
    return f"event: frame\ndata: {json_str}\n\n".encode()


def _obj(model) -> dict:
    # round-trip through the model's own JSON so JSONResponse serializes a plain
    # dict (avoids double-encoding the pydantic model as an escaped string).
    return json.loads(model.model_dump_json())


def create_app(
    runner: NodeRunner,
    *,
    interval: float = 1.5,
    origins=None,
    autostart: bool = True,
) -> FastAPI:
    # broadcast hub: each SSE subscriber gets an asyncio.Queue of frame-JSON strings.
    subscribers: set[asyncio.Queue] = set()
    # serialize the mutating runner.tick() across the ticker and route handlers.
    lock = asyncio.Lock()

    def _publish(frame) -> None:
        payload = frame.model_dump_json()
        for q in list(subscribers):
            _bounded_put(q, payload)

    async def _do_tick():
        # Run the (potentially blocking) tick OFF the event loop: a `serve --llm`
        # generation tick makes a synchronous Anthropic call inside run_cycle, and
        # running it inline would freeze the loop — stalling /claim, /state and
        # /stream for the whole API call. asyncio.to_thread keeps the loop free to
        # serve reads while the tick runs; the lock still serializes ticks.
        async with lock:
            frame = await asyncio.to_thread(runner.tick)
        _publish(frame)
        return frame

    async def _ticker() -> None:
        while True:
            await asyncio.sleep(interval)
            if runner.running:
                try:
                    await _do_tick()
                except Exception:  # noqa: BLE001 — one bad tick must not kill the ticker
                    # e.g. a transient LLM error or a numpy LinAlgError from the layout pass.
                    logger.exception("tick failed; continuing")

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(_ticker()) if autostart else None
        try:
            yield
        finally:
            if task is not None:
                task.cancel()

    app = FastAPI(title="polymer-claims node", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _drift_status() -> dict:
        rec = runner.last_drift
        return {
            "n_reopened": runner.n_reopened,
            "last_drift": None if rec is None
            else {"examined": rec.examined, "drifted": len(rec.drifted)},
        }

    def _status() -> dict:
        last = runner.frames[-1]
        return {
            "running": runner.running,
            "frame_index": runner.frame_index,
            "n_frames": len(runner.frames),
            "n_nodes": last.stats.n_nodes,
            "n_licensed": last.stats.n_licensed,
            **_drift_status(),
        }

    @app.get("/")
    async def root() -> dict:
        return _status()

    @app.get("/state")
    async def state() -> JSONResponse:
        # current (latest) frame as JSON
        return JSONResponse(content=_obj(runner.frames[-1]))

    @app.get("/timeline")
    async def timeline() -> JSONResponse:
        return JSONResponse(content=_obj(runner.snapshot()))

    @app.get("/claim/{claim_id}")
    async def claim(claim_id: str) -> JSONResponse:
        from .claim_detail import claim_detail

        for c in runner.corpus.claims:
            if c.id == claim_id:
                return JSONResponse(content=claim_detail(c))
        return JSONResponse(content={"error": "not found"}, status_code=404)

    @app.get("/consistency")
    async def consistency() -> JSONResponse:
        async with lock:
            corpus = runner.corpus            # snapshot the frozen, immutable corpus, then RELEASE
        # lock released — the eigendecomp must not serialize ticks

        def _compute() -> dict:
            try:
                from polymer_protocol import extract_sheaf
                from .sheaf_spectrum import consistency_report
            except ImportError:               # numpy/[embed] absent — caught INSIDE the worker
                return {"available": False}
            report = consistency_report(extract_sheaf(corpus))
            return {"available": True, **_obj(report)}

        body = await asyncio.to_thread(_compute)
        return JSONResponse(content=body)

    @app.post("/step")
    async def step() -> JSONResponse:
        frame = await _do_tick()
        return JSONResponse(content=_obj(frame))

    @app.post("/refresh")
    async def refresh() -> JSONResponse:
        async with lock:
            current = await asyncio.to_thread(runner.refresh_world)
        return JSONResponse(content={"current": _obj(current), **_drift_status()})

    @app.post("/pause")
    async def pause() -> dict:
        runner.running = False
        return _status()

    @app.post("/resume")
    async def resume() -> dict:
        runner.running = True
        return _status()

    async def _event_source() -> AsyncIterator[bytes]:
        q: asyncio.Queue = asyncio.Queue(maxsize=_SSE_QUEUE_MAX)
        # Subscribe + snapshot the on-connect frame atomically w.r.t. ticks: tick() appends and
        # publishes under `lock`, so doing both here closes the window where a new subscriber
        # could read frames[-1]==K and then ALSO receive K via _publish (a duplicate initial frame).
        async with lock:
            subscribers.add(q)
            initial = runner.frames[-1].model_dump_json()
        try:
            yield _sse_event(initial)
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield _sse_event(payload)
                except asyncio.TimeoutError:
                    yield b": heartbeat\n\n"  # keep proxies open
        finally:
            subscribers.discard(q)

    @app.get("/stream")
    async def stream() -> StreamingResponse:
        return StreamingResponse(_event_source(), media_type="text/event-stream")

    return app
