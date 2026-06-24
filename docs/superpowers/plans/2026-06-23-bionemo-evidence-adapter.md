# BioNeMo Evidence Adapter Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a NVIDIA BioNeMo NIM run a first-class, certifiable evidence source for polymer-claims, proven end-to-end (`run_cycle` → `LICENSED` → `certify`) against a cached NIM call plus a fenced synthetic corroborator — with the scientific wedge deferred.

**Architecture:** A new impure sub-package `src/polymer_claims/bionemo/` plugs into three existing seams: the execution `Adapter` protocol (a NIM run becomes a compute node emitting an `ExecValue`), the `OracleRegistry` (caps claim strength at a conservative validation tier), and the `AdapterRegistry` (records NVIDIA as adapter owner so the air-gap can mint a license against an independent corroborator). Network IO stays out of the pure `grammar`/`protocol` packages; the NIM client uses an injectable transport so all CI tests run offline.

**Tech Stack:** Python ≥3.12, pydantic v2, stdlib only for runtime (`urllib`, `subprocess`, `hashlib`, `json`) — no new runtime dependencies. Tests via `pytest`.

## Global Constraints

- Python floor `>=3.12` (from `pyproject.toml`).
- **Pure/impure boundary:** no network or IO in `grammar/` or `protocol/`. All BioNeMo code lives under `src/polymer_claims/bionemo/` (impure umbrella), alongside `llm_adapter.py`.
- **Offline, deterministic CI:** no live network in any test except the explicitly env-gated live smoke test. Use an injectable transport + a recorded cassette.
- **Secrets:** NVIDIA API key from the macOS keychain (`security` CLI), env var `NVIDIA_API_KEY` as fallback. Never read or write a dotfile.
- **No new runtime deps:** default HTTP transport uses stdlib `urllib`. (A future `[bionemo]` extra may add `httpx`; not needed for Phase 1.)
- **Air-gap honesty fence:** the `SyntheticCorroboratorAdapter` is a TEST DOUBLE under `tests/fixtures/`. Its credential (owner ≠ `"NVIDIA"`) may appear ONLY in a plumbing-validation `AdapterRegistry`, NEVER in the production builder in `bionemo/registry.py`.
- **Conservative oracle tiers:** a pure-compute NIM with no wet-lab anchor is `INDIRECT` (or `UNVALIDATED`), never `ANCHORED`/`GOLD`.
- Follow the repo adapter pattern: an adapter is a class with a `str` `identity` attribute and `execute(self, node, upstream, ctx) -> ExecValue`; it inspects `node.impl` and raises if it cannot handle the node (the evaluator degrades a raise to a node error, never crashes).
- Tests run with `uv run --project . pytest tests/ -q`; full gate is `bash scripts/check-all.sh` (pytest + ruff across all three packages). Keep `ruff check` clean.
- Commit after each task.

---

### Task 1: Scaffold `bionemo` package + keychain-backed API-key loader

**Files:**
- Create: `src/polymer_claims/bionemo/__init__.py`
- Create: `src/polymer_claims/bionemo/auth.py`
- Test: `tests/bionemo/__init__.py`, `tests/bionemo/test_auth.py`

**Interfaces:**
- Produces: `load_nvidia_api_key(*, service: str = "nvidia-build-api", account: str | None = None, runner: Callable[[list[str]], str] | None = None, env: Mapping[str, str] | None = None) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/bionemo/test_auth.py
import pytest
from polymer_claims.bionemo.auth import load_nvidia_api_key


def test_loads_key_from_keychain_runner():
    def fake_runner(cmd):
        assert cmd[0] == "security"
        assert "find-generic-password" in cmd
        return "kc-secret-123\n"
    key = load_nvidia_api_key(runner=fake_runner, env={})
    assert key == "kc-secret-123"


def test_falls_back_to_env_when_keychain_misses():
    def fake_runner(cmd):
        raise FileNotFoundError("security miss")
    key = load_nvidia_api_key(runner=fake_runner, env={"NVIDIA_API_KEY": "env-secret"})
    assert key == "env-secret"


def test_raises_when_neither_source_has_key():
    def fake_runner(cmd):
        raise FileNotFoundError("security miss")
    with pytest.raises(RuntimeError, match="NVIDIA API key"):
        load_nvidia_api_key(runner=fake_runner, env={})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/bionemo/test_auth.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_claims.bionemo'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/polymer_claims/bionemo/__init__.py
"""BioNeMo evidence-adapter layer: turn NVIDIA NIM runs into certifiable claim evidence."""
```

```python
# src/polymer_claims/bionemo/auth.py
from __future__ import annotations

import getpass
import os
import subprocess
from collections.abc import Callable, Mapping


def _default_runner(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def load_nvidia_api_key(
    *,
    service: str = "nvidia-build-api",
    account: str | None = None,
    runner: Callable[[list[str]], str] | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    """Return the NVIDIA build.nvidia.com API key.

    Order: macOS keychain (`security find-generic-password -s <service> -w`), then the
    `NVIDIA_API_KEY` env var. Never reads a dotfile. `runner`/`env` are injectable for tests.
    """
    runner = runner or _default_runner
    env = os.environ if env is None else env
    account = account or getpass.getuser()
    cmd = ["security", "find-generic-password", "-s", service, "-a", account, "-w"]
    try:
        out = runner(cmd).strip()
        if out:
            return out
    except Exception:  # noqa: BLE001 — keychain miss is expected; fall through to env
        pass
    env_key = env.get("NVIDIA_API_KEY", "").strip()
    if env_key:
        return env_key
    raise RuntimeError(
        "NVIDIA API key not found. Add it to the keychain:\n"
        f"  security add-generic-password -s {service} -a {account} -w <KEY>\n"
        "or set NVIDIA_API_KEY in the environment."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project . pytest tests/bionemo/test_auth.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/bionemo/__init__.py src/polymer_claims/bionemo/auth.py tests/bionemo/__init__.py tests/bionemo/test_auth.py
git commit -m "feat(bionemo): scaffold package + keychain-backed API-key loader"
```

