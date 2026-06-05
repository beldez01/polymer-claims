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
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .node import NodeRunner

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


def _frame_obj(frame) -> dict:
    # round-trip through the model's own JSON so JSONResponse serializes a plain
    # dict (avoids double-encoding the pydantic model as an escaped string).
    return json.loads(frame.model_dump_json())


def _obj(model) -> dict:
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
        async with lock:
            frame = runner.tick()
        _publish(frame)
        return frame

    async def _ticker() -> None:
        while True:
            await asyncio.sleep(interval)
            if runner.running:
                await _do_tick()

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

    def _status() -> dict:
        last = runner.frames[-1]
        return {
            "running": runner.running,
            "frame_index": runner.frame_index,
            "n_frames": len(runner.frames),
            "n_nodes": last.stats.n_nodes,
            "n_licensed": last.stats.n_licensed,
        }

    @app.get("/")
    async def root() -> dict:
        return _status()

    @app.get("/state")
    async def state() -> JSONResponse:
        # current (latest) frame as JSON
        return JSONResponse(content=_frame_obj(runner.frames[-1]))

    @app.get("/timeline")
    async def timeline() -> JSONResponse:
        return JSONResponse(content=_obj(runner.snapshot()))

    @app.post("/step")
    async def step() -> JSONResponse:
        frame = await _do_tick()
        return JSONResponse(content=_frame_obj(frame))

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
        subscribers.add(q)
        try:
            # on connect: send the current frame immediately
            yield _sse_event(runner.frames[-1].model_dump_json())
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
