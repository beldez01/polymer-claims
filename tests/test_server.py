import json

import pytest

fastapi = pytest.importorskip("fastapi")
# Imports below the importorskip guard are intentional (skip cleanly when the
# [serve] extra is absent), so E402 does not apply.
from fastapi.testclient import TestClient  # noqa: E402

from polymer_claims.node import NodeRunner  # noqa: E402
from polymer_claims.server import create_app  # noqa: E402
from tests.conftest import licensing_corpus  # noqa: E402


def _client():
    runner = NodeRunner.from_seed(licensing_corpus())
    # autostart=False so only explicit /step advances — deterministic, no timing flakiness
    app = create_app(runner, interval=3600, autostart=False)
    return TestClient(app), runner


def test_root_status():
    client, _ = _client()
    with client:
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["running"] is True
        assert body["n_frames"] >= 1
        assert body["frame_index"] == 0


def test_step_advances_and_state():
    client, runner = _client()
    with client:
        before = client.get("/").json()["frame_index"]
        r = client.post("/step")
        assert r.status_code == 200
        frame = r.json()
        assert "topology" in frame and "stats" in frame
        after = client.get("/").json()["frame_index"]
        assert after == before + 1
        # /state returns the current (latest) frame
        st = client.get("/state").json()
        assert st["stats"]["cycle_index"] == after


def test_timeline_accumulates():
    client, _ = _client()
    with client:
        client.post("/step")
        client.post("/step")
        tl = client.get("/timeline").json()
        assert len(tl["frames"]) >= 3  # frame 0 + 2 steps
        assert tl["n_cycles"] == 2


def test_pause_resume():
    client, _ = _client()
    with client:
        assert client.post("/pause").json()["running"] is False
        assert client.post("/resume").json()["running"] is True


def test_stream_emits_current_frame_on_connect():
    # SSE-test mechanism: we drive the production `/stream` ASGI route DIRECTLY
    # rather than through httpx's TestClient/ASGITransport.
    #
    # Why: the `/stream` endpoint returns a StreamingResponse backed by an
    # *infinite* async generator (the broadcast hub keeps the connection open for
    # live frames). Both httpx.TestClient (.stream/.iter_lines/.iter_raw) and the
    # async ASGITransport deadlock at response-open against such a generator in
    # this httpx/starlette version — they wait for the body to drain before
    # handing back the response object, which never happens. (Verified: the
    # generator and the raw ASGI app both emit `http.response.start` + the first
    # `http.response.body` chunk immediately and correctly.)
    #
    # So we exercise the real route end-to-end at the ASGI layer and assert the
    # contract the task cares about: the FIRST SSE event carries a frame with
    # topology+stats. `receive` parks (no client disconnect); we cancel after the
    # first body chunk lands.
    import asyncio

    runner = NodeRunner.from_seed(licensing_corpus())
    runner.tick()  # ensure there's a non-seed frame
    app = create_app(runner, interval=3600, autostart=False)

    async def drive() -> dict:
        captured: dict = {}

        async def receive():
            await asyncio.sleep(3600)  # never disconnect during the window
            return {"type": "http.disconnect"}

        first_body = {"seen": False}

        async def send(message):
            if message["type"] == "http.response.start":
                assert message["status"] == 200
            elif message["type"] == "http.response.body":
                first_body["seen"] = True
                captured["body"] = message.get("body", b"")
                raise asyncio.CancelledError  # stop after the first chunk

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/stream",
            "raw_path": b"/stream",
            "headers": [],
            "query_string": b"",
        }
        try:
            await app(scope, receive, send)
        except asyncio.CancelledError:
            pass
        assert first_body["seen"]
        return captured

    captured = asyncio.run(asyncio.wait_for(drive(), timeout=10))
    body = captured["body"]
    payload = None
    for raw_line in body.split(b"\n"):
        s = raw_line.decode()
        if s.startswith("data:"):
            payload = json.loads(s[len("data:"):].strip())
            break
    assert payload is not None
    assert "topology" in payload and "stats" in payload


def test_step_serialized_gap_free():
    # lock + async handlers move /step off the threadpool onto the event loop, so
    # tick() is atomic w.r.t. the ticker — sequential steps are gap-free/no-dup.
    client, runner = _client()  # autostart=False, interval high
    with client:
        seen = []
        for _ in range(10):
            r = client.post("/step")
            seen.append(r.json()["stats"]["cycle_index"])
        assert seen == list(range(seen[0], seen[0] + 10))  # contiguous, no gaps/dups


def test_bounded_put_drops_oldest():
    import asyncio

    from polymer_claims.server import _SSE_QUEUE_MAX, _bounded_put

    q = asyncio.Queue(maxsize=3)
    for i in range(10):
        _bounded_put(q, f"p{i}")
    assert q.qsize() == 3
    items = [q.get_nowait() for _ in range(3)]
    assert items == ["p7", "p8", "p9"]  # newest 3 retained, oldest dropped
    assert _SSE_QUEUE_MAX == 1000