---

### Task 2: NIM REST client with injectable transport + disk cache

**Files:**
- Create: `src/polymer_claims/bionemo/client.py`
- Test: `tests/bionemo/test_client.py`

**Interfaces:**
- Consumes: `load_nvidia_api_key` (Task 1)
- Produces:
  - `NimRequest(endpoint: str, payload: dict)` (frozen dataclass)
  - `NimResponse(status: int, body: dict, model_version: str | None)` (frozen dataclass)
  - `Transport = Callable[[NimRequest, str], NimResponse]`
  - `NimClient(transport: Transport, *, cache_dir: Path, api_key: str, model_version_field: str = "model")` with `.call(req: NimRequest) -> NimResponse`

- [ ] **Step 1: Write the failing test**

```python
# tests/bionemo/test_client.py
from pathlib import Path
from polymer_claims.bionemo.client import NimClient, NimRequest, NimResponse


def _canned(req, api_key):
    assert api_key == "k"
    return NimResponse(status=200, body={"score": 0.12, "model": "openfold-2.1"}, model_version=None)


def test_call_returns_response_and_extracts_model_version(tmp_path):
    client = NimClient(transport=_canned, cache_dir=tmp_path, api_key="k")
    resp = client.call(NimRequest(endpoint="https://x/fold", payload={"seq": "MA"}))
    assert resp.body["score"] == 0.12
    assert resp.model_version == "openfold-2.1"


def test_second_identical_call_hits_cache_not_transport(tmp_path):
    calls = {"n": 0}

    def counting(req, api_key):
        calls["n"] += 1
        return NimResponse(status=200, body={"score": 0.12, "model": "m1"}, model_version=None)

    client = NimClient(transport=counting, cache_dir=tmp_path, api_key="k")
    req = NimRequest(endpoint="https://x/fold", payload={"seq": "MA"})
    a = client.call(req)
    b = client.call(req)
    assert calls["n"] == 1            # transport hit once; second served from cache
    assert a.body == b.body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/bionemo/test_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_claims.bionemo.client'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/polymer_claims/bionemo/client.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project . pytest tests/bionemo/test_client.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/bionemo/client.py tests/bionemo/test_client.py
git commit -m "feat(bionemo): NIM client with injectable transport + disk cache"
```

---

### Task 3: NIM apparatus record + materialization-context builder

**Files:**
- Create: `src/polymer_claims/bionemo/apparatus.py`
- Test: `tests/bionemo/test_apparatus.py`

**Interfaces:**
- Consumes: `MaterializationContext` (`from polymer_grammar import MaterializationContext`)
- Produces:
  - `BioNeMoApparatus(endpoint: str, model_id: str, model_version: str, payload_schema: tuple[str, ...])` (frozen dataclass) with `.content_hash() -> str`
  - `build_materialization_context(apparatus: BioNeMoApparatus, *, id: str, api_version: str, data_version: str) -> MaterializationContext`

- [ ] **Step 1: Write the failing test**

```python
# tests/bionemo/test_apparatus.py
from polymer_claims.bionemo.apparatus import BioNeMoApparatus, build_materialization_context


def _app():
    return BioNeMoApparatus(
        endpoint="https://x/fold", model_id="openfold", model_version="2.1",
        payload_schema=("sequence",),
    )


def test_content_hash_is_deterministic_and_prefixed():
    h1 = _app().content_hash()
    h2 = _app().content_hash()
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_context_carries_apparatus_provenance():
    ctx = build_materialization_context(_app(), id="M1", api_version="v1", data_version="d1")
    assert ctx.semantic_run_id == _app().content_hash()
    assert ctx.profile_hash == _app().content_hash()
    assert "nim:openfold@2.1" in ctx.shared_cause_factors
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/bionemo/test_apparatus.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/polymer_claims/bionemo/apparatus.py
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from polymer_grammar import MaterializationContext


@dataclass(frozen=True)
class BioNeMoApparatus:
    """Pinned record of WHICH NIM produced evidence: endpoint + model id/version + the
    payload field names. Hashed into MaterializationContext provenance so a certificate
    records the exact NIM. NOT the methylation AnalysisProfile (that schema is array-specific)."""

    endpoint: str
    model_id: str
    model_version: str
    payload_schema: tuple[str, ...]

    def content_hash(self) -> str:
        canonical = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def build_materialization_context(
    apparatus: BioNeMoApparatus, *, id: str, api_version: str, data_version: str
) -> MaterializationContext:
    digest = apparatus.content_hash()
    return MaterializationContext(
        id=id,
        api_version=api_version,
        data_version=data_version,
        note=f"bionemo:{apparatus.model_id}@{apparatus.model_version}",
        semantic_run_id=digest,
        profile_hash=digest,
        shared_cause_factors=(f"nim:{apparatus.model_id}@{apparatus.model_version}",),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project . pytest tests/bionemo/test_apparatus.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/bionemo/apparatus.py tests/bionemo/test_apparatus.py
git commit -m "feat(bionemo): apparatus record + materialization-context provenance"
```

