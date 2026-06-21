# Sheaf Gauge Viewer Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the sheaf consistency gauge legible on the live 3D universe — a falling energy HUD, per-claim tension halos, and H¹ frustration-cycle overlays — fed by a new throttled `GET /consistency` endpoint, behind one opt-in toggle.

**Architecture:** Two-channel data plane by cost: the cheap **energy-only** headline rides every frame (`TopologyExport.consistency`); the expensive `ConsistencyReport` (λ₂, H⁰, H¹, tension) comes from a new on-demand `GET /consistency` route that snapshots the frozen corpus under the lock then computes in a worker thread. The viewer pulls it (throttled), joins tension by `claim_id`, and renders an overlay/halos/HUD gated by a single toggle. Three prerequisite corrections to the already-merged gauge land first.

**Tech Stack:** Python 3.12, pydantic v2 (frozen `_Model`), numpy (behind `[embed]`), FastAPI SSE, pytest; TypeScript, Next 16, React Three Fiber + drei, Zustand. `uv` for Python.

**Spec:** `docs/superpowers/specs/2026-06-21-sheaf-viewer-viz-design.md` (read it; §2 prerequisites, §9 sequencing, §11 audit reconciliation).

## Global Constraints

- **No per-tick eigendecomposition.** The per-frame headline path must be an O(edges) mat-vec; `eigvalsh` runs only in `consistency_report` (on-demand).
- **`[embed]` gate:** sheaf compute needs numpy. Absent → frame `consistency` is `null`; `GET /consistency` returns `{available: false}`. Viewer degrades silently (no errors).
- **One toggle, off-safe (rendered view):** `overlayOn === false` ⇒ no fetch, no overlay, no halos, no HUD ⇒ rendered chrome + 3D scene unchanged from today. (The frame payload always carries `consistency`; the invariant is the *rendered view*, not byte-identical JSON.)
- **Schema discipline:** P1 retains `ConsistencyHeadline.spectral_gap` as `float | None = None` (schema-compatible for first-party consumers; no `CONTRACT_VERSION` bump). P3 keeps the `per_claim_tension` field, changes only its computation.
- **Purity:** `protocol/`/`grammar/` stay pure/numpy-free; all numpy + the new route are umbrella-side (`src/polymer_claims/`). Frozen `_Model`, tuple collection fields.
- **Discriminated response:** `{available:false} | ({available:true} & ConsistencyReport)`; the UI keys "disabled" off `available===false`, distinct from a real empty report.
- **Per-package gate:** `uv run pytest -q` + `uv run ruff check src tests`. Viewer gate: `cd viewer && npm run typecheck && npm run build`. Float outputs round to 6dp (`_ROUND`).
- **TDD:** failing test first. Commit per task. Merge `--no-ff` to `main` at the end.

## File Structure

**Backend (modify merged gauge + add route):**
- `protocol/src/polymer_protocol/sheaf.py` — `ConsistencyHeadline.spectral_gap` → `float | None = None` (P1).
- `src/polymer_claims/sheaf_spectrum.py` — `_energy()` helper + energy-only `consistency_headline` (P1); edge-share `per_claim_tension` (P3).
- `src/polymer_claims/server.py` — new `GET /consistency` (snapshot-then-release, P2).
- Tests: `tests/test_sheaf_spectrum.py`, the existing server test file (locate via `grep -rl "create_app\|/claim/" tests`).

**Frontend (`viewer/src/`):**
- `lib/topology.ts` — wire types (`ConsistencyHeadline`, `consistency?`, `ConsistencyReport`, `Obstruction`, `ClaimTension`).
- `lib/live.ts` — `ConsistencyResponse` envelope + `fetchConsistency` helper.
- `lib/interpolate.ts` — forward frame-level `consistency`.
- `store.ts` — overlay state, report, derived `tensionByClaimId`/`maxTension`/`obstructions`, `fetchConsistency` action.
- `components/scene/Nodes.tsx` — tension halo on `NodeMesh`.
- `components/scene/Obstructions.tsx` — **new** H¹ overlay pass.
- `components/chrome/EnergyHud.tsx` — **new** HUD + sparkline.
- `components/chrome/RightRail.tsx` — obstruction panel + node tension.
- `components/chrome/LiveControl.tsx` — the overlay toggle.
- `components/ClaimUniverse.tsx` — mount `<Obstructions/>` + `<EnergyHud/>` + `useConsistencySync()`.
- `lib/theme.ts` — tension heat scale + obstruction color.

