# Claims Universe Viewer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** A runnable Next 16 + R3F viewer at `polymer-claims/viewer/` that renders `TopologyExport` as a D2 metrological instrument.

**Spec:** `docs/superpowers/specs/2026-06-05-claims-viewer-design.md` — READ IT (the aesthetic contract + encodings are binding). Reference the live D2 system at `/Users/zbb2/Desktop/PolymerGenomicsAPI/viewer/src/config/theme.ts` + `docs/redesign/2026-05-19-viewer-redesign-design.md` for exact token values.

**Verification:** `cd /Users/zbb2/Desktop/polymer-claims/viewer && npm run dev` (visual) + `npm run build` + `npx tsc --noEmit`. ABSOLUTE paths (Bash cwd persists). This is a NEW app — does not touch grammar/protocol/PolymerGenomicsAPI.

---

### Task 1: Scaffold app + D2 tokens + fonts + sample data

**Files:** `viewer/package.json`, `viewer/next.config.ts`, `viewer/tsconfig.json`, `viewer/postcss.config.mjs`, `viewer/app/layout.tsx`, `viewer/app/globals.css`, `viewer/src/config/theme.ts`, `viewer/scripts/make_sample.py`, `viewer/public/sample-topology.json`, `viewer/.gitignore`.

- [ ] **Step 1: Scaffold** a Next 16 + React 19 + TS + Tailwind 4 app under `viewer/`. Deps: `next@16`, `react@19`, `react-dom@19`, `three@^0.183`, `@react-three/fiber@^9`, `@react-three/drei@^10`, `zustand@^5`. Dev: `typescript`, `@types/*`, `tailwindcss@^4`, `@tailwindcss/postcss`, `@types/three`. Use the `app/` router. Mirror the API viewer's `next.config.ts`/`tsconfig.json` shape.
- [ ] **Step 2: Fonts** — in `app/layout.tsx`, wire `Inter` + `JetBrains_Mono` from `next/font/google` to `--font-inter` / `--font-jetbrains-mono` (copy the API viewer's pattern). Body `antialiased`, canvas bg `#F4F4F5`.
- [ ] **Step 3: Tokens** — `src/config/theme.ts` exporting `COLOR` / `TYPE` / `WEIGHT` / `SPACE` / `LAYOUT` with the EXACT D2 values from the redesign doc §4 (canvas `#F4F4F5`, surfaces `#FAFAFA`/`#EBEBED`, hairline `#D4D4D8`, borders `#E4E4E7`/`#A1A1AA`, text `#18181B`→`#A1A1AA`, primary `#0F62FE`/`#0043CE`/`#002D9C`, data accents teal `#08A097`/amber `#B45309`/violet `#7C3AED`/rose `#BE123C`; the 14px-anchored type scale; 4px-base spacing; LAYOUT headerHeight 56 / sidebarWidth 220 / inspectorWidth 300). Plus a `STATUS_COLOR` map and `EDGE_COLOR` map per the spec's encodings table.
- [ ] **Step 4: Sample data** — `scripts/make_sample.py` imports the engine (`cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run python ...` context; the script can `sys.path` the protocol/grammar src or run via the protocol uv env). Build a visually-rich corpus per the spec §Data (≥24 claims, 3 patterns, all 5 statuses, defeat+equivalence+entails edges with effective/provisional mix, ≥1 representation-revision node, some strength vectors), call `export_topology(corpus, layout=Layout.FORCE_DIRECTED)`, write `model_dump_json()` to `viewer/public/sample-topology.json`. Document the exact run command in a comment. Commit the generated JSON.
- [ ] **Step 5: Types** — `src/lib/topology.ts`: TS interfaces matching the export (`TopologyNode`/`TopologyEdge`/`TopologyCluster`/`TopologyExport`) + a loader.
- [ ] **Step 6: Verify + commit.** `npm install`, `npm run build` succeeds, `npx tsc --noEmit` clean. Commit `feat(viewer): scaffold D2 Next+R3F app + tokens + sample topology`.

### Task 2: The instrument scene (canvas, camera, reference frame, axes, grid, lighting)

**Files:** `viewer/src/components/ClaimUniverse.tsx` (the R3F root, `dynamic(ssr:false)` mounted), `viewer/src/components/scene/ReferenceFrame.tsx`, `viewer/app/page.tsx`.

- [ ] **Step 1:** `app/page.tsx` — full-viewport layout (header slot, canvas, panel slots), bg `#F4F4F5`. Mount `ClaimUniverse` via `dynamic(() => import(...), { ssr:false, loading: <mono "loading…"> })`.
- [ ] **Step 2:** `ClaimUniverse.tsx` — `<Canvas>` (bg `#F4F4F5`, camera perspective ~50° positioned to frame the extent), `OrbitControls` (damping), `ambientLight intensity={0.8}` + `directionalLight intensity={0.4}`. Compute the node-position extent (min/max per axis) once from the loaded export.
- [ ] **Step 3:** `ReferenceFrame.tsx` — a hairline wireframe **bounding box** (`#D4D4D8`) around the extent; a **ground grid** (drei `<Grid>` or `<gridHelper>` restyled to `#E4E4E7` hairlines) at `y = ymin`; **X/Y/Z axes** (`#A1A1AA` `<Line>`) with tick marks at round intervals and **`<Html>` mono tabular-nums labels** of the coordinate values at ticks; a small `layout_id` caption (mono, `#52525B`). No glow.
- [ ] **Step 4: Verify + commit.** Dev server renders the empty instrument frame (grid + box + ticked axes) on light canvas, orbitable. `feat(viewer): metrological scene — reference frame, ticked axes, grid`.

### Task 3: Nodes + edges (matte, glyphs, status/kind encodings, hover)

**Files:** `viewer/src/components/scene/Nodes.tsx`, `viewer/src/components/scene/Edges.tsx`, `viewer/src/store.ts` (zustand).

- [ ] **Step 1: Store** — `store.ts`: zustand store `{ data, selectedId, hoveredId, filters:{statuses:Set, kinds:Set, showProvisional:bool}, setHover, setSelected, toggle… }` + derived counts.
- [ ] **Step 2: Nodes** — one matte mesh per node at `node.position`. Geometry: `octahedronGeometry` if `is_representation_revision` else `sphereGeometry` (small, ~0.28). `meshStandardMaterial color={STATUS_COLOR[status]} metalness={0} roughness={0.9}` (NO emissive). Optional subtle radius scale from `strength.evidence_against_null`. Hover → set hoveredId + a thin electric-blue **hairline ring** (a `<Line>` circle or thin torus, billboarded) + `<Html>` mono label (id + status; 90% `#F4F4F5` bg, 1px node-color border, NO scale-bloom). Click → `setSelected`. Respect filters (hidden if status filtered out).
- [ ] **Step 3: Edges** — one drei `<Line>` per edge between the resolved endpoint positions. `color = EDGE_COLOR[kind]` (defeat→rose, equivalence→`#A1A1AA`, entails→`#0F62FE`); `dashed` + opacity 0.35 if `provisional`; solid full-opacity if `effective`; faint solid otherwise. `lineWidth: 1`. Respect kind + provisional filters; hide if either endpoint hidden.
- [ ] **Step 4: Verify + commit.** Dev server shows the matte universe: status-colored nodes, octahedron revisions, dashed provisional edges, hover ring+label, selection. `feat(viewer): matte nodes + edges with status/kind encodings + hover`.

### Task 4: Chrome — header, legend/filters, inspector, mono readout

**Files:** `viewer/src/components/chrome/Header.tsx`, `LegendRail.tsx`, `InspectorPanel.tsx`, `ReadoutOverlay.tsx`; wire into `app/page.tsx`.

- [ ] **Step 1: Header** — 56px, hairline bottom rule, wordmark + `§` route marker, mono. D2 tokens.
- [ ] **Step 2: LegendRail** (left, ~220px, hairline border) — status colorbar (5 keys w/ exact labels + color chips), edge-kind key, glyph key (sphere=claim / octahedron=revision), and **filter toggles** (status checkboxes, edge-kind checkboxes, show/hide-provisional) wired to the store. Toggling updates the scene live.
- [ ] **Step 3: InspectorPanel** (right, ~300px, hairline, hidden until `selectedId`) — selected node `id`, `status` (chip), `pattern_id`, `subject_kind`, `is_representation_revision`, and the **exact `strength` 6-vector** as a labeled `tabular-nums` mono table (one row/axis; "—" if null). `§02 — NODE` marker. Close deselects.
- [ ] **Step 4: ReadoutOverlay** (bottom-left, mono, tabular-nums) — `§01 — CLAIM UNIVERSE`, total nodes, per-status counts, total edges (+ effective/provisional split), `layout_id`, and **live camera position** `(x,y,z)` (subscribe to the R3F camera via a small bridge that writes coords to the store on `useFrame`, throttled).
- [ ] **Step 5: Verify + commit.** Full instrument: header + legend/filters + inspector + live readout, all D2 hairline/tabular-nums, no shadows/glow. `feat(viewer): D2 chrome — header, legend/filters, inspector, readout`.

### Final
- [ ] `npm run build` + `npx tsc --noEmit` clean; manual eyeball against the acceptance checklist in the spec (no glow/neon/shadow; electric-blue singular accent; reference frame + ticks; tabular-nums; octahedron revisions; dashed provisional edges; all Core interactions). Then finish the branch via superpowers:finishing-a-development-branch (merge local no-ff, no push).

## Self-Review
- Spec coverage: tokens/fonts (T1), scene/frame/axes (T2), nodes/edges/encodings/hover (T3), chrome/filters/inspector/readout (T4). ✓
- No-placeholder: exact hex/token values, geometry/material params, encoding maps, store shape all specified. ✓
- Aesthetic guardrails repeated where they bite (matte, no emissive, hairline, tabular-nums, no shadow). ✓
- Isolation: new app; imports nothing from grammar/protocol at runtime (consumes exported JSON); does not modify PolymerGenomicsAPI. ✓