---

### Task 4: `BioNeMoNIMAdapter` execution adapter

**Files:**
- Create: `src/polymer_claims/bionemo/adapters.py`
- Test: `tests/bionemo/test_adapters.py`

**Interfaces:**
- Consumes: `NimClient`, `NimRequest` (Task 2); `OperationNode`, `DataHandle`, `ExecValue`, `MaterializationContext` (`from polymer_grammar import ...`)
- Produces: `BioNeMoNIMAdapter(client, *, impl: str, endpoint: str, value_path: tuple[str, ...], substrate: Mapping[str, dict], identity: str = "bionemo-nim")` implementing the `Adapter` protocol.

- [ ] **Step 1: Write the failing test**

```python
# tests/bionemo/test_adapters.py
import pytest
from polymer_grammar import DataHandle, MaterializationContext, OperationNode, ProducedLeafSpec
from polymer_grammar import MeasurementBasis
from polymer_claims.bionemo.adapters import BioNeMoNIMAdapter
from polymer_claims.bionemo.client import NimClient, NimRequest, NimResponse


def _client(tmp_path, value):
    def transport(req: NimRequest, api_key: str) -> NimResponse:
        return NimResponse(status=200, body={"out": {"score": value}, "model": "m1"}, model_version=None)
    return NimClient(transport=transport, cache_dir=tmp_path, api_key="k")


def _node(impl="bionemo::plumbing"):
    return OperationNode(
        id="n0", impl=impl, inputs=(DataHandle(ref="seq1"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def _ctx():
    return MaterializationContext(id="M1", api_version="v1", data_version="d1")


def test_adapter_maps_nim_response_to_execvalue(tmp_path):
    adapter = BioNeMoNIMAdapter(
        _client(tmp_path, 0.12), impl="bionemo::plumbing", endpoint="https://x/fold",
        value_path=("out", "score"), substrate={"seq1": {"sequence": "MAAA"}},
    )
    out = adapter.execute(_node(), (), _ctx())
    assert out.value == pytest.approx(0.12)


def test_adapter_raises_on_unhandled_impl(tmp_path):
    adapter = BioNeMoNIMAdapter(
        _client(tmp_path, 0.12), impl="bionemo::plumbing", endpoint="https://x/fold",
        value_path=("out", "score"), substrate={"seq1": {"sequence": "MAAA"}},
    )
    with pytest.raises(ValueError, match="cannot execute impl"):
        adapter.execute(_node(impl="stats::mean_diff"), (), _ctx())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/bionemo/test_adapters.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/polymer_claims/bionemo/adapters.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from polymer_grammar import DataHandle, ExecValue, MaterializationContext, OperationNode

from .client import NimClient, NimRequest


class BioNeMoNIMAdapter:
    """Execution adapter: resolve a node's DataHandle to a NIM payload, call the NIM, and
    map one numeric response field to an ExecValue. Self-selects on `node.impl` and raises
    otherwise (the evaluator degrades a raise to a node error, never crashes)."""

    def __init__(
        self,
        client: NimClient,
        *,
        impl: str,
        endpoint: str,
        value_path: tuple[str, ...],
        substrate: Mapping[str, dict],
        identity: str = "bionemo-nim",
    ) -> None:
        self.client = client
        self.impl = impl
        self.endpoint = endpoint
        self.value_path = value_path
        self.substrate = substrate
        self.identity = identity

    def execute(
        self, node: OperationNode, upstream: tuple[ExecValue, ...], ctx: MaterializationContext
    ) -> ExecValue:
        if node.impl != self.impl:
            raise ValueError(f"{self.identity} cannot execute impl {node.impl!r}")
        handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
        if handle is None:
            raise ValueError(f"{self.identity} node {node.id!r} has no DataHandle input")
        payload = self.substrate.get(handle.ref)
        if payload is None:
            raise ValueError(f"{self.identity} substrate missing ref {handle.ref!r}")
        resp = self.client.call(NimRequest(endpoint=self.endpoint, payload=dict(payload)))
        cursor: Any = resp.body
        for key in self.value_path:
            cursor = cursor[key]
        return ExecValue(value=float(cursor))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project . pytest tests/bionemo/test_adapters.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/bionemo/adapters.py tests/bionemo/test_adapters.py
git commit -m "feat(bionemo): NIM execution adapter (response -> ExecValue)"
```

---

### Task 5: Fenced synthetic corroborator (test double)

**Files:**
- Create: `tests/fixtures/__init__.py`
- Create: `tests/fixtures/synthetic_corroborator.py`
- Test: `tests/bionemo/test_corroborator.py`

**Interfaces:**
- Consumes: `OperationNode`, `ExecValue`, `MaterializationContext` (`from polymer_grammar import ...`)
- Produces: `SyntheticCorroboratorAdapter(*, impl: str, value: float, identity: str = "synthetic-corroborator")`

- [ ] **Step 1: Write the failing test**