---

### Task 1: P1 — energy-only per-frame headline (schema-stable)

**Files:**
- Modify: `protocol/src/polymer_protocol/sheaf.py` (the `ConsistencyHeadline` model)
- Modify: `src/polymer_claims/sheaf_spectrum.py` (add `_energy`, rewrite `consistency_headline`)
- Test: `tests/test_sheaf_spectrum.py`

**Interfaces:**
- Consumes: `_coboundary(structure) -> (x, delta, w, kinds)`, `_ROUND`, `ConsistencyHeadline` (all in `sheaf_spectrum.py`/`sheaf.py`).
- Produces: `_energy(structure) -> float`; `consistency_headline(structure) -> ConsistencyHeadline` now sets `spectral_gap=None` and runs **no** eigendecomposition. `ConsistencyHeadline.spectral_gap: float | None = None`.

- [ ] **Step 1: Make `spectral_gap` nullable on the DTO**

In `protocol/src/polymer_protocol/sheaf.py`, change the `ConsistencyHeadline` model:

```python
class ConsistencyHeadline(_Model):
    inconsistency_energy: float
    spectral_gap: float | None = None
```

- [ ] **Step 2: Write the failing test**

In `tests/test_sheaf_spectrum.py` (it already imports `pytest`, `np`, and has a `_vert` helper + `SheafStructure`/`SheafEdge` imports — reuse them):

```python
def test_headline_is_energy_only_no_eigendecomposition(monkeypatch):
    import polymer_claims.sheaf_spectrum as ss
    s = SheafStructure(
        vertices=(_vert("a", 1.0), _vert("b", 4.0)),
        edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=2.0, sign=1),),
    )
    calls = {"eig": 0}
    real = ss.np.linalg.eigvalsh
    monkeypatch.setattr(ss.np.linalg, "eigvalsh",
                        lambda M: (calls.__setitem__("eig", calls["eig"] + 1), real(M))[1])
    h = ss.consistency_headline(s)
    assert calls["eig"] == 0                 # headline path does NO eigendecomposition
    assert h.spectral_gap is None
    # energy still correct: 2*(1-4)^2 / 2 == 9.0
    assert h.inconsistency_energy == 9.0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run --project . pytest tests/test_sheaf_spectrum.py::test_headline_is_energy_only_no_eigendecomposition -q`
Expected: FAIL — current `consistency_headline` calls `_spectrum_core` → `eigvalsh` (`calls["eig"] == 1`), and `spectral_gap` is `0.0` not `None`.

- [ ] **Step 4: Implement the energy-only path**

In `src/polymer_claims/sheaf_spectrum.py`, add `_energy` (near `_coboundary`) and rewrite `consistency_headline`:

```python
def _energy(structure: SheafStructure) -> float:
    """Inconsistency energy only (Robinson radius): O(edges) mat-vec, NO eigendecomposition."""
    x, delta, w, _kinds = _coboundary(structure)
    total_w = float(w.sum())
    if delta.shape[0] == 0 or total_w == 0.0:
        return 0.0
    d = delta @ x
    return float((w * (d * d)).sum()) / total_w


def consistency_headline(structure: SheafStructure) -> ConsistencyHeadline:
    return ConsistencyHeadline(
        inconsistency_energy=round(_energy(structure), _ROUND),
        spectral_gap=None,                 # λ₂ is on-demand only (see consistency_report)
    )
```

- [ ] **Step 5: Update the now-stale prior headline test**

The existing `test_consistency_headline_matches_report_scalars` (it asserts `headline.spectral_gap == report.spectral_gap`) is now wrong. Find it in `tests/test_sheaf_spectrum.py` and change it to:

```python
def test_consistency_headline_matches_report_scalars():
    s = SheafStructure(
        vertices=(_vert("a", 1.0), _vert("b", 4.0)),
        edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=2.0, sign=1),),
    )
    h = consistency_headline(s)
    r = consistency_report(s)
    assert h.inconsistency_energy == r.inconsistency_energy
    assert h.spectral_gap is None          # λ₂ lives only on the report now
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run --project . pytest tests/test_sheaf_spectrum.py -q`
Expected: PASS (all sheaf-spectrum tests, including the new one).

- [ ] **Step 7: Lint + commit**

