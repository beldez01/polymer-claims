# Sheaf Gauge Viewer Visualization — Design

**Date:** 2026-06-21 · **Status:** Design (approved in brainstorm; pre-plan)
**Builds on:** `docs/superpowers/specs/2026-06-21-sheaf-consistency-gauge-design.md` (the gauge itself,
merged `fe1214d`). This is the named **rich-viz fast-follow** from that spec's §8, and the first
viewer-facing piece of North-Star arc 3 (living universe) / linchpin A3 (Reproducibility Observatory).

> **One line.** Make the sheaf consistency gauge *legible* on the live 3D universe: a falling
> energy HUD, per-claim **tension halos**, and H¹ **frustration-cycle overlays** — contradiction loops
> no pairwise check sees, lit up on the graph. Fed by a new throttled `GET /consistency` endpoint;
> opt-in; byte-for-byte today's view when off.

---

## 1. Goal & non-goals

**Goal.** Surface the gauge's three outputs in the viewer: the corpus **inconsistency energy** (the
falling distance-to-consensus), **per-claim tension** (which claim drags consensus down), and **H¹
frustration obstructions** (locally-consistent-but-globally-contradictory cycles), so a person can
*see* the corpus growing toward — or away from — consensus.

**Non-goals (this slice).**
- **Not a gate.** Pure visualization; no licensing/status change (the gauge stays an instrument).
- **No per-tick rich compute.** The expensive `ConsistencyReport` (eigendecomp + H¹ BFS) must never
  run inside the tick loop — it is pulled on demand and throttled.
- **Rich layer is live-only** in slice 1 (sample/precomputed-timeline mode shows the HUD if the frames
  carry `consistency`, but not the overlay/halos — see §6).
- **No new protocol fields.** `TopologyNode` is unchanged; per-claim tension is joined viewer-side.

## 2. Constraints / invariants

- **Cost split is load-bearing:** the cheap headline (`ConsistencyHeadline` = energy + λ₂) already
  rides every frame (`TopologyExport.consistency`, computed by `NodeRunner._attach_consistency`); the
  expensive `ConsistencyReport` comes only from the new on-demand route. Never bolt the full report
  onto the per-frame path.
- **`[embed]` gate:** all sheaf compute requires the `[embed]` extra (numpy). Without it,
  `consistency` is `null` on frames and `GET /consistency` returns `{available: false}` — the viewer
  degrades silently (HUD hidden, overlay disabled, no errors).
- **Opt-in / off-safe:** a single overlay toggle gates the entire rich layer. When off: no
  `/consistency` fetch, no overlay, no halos — the scene renders byte-for-byte as it does today. (The
  free HUD may show independently when `consistency` is present.)
- **Server purity boundary unchanged:** the new route lives in the umbrella server (`server.py`),
  reuses the existing `lock` + `asyncio.to_thread` pattern so the eigendecomp never blocks the tick
  loop. `protocol/`/`grammar/` untouched.
- Follow the viewer's existing patterns (Zustand store, R3F scene components, drei `Line`/`Billboard`,
  `theme.ts` palette, the `independence_tier` right-rail precedent).

## 3. Data flow (two channels by cost)

```
LIVE, every frame (free):   NodeRunner._attach_consistency → TopologyExport.consistency
                            (energy + λ₂, already computed) ──SSE /stream──▶ Energy HUD

RICH, throttled pull:       GET /consistency ──(lock + asyncio.to_thread)──▶
                            consistency_report(extract_sheaf(runner.corpus))
                            → { h1_obstructions, per_claim_tension, energies, h0_dim, flags }
                            ──▶ store: obstructions[] + tensionByClaimId{} (joined to nodes by id)
```

- **HUD** consumes the per-frame headline → updates every tick, zero new compute.
- **Overlay + halos** consume the pulled report. The viewer fetches `/consistency` when the overlay is
  toggled on, then **refetches at most every `N=5` followed frames** (compare latest `cycle_index` to
  last-fetched). Between refetches the overlay is "as of last fetch"; the HUD stays frame-current.

## 4. Backend — one new route

`GET /consistency` in `src/polymer_claims/server.py`:
- Under the runner `lock`, run `consistency_report(extract_sheaf(runner.corpus))` via
  `asyncio.to_thread` (mirrors the on-demand `GET /claim/{claim_id}` precedent — never blocks ticks).
- Lazy-import `extract_sheaf` (protocol) + `consistency_report` (`sheaf_spectrum`, behind `[embed]`),
  wrapped in `try/except ImportError` → return `{"available": false}` (HTTP 200) when numpy is absent.
- Success → `ConsistencyReport.model_dump()` (plus `available: true`).
- No other server change; `_attach_consistency` already attaches the per-frame headline.

## 5. Frontend

### 5.1 Types & store
- `viewer/src/lib/topology.ts`: add `ConsistencyHeadline { inconsistency_energy; spectral_gap }` and
  `consistency?: ConsistencyHeadline | null` on `TopologyExport`; add `ConsistencyReport`,
  `Obstruction { claim_ids; edges; magnitude }`, `ClaimTension { claim_id; tension }` (mirrors of
  `protocol/.../sheaf.py`).
- `viewer/src/lib/interpolate.ts`: forward frame-level `consistency` onto the interpolated frame
  (carried verbatim — it is not a spatial quantity to interpolate).