```python
# tests/bionemo/test_corroborator.py
import pytest
from polymer_grammar import MaterializationContext, OperationNode, ProducedLeafSpec, MeasurementBasis
from tests.fixtures.synthetic_corroborator import SyntheticCorroboratorAdapter


def _node(impl="bionemo::plumbing"):
    return OperationNode(
        id="n0", impl=impl,
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_corroborator_returns_fixed_value():
    a = SyntheticCorroboratorAdapter(impl="bionemo::plumbing", value=0.12)
    out = a.execute(_node(), (), MaterializationContext(id="M1", api_version="v1", data_version="d1"))
    assert out.value == pytest.approx(0.12)


def test_corroborator_raises_on_unhandled_impl():
    a = SyntheticCorroboratorAdapter(impl="bionemo::plumbing", value=0.12)
    with pytest.raises(ValueError):
        a.execute(_node(impl="other::x"), (), MaterializationContext(id="M1", api_version="v1", data_version="d1"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/bionemo/test_corroborator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.fixtures'`

- [ ] **Step 3: Write minimal implementation**

```python
# tests/fixtures/__init__.py
```

```python
# tests/fixtures/synthetic_corroborator.py
"""TEST DOUBLE ONLY — DO NOT SHIP IN A PRODUCTION ADAPTER REGISTRY.

The air-gap needs two INDEPENDENTLY-OWNED adapters that agree before a license is minted.
This fixture is the independent corroborator used to validate the BioNeMo plumbing end-to-end.
Its credential MUST use a non-"NVIDIA" owner and may appear ONLY in a plumbing-validation
AdapterRegistry — NEVER in `polymer_claims.bionemo.registry`. When a real scientific wedge is
chosen, this is replaced by a real independent model (ESMFold / AlphaMissense / ...) and barred
from any certifying run. No synthetic corroboration may launder into a real claim.
"""
from __future__ import annotations

from polymer_grammar import ExecValue, MaterializationContext, OperationNode


class SyntheticCorroboratorAdapter:
    def __init__(self, *, impl: str, value: float, identity: str = "synthetic-corroborator") -> None:
        self.impl = impl
        self.value = value
        self.identity = identity

    def execute(
        self, node: OperationNode, upstream: tuple[ExecValue, ...], ctx: MaterializationContext
    ) -> ExecValue:
        if node.impl != self.impl:
            raise ValueError(f"{self.identity} cannot execute impl {node.impl!r}")
        return ExecValue(value=float(self.value))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project . pytest tests/bionemo/test_corroborator.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/__init__.py tests/fixtures/synthetic_corroborator.py tests/bionemo/test_corroborator.py
git commit -m "test(bionemo): fenced synthetic corroborator double"
```

---

### Task 6: BioNeMo adapter credential + oracle dossier builders

**Files:**
- Create: `src/polymer_claims/bionemo/registry.py`
- Create: `src/polymer_claims/bionemo/oracle.py`
- Test: `tests/bionemo/test_registry.py`, `tests/bionemo/test_oracle.py`

**Interfaces:**
- Consumes: `implementation_hash_for_adapter` (`from polymer_claims.adapter_identity import implementation_hash_for_adapter`); `AdapterCredential` (`from polymer_protocol import AdapterCredential`); `adapters_independent` (`from polymer_protocol.adapter_registry import adapters_independent`); `OracleRegistry` (`from polymer_protocol import OracleRegistry`); `OracleDossier, ValidationTier, ApplicabilityDomain` (`from polymer_grammar import ...`)
- Produces:
  - `bionemo_credential(adapter_cls: type, *, identity: str, owner: str = "NVIDIA", version: str = "v1") -> AdapterCredential`
  - `bionemo_oracle_registry(*, oracle_id: str, tier: ValidationTier = ValidationTier.INDIRECT, subject_kinds: tuple[str, ...] = (), anchor: str | None = None) -> OracleRegistry`

- [ ] **Step 1: Write the failing tests**

```python
# tests/bionemo/test_registry.py
from polymer_protocol.adapter_registry import adapters_independent
from polymer_claims.bionemo.registry import bionemo_credential
from polymer_claims.bionemo.adapters import BioNeMoNIMAdapter
from tests.fixtures.synthetic_corroborator import SyntheticCorroboratorAdapter


def test_credential_records_nvidia_owner_and_sha256_hash():
    cred = bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim")
    assert cred.owner == "NVIDIA"
    assert cred.identity == "bionemo-nim"
    assert cred.implementation_hash.startswith("sha256:")
    assert cred.trusted is True


def test_bionemo_and_synthetic_are_independent():
    nvidia = bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim")
    synthetic = bionemo_credential(
        SyntheticCorroboratorAdapter, identity="synthetic-corroborator", owner="polymer-claims-test"
    )
    assert adapters_independent(nvidia, synthetic) is True


def test_same_class_pair_is_not_independent():
    a = bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim")
    b = bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim-2")
    assert adapters_independent(a, b) is False   # same owner AND same impl hash
```

