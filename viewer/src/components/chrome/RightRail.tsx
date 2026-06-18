'use client';

import {
  COLOR,
  FONT_FAMILY_MONO,
  FONT_FAMILY_SANS,
  LAYOUT,
  STATUS_COLOR,
  STATUS_ORDER,
  STRENGTH_AXES,
} from '@/config/theme';
import { useEffect, useMemo, useState } from 'react';
import { useViewer, computeCounts, findNode, type Counts } from '@/store';
import { useInterpolatedFrame } from '@/lib/useInterpolatedFrame';
import { fetchClaimDetail, type ClaimDetail } from '@/lib/live';
import type { FrameStats } from '@/lib/timeline';

// ── shared D2 field bits (lifted from the old InspectorPanel) ───────────────

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

const sectionMarker: React.CSSProperties = {
  fontFamily: FONT_FAMILY_MONO,
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: COLOR.text.tertiary,
};

/** status pill — same markup as the old InspectorPanel. */
function StatusPill({ status }: { status: string }) {
  const color = STATUS_COLOR[status] ?? COLOR.text.muted;
  return (
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
      {status}
    </span>
  );
}

function TierPill({ tier }: { tier: string | null | undefined }) {
  if (!tier) return <span style={{ ...value, color: COLOR.text.faint }}>—</span>;
  const isReplicated = tier === 'replicated';
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        fontFamily: FONT_FAMILY_MONO,
        fontSize: 11,
        color: isReplicated ? COLOR.accent.teal : COLOR.text.secondary,
        border: `1px solid ${isReplicated ? COLOR.accent.teal : COLOR.border.default}`,
        borderRadius: 2,
        padding: '2px 7px',
        marginTop: 2,
        textTransform: 'uppercase',
      }}
    >
      {tier}
    </span>
  );
}

/** strength 6-vector table — driven by a `number[] | null` strength vector. */
function StrengthTable({ strength }: { strength: number[] | null }) {
  return (
    <>
      <div className="section-marker" style={{ ...sectionMarker, margin: '8px 0 6px' }}>
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
            const v = strength ? strength[i] : null;
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
    </>
  );
}

// ── §01 overview (lifted from the old ReadoutOverlay) ───────────────────────

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

/** Map a FrameStats into the per-status count shape the overview renders. */
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
    fdrTested: 0,
    fdrDiscoveries: 0,
    fdrRetracted: 0,
  };
}

function UniverseOverview() {
  const data = useViewer((s) => s.data);
  const timeline = useViewer((s) => s.timeline);
  const frame = useViewer((s) => s.frame);
  const camera = useViewer((s) => s.camera);

  const interp = useInterpolatedFrame(timeline, frame);

  // Timeline drives the readout when loaded; else the static export counts.
  const counts = useMemo(
    () => {
      const base = interp ? statsCounts(interp.stats) : computeCounts(data);
      if (!interp) return base;
      return {
        ...base,
        fdrTested: interp.nodes.filter((n) => n.fdr_tested).length,
        fdrDiscoveries: interp.nodes.filter((n) => n.fdr_discovery).length,
        fdrRetracted: interp.nodes.filter((n) => n.fdr_retracted).length,
      };
    },
    [interp, data],
  );

  const stats = interp?.stats ?? null;
  const layoutId = interp?.layoutId ?? data?.layout_id ?? '';

  const f = (n: number) => (n >= 0 ? ` ${n.toFixed(2)}` : n.toFixed(2));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <div className="section-marker" style={{ ...sectionMarker, marginBottom: 3 }}>
        §01 — CLAIMS UNIVERSE
      </div>

      {!interp && !data ? (
        <span style={{ ...cell, color: COLOR.text.faint }}>no topology loaded</span>
      ) : (
        <>
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
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
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
            <span style={{ ...cell, color: COLOR.text.faint }}>fdr ledger</span>
            <span style={{ ...cell, color: COLOR.text.primary }}>{counts.fdrTested}</span>
            <span style={{ ...cell, color: COLOR.text.faint }}>·</span>
            <span style={cell}>disc {counts.fdrDiscoveries}</span>
            <span style={{ ...cell, color: COLOR.text.faint }}>·</span>
            <span style={cell}>retr {counts.fdrRetracted}</span>
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
        </>
      )}
    </div>
  );
}

// ── §02 node — claim-detail card (live) with thin-field fallback ────────────

/** format the plan slot per the spec: const({value}) | impl | —. */
function planText(plan: ClaimDetail['plan']): string {
  if (!plan) return '—';
  if (plan.impl === 'builtin::const' && plan.value !== undefined) {
    return `const(${plan.value})`;
  }
  return plan.impl;
}

