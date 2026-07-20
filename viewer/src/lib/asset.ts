// Prefix root-absolute public-asset URLs (e.g. '/merged-universe.json') with the app
// basePath, so fetches resolve when the viewer is served under a subpath (/claims) as a
// multi-zone on polymerbio.org. NEXT_PUBLIC_BASE_PATH is '' for standalone dev and
// '/claims' in the zone deploy — the SAME env next.config.ts reads for basePath, so the
// two can never disagree. NEXT_PUBLIC_* is inlined at build, so this works in the browser.
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

export function assetUrl(path: string): string {
  return `${BASE_PATH}${path}`;
}
