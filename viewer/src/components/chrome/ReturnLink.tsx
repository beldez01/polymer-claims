'use client';

import { COLOR, FONT_FAMILY_MONO, LAYOUT } from '@/config/theme';

// Slim persistent return into the company site.
//
// LegendRail (always-visible) occupies x:[0, LAYOUT.sidebarWidth], y:[headerHeight, vh] —
// so `left: 12` used to sit inside it. This element is offset past the sidebar's
// right edge (left: sidebarWidth + 16) to clear that column, and lifted to
// `bottom: 72` so it also sits above TransportBar's band (bottom:18, ~42px tall,
// i.e. y:[vh-60, vh-18]) when the transport bar is visible. See ReturnLink
// geometry note in the task-3 review report for the full rectangle math.
export default function ReturnLink() {
  return (
    <a
      href="https://polymerbio.org"
      style={{
        position: 'fixed',
        bottom: 72,
        left: LAYOUT.sidebarWidth + 16,
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
