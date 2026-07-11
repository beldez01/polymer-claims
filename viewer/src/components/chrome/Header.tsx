'use client';

import { COLOR, FONT_FAMILY_SANS, FONT_FAMILY_MONO, LAYOUT, WEIGHT } from '@/config/theme';
import LiveControl from '@/components/chrome/LiveControl';

export default function Header() {
  return (
    <header
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: LAYOUT.headerHeight,
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '0 20px',
        backgroundColor: COLOR.bg.elevated,
        borderBottom: `1px solid ${COLOR.border.subtle}`,
        zIndex: 20,
        pointerEvents: 'auto',
      }}
    >
      <span
        style={{
          fontFamily: FONT_FAMILY_SANS,
          fontSize: 15,
          fontWeight: WEIGHT.semibold,
          letterSpacing: '-0.01em',
          color: COLOR.text.primary,
        }}
      >
        Polymer Claims
      </span>
      <span
        className="mono"
        style={{
          fontFamily: FONT_FAMILY_MONO,
          fontSize: 11,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: COLOR.text.tertiary,
        }}
      >
        § Polymer Claims — Unified Universe
      </span>
      <span style={{ flex: 1 }} />
      <span
        className="mono"
        style={{
          fontFamily: FONT_FAMILY_MONO,
          fontSize: 11,
          color: COLOR.text.faint,
          letterSpacing: '0.04em',
        }}
      >
        pharmaco · synbio · immuno · polymergenomics · fruchterman-reingold
      </span>
      <LiveControl />
    </header>
  );
}
