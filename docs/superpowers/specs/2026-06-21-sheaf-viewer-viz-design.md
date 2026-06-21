# Sheaf Gauge Viewer Visualization — Design

**Date:** 2026-06-21 · **Status:** Design (approved in brainstorm; revised after two spec audits; pre-plan)
**Builds on:** `docs/superpowers/specs/2026-06-21-sheaf-consistency-gauge-design.md` (the gauge itself,
merged `fe1214d`). This is the named **rich-viz fast-follow** from that spec's §8, and the first
viewer-facing piece of North-Star arc 3 (living universe) / linchpin A3 (Reproducibility Observatory).

> **One line.** Make the sheaf consistency gauge *legible* on the live 3D universe: a falling
> energy HUD, per-claim **tension halos**, and H¹ **frustration-cycle overlays** — contradiction loops
> no pairwise check sees, lit up on the graph. Fed by a new throttled `GET /consistency` endpoint;
> one opt-in toggle gates the whole layer, so the **rendered view is unchanged from today** when off.

---

## 1. Goal & non-goals

**Goal.** Surface the gauge's three outputs in the viewer: the corpus **inconsistency energy** (the
falling distance-to-consensus), **per-claim tension** (which claim drags consensus down), and **H¹
frustration obstructions** (locally-consistent-but-globally-contradictory cycles), so a person can
*see* the corpus growing toward — or away from — consensus.

**Non-goals (this slice).**
- **Not a gate.** Pure visualization; no licensing/status change (the gauge stays an instrument).
- **No per-tick eigendecomposition.** The per-frame path must be a true O(edges) mat-vec; the
  expensive `ConsistencyReport` (eigendecomp + H¹ BFS) runs only on demand, throttled.
- **Rich layer is live-only** in slice 1 (sample/precomputed-timeline mode shows the HUD if the frames
  carry the energy headline, but not the overlay/halos — see §7).
- **No new protocol *node* fields.** `TopologyNode` is unchanged; per-claim tension is joined
  viewer-side by `claim_id`.

## 2. Backend prerequisites — correct the merged gauge FIRST

The audits found the shipped gauge can't support a cheap per-frame headline or a non-blocking
endpoint as-is. These three corrections to the already-merged gauge are **prerequisite tasks**, landed
and tested **before** any viewer work:

- **P1 — per-frame headline becomes energy-only (schema-stable, no wire break).** Today
  `consistency_headline()` calls `_spectrum_core()`, which runs dense `np.linalg.eigvalsh(L)` to
  produce λ₂ — so every live frame does an eigendecomposition. Make the headline path compute
  **energy only** (`energy = (w * (δx)²).sum() / Σw`, no eigendecomposition). Because the headline
  rides **every live frame** (`TopologyExport.consistency`, emitted in `NodeRunner._attach_consistency`,
  `node.py`), do **not** delete the λ₂ field — that would be a subtractive wire break. Instead **retain
  `ConsistencyHeadline.spectral_gap` as `float | None = None`** and have the headline path set it to
  `None`. λ₂ is populated **only in `consistency_report`** (on-demand). This is **schema-compatible for
  current first-party consumers** — the field is retained (its value goes numeric→`null` on the live
  headline) and the TS viewer does not yet model it, so **no `CONTRACT_VERSION` bump** is needed.
  Nullable is the right design here; strict numeric compatibility would instead need a sentinel value or
  a separate `live_spectral_gap_available` flag. The HUD's live signal is the falling energy; λ₂ comes
  from the pulled report. Update the `consistency_headline` test to assert no eigendecomposition and
  `spectral_gap is None`.
- **P2 — `/consistency` must not hold the tick lock during compute.** Acquire the runner `lock` only
  long enough to **snapshot `runner.corpus`** (a reference grab — `Corpus` is a frozen, immutable
  model, so the snapshot is safe to read without the lock), **release**, then run
  `extract_sheaf` + `consistency_report` on the snapshot inside `asyncio.to_thread`. The eigendecomp
  never serializes the tick loop.
