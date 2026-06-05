'use client';

import {
  COLOR,
  FONT_FAMILY_MONO,
  LAYOUT,
  STATUS_COLOR,
  STATUS_ORDER,
} from '@/config/theme';
import { useMemo } from 'react';
import { useViewer, computeCounts } from '@/store';

const cell: React.CSSProperties = {
  fontFamily: FONT_FAMILY_MONO,
  fontSize: 11,
  color: COLOR.text.secondary,
  fontVariantNumeric: 'tabular-nums',
  whiteSpace: 'nowrap',
};

function Row({ children }: { children: React.ReactNode }) {
  return <div style={{ display: 'flex', gap: 6, alignItems: 'baseline' }}>{children}</div>;
}

export default function ReadoutOverlay() {
  const data = useViewer((s) => s.data);
  const counts = useMemo(() => computeCounts(data), [data]);
  const camera = useViewer((s) => s.camera);

  if (!data) return null;

  const f = (n: number) => (n >= 0 ? ` ${n.toFixed(2)}` : n.toFixed(2));

  return (
    <div
      style={{
        position: 'absolute',
        left: LAYOUT.sidebarWidth + 16,
        bottom: 16,
        backgroundColor: 'rgba(250,250,250,0.92)',
        border: `1px solid ${COLOR.border.default}`,
        borderRadius: 2,
        padding: '10px 12px',
        zIndex: 14,
        pointerEvents: 'none',
        display: 'flex',
        flexDirection: 'column',
        gap: 3,
      }}
    >
      <div
        className="section-marker"
        style={{
          fontFamily: FONT_FAMILY_MONO,
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: COLOR.text.tertiary,
          marginBottom: 3,
        }}
      >
        §01 — CLAIM UNIVERSE
      </div>

      <Row>
        <span style={{ ...cell, color: COLOR.text.faint }}>nodes</span>
        <span style={{ ...cell, color: COLOR.text.primary }}>{counts.total}</span>
      </Row>

      {/* per-status counts */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', maxWidth: 320 }}>
        {STATUS_ORDER.map((st) => (
          <span key={st} style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                backgroundColor: STATUS_COLOR[st],
                display: 'inline-block',
              }}
            />
            <span style={{ ...cell, color: COLOR.text.faint, fontSize: 10 }}>{st}</span>
            <span style={{ ...cell, fontSize: 10 }}>{counts.byStatus[st] ?? 0}</span>
          </span>
        ))}
      </div>

      <Row>
        <span style={{ ...cell, color: COLOR.text.faint }}>edges</span>
        <span style={{ ...cell, color: COLOR.text.primary }}>{counts.edgeTotal}</span>
        <span style={{ ...cell, color: COLOR.text.faint }}>·</span>
        <span style={cell}>eff {counts.edgeEffective}</span>
        <span style={{ ...cell, color: COLOR.text.faint }}>·</span>
        <span style={cell}>prov {counts.edgeProvisional}</span>
      </Row>

      <Row>
        <span style={{ ...cell, color: COLOR.text.faint }}>layout</span>
        <span style={cell}>{data.layout_id}</span>
      </Row>

      <Row>
        <span style={{ ...cell, color: COLOR.text.faint }}>cam</span>
        <span style={cell}>
          ({f(camera.x)},{f(camera.y)},{f(camera.z)})
        </span>
      </Row>
    </div>
  );
}