```python
# tests/bionemo/test_oracle.py
from polymer_grammar import ValidationTier
from polymer_claims.bionemo.oracle import bionemo_oracle_registry


def test_oracle_registry_resolves_conservative_tier():
    reg = bionemo_oracle_registry(oracle_id="bionemo-plumbing@v1")
    dossier = reg.resolve("bionemo-plumbing@v1")
    assert dossier is not None
    assert dossier.validation_tier == ValidationTier.INDIRECT   # never ANCHORED for pure compute


def test_oracle_default_domain_is_unbounded():
    reg = bionemo_oracle_registry(oracle_id="bionemo-plumbing@v1")
    dossier = reg.resolve("bionemo-plumbing@v1")
    assert dossier.applicability_domain.subject_kinds == ()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project . pytest tests/bionemo/test_registry.py tests/bionemo/test_oracle.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementations**

```python
# src/polymer_claims/bionemo/registry.py
from __future__ import annotations

from polymer_protocol import AdapterCredential

from polymer_claims.adapter_identity import implementation_hash_for_adapter


def bionemo_credential(
    adapter_cls: type, *, identity: str, owner: str = "NVIDIA", version: str = "v1"
) -> AdapterCredential:
    """Operator-asserted trust metadata for a BioNeMo adapter class. `implementation_hash`
    is derived from the class's `execute` bytecode. PRODUCTION builders here must only ever
    carry real, independently-owned sources — never the synthetic test corroborator."""
    return AdapterCredential(
        identity=identity,
        owner=owner,
        implementation_hash=implementation_hash_for_adapter(adapter_cls),
        version=version,
        trusted=True,
    )
```

```python
# src/polymer_claims/bionemo/oracle.py
from __future__ import annotations

from polymer_grammar import ApplicabilityDomain, OracleDossier, ValidationTier
from polymer_protocol import OracleRegistry


def bionemo_oracle_registry(
    *,
    oracle_id: str,
    tier: ValidationTier = ValidationTier.INDIRECT,
    subject_kinds: tuple[str, ...] = (),
    anchor: str | None = None,
) -> OracleRegistry:
    """One-dossier registry capping a BioNeMo-evidenced claim's strength at `tier`.

    Default `INDIRECT`: a pure-compute NIM checked against literature/heuristic values, with
    no direct wet-lab anchor for the subject. NEVER default to ANCHORED/GOLD — those require a
    real bounded wet-lab/clinical anchor. `subject_kinds=()` leaves the domain unbounded.
    """
    return OracleRegistry(
        dossiers=(
            OracleDossier(
                oracle_id=oracle_id,
                validation_tier=tier,
                applicability_domain=ApplicabilityDomain(subject_kinds=subject_kinds),
                anchor=anchor,
            ),
        )
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project . pytest tests/bionemo/test_registry.py tests/bionemo/test_oracle.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/bionemo/registry.py src/polymer_claims/bionemo/oracle.py tests/bionemo/test_registry.py tests/bionemo/test_oracle.py
git commit -m "feat(bionemo): adapter-credential + conservative oracle-dossier builders"
```

---

### Task 7: Worked example — cached NIM run licenses a claim (no oracle)

**Files:**
- Create: `examples/bionemo_plumbing/__init__.py`
- Create: `examples/bionemo_plumbing/cassette.json`
- Create: `examples/bionemo_plumbing/run.py`
- Test: `tests/bionemo/test_integration_plumbing.py`

**Interfaces:**
- Consumes: everything from Tasks 1–6; `Claim, CategoricalLeaf, Comparator, ComputeGraph, EvaluationPlan, FDRLedger, MaterializationContext, MeasurementBasis, OperationNode, DataHandle, PatternRef, PendingReason, ProducedLeafSpec, SatisfactionCriterion, Status` (`from polymer_grammar import ...`); `Corpus, run_cycle, AdapterRegistry` (`from polymer_protocol import ...`)
- Produces: `build_plumbing_corpus() -> tuple[Corpus, MaterializationContext, tuple, AdapterRegistry]` and `run_plumbing(cache_dir) -> CycleResult` in `run.py`

**Notes on agreement:** the air-gap mints a Satisfaction only if both adapters' verdicts match, their terminal values agree within tolerance (abs 1e-9 / rel 1e-6), and the verdict is SATISFIED. So the synthetic corroborator's `value` is set equal to the cassette's numeric field, and the criterion (`LT 0.5` over a value of `0.12`) is satisfied by both. `oracle_ref=None` here — the oracle is wired in Task 9.

- [ ] **Step 1: Write the failing test**

```python
# tests/bionemo/test_integration_plumbing.py
from polymer_grammar import Status
from examples.bionemo_plumbing.run import run_plumbing


def test_cached_nim_run_licenses_the_claim(tmp_path):
    result = run_plumbing(cache_dir=tmp_path)
    claim = result.corpus.by_id()["bionemo-plumbing-1"]
    assert claim.status == Status.LICENSED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/bionemo/test_integration_plumbing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'examples.bionemo_plumbing.run'`

- [ ] **Step 3: Write the cassette + the implementation**

```json
// examples/bionemo_plumbing/cassette.json
{"status": 200, "body": {"out": {"score": 0.12}, "model": "plumbing-nim-1.0"}, "model_version": "plumbing-nim-1.0"}
```

```python
# examples/bionemo_plumbing/__init__.py
```

```python
# examples/bionemo_plumbing/run.py
"""End-to-end plumbing: a cached BioNeMo NIM run + a fenced synthetic corroborator drive ONE
claim to LICENSED, offline. Deferred-wedge: the metric here is a neutral plumbing score."""
from __future__ import annotations

import json
from pathlib import Path

from polymer_grammar import (
    CategoricalLeaf, Claim, Comparator, ComputeGraph, DataHandle, EvaluationPlan, FDRLedger,
    MeasurementBasis, OperationNode, PatternRef, PendingReason, ProducedLeafSpec,
    SatisfactionCriterion, Status,
)
from polymer_protocol import AdapterRegistry, Corpus, run_cycle

from polymer_claims.bionemo.adapters import BioNeMoNIMAdapter
from polymer_claims.bionemo.apparatus import BioNeMoApparatus, build_materialization_context
from polymer_claims.bionemo.client import NimClient, NimRequest, NimResponse
from polymer_claims.bionemo.registry import bionemo_credential

import sys
# import the fenced fixture (lives under tests/, not shipped in the package)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.fixtures.synthetic_corroborator import SyntheticCorroboratorAdapter  # noqa: E402

_IMPL = "bionemo::plumbing"
_CLAIM_ID = "bionemo-plumbing-1"
_CASSETTE = Path(__file__).with_name("cassette.json")


def _cassette_transport(req: NimRequest, api_key: str) -> NimResponse:
    rec = json.loads(_CASSETTE.read_text())
    return NimResponse(status=rec["status"], body=rec["body"], model_version=rec["model_version"])


def _claim() -> Claim:
    node = OperationNode(
        id="n0", impl=_IMPL, inputs=(DataHandle(ref="seq1"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.5),
    )
    return Claim(
        id=_CLAIM_ID, title="BioNeMo plumbing claim",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="plumbing"),),
        status=Status.PENDING, pending_reason=PendingReason.UNTESTED,
        evaluation_plan=plan,
    )


