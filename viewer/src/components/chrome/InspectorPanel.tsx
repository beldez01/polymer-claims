'use client';

import {
  COLOR,
  FONT_FAMILY_MONO,
  FONT_FAMILY_SANS,
  LAYOUT,
  STATUS_COLOR,
  STRENGTH_AXES,
} from '@/config/theme';
import { useMemo } from 'react';
import { useViewer, findNode } from '@/store';

const label: React.CSSProperties = {
  fontFamily: FONT_FAMILY_MONO,
  fontSize: 10,
  letterSpacing: '0.04em',
  color: COLOR.text.faint,
  textTransform: 'uppercase',
};

const value: React.CSSProperties = {
  fontFamily: FONT_FAMILY_MONO,
  fontSize: 12,
  color: COLOR.text.primary,
  fontVariantNumeric: 'tabular-nums',
  wordBreak: 'break-all',
};

function Field({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={label}>{name}</div>
      <div style={value}>{children}</div>
    </div>
  );
}

export default function InspectorPanel() {
  const data = useViewer((s) => s.data);
  const selectedId = useViewer((s) => s.selectedId);
  const setSelected = useViewer((s) => s.setSelected);
  const node = useMemo(() => findNode(data, selectedId), [data, selectedId]);

  if (!node) return null;

  const color = STATUS_COLOR[node.status] ?? COLOR.text.muted;

  return (
    <aside
      style={{
        position: 'absolute',
        top: LAYOUT.headerHeight,
        right: 0,
        bottom: 0,
        width: LAYOUT.inspectorWidth,
        backgroundColor: COLOR.bg.elevated,
        borderLeft: `1px solid ${COLOR.border.subtle}`,
        padding: '16px 16px',
        overflowY: 'auto',
        zIndex: 15,
        pointerEvents: 'auto',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
        }}
      >
        <span
          className="section-marker"
          style={{
            fontFamily: FONT_FAMILY_MONO,
            fontSize: 10,
            fontWeight: 500,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: COLOR.text.tertiary,
          }}
        >
          §02 — NODE
        </span>
        <button
          onClick={() => setSelected(null)}
          style={{
            fontFamily: FONT_FAMILY_MONO,
            fontSize: 11,
            color: COLOR.text.muted,
            background: 'transparent',
            border: `1px solid ${COLOR.border.strong}`,
            borderRadius: 2,
            padding: '1px 7px',
            cursor: 'pointer',
          }}
        >
          ✕
        </button>
      </div>

      <Field name="id">{node.id}</Field>

      <div style={{ marginBottom: 12 }}>
        <div style={label}>status</div>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontFamily: FONT_FAMILY_MONO,
            fontSize: 12,
            color: COLOR.text.primary,
            border: `1px solid ${COLOR.border.default}`,
            borderRadius: 2,
            padding: '2px 8px',
            marginTop: 2,
          }}
        >
          <span
            style={{
              width: 9,
              height: 9,
              borderRadius: '50%',
              backgroundColor: color,
              display: 'inline-block',
            }}
          />
          {node.status}
        </span>
      </div>

      <Field name="pattern_id">{node.pattern_id}</Field>
      <Field name="subject_kind">{node.subject_kind ?? '—'}</Field>
      <Field name="is_representation_revision">
        {node.is_representation_revision ? 'true · octahedron' : 'false'}
      </Field>

      {/* strength 6-vector */}
      <div
        className="section-marker"
        style={{
          fontFamily: FONT_FAMILY_MONO,
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: COLOR.text.tertiary,
          margin: '8px 0 6px',
        }}
      >
        § Strength — 6-vector
      </div>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontFamily: FONT_FAMILY_MONO,
          fontSize: 11,
        }}
      >
        <tbody>
          {STRENGTH_AXES.map((axis, i) => {
            const v = node.strength ? node.strength[i] : null;
            return (
              <tr key={axis} style={{ borderTop: `1px solid ${COLOR.border.default}` }}>
                <td
                  style={{
                    padding: '4px 0',
                    color: COLOR.text.secondary,
                    fontFamily: FONT_FAMILY_SANS,
                    fontSize: 11,
                  }}
                >
                  {axis}
                </td>
                <td
                  style={{
                    padding: '4px 0',
                    textAlign: 'right',
                    color: v === null ? COLOR.text.faint : COLOR.text.primary,
                    fontVariantNumeric: 'tabular-nums',
                  }}
                  className="tabular"
                >
                  {v === null ? '—' : v.toFixed(3)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </aside>
  );
}