```bash
cd protocol && uv run ruff check src && cd /Users/zbb2/Desktop/polymer-claims
uv run --project . ruff check src tests
git add protocol/src/polymer_protocol/sheaf.py src/polymer_claims/sheaf_spectrum.py tests/test_sheaf_spectrum.py
git commit -m "fix(sheaf): P1 energy-only per-frame headline; spectral_gap nullable (no per-tick eigendecomp)"
```

---

### Task 2: P3 — nonnegative edge-share per-claim tension

**Files:**
- Modify: `src/polymer_claims/sheaf_spectrum.py` (`consistency_report` tension; add `_edge_share_tension`)
- Test: `tests/test_sheaf_spectrum.py`

**Interfaces:**
- Consumes: `_coboundary`, `_ROUND`, `ClaimTension`, `SheafStructure`.
- Produces: `_edge_share_tension(structure, total_w) -> tuple[ClaimTension, ...]` (nonnegative, sums to energy). `consistency_report` uses it instead of the Rayleigh diagonal.

- [ ] **Step 1: Write the failing test**

In `tests/test_sheaf_spectrum.py`:

```python
def test_per_claim_tension_nonnegative_and_reconciles_with_energy():
    # mixed corpus: a disagreeing equivalence + a defeat — Rayleigh diagonal could go negative here
    s = SheafStructure(
        vertices=(_vert("a", 1.0), _vert("b", 4.0), _vert("c", 2.0)),
        edges=(
            SheafEdge(kind="equivalence", u="a", v="b", weight=2.0, sign=1),
            SheafEdge(kind="defeat", u="b", v="c", weight=1.0, sign=-1),
        ),
    )
    r = consistency_report(s)
    assert all(t.tension >= 0.0 for t in r.per_claim_tension)        # valid as opacity
    total = sum(t.tension for t in r.per_claim_tension)
    n = len(r.per_claim_tension)
    assert abs(total - r.inconsistency_energy) <= n * 1e-6           # 6dp-rounded tolerance
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project . pytest tests/test_sheaf_spectrum.py::test_per_claim_tension_nonnegative_and_reconciles_with_energy -q`
Expected: FAIL — the Rayleigh-diagonal `x_i*(Lx)_i` yields a negative tension for at least one node here.

- [ ] **Step 3: Implement the edge-share attribution**

In `src/polymer_claims/sheaf_spectrum.py`, add the helper:

```python
def _edge_share_tension(structure: SheafStructure, total_w: float) -> tuple[ClaimTension, ...]:
    """Nonnegative per-claim attribution: each edge's w·d² split half to each endpoint.
    Sums to the inconsistency energy. Defensively skips self-loop / malformed edges."""
    x, delta, w, _kinds = _coboundary(structure)
    d = delta @ x
    per_edge = w * (d * d)
    acc = {v.claim_id: 0.0 for v in structure.vertices}
    for k, e in enumerate(structure.edges):
        if e.u == e.v or e.u not in acc or e.v not in acc:
            continue                                   # self-loop / malformed: should not occur
        share = float(per_edge[k]) / 2.0
        acc[e.u] += share
        acc[e.v] += share
    return tuple(
        ClaimTension(claim_id=v.claim_id, tension=round(acc[v.claim_id] / total_w, _ROUND))
        for v in structure.vertices
    )
```

In `consistency_report`, replace the Rayleigh-diagonal tension block:

```python
    Lx = L @ x
    tensions = tuple(
        ClaimTension(claim_id=v.claim_id, tension=round(float(x[i] * Lx[i]) / total_w, _ROUND))
        for i, v in enumerate(structure.vertices)
    )
```

with:

```python
    tensions = _edge_share_tension(structure, total_w)
```