- **P3 — `per_claim_tension` becomes a nonnegative edge-share attribution (same field, new compute).**
  Today `tension_i = x_i·(Lx)_i / Σw` (the Rayleigh diagonal) sums to energy but **individual terms can
  be negative** — invalid as an opacity. Keep the `per_claim_tension` field but recompute it as the
  **edge-share attribution** `tension_i = Σ_{e incident to i} w_e · d_e² / 2`, normalized by total edge
  weight. This is **nonnegative**, still sums to the inconsistency energy, and is directly
  interpretable ("how much edge tension touches this claim"). The attribution must **defensively skip
  self-loop / malformed edges** (an endpoint not a participating vertex) even though the extractor
  should never produce them. Update `sheaf_spectrum.py` + its test.

**Schema discipline (resolves the additive-vs-subtractive concern):** P1 is **schema-compatible for
current first-party consumers** (retains `spectral_gap` as Optional; its value goes numeric→`None` on
the live headline). This is a *semantic* change (number→null) for any client reading the live λ₂, not a
structural field removal — and the TS viewer doesn't model the field yet, so no version bump. P3 keeps
the same `per_claim_tension` field and changes only how it is **computed** (nonnegative edge-share, same
units, still sums to energy). The only runtime consumers today are the `export-consistency` CLI + tests,
and the viewer doesn't yet read these — so both are explicit, versioned schema corrections, not silent
breaks. (The gauge's structural invariants — pure protocol extractor, numpy behind `[embed]` — hold.)

## 3. Constraints / invariants

- **Cost split (post-P1):** the **energy-only** headline rides every frame
  (`TopologyExport.consistency`) — a genuine mat-vec. The expensive report (λ₂, H⁰, H¹, tension) comes
  only from the new on-demand route. Never put eigendecomposition on the per-tick path.
- **`[embed]` gate:** all sheaf compute needs the `[embed]` extra (numpy). Without it, `consistency`
  is `null` on frames and `GET /consistency` returns `{available: false}` — the viewer degrades
  silently (HUD hidden, overlay disabled, no errors).
- **One toggle, fully off-safe (rendered view):** a single "consistency overlay" toggle gates the
  **entire** layer — HUD, halos, obstruction overlay, and panel. When `overlayOn === false`: no
  `/consistency` fetch, no overlay, no halos, **no HUD** → the **rendered chrome + 3D scene are
  unchanged from today**. The invariant is about the *rendered view*, not byte-identical network JSON —
  the frame payload already carries `TopologyExport.consistency` today, regardless of the toggle.
- **Server purity boundary unchanged:** the new route lives in the umbrella server (`server.py`);
  `protocol/`/`grammar/` untouched.
- Follow the viewer's existing patterns (Zustand store, R3F scene components, drei `Line`/`Billboard`,
  `theme.ts` palette, the `independence_tier` right-rail precedent).

## 4. Data flow (two channels by cost)

```
LIVE, every frame (cheap mat-vec):   NodeRunner._attach_consistency → TopologyExport.consistency
                                     ({inconsistency_energy, spectral_gap: null}) ──SSE──▶ Energy HUD

RICH, throttled pull:   GET /consistency ──(lock: snapshot corpus → release)──▶
                        asyncio.to_thread: consistency_report(extract_sheaf(snapshot))
                        → { spectral_gap, h0_dim, h1_obstructions, per_claim_tension, energies, flags }
                        ──▶ store: obstructions[] + tensionByClaimId{} (+ maxTension) joined by id
```

