# Claims Universe → polymerbio.org graft (V1) — design

**Date:** 2026-07-20
**Status:** DESIGN — approved through brainstorming; awaiting spec review before writing-plans
**Scope:** Replace the obsolete claims viewer on polymerbio.org with the current
`polymer-claims` Claims Universe viewer, single-source, static real corpus, without
breaking the live site.

---

## 1. Context

`polymerbio.org` is the umbrella company surface for the Polymer ecosystem and the
credibility surface for the Polymer Biologics pitch. Its current claims page is an
**obsolete fork**: `PolymerGenomicsAPI/viewer/src/components/FormalClaimUniverse` carries a
source comment *"Forked from viewer/src/components/claims/ClaimUniverse.tsx"* — i.e. it was
copied from an early ancestor of the viewer that has since been fully rebuilt in this
(`polymer-claims`) repo. Copying source between repos is what produced the rot; this design
does not do it again.

**Ecosystem (separate repos, unified workspace at `~/Desktop/PolymerBio/` via symlinks):**
- `PolymerGenomicsAPI` — FastAPI API + the `viewer/` deployed to Vercel as polymerbio.org.
- `polymer-claims` (this repo) — grammar/protocol/node + the current Claims Universe viewer.
- `SensorKit` — the locked ADAR-sensor scorer (pip pkg `sensorkit`).
- `Polymer Biologics` — docs-only: the cross-class sensor screen, the deck, bridge specs.

**The spine this serves:** SensorKit → cross-class screen (RUN → EBV/PTLD + AML lead) →
[PLANNED bridge `sensor::senseability@v1`] licenses screen results as claims → Claims
Universe renders them → baked onto polymerbio.org → cited in the deck.

## 2. Goal / Non-goals

**Goal (V1):** A visitor to `polymerbio.org/claims` sees the current 3D Claims Universe,
rendering the **real warranted corpus** (`merged-universe.json`), as an immersive standalone
instrument — served single-source from this repo, deployable and revertible without risk to
the rest of the live site.

**Non-goals (explicitly deferred):**
- The `sensor::senseability@v1` bridge (the sensor claims join the *same* universe later, no
  viewer rework). Separate workstream.
- Live-node streaming (`polymer-claims serve` over the public internet) — the node is
  loopback-only with unauthenticated mutating routes by design; exposing it is a separate,
  security-sensitive effort. V1 is static-only.
- Physical repo consolidation (moving repos under one parent) — requires fixing absolute
  paths first (SensorKit editable path in the API `pyproject.toml`, `.env`, `.vercel`,
  `.mcp.json`). The symlink umbrella already gives us a unified workspace.

## 3. Decisions (locked in brainstorming)

| Decision | Choice |
|---|---|
| Backend posture | **Static baked real corpus** (no public node) |
| Starting workstream | **Viewer graft first** (sensor bridge later) |
| Integration mechanism | **B — single-source, Next.js multi-zone** (viewer owned by polymer-claims; polymerbio.org rewrites `/claims` to it) |
| Chrome | **Immersive takeover** — viewer's own chrome + a slim persistent "PolymerBio" return link into the company site |
| Old surfaces | Retire `/portal/latent3d` + `/portal/graph`; delete already-dead `components/claims/*` + `config/claims.ts`; `/claims` becomes the real page |

## 4. Architecture (multi-zone)

```
                         polymerbio.org  (PolymerGenomicsAPI/viewer — Vercel project A)
                          │  next.config.ts rewrites():
                          │    /claims        → <claims-viewer deployment>/claims
                          │    /claims/:path* → <claims-viewer deployment>/claims/:path*
                          ▼
   polymer-claims/viewer  (Vercel project B — NEW, owned by this repo)
     basePath: '/claims', assetPrefix matching
     public/merged-universe.json  ← the real corpus, shipped in the build
     boots into static "sample/corpus" mode — NO backend
```

- **No source copied.** The viewer stays 100% in `polymer-claims/viewer`. The API repo's only
  change is the rewrite config + nav repoint + deletion of dead code.
- **Independent deploys.** Rebuild polymer-claims → project B redeploys → `/claims` updates.
  The API repo never changes again for viewer work.
- **`basePath: '/claims'`** so the viewer's internal links/assets resolve under the subpath.
  (Today `next.config.ts` sets only `turbopack.root`; add `basePath` + `assetPrefix`.)

## 5. Data flow — real corpus, baked static

- The viewer already `fetch()`es `/merged-universe.json` from its own `public/` on mount
  (fallback chain → `pharmaco-universe.json` → `sample-timeline.json`). No API call, no node.
