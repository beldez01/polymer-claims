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
