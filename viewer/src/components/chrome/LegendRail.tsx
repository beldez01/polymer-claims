'use client';

import {
  COLOR,
  FONT_FAMILY_MONO,
  FONT_FAMILY_SANS,
  LAYOUT,
  STATUS_COLOR,
  STATUS_ORDER,
  EDGE_COLOR,
} from '@/config/theme';
import { useMemo } from 'react';
import { useViewer, EDGE_BUCKETS, computeCounts } from '@/store';

const EDGE_BUCKET_META: Record<string, { label: string; color: string; dashed?: boolean }> = {
  defeat: { label: 'defeat', color: EDGE_COLOR.rebut },
  equivalence: { label: 'equivalence', color: EDGE_COLOR.equivalence },
  entails: { label: 'entails', color: EDGE_COLOR.entails },
};

function SectionMarker({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="section-marker"
      style={{
        fontFamily: FONT_FAMILY_MONO,
        fontSize: 10,
        fontWeight: 500,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        color: COLOR.text.tertiary,
        marginBottom: 8,
      }}
    >
      {children}
    </div>
  );
}

function Chip({ color, square, octa }: { color: string; square?: boolean; octa?: boolean }) {
  if (octa) {
    return (
      <span
        style={{
          width: 11,
          height: 11,
          backgroundColor: color,
          display: 'inline-block',
          transform: 'rotate(45deg)',
          flexShrink: 0,
        }}
      />
    );
  }
  return (
    <span
      style={{
        width: 11,
        height: 11,
        backgroundColor: color,
        borderRadius: square ? 0 : '50%',
        display: 'inline-block',
        flexShrink: 0,
      }}
    />
  );
}

function CheckRow({
  checked,
  onToggle,
  children,
}: {
  checked: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onToggle}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        width: '100%',
        padding: '3px 4px',
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        textAlign: 'left',
        opacity: checked ? 1 : 0.4,
        transition: 'opacity 0.12s',
      }}
    >
      <span
        style={{
          width: 12,
          height: 12,
          border: `1px solid ${checked ? COLOR.primary.base : COLOR.border.strong}`,
          backgroundColor: checked ? COLOR.primary.base : 'transparent',
          borderRadius: 2,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {checked && (
          <span style={{ color: COLOR.bg.white, fontSize: 9, lineHeight: 1 }}>✓</span>
        )}
      </span>
      {children}
    </button>
  );
}

const rowLabel: React.CSSProperties = {
  fontFamily: FONT_FAMILY_MONO,
  fontSize: 11,
  color: COLOR.text.secondary,
  fontVariantNumeric: 'tabular-nums',
};

export default function LegendRail() {
  const filters = useViewer((s) => s.filters);
  const toggleStatus = useViewer((s) => s.toggleStatus);
  const toggleEdgeKind = useViewer((s) => s.toggleEdgeKind);
  const setShowProvisional = useViewer((s) => s.setShowProvisional);
  const data = useViewer((s) => s.data);
  const counts = useMemo(() => computeCounts(data), [data]);

  return (
    <aside
      style={{
        position: 'absolute',
        top: LAYOUT.headerHeight,
        left: 0,
        bottom: 0,
        width: LAYOUT.sidebarWidth,
        backgroundColor: COLOR.bg.elevated,
        borderRight: `1px solid ${COLOR.border.subtle}`,
        padding: '16px 14px',
        overflowY: 'auto',
        zIndex: 15,
        pointerEvents: 'auto',
      }}
    >
      {/* STATUS */}
      <SectionMarker>§ Status — node color</SectionMarker>
      <div style={{ marginBottom: 20 }}>
        {STATUS_ORDER.map((st) => (
          <CheckRow
            key={st}
            checked={filters.statuses.has(st)}
            onToggle={() => toggleStatus(st)}
          >
            <Chip color={STATUS_COLOR[st]} />
            <span style={{ ...rowLabel, flex: 1 }}>{st}</span>
            <span style={{ ...rowLabel, color: COLOR.text.faint }}>
              {counts.byStatus[st] ?? 0}
            </span>
          </CheckRow>
        ))}
      </div>

      {/* EDGE KIND */}
      <SectionMarker>§ Edge — kind color</SectionMarker>
      <div style={{ marginBottom: 12 }}>
        {EDGE_BUCKETS.map((bucket) => {
          const meta = EDGE_BUCKET_META[bucket];
          return (
            <CheckRow
              key={bucket}
              checked={filters.edgeKinds.has(bucket)}
              onToggle={() => toggleEdgeKind(bucket)}
            >
              <Chip color={meta.color} square />
              <span style={{ ...rowLabel, flex: 1 }}>{meta.label}</span>
            </CheckRow>
          );
        })}
      </div>

      {/* PROVISIONAL TOGGLE */}
      <div style={{ marginBottom: 20 }}>
        <CheckRow
          checked={filters.showProvisional}
          onToggle={() => setShowProvisional(!filters.showProvisional)}
        >
          <span style={{ ...rowLabel, flex: 1 }}>show provisional</span>
          <span style={{ ...rowLabel, color: COLOR.text.faint }}>
            {counts.edgeProvisional}
          </span>
        </CheckRow>
        <div
          style={{
            fontFamily: FONT_FAMILY_SANS,
            fontSize: 10,
            color: COLOR.text.faint,
            paddingLeft: 24,
            lineHeight: 1.4,
          }}
        >
          dashed · inert until source licensed
        </div>
      </div>

      {/* GLYPH KEY */}
      <SectionMarker>§ Glyph</SectionMarker>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Chip color={COLOR.text.muted} />
          <span style={rowLabel}>sphere · claim</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Chip color={COLOR.primary.base} octa />
          <span style={rowLabel}>octahedron · revision</span>
        </div>
      </div>
    </aside>
  );
}