- `merged-universe.json` (1.2 MB) is the **real warranted corpus** — built from real data
  dirs in this repo (`data/tcga_laml`, `data/target_aml_fusion_expr` [real TARGET-AML STAR
  TPM], `data/tcga_laml_cbf_fusion_expr` [CBF fusions RUNX1-RUNX1T1 / CBFB-MYH11], `data/gtex`,
  `data/pharmaco`, TE campaigns), each with `SOURCE.txt` + `license_spine.py`.
- **OPEN ITEM (confirm in planning, do not assume):** identify the exact command/script that
  regenerates `merged-universe.json`, so the corpus is a *refreshable build step* rather than a
  mystery artifact. V1 ships the existing real corpus; the refresh path must be documented.

## 6. Staging & rollback (the "don't break anything" core)

Ordered, each step reversible; the live site is untouched until the single flip in step 3.

1. **Config the viewer** for subpath: `basePath: '/claims'` + `assetPrefix`; add the slim
   "PolymerBio" return link to the viewer chrome. Verify `next build` is green locally.
2. **Deploy claims viewer as a separate Vercel project (B)** → verify on its own preview URL.
   **Touches nothing live.** Confirm: universe renders, per-node inspector works, corpus is the
   real one, assets load under `/claims`.
3. **Add the `/claims` rewrite** to polymerbio.org (project A) → the *only* change to the live
   site. Atomic + instant Vercel rollback if wrong. Old `/portal/latent3d` stays live in parallel.
4. **Verify** `polymerbio.org/claims` end-to-end in production.
5. **Flip nav** (BrandBar, Footer, home) from `/portal/latent3d` → `/claims`; remove the old
   `/claims`→`/portal/latent3d` 308 redirect.
6. **Cleanup follow-up commit** (only after 4–5 confirmed): delete `app/portal/latent3d`,
   `app/portal/graph`, `components/FormalClaim*`, `components/claims/*`, `config/claims.ts`,
   `config/formal_claims.ts`, `config/formal_projection.ts`, `data/formal_claim_projection_v1.json`,
   and their claims-only deps (`@xyflow/react`, `dagre`, three/@react-three — *verify no other
   route consumes three.js first*). Preserve shared `config/theme`, `BrandBar`, `Footer`,
   `useBreakpoint`, and `app/portal/layout.tsx` (still wraps non-claims portal routes).

## 7. Risks / landmines

- **Preserve shared, non-claims code** (blast-radius map): `config/theme` (imported by ~142
  files), `BrandBar`, `Footer`, `useBreakpoint`, `app/portal/layout.tsx`. Do not remove with
  the claims deletion.
- **three.js dep removal** — confirmed claims-only in `src/` but not exhaustively proven; verify
  before dropping the dependency.
- **basePath asset paths** — the most likely source of a broken deploy; step 2's isolated
  preview exists precisely to catch it before touching the live site.
- **Corpus provenance** — do not ship a corpus we can't regenerate (§5 open item).
- **Unrelated to V1 but latent:** the API's SensorKit editable-path dependency will break
  `fly deploy` of the *API*. Out of scope here (the viewer is Vercel-static and does not touch
  it), but flagged so it isn't tripped over.

## 8. Acceptance criteria (verification boundaries)

- [ ] `polymer-claims/viewer` builds green with `basePath: '/claims'`; assets resolve under `/claims`.
- [ ] Separate Vercel deployment of the viewer renders the **real** `merged-universe.json`
      universe + working per-node inspector on its own preview URL (live site untouched).
- [ ] `polymerbio.org/claims` serves the new viewer in production via the rewrite.
- [ ] Nav (BrandBar/Footer/home) points at `/claims`; old redirect removed; `/portal/*`
      non-claims routes still work.
- [ ] The regeneration command for `merged-universe.json` is identified and documented.
- [ ] Rollback rehearsed: reverting the rewrite restores the prior live state instantly.

## 9. Future (out of V1, tracked)

- **Workstream B — `sensor::senseability@v1` bridge:** two-adapter capability (Leg A =
  SensorKit tier via `classify_variant`; Leg B = independent geometry/register/CCA reimpl),
  mint `LICENSED` claims at `IndependenceTier.REPRODUCED`, ingest the cross-class screen →
  the sensor claims appear in the same universe on the next static rebuild. Spec:
  `Polymer Biologics/claims-warrant/BRIDGE-SENSORKIT-CLAIMS-SPEC.md`.
- Live-node streaming; physical repo consolidation.
