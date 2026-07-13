/**
 * Claims Universe Viewer — D2 design tokens.
 *
 * Mirrors PolymerGenomicsAPI/viewer/src/config/theme.ts (IBM Carbon ×
 * Bloomberg Reference): light-gray canvas, electric blue, hairline rules.
 * Token SHAPE (COLOR / TYPE / WEIGHT / SPACE / LAYOUT) and exact hex/scale
 * values are kept identical so the <ClaimUniverse> component lifts back into
 * the API viewer as a value match, not a rewrite.
 *
 * Plus the claims-specific STATUS_COLOR / EDGE_COLOR encoding maps (spec
 * §Encodings). NO emissive, NO glow, NO neon. Electric blue is the singular
 * structural accent; the data-identity colors encode information only.
 */

// ── Typography ─────────────────────────────────────────────────────────────
export const FONT_FAMILY_SANS =
  "var(--font-inter), -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";

export const FONT_FAMILY_MONO =
  "var(--font-jetbrains-mono), 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace";

// Modular scale anchored at 14px body, ratio ~1.25
export const TYPE = {
  xs:    { fontSize: 11, lineHeight: 1.45, letterSpacing: '0.04em' },
  sm:    { fontSize: 12, lineHeight: 1.5,  letterSpacing: '0.02em' },
  base:  { fontSize: 14, lineHeight: 1.6,  letterSpacing: '0em' },
  md:    { fontSize: 17, lineHeight: 1.5,  letterSpacing: '-0.01em' },
  lg:    { fontSize: 22, lineHeight: 1.4,  letterSpacing: '-0.02em' },
  xl:    { fontSize: 30, lineHeight: 1.25, letterSpacing: '-0.025em' },
  '2xl': { fontSize: 44, lineHeight: 1.15, letterSpacing: '-0.03em' },
  '3xl': { fontSize: 64, lineHeight: 1.05, letterSpacing: '-0.035em' },
} as const;

export const WEIGHT = {
  normal:   400,
  medium:   500,
  semibold: 600,
  bold:     700,
} as const;

// ── Spacing — 4px base ─────────────────────────────────────────────────────
const BASE = 4;
export function sp(n: number): number { return n * BASE; }

export const SPACE = {
  0:  0,
  1:  sp(1),   //  4
  2:  sp(2),   //  8
  3:  sp(3),   // 12
  4:  sp(4),   // 16
  5:  sp(5),   // 20
  6:  sp(6),   // 24
  8:  sp(8),   // 32
  10: sp(10),  // 40
  12: sp(12),  // 48
  16: sp(16),  // 64
  24: sp(24),  // 96
} as const;

// ── Color — D2 foundation ──────────────────────────────────────────────────
export const COLOR = {
  bg: {
    primary:  '#F4F4F5',   // canvas
    elevated: '#FAFAFA',   // cards, elevated panels
    surface:  '#FAFAFA',
    deep:     '#EBEBED',   // recessed sections, alt rows
    white:    '#FFFFFF',
  },

  border: {
    subtle:  '#D4D4D8',    // 1px rules — "line container work"
    default: '#E4E4E7',
    strong:  '#A1A1AA',
    input:   '#A1A1AA',
  },

  text: {
    primary:   '#18181B',
    secondary: '#3F3F46',
    tertiary:  '#52525B',
    muted:     '#71717A',
    faint:     '#A1A1AA',
  },

  // Electric blue — IBM Carbon Blue 60. The singular structural accent.
  primary: {
    base:   '#0F62FE',
    hover:  '#0043CE',
    active: '#002D9C',
  },

  // Data-identity accents — encode information only, never decoration.
  accent: {
    teal:   '#08A097',
    amber:  '#B45309',
    violet: '#7C3AED',
    rose:   '#BE123C',
    blue:   '#0F62FE',
  },
} as const;

// ── Layout ─────────────────────────────────────────────────────────────────
export const LAYOUT = {
  headerHeight:   56,
  sidebarWidth:  220,   // left legend / filter rail
  inspectorWidth: 300,  // right inspector panel
} as const;

// ── Claims encodings (spec §Encodings) ─────────────────────────────────────

// status → node color
export const STATUS_COLOR: Record<string, string> = {
  licensed:    '#4589FF',  // classic Polymer blue (Carbon Blue 50) — the licensed core
  pending:     '#B45309',  // amber
  exploratory: '#7C3AED',  // violet
  conjectured: '#71717A',  // neutral gray
  rejected:    '#FA4D56',  // bright red (Carbon Red 50) — high-visibility
};

// human-facing order for the legend colorbar
export const STATUS_ORDER = [
  'licensed',
  'pending',
  'exploratory',
  'conjectured',
  'rejected',
] as const;

// edge kind → color. The defeat family (rebut/undercut/undermine/reclassify/
// reinterpret) all map to rose; evidence_for teal; equivalence neutral gray; entails blue.
export const EDGE_COLOR: Record<string, string> = {
  // defeat family
  rebut:       '#BE123C',
  undercut:    '#BE123C',
  undermine:   '#BE123C',
  reclassify:  '#BE123C',
  reinterpret: '#BE123C',
  // support
  evidence_for: '#08A097',
  // structural
  equivalence: '#A1A1AA',
  entails:     '#0F62FE',
  // cross-arm relations (Task 6+) — coheres reads positive/green, tension reads
  // negative/red (distinct from the defeat-family rose), restriction_map reads
  // structural like entails but in a distinguishable hue (cyan vs blue).
  coheres:         '#24A148', // Carbon Green 50
  tension:         '#A2191F', // Carbon Red 60 — darker/warmer than defeat's rose
  restriction_map: '#1192E8', // Carbon Cyan 50
};

export const DEFEAT_KINDS = [
  'rebut',
  'undercut',
  'undermine',
  'reclassify',
  'reinterpret',
] as const;

// ── Consistency / Energy heat scale ───────────────────────────────────────
// 3-stop gradient: teal (low) → amber (mid) → rose (high).
// `tensionScale(t01)` accepts a value in [0, 1] and returns a hex colour.
// Stops are anchored at the D2 accent tokens; lerp is in linear RGB.

const HEAT_STOPS: [number, number, number][] = [
  // #08A097 — teal
  [0x08, 0xa0, 0x97],
  // #B45309 — amber
  [0xb4, 0x53, 0x09],
  // #BE123C — rose
  [0xbe, 0x12, 0x3c],
];

/**
 * Map a normalised energy value (0 = min tension, 1 = max tension) to a heat
 * colour: teal → amber → rose.  Values outside [0, 1] are clamped.
 */
export function tensionScale(t01: number): string {
  const clamped = Math.max(0, Math.min(1, t01));
  // segment: 0→0.5 maps to stop 0→1; 0.5→1 maps to stop 1→2
  const seg = clamped < 0.5 ? 0 : 1;
  const local = clamped < 0.5 ? clamped / 0.5 : (clamped - 0.5) / 0.5;
  const a = HEAT_STOPS[seg];
  const b = HEAT_STOPS[seg + 1];
  const r = Math.round(a[0] + (b[0] - a[0]) * local);
  const g = Math.round(a[1] + (b[1] - a[1]) * local);
  const bv = Math.round(a[2] + (b[2] - a[2]) * local);
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${bv.toString(16).padStart(2, '0')}`;
}

// the 6 strength axes, in canonical order (matches polymer_grammar.AXES)
export const STRENGTH_AXES = [
  'magnitude',
  'certainty',
  'evidence_against_null',
  'severity',
  'world_contact',
  'explanatory_virtue',
] as const;