def run_plumbing(cache_dir):
    cassette = json.loads(_CASSETTE.read_text())
    score = cassette["body"]["out"]["score"]

    apparatus = BioNeMoApparatus(
        endpoint="https://example/nim/plumbing", model_id="plumbing-nim",
        model_version=cassette["model_version"], payload_schema=("sequence",),
    )
    ctx = build_materialization_context(apparatus, id="M1", api_version="v1", data_version="d1")

    client = NimClient(transport=_cassette_transport, cache_dir=Path(cache_dir), api_key="cassette")
    bionemo = BioNeMoNIMAdapter(
        client, impl=_IMPL, endpoint=apparatus.endpoint, value_path=("out", "score"),
        substrate={"seq1": {"sequence": "MAAAAA"}}, identity="bionemo-nim",
    )
    corroborator = SyntheticCorroboratorAdapter(impl=_IMPL, value=score)

    registry = AdapterRegistry(credentials=(
        bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim"),
        bionemo_credential(
            SyntheticCorroboratorAdapter, identity="synthetic-corroborator", owner="polymer-claims-test"
        ),
    ))

    corpus = Corpus(claims=(_claim(),), fdr_ledger=FDRLedger(target_fdr=0.05))
    return run_cycle(corpus, (bionemo, corroborator), ctx, adapter_registry=registry)


if __name__ == "__main__":  # pragma: no cover
    import tempfile
    res = run_plumbing(cache_dir=tempfile.mkdtemp())
    print(res.corpus.by_id()[_CLAIM_ID].status)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project . pytest tests/bionemo/test_integration_plumbing.py -v`
Expected: PASS — claim status `LICENSED`.
(If it is PENDING, inspect `result.audit` and the agreement: confirm the corroborator value equals the cassette score and that `Comparator.LT` exists in `polymer_grammar`; adjust the threshold/value only, not the architecture.)

- [ ] **Step 5: Commit**

```bash
git add examples/bionemo_plumbing/ tests/bionemo/test_integration_plumbing.py
git commit -m "feat(bionemo): worked example — cached NIM run licenses a claim (offline)"
```

---

### Task 8: Certify the licensed plumbing claim

**Files:**
- Modify: `examples/bionemo_plumbing/run.py` (add `certify_plumbing`)
- Test: `tests/bionemo/test_integration_plumbing.py` (add a test)

**Interfaces:**
- Consumes: `build_certificate` (`from polymer_claims.attestation import build_certificate`)
- Produces: `certify_plumbing(cache_dir) -> Certificate`

- [ ] **Step 1: Write the failing test**

```python
# tests/bionemo/test_integration_plumbing.py  (append)
def test_licensed_claim_can_be_certified(tmp_path):
    from examples.bionemo_plumbing.run import certify_plumbing
    cert = certify_plumbing(cache_dir=tmp_path)
    assert cert.statement is not None
    assert any(sub.name == "bionemo-plumbing-1" for sub in cert.statement.subject)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/bionemo/test_integration_plumbing.py::test_licensed_claim_can_be_certified -v`
Expected: FAIL with `ImportError: cannot import name 'certify_plumbing'`

- [ ] **Step 3: Write the implementation**

```python
# examples/bionemo_plumbing/run.py  (append)
from polymer_claims.attestation import build_certificate  # noqa: E402


