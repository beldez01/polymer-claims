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