- **HUD** consumes the per-frame energy → updates every tick, no eigendecomposition. λ₂ is shown from
  the pulled report (the headline's `spectral_gap` is `null`).
- **Overlay + halos + λ₂** consume the pulled report. The viewer fetches `/consistency` when the
  toggle turns on, then **refetches at most every `N=5` followed frames** (compare latest `cycle_index`
  to last-fetched), **guarded by an in-flight flag** so a slow report can't stack duplicate fetches.
  Between refetches the overlay/λ₂ are "as of last fetch"; the energy HUD stays frame-current.

## 5. Backend — one new route

`GET /consistency` in `src/polymer_claims/server.py` (uses the P2 snapshot pattern):
- Acquire `lock` → take `corpus = runner.corpus` → release lock. Then run the work in
  `asyncio.to_thread`; the lazy import of `extract_sheaf` (protocol) + `consistency_report`
  (`sheaf_spectrum`, `[embed]`) and its `try/except ImportError` live **inside the worker function**
  (the import executes in the thread, so the ImportError is raised there) — the worker returns a
  sentinel the route maps to `{available:false}`. Do not wrap only the `await`.
- **Response is a discriminated union:** `{ "available": false }` (HTTP 200) when numpy is absent;
  otherwise `{ "available": true, ...ConsistencyReport.model_dump() }`. The UI keys "disabled" off
  `available === false` — distinct from a real `available:true` report whose `h1_obstructions` is
  empty (a genuinely consistent corpus). Never conflate "unavailable" with "no obstructions."
- Read-only: does not mutate corpus/runner state. No other server change (`_attach_consistency`
  already attaches the energy headline post-P1).

## 6. Frontend

### 6.1 Types & store (the contract comes first)
**First frontend task — the viewer contract** (the field the rest builds on is currently absent in TS):
- `viewer/src/lib/topology.ts` (**frame/timeline wire types only**): add
  `ConsistencyHeadline { inconsistency_energy: number; spectral_gap: number | null }` (λ₂ is `null` on
  the live headline post-P1) and `consistency?: ConsistencyHeadline | null` on `TopologyExport`; add the
  report wire types `ConsistencyReport` (the home of the real `spectral_gap`),
  `Obstruction { claim_ids; edges; magnitude }`, `ClaimTension { claim_id; tension }`.
- `viewer/src/lib/live.ts` (**live-route concerns**): the route envelope type
  `type ConsistencyResponse = { available: false } | ({ available: true } & ConsistencyReport)` and the
  `fetchConsistency` HTTP helper live here, keeping `topology.ts` to pure frame/timeline shapes.
- `viewer/src/lib/interpolate.ts`: forward frame-level `consistency` onto the interpolated frame
  (carried verbatim — `interpolateFrame` currently returns only nodes/edges/stats/layoutId, so this is
  an explicit addition).

**Store** (`viewer/src/store.ts`): `overlayOn: boolean`; `consistencyReport: ConsistencyReport | null`;
`consistencyAvailable: boolean`; derived `tensionByClaimId: Record<string, number>` + `maxTension`;
`obstructions: Obstruction[]`; `lastConsistencyCycle: number`; an `inFlight` guard; and a
`fetchConsistency()` **store action** (calls the `live.ts` helper; sets/clears `inFlight`, updates
report + derived maps + `lastConsistencyCycle`, sets `consistencyAvailable`).

**Fetch trigger — explicit (resolves audit finding 5):** the throttle lives in a **single React effect**
(a `useConsistencySync()` hook mounted once in `ClaimUniverse`), **not** inside `pushFrame`. The effect
depends on `[latestCycle, overlayOn]` and calls `fetchConsistency()` only when
`overlayOn && !inFlight && (latestCycle - lastConsistencyCycle >= N)` (and once immediately when the
toggle flips on). One effect + the `inFlight` guard prevents duplicate fetches and stale-report races.

### 6.2 Visual encodings (D2 metrological palette: blue primary, rose = defeat/contradiction, teal =
discovery, amber = pending) — all rendered only when `overlayOn`
- **Energy HUD** (`viewer/src/components/chrome/EnergyHud.tsx`, new): fixed-corner readout of
  `inconsistency_energy` (live, per-frame) with a **sparkline** over the timeline's per-frame energies
  so the fall is visible; `spectral_gap` (from the pulled report — the headline's field is `null`)
  shown beneath when a report is available (may lag ≤N frames). Hue warms teal→amber→rose with energy.
- **Per-node tension halo** (`viewer/src/components/scene/Nodes.tsx`, `NodeMesh`): a soft billboarded
  disc/ring behind the node, color+opacity = `tension / maxTension` (teal→amber→rose) — valid because
  tension is **nonnegative** (P3). Placed at a radius distinct from the FDR ring (r·2.25) and hover
  ring (r·1.7). Only nodes present in `tensionByClaimId` (Quantity-leaf, sheaf-participating) get a
  halo; all others render unchanged.
- **H¹ obstruction overlay** (`viewer/src/components/scene/Obstructions.tsx`, new): a separate scene
  pass. For each `Obstruction`, draw its `edges` (claim-id pairs) as bold rose `Line`s between member
  node positions, animated (pulsing dash/opacity), plus a rose outline on member nodes. Separate from
  `Edges.tsx` because cycle pairs are not necessarily topology edges; positions resolved from the same
  interpolation path; pairs whose endpoints aren't in the current frame are skipped.
- **Obstruction panel + node tension** (`viewer/src/components/chrome/RightRail.tsx`): a new section
  listing each obstruction (member `claim_ids` + `magnitude`), **click-to-focus** (sets a focused
  obstruction the overlay brightens). Per-claim `tension` shown in `NodePanel`/`ClaimDetailCard` when a
  node is selected (follows the `independence_tier` precedent).
- **Toggle** (`viewer/src/components/chrome/LiveControl.tsx`): the single control setting `overlayOn`
  (gates HUD + halos + overlay + panel + the fetch).
- **`theme.ts`**: a 3-stop tension heat scale (teal→amber→rose) + the obstruction overlay color (rose).
- **Mounting** (`viewer/src/components/ClaimUniverse.tsx` / its `Scene`): mount `<Obstructions/>` +
  `<EnergyHud/>` + the `useConsistencySync()` hook.

## 7. Sample mode

The precomputed `sample-timeline.json` path has no `/consistency` server, so the rich layer is
**live-only** in slice 1. Sample mode shows the **HUD** only when `overlayOn` is enabled **and** its
frames carry the energy headline (otherwise hidden) — the toggle gates the HUD identically to live
mode. Bundling a static `ConsistencyReport` fixture (or precomputing reports into the sample timeline)
so the overlay works in sample mode is a deferred enrichment (§10).

## 8. Testing & verification

- **Backend prerequisites:**
  - **P1** — assert `consistency_headline` performs no eigendecomposition (its energy matches the
    report's energy; `ConsistencyHeadline.spectral_gap is None`).
  - **P3** — on a mixed equivalence/defeat corpus, assert every `per_claim_tension.tension ≥ 0` and
    that `Σ tension` reconciles with `inconsistency_energy`. Assert the **unrounded** internal values to
    ~1e-9, **or** the public (6-dp-rounded) DTO values to a tolerance of **`n_claims · 1e-6`** — rounded
    per-claim terms need not sum to the rounded total within 1e-9.
  - **P2** — a real **concurrency test**: monkeypatch `consistency_report` to block (a sleep/event),
    fire `GET /consistency`, and assert a concurrent `POST /step` still completes promptly (is **not**
    serialized behind the eigendecomp), proving the lock is released after the corpus snapshot.
- **New route (pytest, mirrors existing server tests):** serve a node with `[embed]`; `GET /consistency`
  → `available: true` + the `ConsistencyReport` shape; assert `{available: false}` when the
  `sheaf_spectrum` import is unavailable; assert it does not mutate corpus/runner state.
- **Frontend automated bar:** `npm run typecheck` clean + `next build` clean (the repo has no viewer
  component-unit tests; `tsc`+build is the gate).
- **Manual visual verification** (via the `verify`/`run` skill, `serve` a node): (1) the HUD energy
  **falls** over ticks; (2) a frustrated cycle **lights up** as a rose overlay; (3) halos **scale** with
  (nonnegative) tension and sit clear of the FDR/hover rings; (4) **toggle off ⇒ rendered chrome + 3D
  scene identical to today**; (5) no `[embed]` ⇒ HUD hidden, overlay disabled (`available:false`), **no
  console errors**; (6) a genuinely consistent corpus (`available:true`, empty obstructions) shows the
  HUD with **no** overlay — distinct from the unavailable state.
- **Verification dependency:** the manual check needs a live seed corpus that yields an H¹ obstruction —
  a frustrated cycle (e.g. `A≡B`, `B≡C`, `C⊣A` over Quantity-leaf claims). The default seed may not
  contain one, so the plan includes crafting a small demo seed corpus (or `--seed-corpus` fixture) for
  verification.

## 9. Implementation note & sequencing

Task order: **(1) backend prerequisites P1–P3** (correct the gauge) → **(2) the `/consistency` route** →
**(3) the viewer contract** (`topology.ts` types + `live.ts` envelope/helper + `interpolateFrame`
forwarding) → **(4) store + `useConsistencySync` hook** → **(5) R3F visuals + chrome**. The R3F/chrome
work (5) should be built via the **frontend-design** skill; P1–P3, the route, types, and store are
ordinary TDD tasks.

**Carry-forward implementation notes:** (a) P3's edge-share attribution guards self-loop / malformed
edges defensively; (b) `/consistency` catches `ImportError` **inside** the `to_thread` worker (not
around the `await`), since the lazy import runs in the thread; (c) `ConsistencyHeadline.spectral_gap` is
nullable — first-party-compatible, a number→null semantic change, not a structural removal.

## 10. Future enrichments (deferred)

- **Rich layer in sample mode** — bundle a static `ConsistencyReport` fixture or precompute per-frame
  reports into the sample timeline.
- **Per-frame rich history** — a throttled server-pushed SSE `consistency` event instead of viewer pull,
  if the pull cadence proves insufficient.
- **λ₂ on the live frame** — if a live spectral-gap readout is wanted without a pull, compute it via a
  cheap iterative method (e.g. a few Lanczos iterations) and repopulate the headline's `spectral_gap`,
  rather than dense `eigvalsh`.
- **Tension in protocol export** — if the viewer-side join proves limiting, add an optional
  `sheaf_tension: float | None` to `TopologyNode` (additive) so tension travels with the frame.
- **Obstruction-aware camera**; **Hyperbolic/Lorentz layout** (North-Star §5); **instrument→gate** —
  separate arc-3 slices.

## 11. Audit reconciliation

**Round 1:**
| Finding | Resolution |
|---|---|
| 1. Headline not cheap (eigvalsh per frame) | **P1** — headline energy-only; λ₂ → report (§2, §4) |
| 2. Lock held during eigendecomp stalls ticks | **P2** — snapshot corpus under lock, release, compute in thread (§2, §5) |
| 3. Off-safe contradicts always-on HUD | One toggle gates the **whole** layer incl. HUD (§3) |
| 4. Viewer `consistency` field missing | First frontend task: add the type + forward through `interpolateFrame` (§6.1, §9) |
| 5. Fetch trigger underspecified | Single `useConsistencySync()` effect on `[latestCycle, overlayOn]` + in-flight guard (§6.1) |
| 6. Tension can be negative | **P3** — nonnegative edge-share attribution `Σ_{e∋i} w·d²/2` (§2) |
| 7. Response should be discriminated union | `{available:false} | ({available:true} & ConsistencyReport)`; UI disables on unavailable (§5, §6.1) |

**Round 2:**
| Finding | Resolution |
|---|---|
| 1/2. P1 removal is a wire break, not additive | **Retain `spectral_gap` as `float \| None = None`** — schema-compatible for first-party consumers (numeric→null semantic change, no `CONTRACT_VERSION` bump); headline sets it `None` (§2) |
| 3. P3 1e-9 tolerance too strict vs 6-dp rounding | Assert unrounded ~1e-9 **or** public DTO to `n_claims·1e-6` (§8) |
| 4. P2 "inspection" too weak | Real **concurrency test**: block `consistency_report`, assert `/step` not serialized (§8) |
| 5. "byte-for-byte" wrong (payload carries `consistency`) | Invariant is **rendered view** unchanged, not network JSON (§3, one-liner) |
| 6. Sample-mode HUD must obey toggle | Sample HUD shows only **when `overlayOn`** + headline present (§7) |
| 7. Route type location | `ConsistencyResponse` + `fetchConsistency` in **`live.ts`**; wire types in `topology.ts` (§6.1) |