def certify_plumbing(cache_dir):
    """Run the plumbing loop, then build a single-claim certificate. Statements are
    reconstructed on-demand from the LICENSED claim's licensing field (run_cycle does not
    store them), so a plain corpus is all build_certificate needs."""
    result = run_plumbing(cache_dir=cache_dir)
    return build_certificate(result.corpus, _CLAIM_ID, ledger=None, target_q=0.05)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project . pytest tests/bionemo/test_integration_plumbing.py -v`
Expected: PASS (2 tests).
(If `build_certificate` raises about a missing contract index for this oracle-free claim, pass `contract_index=resolve_contract_index(result.corpus)` explicitly — `from polymer_claims.attestation import resolve_contract_index` — but the default path should resolve it.)

- [ ] **Step 5: Commit**

```bash
git add examples/bionemo_plumbing/run.py tests/bionemo/test_integration_plumbing.py
git commit -m "feat(bionemo): certify the licensed plumbing claim end-to-end"
```

---

### Task 9: Wire the oracle into the worked example (strength cap), assert still LICENSED

**Files:**
- Modify: `examples/bionemo_plumbing/run.py` (set `oracle_ref` + pass `oracles`)
- Test: `tests/bionemo/test_integration_plumbing.py` (add a test)

**Interfaces:**
- Consumes: `bionemo_oracle_registry` (Task 6)
- Produces: `run_plumbing(cache_dir, *, with_oracle: bool = True)` — adds an optional oracle path; existing callers keep current behavior via the default.

- [ ] **Step 1: Write the failing test**

```python
# tests/bionemo/test_integration_plumbing.py  (append)
def test_oracle_bound_claim_still_licenses_and_resolves(tmp_path):
    from polymer_grammar import Status, ValidationTier
    from polymer_claims.bionemo.oracle import bionemo_oracle_registry
    from examples.bionemo_plumbing.run import run_plumbing

    result = run_plumbing(cache_dir=tmp_path, with_oracle=True)
    claim = result.corpus.by_id()["bionemo-plumbing-1"]
    assert claim.status == Status.LICENSED

    reg = bionemo_oracle_registry(oracle_id="bionemo-plumbing@v1")
    assert reg.resolve("bionemo-plumbing@v1").validation_tier == ValidationTier.INDIRECT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/bionemo/test_integration_plumbing.py::test_oracle_bound_claim_still_licenses_and_resolves -v`
Expected: FAIL — `run_plumbing()` has no `with_oracle` keyword.

- [ ] **Step 3: Write the implementation**

Edit `_claim()` to accept an oracle ref, and thread an oracle registry through `run_plumbing`:

```python
# examples/bionemo_plumbing/run.py  (replace _claim and run_plumbing signatures)
from polymer_claims.bionemo.oracle import bionemo_oracle_registry  # noqa: E402

_ORACLE_ID = "bionemo-plumbing@v1"


def _claim(oracle_ref=None) -> Claim:
    node = OperationNode(
        id="n0", impl=_IMPL, inputs=(DataHandle(ref="seq1"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
        oracle_ref=oracle_ref,
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.5),
    )
    return Claim(
        id=_CLAIM_ID, title="BioNeMo plumbing claim",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="plumbing"),),
        status=Status.PENDING, pending_reason=PendingReason.UNTESTED,
        evaluation_plan=plan,
    )


def run_plumbing(cache_dir, *, with_oracle: bool = False):
    cassette = json.loads(_CASSETTE.read_text())
    score = cassette["body"]["out"]["score"]
    apparatus = BioNeMoApparatus(
        endpoint="https://example/nim/plumbing", model_id="plumbing-nim",
        model_version=cassette["model_version"], payload_schema=("sequence",),
    )
    ctx = build_materialization_context(apparatus, id="M1", api_version="v1", data_version="d1")
    client = NimClient(transport=_cassette_transport, cache_dir=Path(cache_dir), api_key="cassette")
    bionemo = BioNeMoNIMAdapter(
        client, impl=_IMPL, endpoint=apparatus.endpoint, value_path=("out", "score"),
        substrate={"seq1": {"sequence": "MAAAAA"}}, identity="bionemo-nim",
    )
    corroborator = SyntheticCorroboratorAdapter(impl=_IMPL, value=score)
    registry = AdapterRegistry(credentials=(
        bionemo_credential(BioNeMoNIMAdapter, identity="bionemo-nim"),
        bionemo_credential(
            SyntheticCorroboratorAdapter, identity="synthetic-corroborator", owner="polymer-claims-test"
        ),
    ))
    oracle_ref = _ORACLE_ID if with_oracle else None
    corpus = Corpus(claims=(_claim(oracle_ref=oracle_ref),), fdr_ledger=FDRLedger(target_fdr=0.05))
    oracles = bionemo_oracle_registry(oracle_id=_ORACLE_ID) if with_oracle else None
    return run_cycle(corpus, (bionemo, corroborator), ctx, oracles=oracles, adapter_registry=registry)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project . pytest tests/bionemo/test_integration_plumbing.py -v`
Expected: PASS (3 tests). The claim licenses with the oracle bound; the INDIRECT dossier resolves.
(If binding the oracle blocks licensing, that is a real oracle-cap-vs-license finding: report it; do not loosen the tier below `INDIRECT` to force a pass.)

- [ ] **Step 5: Commit**

```bash
git add examples/bionemo_plumbing/run.py tests/bionemo/test_integration_plumbing.py
git commit -m "feat(bionemo): bind oracle dossier to the worked example (strength cap)"
```

---

### Task 10: Opt-in live smoke test + example README

**Files:**
- Create: `tests/bionemo/test_live_smoke.py`
- Create: `examples/bionemo_plumbing/README.md`

**Interfaces:**
- Consumes: `NimClient`, `urllib_transport` (Task 2); `load_nvidia_api_key` (Task 1)

- [ ] **Step 1: Write the (skipped-by-default) live test**

```python
# tests/bionemo/test_live_smoke.py
import os
import pytest

