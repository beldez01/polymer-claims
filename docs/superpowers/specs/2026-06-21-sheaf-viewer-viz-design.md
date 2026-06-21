# Sheaf Gauge Viewer Visualization — Design

**Date:** 2026-06-21 · **Status:** Design (approved in brainstorm; revised after spec audit; pre-plan)
**Builds on:** `docs/superpowers/specs/2026-06-21-sheaf-consistency-gauge-design.md` (the gauge itself,
merged `fe1214d`). This is the named **rich-viz fast-follow** from that spec's §8, and the first
viewer-facing piece of North-Star arc 3 (living universe) / linchpin A3 (Reproducibility Observatory).

> **One line.** Make the sheaf consistency gauge *legible* on the live 3D universe: a falling
> energy HUD, per-claim **tension halos**, and H¹ **frustration-cycle overlays** — contradiction loops
> no pairwise check sees, lit up on the graph. Fed by a new throttled `GET /consistency` endpoint;
> one opt-in toggle gates the whole layer, so the view is byte-for-byte today's when off.

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

The audit found the shipped gauge can't support a cheap per-frame headline or a non-blocking
endpoint as-is. These three corrections to the already-merged gauge are **prerequisite tasks**, landed
and tested **before** any viewer work:

- **P1 — per-frame headline becomes energy-only.** Today `consistency_headline()` calls
  `_spectrum_core()`, which runs dense `np.linalg.eigvalsh(L)` to produce λ₂ — so every frame does an
  eigendecomposition. Change `ConsistencyHeadline` to carry **`inconsistency_energy` only**, computed
  by a cheap path (`energy = (w * (δx)²).sum() / Σw`, no eigendecomposition). **`spectral_gap` (λ₂)
  moves to `consistency_report` only** (on-demand). The HUD's live signal is the falling energy; λ₂ is
  shown from the pulled report. Update the gauge's `consistency_headline` test accordingly.
- **P2 — `/consistency` must not hold the tick lock during compute.** Acquire the runner `lock` only
  long enough to **snapshot `runner.corpus`** (a reference grab — `Corpus` is a frozen, immutable
  model, so the snapshot is safe to read without the lock), **release**, then run
  `extract_sheaf` + `consistency_report` on the snapshot inside `asyncio.to_thread`. The eigendecomp
  never serializes the tick loop.
- **P3 — `per_claim_tension` becomes a nonnegative edge-share attribution.** Today
  `tension_i = x_i·(Lx)_i / Σw` (the Rayleigh diagonal) sums to energy but **individual terms can be
  negative** — invalid as an opacity. Replace with the **edge-share attribution**
  `tension_i = Σ_{e incident to i} w_e · d_e² / 2`, normalized by total edge weight. This is
  **nonnegative**, still sums to the inconsistency energy, and is directly interpretable ("how much
  edge tension touches this claim"). Update `sheaf_spectrum.py` + its tension test.

These keep the gauge's invariants (pure protocol extractor; numpy behind `[embed]`; additive). P1/P3
change a shipped DTO/field, but the only current consumer is the `export-consistency` CLI + tests,
and the viz isn't built yet — so this is a safe, honest correction, not a break.

## 3. Constraints / invariants

- **Cost split (post-P1):** the **energy-only** headline rides every frame
  (`TopologyExport.consistency`) — a genuine mat-vec. The expensive report (λ₂, H⁰, H¹, tension) comes
  only from the new on-demand route. Never put eigendecomposition on the per-tick path.
- **`[embed]` gate:** all sheaf compute needs the `[embed]` extra (numpy). Without it, `consistency`
  is `null` on frames and `GET /consistency` returns `{available: false}` — the viewer degrades
  silently (HUD hidden, overlay disabled, no errors).
- **One toggle, fully off-safe:** a single "consistency overlay" toggle gates the **entire** layer —
  HUD, halos, obstruction overlay, and panel. When **off**: no `/consistency` fetch, no overlay, no
  halos, **no HUD** → the chrome and 3D scene are byte-for-byte today's view. (Resolves the audit's
  off-safe contradiction: the HUD is part of the gated layer, not always-on.)
- **Server purity boundary unchanged:** the new route lives in the umbrella server (`server.py`);
  `protocol/`/`grammar/` untouched.
- Follow the viewer's existing patterns (Zustand store, R3F scene components, drei `Line`/`Billboard`,
  `theme.ts` palette, the `independence_tier` right-rail precedent).

## 4. Data flow (two channels by cost)