- `viewer/src/store.ts`: `overlayOn: boolean`; `consistencyReport: ConsistencyReport | null`; derived
  `tensionByClaimId: Record<string, number>` and `obstructions: Obstruction[]`; `maxTension` (for
  normalization); `fetchConsistency()` (uses the live base URL) with throttle bookkeeping
  (`lastConsistencyCycle`). Toggling `overlayOn` on triggers an immediate fetch; following live
  refetches when `latestCycle - lastConsistencyCycle >= 5`.

### 5.2 Visual encodings (D2 metrological palette: blue primary, rose = defeat/contradiction, teal =
discovery, amber = pending)
- **Energy HUD** (`viewer/src/components/chrome/EnergyHud.tsx`, new): fixed-corner readout of
  `inconsistency_energy` + `spectral_gap`, with a **sparkline** over the timeline's per-frame headlines
  so the fall is visible. Hue warms teal→amber→rose with energy. Hidden when `consistency == null`.
- **Per-node tension halo** (`viewer/src/components/scene/Nodes.tsx`, `NodeMesh`): a soft billboarded
  disc/ring behind the node, color+opacity scaled by `tension / maxTension` (teal→amber→rose), placed
  at a radius distinct from the FDR ring (r·2.25) and hover ring (r·1.7). Only nodes present in
  `tensionByClaimId` (Quantity-leaf, sheaf-participating) get a halo; all others render unchanged.
  Rendered only when `overlayOn`.
- **H¹ obstruction overlay** (`viewer/src/components/scene/Obstructions.tsx`, new): a separate scene
  pass. For each `Obstruction`, draw its `edges` (claim-id pairs) as bold rose `Line`s between the
  member nodes' positions, animated (pulsing dash/opacity), plus a rose outline ring on member nodes.
  Separate from `Edges.tsx` because cycle pairs are not necessarily topology edges. Positions resolved
  from the same interpolation path `Edges`/`Nodes` use; pairs whose endpoints aren't in the current
  frame are skipped. Rendered only when `overlayOn`.
- **Obstruction panel + node tension** (`viewer/src/components/chrome/RightRail.tsx`): a new section
  listing each obstruction (member `claim_ids` + `magnitude`), **click-to-focus** (selects/highlights
  that cycle — e.g. sets a focused-obstruction id the overlay brightens). Per-claim `tension` shown in
  the existing `NodePanel` and `ClaimDetailCard` when a node is selected (follows the
  `independence_tier` display precedent).
- **Toggle** (`viewer/src/components/chrome/LiveControl.tsx`): a single "consistency overlay" control
  setting `overlayOn`. Off ⇒ no fetch, no overlay, no halos.
- **`theme.ts`**: a 3-stop tension heat scale (teal→amber→rose) + the obstruction overlay color
  (rose family, consistent with the defeat palette).
- **Mounting** (`viewer/src/components/ClaimUniverse.tsx` / its `Scene`): mount `<Obstructions/>` and
  `<EnergyHud/>`.

## 6. Sample mode

The precomputed `sample-timeline.json` path has no `/consistency` server, so the rich layer is
**live-only** in slice 1. Sample mode still shows the **HUD** if its frames carry `consistency`
(otherwise the HUD hides). Bundling a static `ConsistencyReport` fixture (or precomputing per-frame
reports into the sample timeline) so the overlay works in sample mode is a deferred enrichment (§9).

## 7. Testing & verification

- **Backend (pytest, mirrors existing server tests):** serve a node with `[embed]`; `GET /consistency`
  → assert it returns `available: true` and the `ConsistencyReport` shape (`h1_obstructions`,
  `per_claim_tension`, energies, `h0_dim`). Assert graceful `{available: false}` when the
  `sheaf_spectrum` import is unavailable. Assert it does not mutate corpus/runner state.
- **Frontend automated bar:** `npm run typecheck` clean + `next build` clean (the repo has no viewer
  component-unit tests; `tsc`+build is the gate).
- **Manual visual verification** (via the `verify`/`run` skill, `serve` a node): confirm
  (1) the HUD energy **falls** over ticks; (2) a frustrated cycle **lights up** as a rose overlay;
  (3) halos **scale** with tension and sit clear of the FDR/hover rings; (4) **toggle off ⇒ the scene
  is identical to today** (the off-safe invariant); (5) no `[embed]` ⇒ HUD hidden, overlay disabled,
  **no console errors**.
- **Verification dependency:** the manual check needs a live seed corpus that actually yields an H¹
  obstruction — a frustrated cycle (e.g. `A≡B`, `B≡C`, `C⊣A` over Quantity-leaf claims). The default
  seed may not contain one, so the plan includes crafting a small demo seed corpus (or a
  `--seed-corpus` fixture) used solely for verification.

## 8. Implementation note

The R3F scene + chrome components should be built via the **frontend-design** skill (the right tool
for the viewer work); the implementation plan will call that out for the visual tasks. Backend +
types/store are ordinary TDD tasks.

## 9. Future enrichments (deferred)

- **Rich layer in sample mode** — bundle a static `ConsistencyReport` fixture or precompute per-frame
  reports into the sample timeline.
- **Per-frame rich history** — a throttled SSE `consistency` event (server-pushed every N ticks)
  instead of viewer pull, if the pull cadence proves insufficient.
- **Obstruction-aware camera** — auto-frame the worst obstruction; animate energy descent.
- **Tension in protocol export** — if a viewer-side join proves limiting, add an optional
  `sheaf_tension: float | None` to `TopologyNode` (additive) so tension travels with the frame.
- **Hyperbolic/Lorentz layout** (North-Star §5) and **instrument→gate** remain separate arc-3 slices.