LIVE = os.environ.get("POLYMER_BIONEMO_LIVE") == "1"
pytestmark = pytest.mark.skipif(not LIVE, reason="set POLYMER_BIONEMO_LIVE=1 + a real key to run")


def test_live_nim_returns_numeric(tmp_path):
    from polymer_claims.bionemo.auth import load_nvidia_api_key
    from polymer_claims.bionemo.client import NimClient, NimRequest, urllib_transport

    endpoint = os.environ["POLYMER_BIONEMO_ENDPOINT"]   # operator supplies the NIM URL
    client = NimClient(
        transport=urllib_transport, cache_dir=tmp_path, api_key=load_nvidia_api_key()
    )
    resp = client.call(NimRequest(endpoint=endpoint, payload={"sequence": "MAAAAA"}))
    assert resp.status == 200
    assert isinstance(resp.body, dict)
```

- [ ] **Step 2: Run to verify it is collected but skipped**

Run: `uv run --project . pytest tests/bionemo/test_live_smoke.py -v`
Expected: SKIPPED (1 skipped) — no live network in CI.

- [ ] **Step 3: Write the README**

```markdown
# BioNeMo plumbing example

Proves the full evidence loop offline: a cached BioNeMo NIM response + a fenced synthetic
corroborator drive one claim to `LICENSED`, then `certify` emits a certificate.

## Run (offline, from a cassette)

```bash
uv run --project . python -m examples.bionemo_plumbing.run
# prints: Status.LICENSED
```

## Certify

```bash
# run.certify_plumbing() builds the certificate in-process; or via the CLI on a saved corpus:
polymer-claims certify bionemo-plumbing-1 --corpus <saved-corpus.json> --format text
```

## Going live (real NIM)

1. Store the key in the macOS keychain (never a dotfile):
   ```bash
   security add-generic-password -s nvidia-build-api -a "$USER" -w <YOUR_NVIDIA_API_KEY>
   ```
2. Run the live smoke test against a hosted NIM:
   ```bash
   POLYMER_BIONEMO_LIVE=1 POLYMER_BIONEMO_ENDPOINT=<nim-url> \
     uv run --project . pytest tests/bionemo/test_live_smoke.py -v
   ```
   build.nvidia.com starts with free credits; responses cache to disk so re-runs do not reburn them.

## The synthetic-corroborator fence

`tests/fixtures/synthetic_corroborator.py` is a TEST DOUBLE. Its credential (owner
`polymer-claims-test`) may appear ONLY in a plumbing `AdapterRegistry` — never in
`polymer_claims.bionemo.registry`. The air-gap needs two independently-owned adapters; when a
real wedge is chosen (variant-effect scoring + an independent VEP, etc.), the double is replaced
by a real second model and barred from any certifying run.
```

- [ ] **Step 4: Run the full suite + ruff**

Run: `bash scripts/check-all.sh`
Expected: all tests pass (existing 1200+ plus the new bionemo tests), ruff clean.

- [ ] **Step 5: Commit**

```bash
git add tests/bionemo/test_live_smoke.py examples/bionemo_plumbing/README.md
git commit -m "feat(bionemo): opt-in live smoke test + example README"
```

---

## Self-Review

**Spec coverage:**
- §3.3 #1 client → Task 2. #2 adapter → Task 4. #3 oracle → Task 6 + Task 9. #4 registry/credentials → Task 6. #5 apparatus record → Task 3. ✓
- §3.4 air-gap + fenced synthetic corroborator → Task 5 (double) + Task 7 (registry wiring) + Task 10 (README fence). ✓
- §3.5 data flow (node → 2 adapters → verify → oracle cap → LICENSED → certify) → Tasks 7–9. ✓
- §3.6 error handling (adapter raises → PENDING, never false license) → adapter raise paths in Tasks 4/5; covered by the unhandled-impl tests. ✓
- §3.7 worked example + offline cassette + opt-in live smoke → Tasks 7, 8, 10. ✓
- Auth from keychain → Task 1. ✓
- §3.8 out-of-scope items (no science, no new subject kinds, no SE-Contract seam) are respected — the plumbing metric is neutral and `oracle_ref` binds without a methylation profile. ✓

**Placeholder scan:** No TBD/TODO; every code step shows real code. The two "if it fails, investigate" notes (Tasks 7, 8, 9) point at concrete fallbacks (threshold/value, `contract_index=resolve_contract_index(...)`, report-don't-loosen) rather than deferred work. ✓

**Type consistency:** `_IMPL = "bionemo::plumbing"` and `_CLAIM_ID = "bionemo-plumbing-1"` are used consistently across Tasks 7–9. `BioNeMoNIMAdapter` constructor signature (Task 4) matches its use in Task 7. `bionemo_credential` / `bionemo_oracle_registry` signatures (Task 6) match their callers (Tasks 7, 9). `NimResponse(status, body, model_version)` consistent across Tasks 2, 4, 7, 10. ✓

**Note for the implementer:** confirm `Comparator.LT` and `ValidationTier.INDIRECT` exist in `polymer_grammar` (verified in extraction); the worked example depends on both.