```
LIVE, every frame (cheap mat-vec):   NodeRunner._attach_consistency → TopologyExport.consistency
                                     ({inconsistency_energy}) ──SSE /stream──▶ Energy HUD

RICH, throttled pull:   GET /consistency ──(lock: snapshot corpus → release)──▶
                        asyncio.to_thread: consistency_report(extract_sheaf(snapshot))
                        → { spectral_gap, h0_dim, h1_obstructions, per_claim_tension, energies, flags }
                        ──▶ store: obstructions[] + tensionByClaimId{} (+ maxTension) joined by id
```

- **HUD** consumes the per-frame energy → updates every tick, no eigendecomposition.
- **Overlay + halos + λ₂** consume the pulled report. The viewer fetches `/consistency` when the
  toggle turns on, then **refetches at most every `N=5` followed frames** (compare latest `cycle_index`
  to last-fetched), **guarded by an in-flight flag** so a slow report can't stack duplicate fetches.
  Between refetches the overlay/λ₂ are "as of last fetch"; the energy HUD stays frame-current.

## 5. Backend — one new route

`GET /consistency` in `src/polymer_claims/server.py` (uses the P2 snapshot pattern):
- Acquire `lock` → take `corpus = runner.corpus` → release lock. Then in `asyncio.to_thread`, lazily
  import `extract_sheaf` (protocol) + `consistency_report` (`sheaf_spectrum`, `[embed]`), wrapped in
  `try/except ImportError`.
- **Response is a discriminated union:** `{ "available": false }` (HTTP 200) when numpy is absent;
  otherwise `{ "available": true, ...ConsistencyReport.model_dump() }`. The UI keys "disabled" off
  `available === false` — distinct from a real `available:true` report whose `h1_obstructions` is
  empty (a genuinely consistent corpus). Never conflate "unavailable" with "no obstructions."
- Read-only: does not mutate corpus/runner state. No other server change (`_attach_consistency`
  already attaches the energy headline post-P1).

## 6. Frontend

### 6.1 Types & store (the contract comes first)
**First frontend task — the viewer contract** (the field the rest builds on is currently absent):
- `viewer/src/lib/topology.ts`: add `ConsistencyHeadline { inconsistency_energy }` (energy-only,
  per P1) and `consistency?: ConsistencyHeadline | null` on `TopologyExport`; add `ConsistencyReport`
  (now the home of `spectral_gap`), `Obstruction { claim_ids; edges; magnitude }`,
  `ClaimTension { claim_id; tension }`. Add the route type:
  `type ConsistencyResponse = { available: false } | ({ available: true } & ConsistencyReport)`.
- `viewer/src/lib/interpolate.ts`: forward frame-level `consistency` onto the interpolated frame
  (carried verbatim — `interpolateFrame` currently returns only nodes/edges/stats/layoutId, so this
  is an explicit addition).

**Store** (`viewer/src/store.ts`): `overlayOn: boolean`; `consistencyReport: ConsistencyReport | null`;
`consistencyAvailable: boolean`; derived `tensionByClaimId: Record<string, number>` + `maxTension`;
`obstructions: Obstruction[]`; `lastConsistencyCycle: number`; an `inFlight` guard; and a
`fetchConsistency()` **store action** (uses the live base URL; sets/clears `inFlight`, updates report +
derived maps + `lastConsistencyCycle`, sets `consistencyAvailable`).

**Fetch trigger — explicit (resolves audit finding 5):** the throttle lives in a **single React effect**
(a `useConsistencySync()` hook mounted once in `ClaimUniverse`), **not** inside `pushFrame`. The effect
depends on `[latestCycle, overlayOn]` and calls `fetchConsistency()` only when
`overlayOn && !inFlight && (latestCycle - lastConsistencyCycle >= N)` (and once immediately when the
toggle flips on). Keeping it in one effect with the `inFlight` guard prevents duplicate fetches and
stale-report races.

### 6.2 Visual encodings (D2 metrological palette: blue primary, rose = defeat/contradiction, teal =
discovery, amber = pending) — all rendered only when `overlayOn`
- **Energy HUD** (`viewer/src/components/chrome/EnergyHud.tsx`, new): fixed-corner readout of
  `inconsistency_energy` (live, per-frame) with a **sparkline** over the timeline's per-frame energies
  so the fall is visible; `spectral_gap` shown beneath when a report is available (may lag by ≤N
  frames). Hue warms teal→amber→rose with energy. Hidden when `consistency == null` / overlay off.
