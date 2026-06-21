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


def test_claim_detail_endpoint():
    client, _ = _client()
    with client:
        # licensing_corpus seeds one claim with id "a"
        r = client.get("/claim/a")
        assert r.status_code == 200
        body = r.json()
        for key in (
            "id",
            "title",
            "status",
            "pattern_id",
            "plan",
            "criterion",
            "strength",
            "provenance",
            "rejection_reason",
        ):
            assert key in body
        assert body["id"] == "a"


def test_claim_detail_not_found():
    client, _ = _client()
    with client:
        r = client.get("/claim/__nope__")
        assert r.status_code == 404
        assert r.json() == {"error": "not found"}


def test_consistency_route_returns_report():
    client, _ = _client()
    with client:
        r = client.get("/consistency")
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is True
        assert "inconsistency_energy" in body and "h1_obstructions" in body and "per_claim_tension" in body


def test_consistency_does_not_block_step(monkeypatch):
    """P2: holding the lock during the eigendecomp would serialize /step behind /consistency.
    Block consistency_report; a concurrent /step must still complete promptly."""
    import threading
    import time

    import polymer_claims.sheaf_spectrum as ss

    release = threading.Event()
    real = ss.consistency_report

    def slow(structure):
        release.wait(timeout=5.0)  # block the worker thread
        return real(structure)

    monkeypatch.setattr(ss, "consistency_report", slow)

    client, _ = _client()
    out = {}

    def hit_consistency():
        out["consistency"] = client.get("/consistency").status_code

    with client:
        t = threading.Thread(target=hit_consistency)
        t.start()
        time.sleep(0.2)  # let /consistency take its corpus snapshot + enter the worker
        step = client.post("/step")  # must NOT be serialized behind the blocked worker
        assert step.status_code == 200  # completes while /consistency is still blocked
        release.set()
        t.join(timeout=5.0)
    assert out["consistency"] == 200


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


def _methyl_client():
    from tests.conftest import methyl_node

    runner = methyl_node()
    app = create_app(runner, interval=3600, autostart=False)
    return TestClient(app), runner


def test_refresh_endpoint_and_status_drift(monkeypatch):
    client, runner = _methyl_client()
    with client:
        for _ in range(3):
            client.post("/step")  # license the claim (records the address)

        body = client.post("/refresh").json()
        assert body["current"]["dimnames_hash"] is not None
        assert body["n_reopened"] == 0
        assert body["last_drift"] is None

        # status carries the same drift fields
        status = client.get("/").json()
        assert status["n_reopened"] == 0

        # move the world, refresh, step -> drift re-opens the claim
        import polymer_claims.materialization as mat_mod
        from polymer_claims.contracts import load_contract as real_load

        monkeypatch.setattr(
            mat_mod, "load_contract",
            lambda ref: real_load(ref).model_copy(update={"dimnames_hash": "sha256:" + "b" * 64}),
        )
        body2 = client.post("/refresh").json()
        assert body2["current"]["dimnames_hash"] != body["current"]["dimnames_hash"]
        client.post("/step")  # DRIFT tick

        status = client.get("/").json()
        assert status["n_reopened"] == 1
        assert status["last_drift"]["drifted"] == 1


def test_tick_does_not_block_reads(monkeypatch):
    """A slow (blocking) tick — e.g. a synchronous LLM call inside run_cycle —
    must NOT freeze the event loop: concurrent reads like /state must still be
    served promptly while a tick is in flight. Regression guard for the live
    `serve --llm` node, where the Anthropic call would otherwise stall /claim,
    /state and /stream for the full duration of each generation tick."""
    import asyncio
    import time

    import httpx

    runner = NodeRunner.from_seed(licensing_corpus())
    real_tick = runner.tick

    def slow_tick():
        time.sleep(0.4)  # stand in for a blocking LLM/network call inside the tick
        return real_tick()

    monkeypatch.setattr(runner, "tick", slow_tick)
    app = create_app(runner, interval=3600, autostart=False)

    async def scenario():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            order: list[str] = []
            codes: dict[str, int] = {}

            async def do_step():
                r = await c.post("/step")        # runs the slow (0.4s) tick
                codes["step"] = r.status_code
                order.append("step")

            async def do_state():
                r = await c.get("/state")        # a cheap read
                codes["state"] = r.status_code
                order.append("state")

            # Both issued concurrently, /step (the tick) scheduled first.
            await asyncio.gather(do_step(), do_state())
            return order, codes

    order, codes = asyncio.run(scenario())
    assert codes["state"] == 200
    assert codes["step"] == 200
    # If the tick blocks the event loop, the cheap /state read cannot complete
    # until the 0.4s tick finishes -> /step completes first. With the tick run
    # off-loop, /state returns immediately and completes BEFORE /step.
    assert order[0] == "state", f"/state was blocked behind the tick; order={order}"