(`Lx` is no longer needed for tension; leave the rest of `consistency_report` unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project . pytest tests/test_sheaf_spectrum.py -q`
Expected: PASS (new test + all prior — energy/H⁰/H¹/determinism unchanged; only tension values changed).

- [ ] **Step 5: Lint + commit**

```bash
uv run --project . ruff check src tests
git add src/polymer_claims/sheaf_spectrum.py tests/test_sheaf_spectrum.py
git commit -m "fix(sheaf): P3 nonnegative edge-share per-claim tension (valid as opacity)"
```

---

### Task 3: `GET /consistency` route (P2 snapshot-then-release + discriminated response)

**Files:**
- Modify: `src/polymer_claims/server.py`
- Test: the existing server test file (locate: `grep -rl "create_app" tests`)

**Interfaces:**
- Consumes: `create_app`'s `runner`, `lock`, `asyncio`, `JSONResponse`, `_obj(model)` (all already in `server.py`); `extract_sheaf` (from `polymer_protocol`), `consistency_report` (from `.sheaf_spectrum`).
- Produces: `GET /consistency` → `{available: false}` or `{available: true, ...ConsistencyReport}`. Snapshots `runner.corpus` under the lock, releases, computes in `asyncio.to_thread`; `ImportError` caught **inside** the worker.

- [ ] **Step 1: Write the failing tests**

In the server test file (mirror its existing `create_app(...)` + client fixture — it uses FastAPI's test client over the app's lifespan):

```python
def test_consistency_route_returns_report(make_test_client):   # reuse the file's existing client factory
    client = make_test_client()
    r = client.get("/consistency")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert "inconsistency_energy" in body and "h1_obstructions" in body and "per_claim_tension" in body


def test_consistency_does_not_block_step(monkeypatch, make_test_client):
    """P2: holding the lock during the eigendecomp would serialize /step behind /consistency.
    Block consistency_report; a concurrent /step must still complete promptly."""
    import threading, time
    import polymer_claims.sheaf_spectrum as ss
    release = threading.Event()
    real = ss.consistency_report
    def slow(structure):
        release.wait(timeout=5.0)          # block the worker thread
        return real(structure)
    monkeypatch.setattr(ss, "consistency_report", slow)

    client = make_test_client()
    out = {}
    def hit_consistency():
        out["consistency"] = client.get("/consistency").status_code
    t = threading.Thread(target=hit_consistency); t.start()
    time.sleep(0.2)                        # let /consistency take its corpus snapshot + enter the worker
    step = client.post("/step")            # must NOT be serialized behind the blocked worker
    assert step.status_code == 200         # completes while /consistency is still blocked
    release.set(); t.join(timeout=5.0)
    assert out["consistency"] == 200
```

> If the test file has no `make_test_client`/client factory, build one from `create_app(runner=...)` exactly as the existing tests do (grep `create_app(` in that file) — pass a runner seeded with a small corpus that has `[embed]` available. The concurrency test relies on the real threadpool, so use the synchronous `TestClient` from FastAPI/Starlette (it runs the app with a live event loop) the same way the existing tests do.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project . pytest <server_test_file> -k consistency -q`
Expected: FAIL — `GET /consistency` is 404 (route not defined).

- [ ] **Step 3: Add the route**

In `src/polymer_claims/server.py`, add (next to the `/claim/{claim_id}` route, using the same `lock`/`asyncio`/`JSONResponse`/`_obj` already in scope):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project . pytest <server_test_file> -k consistency -q`
Expected: PASS (both: the report shape, and `/step` completing while `/consistency` is blocked).

- [ ] **Step 5: Full umbrella gate + commit**

```bash
uv run --project . pytest -q
uv run --project . ruff check src tests
git add src/polymer_claims/server.py <server_test_file>
git commit -m "feat(server): GET /consistency — snapshot-then-release, discriminated response (P2)"
```

---

### Task 4: Viewer wire types + live helper + interpolation passthrough

**Files:**
- Modify: `viewer/src/lib/topology.ts`, `viewer/src/lib/live.ts`, `viewer/src/lib/interpolate.ts`

**Interfaces:**
- Produces (TS): `ConsistencyHeadline { inconsistency_energy: number; spectral_gap: number | null }`, `consistency?: ConsistencyHeadline | null` on `TopologyExport`, `ConsistencyReport`, `Obstruction`, `ClaimTension` (in `topology.ts`); `ConsistencyResponse` + `fetchConsistency(baseUrl): Promise<ConsistencyResponse>` (in `live.ts`); `InterpFrame.consistency` carried through `interpolateFrame`.

- [ ] **Step 1: Add wire types (`topology.ts`)**

Append to `viewer/src/lib/topology.ts`:

```typescript
export interface ConsistencyHeadline {
  inconsistency_energy: number;
  spectral_gap: number | null;   // null on the live headline; populated only by the full report
}

export interface ClaimTension { claim_id: string; tension: number; }
export interface Obstruction {
  claim_ids: string[];
  edges: [string, string][];
  magnitude: number;
}
export interface ConsistencyReport {
  inconsistency_energy: number;
  equivalence_energy: number;
  defeat_energy: number;
  spectral_gap: number;
  h0_dim: number;
  h1_obstructions: Obstruction[];
  per_claim_tension: ClaimTension[];
  flags: { kind: string; claim_ids: [string, string]; detail: string }[];
}
```

And add the optional field on the existing `TopologyExport` interface:

```typescript
  consistency?: ConsistencyHeadline | null;
```

- [ ] **Step 2: Add the route envelope + fetch helper (`live.ts`)**

In `viewer/src/lib/live.ts` add (import the types from `./topology`):

```typescript
import type { ConsistencyReport } from './topology';

export type ConsistencyResponse =
  | { available: false }
  | ({ available: true } & ConsistencyReport);

export async function fetchConsistency(baseUrl: string): Promise<ConsistencyResponse> {
  const res = await fetch(baseUrl.replace(/\/$/, '') + '/consistency');
  if (!res.ok) return { available: false };
  return (await res.json()) as ConsistencyResponse;
}
```

- [ ] **Step 3: Forward `consistency` through interpolation (`interpolate.ts`)**

Find `interpolateFrame` (it returns `{ nodes, edges, stats, layoutId }`). Carry the frame-level `consistency` verbatim. Add `consistency?: ConsistencyHeadline | null` to the `InterpFrame` type and set it in the return:

```typescript
  consistency: frame.topology.consistency ?? null,
```

(Import `ConsistencyHeadline` from `./topology`; the headline is a scalar readout, not a spatial quantity — carry the latest, do not interpolate.)

- [ ] **Step 4: Typecheck + commit**

```bash
cd viewer && npm run typecheck && cd /Users/zbb2/Desktop/polymer-claims
git add viewer/src/lib/topology.ts viewer/src/lib/live.ts viewer/src/lib/interpolate.ts
git commit -m "feat(viewer): consistency wire types + fetch helper + interpolation passthrough"
```

> No runtime behavior changes yet — this is the contract. `tsc` clean is the bar.

---

### Task 5: Store state + throttled fetch hook + toggle

**Files:**
- Modify: `viewer/src/store.ts`, `viewer/src/components/ClaimUniverse.tsx`, `viewer/src/components/chrome/LiveControl.tsx`
- Create: `viewer/src/lib/useConsistencySync.ts`

**Interfaces:**
- Consumes: `fetchConsistency` (Task 4), the store's existing live base URL + latest frame `cycle_index`.
- Produces: store fields `overlayOn`, `consistencyReport`, `consistencyAvailable`, `obstructions`, `tensionByClaimId`, `maxTension`, `lastConsistencyCycle`, `consistencyInFlight`; actions `setOverlayOn(b)`, `fetchConsistency()`; the `useConsistencySync()` hook.

- [ ] **Step 1: Extend the store**

In `viewer/src/store.ts`, add state + actions (follow the file's existing Zustand `set/get` style). Derivation builds `tensionByClaimId` + `maxTension` from the report; `obstructions` from `report.h1_obstructions`:

```typescript
  overlayOn: false,
  consistencyReport: null as ConsistencyReport | null,
  consistencyAvailable: false,
  obstructions: [] as Obstruction[],
  tensionByClaimId: {} as Record<string, number>,
  maxTension: 0,
  lastConsistencyCycle: -1,
  consistencyInFlight: false,

  setOverlayOn: (b: boolean) => set({ overlayOn: b }),

  fetchConsistency: async () => {
    const { liveUrl, consistencyInFlight } = get();   // liveUrl = the live base; rename to match the store
    if (!liveUrl || consistencyInFlight) return;
    set({ consistencyInFlight: true });
    try {
      const resp = await fetchConsistency(liveUrl);
      const latest = get().timeline?.frames.at(-1)?.cycle_index ?? -1;
      if (resp.available) {
        const tension: Record<string, number> = {};
        let max = 0;
        for (const t of resp.per_claim_tension) { tension[t.claim_id] = t.tension; if (t.tension > max) max = t.tension; }
        set({ consistencyReport: resp, consistencyAvailable: true, obstructions: resp.h1_obstructions,
              tensionByClaimId: tension, maxTension: max, lastConsistencyCycle: latest });
      } else {
        set({ consistencyAvailable: false, obstructions: [], tensionByClaimId: {}, maxTension: 0,
              lastConsistencyCycle: latest });
      }
    } finally {
      set({ consistencyInFlight: false });
    }
  },
```

> Match the store's actual field name for the live base URL (grep `EventSource`/`connectLive` in `store.ts`; the Explore notes call it the live base). If the store holds no base URL, thread it from where `connectLive(url)` is called.

- [ ] **Step 2: Create the throttle hook**

Create `viewer/src/lib/useConsistencySync.ts`:

```typescript
import { useEffect } from 'react';
import { useViewer } from '../store';   // match the store's hook export name

const N = 5;   // refetch at most every N followed frames

export function useConsistencySync(): void {
  const overlayOn = useViewer((s) => s.overlayOn);
  const latestCycle = useViewer((s) => s.timeline?.frames.at(-1)?.cycle_index ?? -1);
  const lastFetched = useViewer((s) => s.lastConsistencyCycle);
  const inFlight = useViewer((s) => s.consistencyInFlight);
  const fetchConsistency = useViewer((s) => s.fetchConsistency);

  useEffect(() => {
    if (!overlayOn || inFlight) return;
    if (lastFetched < 0 || latestCycle - lastFetched >= N) {
      void fetchConsistency();
    }
  }, [overlayOn, latestCycle, lastFetched, inFlight, fetchConsistency]);
}
```

(One effect, guarded by `inFlight` + the `N`-frame throttle, fires immediately when the toggle flips on because `lastFetched < 0`.)

- [ ] **Step 3: Mount the hook + add the toggle**

In `viewer/src/components/ClaimUniverse.tsx`, call `useConsistencySync()` once in the root component body (alongside the existing hooks). In `viewer/src/components/chrome/LiveControl.tsx`, add a toggle bound to `overlayOn`/`setOverlayOn` (mirror the file's existing control styling):

```tsx
const overlayOn = useViewer((s) => s.overlayOn);
const setOverlayOn = useViewer((s) => s.setOverlayOn);
// ... a labeled toggle button/checkbox: "Consistency overlay" → setOverlayOn(!overlayOn)
```

- [ ] **Step 4: Typecheck + commit**

```bash
cd viewer && npm run typecheck && cd /Users/zbb2/Desktop/polymer-claims
git add viewer/src/store.ts viewer/src/lib/useConsistencySync.ts viewer/src/components/ClaimUniverse.tsx viewer/src/components/chrome/LiveControl.tsx
git commit -m "feat(viewer): consistency store state + throttled useConsistencySync + overlay toggle"
```

---

### Task 6: Energy HUD (frontend-design)

**Files:**
- Create: `viewer/src/components/chrome/EnergyHud.tsx`
- Modify: `viewer/src/components/ClaimUniverse.tsx` (mount), `viewer/src/lib/theme.ts` (heat scale)

**Build via the `frontend-design` skill to this contract:**
- **Data:** reads `overlayOn`, the current frame's `consistency.inconsistency_energy` (live, every frame), and `consistencyReport?.spectral_gap` (from the pulled report; may be `null`/absent). Reads the timeline's per-frame `consistency.inconsistency_energy` history for the sparkline.
- **Behavior:** render **only when `overlayOn`**. Show the energy number + a sparkline of energy over recent frames (so the fall is visible) + λ₂ beneath *when a report is available*. Hue warms teal→amber→rose with energy (add a `tensionScale(t01)` / `energyScale` helper to `theme.ts`, 3 stops). Hidden when `overlayOn === false` or `consistency == null`.
- **Acceptance:** `npm run typecheck` + `npm run build` clean; toggle off ⇒ HUD absent.

- [ ] **Step 1:** Invoke `frontend-design` to build `EnergyHud.tsx` + the `theme.ts` scale to the contract above; mount `<EnergyHud/>` in `ClaimUniverse`/`Scene`.
- [ ] **Step 2:** `cd viewer && npm run typecheck && npm run build` — both clean.
- [ ] **Step 3:** Commit: `git commit -m "feat(viewer): energy HUD + sparkline (consistency overlay)"`

---

### Task 7: Per-node tension halo (frontend-design)

**Files:**
- Modify: `viewer/src/components/scene/Nodes.tsx` (`NodeMesh`), `viewer/src/lib/theme.ts`

**Build via the `frontend-design` skill to this contract:**
- **Data:** `NodeMesh` reads `overlayOn` + `tensionByClaimId[node.id]` + `maxTension` from the store.
- **Behavior:** when `overlayOn` and the node id is in `tensionByClaimId`, render a soft billboarded halo (disc or ring) behind the node, color+opacity = `tension / maxTension` via the `theme.ts` heat scale (teal→amber→rose). Place it at a radius **distinct from** the FDR ring (r·2.25) and hover ring (r·1.7) so they don't collide. Nodes absent from the map, or when `overlayOn === false`, render exactly as today (no halo).
- **Acceptance:** typecheck + build clean; toggle off ⇒ node meshes byte-identical to current; tension is nonnegative (Task 2) so opacity ∈ [0,1].

- [ ] **Step 1:** Invoke `frontend-design` to add the tension halo to `NodeMesh` to the contract above.
- [ ] **Step 2:** `cd viewer && npm run typecheck && npm run build` — both clean.
- [ ] **Step 3:** Commit: `git commit -m "feat(viewer): per-node tension halo (consistency overlay)"`

---

### Task 8: H¹ obstruction overlay (frontend-design)

**Files:**
- Create: `viewer/src/components/scene/Obstructions.tsx`
- Modify: `viewer/src/components/ClaimUniverse.tsx` (mount in `Scene`)

**Build via the `frontend-design` skill to this contract:**
- **Data:** reads `overlayOn` + `obstructions` from the store + the same interpolated node positions `Edges`/`Nodes` use (resolve positions by `claim_id`; reuse the interpolation path).
- **Behavior:** render **only when `overlayOn`**. For each `Obstruction`, draw its `edges` (claim-id pairs) as bold rose `Line`s between the member nodes' positions, animated (pulsing dash/opacity), plus a rose outline on member nodes. **Separate pass** from `Edges.tsx` (cycle pairs are not topology edges). Skip any pair whose endpoint isn't present in the current frame. Honor a `focusedObstruction` (set by the panel, Task 9) by brightening that cycle.
- **Acceptance:** typecheck + build clean; with a frustrated-cycle corpus the loop renders; toggle off ⇒ no overlay.

- [ ] **Step 1:** Invoke `frontend-design` to build `Obstructions.tsx` to the contract; mount `<Obstructions/>` in `Scene`.
- [ ] **Step 2:** `cd viewer && npm run typecheck && npm run build` — both clean.
- [ ] **Step 3:** Commit: `git commit -m "feat(viewer): H1 frustration-cycle overlay (consistency overlay)"`

---

### Task 9: Obstruction panel + node tension in the right rail (frontend-design)

**Files:**
- Modify: `viewer/src/components/chrome/RightRail.tsx`, `viewer/src/store.ts` (a `focusedObstruction` id + setter)

**Build via the `frontend-design` skill to this contract:**
- **Data:** `obstructions` + `tensionByClaimId` from the store; the existing `selectedId` for the node panel.
- **Behavior:** a new right-rail section (only when `overlayOn`) listing each obstruction — member `claim_ids` + `magnitude` — each row **click-to-focus** (sets `focusedObstruction`, which Task 8's overlay brightens). In the existing `NodePanel`/`ClaimDetailCard`, show the selected node's `tension` (from `tensionByClaimId`) following the `independence_tier` display precedent. When `overlayOn === false`, the section is absent and the node panel is unchanged from today.
- **Acceptance:** typecheck + build clean; clicking an obstruction focuses its cycle; toggle off ⇒ right rail identical to today.

- [ ] **Step 1:** Add `focusedObstruction: string | null` + `setFocusedObstruction` to the store.
- [ ] **Step 2:** Invoke `frontend-design` to build the panel section + node-tension display to the contract.
- [ ] **Step 3:** `cd viewer && npm run typecheck && npm run build` — both clean.
- [ ] **Step 4:** Commit: `git commit -m "feat(viewer): obstruction panel (click-to-focus) + node tension display"`

---

### Task 10: Demo seed corpus + manual verification + docs

**Files:**
- Create: a small seed-corpus fixture with a frustrated cycle (e.g. `data/demo/frustrated_cycle_corpus.json` or a `--seed-corpus` file) — A≡B, B≡C, C⊣A over three Quantity-leaf LICENSED/PENDING claims with disagreeing values.
- Modify: `docs/superpowers/CONTINUE.md`, `GLOSSARY.md`, `ARCHITECTURE_CURRENT.md`.

- [ ] **Step 1: Build the frustrated-cycle seed corpus**

Create a corpus JSON the server can load via `serve --seed-corpus <path>` containing three Quantity-leaf claims (a,b,c) with a `Dimension`, two `equivalence` EquivalenceClaims (a–b, b–c) and one effective `defeat` edge (c→a), with values that disagree (so energy > 0). Validate it loads: `uv run --project . polymer-claims export-consistency <path>` returns a report with exactly one `h1_obstructions` entry over {a,b,c}. (Reuse the analytic example from the gauge tests.)

- [ ] **Step 2: Manual visual verification (the `verify`/`run` skill)**

Launch `uv run --project '.[serve,embed]' polymer-claims serve --seed-corpus <path>` and open the viewer (live mode). With the **consistency overlay toggled on**, confirm:
1. the HUD energy **falls** over ticks;
2. the frustrated cycle **lights up** as a rose overlay;
3. tension halos **scale** with tension and sit clear of the FDR/hover rings;
4. **toggle off ⇒ rendered chrome + 3D scene identical to today**;
5. run once **without `[embed]`** (`'.[serve]'`) ⇒ HUD hidden, overlay disabled (`available:false`), **no console errors**;
6. a consistent corpus (no frustrated cycle) ⇒ `available:true`, HUD shows, **no overlay**.
Capture a screenshot of the lit obstruction for the record.

- [ ] **Step 3: Update docs**

- `GLOSSARY.md`: under the sheaf entries, note the viewer surfaces the gauge (energy HUD, tension halos, H¹ obstruction overlay) behind the consistency toggle.
- `ARCHITECTURE_CURRENT.md`: one line — the sheaf gauge is now visualized live (`GET /consistency` + viewer overlay), instrument-only.
- `CONTINUE.md`: Done entry — sheaf viewer viz shipped; spec+plan `docs/superpowers/{specs,plans}/2026-06-21-sheaf-viewer-viz*`; deferred items from spec §10 (sample-mode rich layer, λ₂-on-frame, tension-in-protocol, hyperbolic layout, instrument→gate). Note P1/P3 corrected the gauge (energy-only headline; nonnegative tension).

- [ ] **Step 4: Full gate + commit**

```bash
bash scripts/check-all.sh     # Python + ruff + isolation + viewer tsc/build (next build may fail only on the known font-fetch network block)
git add data/ docs/superpowers/CONTINUE.md GLOSSARY.md ARCHITECTURE_CURRENT.md
git commit -m "docs+demo(sheaf-viz): frustrated-cycle seed corpus + verification + docs"
```

---

## Self-Review

**Spec coverage:** §2 P1→Task 1, P3→Task 2, P2→Task 3 (snapshot-then-release + concurrency test). §4/§5 route + discriminated response→Task 3. §6.1 types/live/interpolate→Task 4; store + fetch trigger→Task 5. §6.2 HUD→Task 6, halo→Task 7, overlay→Task 8, panel+node tension→Task 9. §7 sample-mode (HUD obeys toggle) is honored by the `overlayOn` gate across Tasks 6–9. §8 testing: backend P1/P3/P2 + route tests in Tasks 1–3, frontend tsc/build per task, manual verification + seed dependency in Task 10. §10 deferrals recorded in Task 10 docs. All spec sections map to a task.

**Placeholder scan:** Backend Tasks 1–3 carry complete code + real assertions (analytic values 9.0; tension≥0 + `n·1e-6`; concurrency via a blocking monkeypatch). Data-layer Tasks 4–5 carry complete TS. Tasks 6–9 are explicitly delegated to `frontend-design` with a complete **data/behavior/acceptance contract** (the spec routes visual work there, §9) — not vague "build the UI": each names its store inputs, render gating, placement constraints, and pass/fail bar. The few "grep to confirm the store's live-URL field / client factory" notes are verification instructions against unseen local names, not deferred logic.

**Type consistency:** `ConsistencyHeadline { inconsistency_energy; spectral_gap: number|null }`, `ConsistencyReport`/`Obstruction { claim_ids; edges; magnitude }`/`ClaimTension { claim_id; tension }`, `ConsistencyResponse = {available:false} | ({available:true} & ConsistencyReport)`, `fetchConsistency(baseUrl)`, store fields (`overlayOn`, `consistencyReport`, `tensionByClaimId`, `maxTension`, `obstructions`, `lastConsistencyCycle`, `consistencyInFlight`, `focusedObstruction`), `useConsistencySync()`, `_energy`, `_edge_share_tension(structure, total_w)` — names are used identically across tasks. `consistency_headline` returns `spectral_gap=None`; `GET /consistency` envelope matches the TS `ConsistencyResponse`.