function ClaimDetailCard({ detail }: { detail: ClaimDetail }) {
  return (
    <>
      <Field name="id">{detail.id}</Field>
      {detail.title && <Field name="claim">{detail.title}</Field>}
      {detail.rationale && <Field name="rationale">{detail.rationale}</Field>}

      <div style={{ marginBottom: 12 }}>
        <div style={label}>status</div>
        <StatusPill status={detail.status} />
      </div>

      <Field name="pattern_id">{detail.pattern_id}</Field>
      <Field name="subject_term">{detail.subject_term ?? '—'}</Field>
      <Field name="plan">{planText(detail.plan)}</Field>

      {detail.criterion && (
        <div style={{ marginBottom: 12 }}>
          <div style={label}>criterion</div>
          <div style={{ ...value, display: 'flex', alignItems: 'baseline', gap: 6 }}>
            <span>
              {detail.criterion.comparator}{' '}
              {detail.criterion.threshold === null ? '—' : detail.criterion.threshold}
            </span>
            {detail.criterion_satisfied !== null && (
              <span
                style={{
                  color: detail.criterion_satisfied
                    ? STATUS_COLOR.licensed
                    : STATUS_COLOR.rejected,
                }}
              >
                {detail.criterion_satisfied ? '✓' : '✗'}
              </span>
            )}
          </div>
        </div>
      )}

      {detail.rejection_reason !== null && (
        <div style={{ marginBottom: 12 }}>
          <div style={label}>rejection_reason</div>
          <div style={{ ...value, color: STATUS_COLOR.rejected }}>
            {detail.rejection_reason}
          </div>
        </div>
      )}

      <StrengthTable strength={detail.strength} />

      {detail.provenance && (
        <>
          <div className="section-marker" style={{ ...sectionMarker, margin: '12px 0 6px' }}>
            § Provenance
          </div>
          <Field name="generated_by">{detail.provenance.generated_by}</Field>
          <Field name="agent_id">{detail.provenance.agent_id ?? '—'}</Field>
          <Field name="method">{detail.provenance.method ?? '—'}</Field>
        </>
      )}
    </>
  );
}

function NodePanel({ selectedId }: { selectedId: string }) {
  const data = useViewer((s) => s.data);
  const timeline = useViewer((s) => s.timeline);
  const frame = useViewer((s) => s.frame);
  const connected = useViewer((s) => s.connected);
  const liveUrl = useViewer((s) => s.liveUrl);

  const interp = useInterpolatedFrame(timeline, frame);

  const [detail, setDetail] = useState<ClaimDetail | null>(null);

  // Fetch the full claim detail when connected. Race-guarded: a stale response
  // for a previous selection (or after disconnect) is dropped.
  useEffect(() => {
    setDetail(null);
    if (!connected || !liveUrl || !selectedId) return;
    let ignore = false;
    fetchClaimDetail(liveUrl, selectedId).then((d) => {
      if (!ignore) setDetail(d);
    });
    return () => {
      ignore = true;
    };
  }, [connected, liveUrl, selectedId]);

  // Thin static node for the fallback view.
  const node = useMemo(() => {
    if (interp) return interp.nodes.find((n) => n.id === selectedId) ?? null;
    return findNode(data, selectedId);
  }, [interp, data, selectedId]);

  if (detail) return <ClaimDetailCard detail={detail} />;

  // Fallback: not connected / fetch failed / static mode — thin fields.
  if (!node) {
    return <span style={{ ...cell, color: COLOR.text.faint }}>node not found</span>;
  }

  return (
    <>
      <Field name="id">{node.id}</Field>

      <div style={{ marginBottom: 12 }}>
        <div style={label}>status</div>
        <StatusPill status={node.status} />
      </div>

      <Field name="pattern_id">{node.pattern_id}</Field>
      <Field name="subject_kind">{node.subject_kind ?? '—'}</Field>
      <Field name="is_representation_revision">
        {node.is_representation_revision ? 'true · octahedron' : 'false'}
      </Field>
      <Field name="fdr_ledger">
        {node.fdr_tested
          ? `#${node.fdr_index ?? '—'} · ${
              node.fdr_discovery ? 'discovery' : 'tested'
            }${node.fdr_retracted ? ' · retracted' : ''}`
          : '—'}
      </Field>
      <div style={{ marginBottom: 12 }}>
        <div style={label}>independence_tier</div>
        <TierPill tier={node.independence_tier ?? null} />
      </div>
      {node.fdr_tested && (
        <>
          <Field name="e_value">{node.fdr_e_value ?? '—'}</Field>
          <Field name="alpha_allocated">{node.fdr_alpha_allocated ?? '—'}</Field>
        </>
      )}

      <StrengthTable strength={node.strength ?? null} />
    </>
  );
}

/**
 * Unified right rail — always docked. Shows the §01 Claims-Universe overview by
 * default; when a node is selected, swaps to the §02 claim-detail card (live
 * fetch with a thin static fallback) and a ✕ that clears the selection.
 */
export default function RightRail() {
  const selectedId = useViewer((s) => s.selectedId);
  const setSelected = useViewer((s) => s.setSelected);

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
      {selectedId === null ? (
        <UniverseOverview />
      ) : (
        <>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 16,
            }}
          >
            <span className="section-marker" style={sectionMarker}>
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

          <NodePanel selectedId={selectedId} />
        </>
      )}
    </aside>
  );
}