- **Per-node tension halo** (`viewer/src/components/scene/Nodes.tsx`, `NodeMesh`): a soft billboarded
  disc/ring behind the node, color+opacity = `tension / maxTension` (teal→amber→rose) — now valid
  because tension is **nonnegative** (P3). Placed at a radius distinct from the FDR ring (r·2.25) and
  hover ring (r·1.7). Only nodes present in `tensionByClaimId` (Quantity-leaf, sheaf-participating) get
  a halo; all others render unchanged.
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
**live-only** in slice 1. Sample mode shows the **HUD** only if its frames carry the energy headline
(otherwise hidden). Bundling a static `ConsistencyReport` fixture (or precomputing reports into the
sample timeline) so the overlay works in sample mode is a deferred enrichment (§9).

## 8. Testing & verification

- **Backend prerequisites:** P1 — assert `consistency_headline` no longer calls `eigvalsh` (energy
  matches the report's energy; `ConsistencyHeadline` has no `spectral_gap`). P3 — assert every
  `per_claim_tension.tension ≥ 0` and `Σ tension == inconsistency_energy` (within 1e-9) on a mixed
  equivalence/defeat corpus. P2 — assert (by construction/inspection) the endpoint computes outside
  the lock (snapshot then release).
- **New route (pytest, mirrors existing server tests):** serve a node with `[embed]`; `GET /consistency`
  → `available: true` + the `ConsistencyReport` shape; assert `{available: false}` when the
  `sheaf_spectrum` import is unavailable; assert it does not mutate corpus/runner state.
- **Frontend automated bar:** `npm run typecheck` clean + `next build` clean (the repo has no viewer
  component-unit tests; `tsc`+build is the gate).
- **Manual visual verification** (via the `verify`/`run` skill, `serve` a node): (1) the HUD energy
  **falls** over ticks; (2) a frustrated cycle **lights up** as a rose overlay; (3) halos **scale** with
  (nonnegative) tension and sit clear of the FDR/hover rings; (4) **toggle off ⇒ chrome + 3D scene
  identical to today**; (5) no `[embed]` ⇒ HUD hidden, overlay disabled (`available:false`), **no
  console errors**; (6) a genuinely consistent corpus (`available:true`, empty obstructions) shows the
  HUD with **no** overlay — distinct from the unavailable state.
- **Verification dependency:** the manual check needs a live seed corpus that yields an H¹ obstruction —
  a frustrated cycle (e.g. `A≡B`, `B≡C`, `C⊣A` over Quantity-leaf claims). The default seed may not
  contain one, so the plan includes crafting a small demo seed corpus (or `--seed-corpus` fixture) for
  verification.

## 9. Implementation note & sequencing

Task order: **(1) backend prerequisites P1–P3** (correct the gauge) → **(2) the `/consistency` route** →
**(3) the viewer contract** (types + `interpolateFrame` forwarding) → **(4) store + fetch hook** →
**(5) R3F visuals + chrome**. The R3F/chrome work (5) should be built via the **frontend-design** skill;
P1–P3, the route, types, and store are ordinary TDD tasks.

## 10. Future enrichments (deferred)

- **Rich layer in sample mode** — bundle a static `ConsistencyReport` fixture or precompute per-frame
  reports into the sample timeline.
- **Per-frame rich history** — a throttled server-pushed SSE `consistency` event instead of viewer pull,
  if the pull cadence proves insufficient.
- **λ₂ on the live frame** — if a live spectral-gap readout is wanted without a pull, compute it via a
  cheap iterative method (e.g. a few Lanczos iterations) rather than dense `eigvalsh`.
- **Tension in protocol export** — if the viewer-side join proves limiting, add an optional
  `sheaf_tension: float | None` to `TopologyNode` (additive) so tension travels with the frame.
- **Obstruction-aware camera**; **Hyperbolic/Lorentz layout** (North-Star §5); **instrument→gate** —
  separate arc-3 slices.

## 11. Audit reconciliation (this revision)

| Audit finding | Resolution |
|---|---|
| 1. Headline not actually cheap (eigvalsh per frame) | **P1** — headline energy-only; λ₂ → report (§2, §4) |
| 2. Lock held during eigendecomp stalls ticks | **P2** — snapshot corpus under lock, release, compute in thread (§2, §5) |
| 3. Off-safe contradicts always-on HUD | One toggle gates the **whole** layer incl. HUD; off = identical (§3) |
| 4. Viewer `consistency` field missing | First frontend task: add the type + forward through `interpolateFrame` (§6.1, §9) |
| 5. Fetch trigger underspecified | Single `useConsistencySync()` effect on `[latestCycle, overlayOn]` + in-flight guard (§6.1) |
| 6. Tension can be negative | **P3** — nonnegative edge-share attribution `Σ_{e∋i} w·d²/2` (§2) |
| 7. Response should be discriminated union | `{available:false} | ({available:true} & ConsistencyReport)`; UI disables on unavailable (§5, §6.1) |
