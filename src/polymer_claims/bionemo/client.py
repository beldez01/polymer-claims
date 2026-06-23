from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class NimRequest:
    endpoint: str
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class NimResponse:
    status: int
    body: dict
    model_version: str | None = None


Transport = Callable[["NimRequest", str], "NimResponse"]


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def urllib_transport(req: NimRequest, api_key: str) -> NimResponse:
    """Default transport: POST JSON to a hosted NIM endpoint. Exercised by the live smoke
    test only (CI injects a fake transport)."""
    data = _canonical(req.payload).encode()
    request = urllib.request.Request(
        req.endpoint,
        data=data,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as r:  # noqa: S310 — hosted https NIM
        body = json.loads(r.read().decode())
        return NimResponse(status=r.status, body=body, model_version=None)


class NimClient:
    def __init__(
        self,
        transport: Transport,
        *,
        cache_dir: Path,
        api_key: str,
        model_version_field: str = "model",
    ) -> None:
        self.transport = transport
        self.cache_dir = Path(cache_dir)
        self.api_key = api_key
        self.model_version_field = model_version_field
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, req: NimRequest) -> Path:
        key = hashlib.sha256((req.endpoint + "\n" + _canonical(req.payload)).encode()).hexdigest()
        return self.cache_dir / f"{key}.json"

    def call(self, req: NimRequest) -> NimResponse:
        path = self._cache_path(req)
        if path.exists():
            cached = json.loads(path.read_text())
            return NimResponse(**cached)
        resp = self.transport(req, self.api_key)
        version = resp.model_version or (
            resp.body.get(self.model_version_field) if isinstance(resp.body, dict) else None
        )
        resp = NimResponse(status=resp.status, body=resp.body, model_version=version)
        path.write_text(json.dumps({"status": resp.status, "body": resp.body, "model_version": resp.model_version}))
        return resp
