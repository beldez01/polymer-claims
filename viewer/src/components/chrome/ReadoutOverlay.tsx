'use client';

import {
  COLOR,
  FONT_FAMILY_MONO,
  LAYOUT,
  STATUS_COLOR,
  STATUS_ORDER,
} from '@/config/theme';
import { useMemo } from 'react';
import { useViewer, computeCounts, type Counts } from '@/store';
import { useInterpolatedFrame } from '@/lib/useInterpolatedFrame';
import type { FrameStats } from '@/lib/timeline';

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

/** Map a FrameStats into the per-status count shape the readout renders. */
function statsCounts(stats: FrameStats): Counts {
  const byStatus: Record<string, number> = {};
  for (const st of STATUS_ORDER) byStatus[st] = 0;
  byStatus.licensed = stats.n_licensed;
  byStatus.pending = stats.n_pending;
  byStatus.conjectured = stats.n_conjectured;
  byStatus.rejected = stats.n_rejected;
  return {
    total: stats.n_nodes,
    byStatus,
    edgeTotal: stats.n_edges,
    edgeEffective: stats.n_effective_edges,
    edgeProvisional: stats.n_provisional_edges,
  };
}

export default function ReadoutOverlay() {
  const data = useViewer((s) => s.data);
  const timeline = useViewer((s) => s.timeline);
  const frame = useViewer((s) => s.frame);
  const camera = useViewer((s) => s.camera);

  const interp = useInterpolatedFrame(timeline, frame);

  // Timeline drives the readout when loaded; else the static export counts.
  const counts = useMemo(
    () => (interp ? statsCounts(interp.stats) : computeCounts(data)),
    [interp, data],
  );

  if (!interp && !data) return null;

  const stats = interp?.stats ?? null;
  const layoutId = interp?.layoutId ?? data?.layout_id ?? '';

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

      {/* cycle index (timeline only) */}
      {stats && (
        <Row>
          <span style={{ ...cell, color: COLOR.text.faint }}>cycle</span>
          <span style={{ ...cell, color: COLOR.text.primary }}>{stats.cycle_index}</span>
          <span style={{ ...cell, color: COLOR.text.faint }}>·</span>
          <span style={{ ...cell, color: COLOR.text.faint }}>frontier</span>
          <span style={cell}>{stats.n_frontier}</span>
        </Row>
      )}

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

      {/* per-cycle deltas (timeline only) */}
      {stats && (
        <Row>
          <span style={{ ...cell, color: COLOR.primary.base }}>+{stats.n_added}</span>
          <span style={{ ...cell, color: COLOR.text.faint }}>added</span>
          <span style={{ ...cell, color: COLOR.text.faint }}>·</span>
          <span style={{ ...cell, color: COLOR.primary.base }}>+{stats.n_newly_licensed}</span>
          <span style={{ ...cell, color: COLOR.text.faint }}>newly licensed</span>
        </Row>
      )}

      <Row>
        <span style={{ ...cell, color: COLOR.text.faint }}>layout</span>
        <span style={cell}>{layoutId}</span>
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
