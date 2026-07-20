# Claims Universe → polymerbio.org graft (V1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the current `polymer-claims` Claims Universe viewer at `polymerbio.org/claims`, rendering the real warranted corpus, single-source (no code copied into the API repo), without breaking the live site.

**Architecture:** Next.js **multi-zone**. The viewer stays in `polymer-claims/viewer` and deploys as its own Vercel project with `basePath: '/claims'`. polymerbio.org (the API repo's `viewer/`) gains a `rewrites()` entry proxying `/claims/*` to that deployment. The viewer runs static — it fetches the bundled real corpus `public/merged-universe.json`, no backend.

**Tech Stack:** Next.js 16.1.6, React 19, React Three Fiber, zustand, Vercel. Python (uv) only for the corpus regen script.

## Global Constraints

- **No source copied between repos.** The viewer lives only in `polymer-claims/viewer`. The API repo changes are limited to `viewer/next.config.ts` (rewrite) and 3 nav-link edits.
- **Live site untouched until Task 5.** Tasks 1–4 operate on the claims viewer and its own isolated Vercel deployment; nothing a polymerbio.org visitor sees changes until the Task 5 rewrite.
- **No JS unit-test runner exists in `viewer/`** (package.json has no test script; pattern is verify-by-typecheck+build). Verification cadence per task = `npm run typecheck` → `npm run build` → deploy-preview check. Do not add vitest/jest (YAGNI).
- **Corpus is real and already committed.** V1 ships the existing `viewer/public/merged-universe.json`. Regen command (documented, not run for V1): `cd ~/Desktop/polymer-claims && uv run --project . python viewer/scripts/make_merged_universe.py` (needs gitignored GDSC pharmaco data).
- **Env var (single source of the subpath):** `NEXT_PUBLIC_BASE_PATH` — `''`/unset for standalone dev, `/claims` in the zone deploy. Read by BOTH `next.config.ts` (basePath/assetPrefix) and `src/lib/asset.ts` (fetch prefix) so they never drift.
- **Commits/branches happen on the user's go** (their standing rule). Branches: `polymer-claims` → `feat/claims-universe-graft`; `PolymerGenomicsAPI` → `feat/claims-zone-rewrite`. Commit messages below are the intended messages; confirm before running `git commit`.
- Node version: Next 16.1.6 requires Node ≥ 20.

---

### Task 1: basePath-aware public-asset fetches

Makes the viewer's static-corpus fetches resolve under `/claims`. Root cause: `ClaimUniverse.tsx` fetches `/merged-universe.json` (root-absolute); under `basePath` the file lives at `/claims/merged-universe.json`, so without this the deploy shows "loading topology…" forever.

**Files:**
- Create: `viewer/src/lib/asset.ts`
- Modify: `viewer/src/lib/timeline.ts:43`
- Modify: `viewer/src/lib/topology.ts:148`

**Interfaces:**
- Produces: `assetUrl(path: string): string` — prefixes a root-absolute public path with `NEXT_PUBLIC_BASE_PATH`. Consumed by `timeline.ts`, `topology.ts` (and available to any future public-asset fetch).

- [ ] **Step 1: Create the helper**

`viewer/src/lib/asset.ts`:
```ts
// Prefix root-absolute public-asset URLs (e.g. '/merged-universe.json') with the app
// basePath, so fetches resolve when the viewer is served under a subpath (/claims) as a
// multi-zone on polymerbio.org. NEXT_PUBLIC_BASE_PATH is '' for standalone dev and
// '/claims' in the zone deploy — the SAME env next.config.ts reads for basePath, so the
// two can never disagree. NEXT_PUBLIC_* is inlined at build, so this works in the browser.
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

export function assetUrl(path: string): string {
  return `${BASE_PATH}${path}`;
}
```

- [ ] **Step 2: Wrap the timeline fetch**

In `viewer/src/lib/timeline.ts`, add the import at the top (with the other imports):
```ts
import { assetUrl } from './asset';
```
Change line 43 from:
```ts
  const res = await fetch(url);
```
to:
```ts
  const res = await fetch(assetUrl(url));
```
(Leave the `url = '/sample-timeline.json'` default and all callers passing plain `/merged-universe.json` etc. unchanged — prefixing happens in this one place. Live-mode fetches in `live.ts` are NOT touched: they target a user-entered node base URL, not a public asset.)

- [ ] **Step 3: Wrap the topology fetch**

In `viewer/src/lib/topology.ts`, add near the other imports:
```ts
import { assetUrl } from './asset';
```
Change line 148 from:
```ts
  const res = await fetch(url);
```
to:
```ts
  const res = await fetch(assetUrl(url));
```

- [ ] **Step 4: Verify types + standalone still works**

Run: `cd viewer && npm run typecheck`
Expected: exits 0, no errors.

Run: `NEXT_PUBLIC_BASE_PATH='' npm run build`
Expected: build succeeds. (Empty base path → `assetUrl('/x')` === `/x`, identical to today.)

- [ ] **Step 5: Commit**

```bash
git add viewer/src/lib/asset.ts viewer/src/lib/timeline.ts viewer/src/lib/topology.ts
git commit -m "feat(viewer): basePath-aware public-asset fetches (multi-zone prep)"
```

---

### Task 2: basePath / assetPrefix from env in the viewer next.config

**Files:**
- Modify: `viewer/next.config.ts`

**Interfaces:**
- Consumes: `NEXT_PUBLIC_BASE_PATH` env.
- Produces: a viewer that serves under `/claims` when the env is set, and at root when it isn't.

- [ ] **Step 1: Edit the config**

Replace `viewer/next.config.ts` contents with:
```ts
import type { NextConfig } from "next";
import path from "node:path";

// '' for standalone dev; '/claims' in the multi-zone deploy on polymerbio.org.
// Must start with '/' or be undefined — never the empty string — per Next's basePath rule.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || undefined;

const nextConfig: NextConfig = {
  basePath,
  // assetPrefix = basePath is the documented multi-zone pattern: the child's _next
  // assets are requested under /claims so the parent rewrite forwards them.
  assetPrefix: basePath,
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
```

- [ ] **Step 2: Verify both modes build**

Run: `cd viewer && NEXT_PUBLIC_BASE_PATH='' npm run build`
Expected: succeeds; output routes listed at `/` (no basePath).

Run: `NEXT_PUBLIC_BASE_PATH=/claims npm run build`
Expected: succeeds; build logs show routes/assets under `/claims`.

- [ ] **Step 3: Runtime smoke (subpath)**

Run: `NEXT_PUBLIC_BASE_PATH=/claims npm run build && NEXT_PUBLIC_BASE_PATH=/claims npm run start &` then
`sleep 3 && curl -sI http://localhost:3000/claims | head -1 && curl -sI http://localhost:3000/claims/merged-universe.json | head -1`
Expected: both return `HTTP/1.1 200`. Then stop the server (`kill %1`).

- [ ] **Step 4: Commit**

```bash
git add viewer/next.config.ts
git commit -m "feat(viewer): basePath+assetPrefix from NEXT_PUBLIC_BASE_PATH (multi-zone)"
```

---

### Task 3: Immersive "return to PolymerBio" affordance

The immersive-takeover decision: the viewer keeps its own chrome; add one slim persistent link back into the company site so `/claims` isn't a dead end.

**Files:**
- Create: `viewer/src/components/chrome/ReturnLink.tsx`
- Modify: `viewer/app/page.tsx`

**Interfaces:**
- Produces: `<ReturnLink />` — a fixed-position anchor to `https://polymerbio.org`.

- [ ] **Step 1: Create the component**

`viewer/src/components/chrome/ReturnLink.tsx`:
```tsx
'use client';

import { COLOR, FONT_FAMILY_MONO } from '@/config/theme';

// Slim persistent return into the company site. Bottom-left so it clears the
// top Header and the right-side rails; z-index above the canvas.
export default function ReturnLink() {
  return (
    <a
      href="https://polymerbio.org"
      style={{
        position: 'fixed',
        bottom: 12,
        left: 12,
        zIndex: 50,
        fontFamily: FONT_FAMILY_MONO,
        fontSize: 11,
        letterSpacing: '0.04em',
        color: COLOR.text.muted,
        textDecoration: 'none',
      }}
      className="mono"
    >
      ← polymerbio.org
    </a>
  );
}
```

- [ ] **Step 2: Mount it in the page**

In `viewer/app/page.tsx`, add the import with the other chrome imports:
```tsx
import ReturnLink from '@/components/chrome/ReturnLink';
```
Then add `<ReturnLink />` inside `<main>`, right after `<EnergyHud />`:
```tsx
      <EnergyHud />
      <ReturnLink />
    </main>
```

- [ ] **Step 3: Verify + visual nudge**

Run: `cd viewer && npm run typecheck` → exits 0.
Run: `npm run dev` and open `http://localhost:3000`. Confirm the "← polymerbio.org" link is visible bottom-left and does NOT overlap `LegendRail`/`TransportBar`. If it collides, adjust `bottom`/`left` in `ReturnLink.tsx` until clear.

- [ ] **Step 4: Commit**

```bash
git add viewer/src/components/chrome/ReturnLink.tsx viewer/app/page.tsx
git commit -m "feat(viewer): persistent return link to polymerbio.org (immersive chrome)"
```

---

### Task 4: Deploy the claims viewer as its own Vercel project (isolated)

Nothing a polymerbio.org visitor sees changes here — this is a standalone deployment we verify on its own URL first.

**Files:** none (deploy config only).

- [ ] **Step 1: Link a new Vercel project**

Run: `cd viewer && vercel link` — create a NEW project (suggested name `polymer-claims-viewer`). Root directory = the `viewer/` dir itself (you're in it).

- [ ] **Step 2: Set the zone env var**

Run: `vercel env add NEXT_PUBLIC_BASE_PATH production` → value `/claims`. Repeat for `preview` scope with value `/claims`.

- [ ] **Step 3: Deploy a preview**

Run: `vercel deploy` (preview). Capture the resulting deployment URL as `$ZONE`.

- [ ] **Step 4: Verify the isolated deployment**

Run:
```bash
curl -sI "$ZONE/claims" | head -1
curl -sI "$ZONE/claims/merged-universe.json" | head -1
```
Expected: both `HTTP/2 200`.
Then open `$ZONE/claims` in a browser: confirm the 3D universe renders the REAL corpus (nodes present, per-node inspector opens on click, arms like `polymergenomics`/`pharmaco` visible in the legend), and the return link shows.

- [ ] **Step 5: Promote to a stable production URL for the zone**

Run: `vercel deploy --prod`. Capture the production URL as `$ZONE_PROD` (e.g. `https://polymer-claims-viewer.vercel.app`). This is the stable target the parent rewrite will point at. No git commit (deploy-only task).

- [ ] **Step 6: Document the regen command**

Append to `viewer/README.md` (create if absent) a short "Corpus regeneration" note with the exact command from Global Constraints, so the shipped corpus is reproducible.
```bash
git add viewer/README.md
git commit -m "docs(viewer): document merged-universe corpus regen command"
```

---

### Task 5: Rewrite `/claims` on polymerbio.org to the zone (the one live change)

**Repo:** `PolymerGenomicsAPI` (branch `feat/claims-zone-rewrite`).

**Files:**
- Modify: `PolymerGenomicsAPI/viewer/next.config.ts`

**Interfaces:**
- Consumes: `$ZONE_PROD` from Task 4 via env `NEXT_PUBLIC_CLAIMS_ZONE`.

- [ ] **Step 1: Add the zone base + swap redirect for rewrite**

In `PolymerGenomicsAPI/viewer/next.config.ts`:

Add near the top, after the `apiBase` block:
```ts
// The claims Claims-Universe viewer is a separate Vercel deployment (multi-zone).
const claimsZone = process.env.NEXT_PUBLIC_CLAIMS_ZONE || "";
```

Delete the entire legacy `/claims` → `/portal/latent3d` object from `redirects()` (leave `redirects()` returning `[]` if it becomes empty).

Add to the `rewrites()` array (alongside the existing `/api/:path*` entry), guarded so a missing env doesn't emit a broken rewrite:
```ts
      ...(claimsZone
        ? [
            { source: '/claims', destination: `${claimsZone}/claims` },
            { source: '/claims/:path*', destination: `${claimsZone}/claims/:path*` },
          ]
        : []),
```

- [ ] **Step 2: Set the env on the polymerbio.org Vercel project**

Run (from `PolymerGenomicsAPI/viewer`): `vercel env add NEXT_PUBLIC_CLAIMS_ZONE production` → value = `$ZONE_PROD` (e.g. `https://polymer-claims-viewer.vercel.app`).

- [ ] **Step 3: Deploy a PREVIEW of polymerbio.org and verify (still not touching prod)**

Run: `vercel deploy` (preview) from `PolymerGenomicsAPI/viewer`. Capture preview URL `$SITE_PREVIEW`.
Run: `curl -sI "$SITE_PREVIEW/claims" | head -1` → expect `HTTP/2 200`.
Open `$SITE_PREVIEW/claims`: confirm it serves the NEW viewer (immersive universe), and that `$SITE_PREVIEW/portal/latent3d` still serves the OLD one (parallel, unbroken).

- [ ] **Step 4: Ship to production**

Run: `vercel deploy --prod`. Verify `https://polymerbio.org/claims` serves the new viewer.
**Rollback rehearsal:** confirm you can revert instantly via `vercel rollback` (or redeploying the prior deployment) — note the previous prod deployment id before shipping.

- [ ] **Step 5: Commit**

```bash
git add viewer/next.config.ts
git commit -m "feat(viewer): multi-zone /claims → Claims Universe deployment; drop legacy redirect"
```

---

### Task 6: Flip site navigation to `/claims`

**Repo:** `PolymerGenomicsAPI` (same branch).

**Files:**
- Modify: `PolymerGenomicsAPI/viewer/src/components/BrandBar.tsx:107`
- Modify: `PolymerGenomicsAPI/viewer/src/components/Footer.tsx:53`
- Modify: `PolymerGenomicsAPI/viewer/src/app/page.tsx:80`

- [ ] **Step 1: Repoint the three links**

In each file, change the claims nav target from `/portal/latent3d` to `/claims`:
- `BrandBar.tsx:107` — the `<NavLink href="/portal/latent3d">Claims</NavLink>` → `href="/claims"`.
- `Footer.tsx:53` — `<FootLink href="/portal/latent3d">Claims</FootLink>` → `href="/claims"`.
- `app/page.tsx:80` — the home nav item `href: '/portal/latent3d'` (name `'Claims'`) → `href: '/claims'`.

- [ ] **Step 2: Verify**

Run: `cd PolymerGenomicsAPI/viewer && npm run build` → succeeds.
Run: `grep -rn "portal/latent3d" src/ app/` → expect ZERO remaining nav references (portal sub-tab config in `app/portal/layout.tsx` may still list it; that's retired in Task 7).

- [ ] **Step 3: Deploy + confirm**

Run: `vercel deploy --prod`. On `polymerbio.org`, click "Claims" in header and footer → both land on `/claims` (the new viewer).

- [ ] **Step 4: Commit**

```bash
git add viewer/src/components/BrandBar.tsx viewer/src/components/Footer.tsx viewer/src/app/page.tsx
git commit -m "feat(viewer): repoint Claims nav to /claims (retire /portal/latent3d)"
```

---

### Task 7: Cleanup — retire old claims surfaces + dead code (GATED)

**Do this only after Tasks 5–6 are confirmed live and stable in production.** Separate commit so it can be reverted independently of the graft.

**Repo:** `PolymerGenomicsAPI` (same branch).

**Files (delete):**
- `viewer/src/app/portal/latent3d/` (dir)
- `viewer/src/app/portal/graph/` (dir)
- `viewer/src/components/FormalClaim/` (dir)
- `viewer/src/components/FormalClaimUniverse/` (dir)
- `viewer/src/components/claims/` (dir — already dead)
- `viewer/src/config/claims.ts`, `viewer/src/config/formal_claims.ts`, `viewer/src/config/formal_projection.ts`
- `viewer/src/data/formal_claim_projection_v1.json`
- `viewer/src/lib/formalClaimsHelpers.ts`, `formalClaimsRegion.ts`, `formalClaimsExport.ts` (verify exact names before deleting)
- `viewer/src/components/newsroom/NewsroomEntry.tsx` (orphaned; imports `claims.ts`)

**Files (modify):**
- `viewer/src/app/portal/layout.tsx` — remove the `latent3d` and `graph` entries from `PROJECTION_TABS` (keep the layout + remaining tabs intact).

- [ ] **Step 1: Confirm three.js / xyflow / dagre are claims-only before dropping deps**

Run: `cd PolymerGenomicsAPI/viewer && grep -rn "@react-three\|from 'three'\|@xyflow/react\|dagre" src/ app/ | grep -viE "FormalClaim|components/claims|portal/(latent3d|graph)"`
Expected: ZERO hits. If any appear, those deps stay — do NOT remove them from package.json.

- [ ] **Step 2: Delete the dead surfaces**

Run the deletions for every path listed above (use `git rm -r`).

- [ ] **Step 3: Prune the portal tabs**

Edit `viewer/src/app/portal/layout.tsx`: remove the `latent3d` + `graph` objects from `PROJECTION_TABS` (around lines 13–14). Leave `dev/claim/[id]` alone (already prod-gated) unless you also want it gone — out of scope; leave it.

- [ ] **Step 4: Remove now-unused deps (only if Step 1 was clean)**

Edit `viewer/package.json` to drop `@xyflow/react`, `dagre`, `three`, `@react-three/*`, `@types/three` **only for those Step 1 proved unused**. Run `npm install` to update the lockfile.

- [ ] **Step 5: Verify the site still builds and non-claims routes work**

Run: `npm run build` → succeeds with no missing-import errors.
Run: `npm run start &` then visit `/`, `/portal`, `/portal/submit`, and any remaining `/portal/*` → all render; `/claims` still proxies to the zone. Stop the server.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore(viewer): remove obsolete forked claims viewer + dead v2 claims code"
```

---

## Self-Review

**Spec coverage:**
- §3 decisions → Tasks 1–6 (multi-zone, basePath, immersive chrome, retire old, static corpus). ✓
- §4 architecture (multi-zone, no copy) → Tasks 2, 4, 5. ✓
- §5 data flow + open item (regen command) → Global Constraints + Task 4 Step 6. ✓ (open item resolved: `make_merged_universe.py`)
- §6 staging order (isolated deploy → single rewrite → nav flip → gated cleanup) → Tasks 4→5→6→7, each with parallel-old-surface preserved until confirmed. ✓
- §7 risks: basePath asset paths → Task 1; preserve shared theme/BrandBar/Footer/layout → Task 7 keeps them; three.js dep proof-before-removal → Task 7 Step 1. ✓
- §8 acceptance criteria → covered by Task 2 (build under basePath), Task 4 (isolated real-corpus render), Task 5 (prod /claims + rollback rehearsal), Task 6 (nav), Task 4.6 (regen documented). ✓

**Placeholder scan:** No TBD/TODO; every code step shows the code; every verify step shows the command + expected output. One deliberate verify-and-nudge (Task 3 Step 3, pixel position) is a genuine visual check, not a placeholder.

**Type consistency:** `assetUrl(path: string): string` defined in Task 1, consumed identically in `timeline.ts`/`topology.ts`. `NEXT_PUBLIC_BASE_PATH` used consistently in Task 1 (asset.ts), Task 2 (next.config), Task 4 (Vercel env). `NEXT_PUBLIC_CLAIMS_ZONE` defined and consumed in Task 5 only. `$ZONE_PROD` produced in Task 4 Step 5, consumed in Task 5 Step 2. Consistent.
