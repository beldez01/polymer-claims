'use client';

import { useMemo } from 'react';
import { Billboard, Line, Html } from '@react-three/drei';
import { Color } from 'three';
import { ThreeEvent } from '@react-three/fiber';
import { COLOR, STATUS_COLOR, FONT_FAMILY_MONO } from '@/config/theme';
import { useViewer } from '@/store';
import { useInterpolatedFrame } from '@/lib/useInterpolatedFrame';
import type { InterpNode } from '@/lib/interpolate';
import type { StrengthVector, Vec3 } from '@/lib/topology';

const BASE_RADIUS = 0.28;
const RING_SEGMENTS = 48;

function statusColor(status: string): string {
  return STATUS_COLOR[status] ?? COLOR.text.muted;
}

/**
 * Crossfade between two status colors at fraction t (0 = from, 1 = to). Used to
 * render the "licensing moment" — a node sliding pending-amber → licensed-blue.
 */
function crossfadeColor(from: string, to: string, t: number): string {
  if (from === to || t >= 1) return statusColor(to);
  const c = new Color(statusColor(from)).lerp(new Color(statusColor(to)), t);
  return `#${c.getHexString()}`;
}

// strength axis 2 = evidence_against_null — drives a subtle radius scale.
function nodeRadius(strength: StrengthVector | null): number {
  const ean = strength ? strength[2] : 0.5;
  return BASE_RADIUS * (0.8 + 0.5 * ean);
}

function ringPoints(radius: number): [number, number, number][] {
  const pts: [number, number, number][] = [];
  for (let i = 0; i <= RING_SEGMENTS; i++) {
    const a = (i / RING_SEGMENTS) * Math.PI * 2;
    pts.push([Math.cos(a) * radius, Math.sin(a) * radius, 0]);
  }
  return pts;
}

function NodeMesh({ node }: { node: InterpNode }) {
  const hoveredId = useViewer((s) => s.hoveredId);
  const selectedId = useViewer((s) => s.selectedId);
  const setHovered = useViewer((s) => s.setHovered);
  const setSelected = useViewer((s) => s.setSelected);

  const color = crossfadeColor(node.prevStatus, node.status, node.statusT);
  const r = nodeRadius(node.strength);
  const isHovered = hoveredId === node.id;
  const isSelected = selectedId === node.id;
  const ringR = r * 1.7;
  const ring = useMemo(() => ringPoints(ringR), [ringR]);
  const ledgerRingR = r * 2.25;
  const ledgerRing = useMemo(() => ringPoints(ledgerRingR), [ledgerRingR]);
  const ledgerColor = node.fdr_retracted
    ? COLOR.accent.rose
    : node.fdr_discovery
      ? COLOR.accent.teal
      : COLOR.border.strong;
  const ledgerOpacity = node.fdr_retracted ? 0.9 : node.fdr_discovery ? 0.85 : 0.55;

  // enter/exit: scale the whole group toward 0 and fade the material.
  const scale = Math.max(node.scale, 0.0001);
  const transparent = node.opacity < 0.999;

  const onOver = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    setHovered(node.id);
    document.body.style.cursor = 'pointer';
  };
  const onOut = () => {
    setHovered(null);
    document.body.style.cursor = 'default';
  };
  const onClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    setSelected(node.id);
  };

  return (
    <group position={node.position} scale={scale}>
      <mesh onPointerOver={onOver} onPointerOut={onOut} onClick={onClick}>
        {node.is_representation_revision ? (
          <octahedronGeometry args={[r * 1.25, 0]} />
        ) : (
          <sphereGeometry args={[r, 24, 24]} />
        )}
        {/* matte — metalness 0, roughness 0.9, NO emissive */}
        <meshStandardMaterial
          color={color}
          metalness={0}
          roughness={0.9}
          transparent={transparent}
          opacity={node.opacity}
        />
      </mesh>

      {/* hover / selection — thin electric-blue hairline ring, billboarded */}
      {(isHovered || isSelected) && (
        <Billboard>
          <Line
            points={ring}
            color={COLOR.primary.base}
            lineWidth={1}
            transparent
            opacity={isSelected ? 1 : 0.85}
          />
        </Billboard>
      )}

      {/* FDR ledger overlay: node body is graph status; this ring is ledger state. */}
      {node.fdr_tested && (
        <Billboard>
          <Line
            points={ledgerRing}
            color={ledgerColor}
            lineWidth={1}
            transparent
            opacity={ledgerOpacity * node.opacity}
            dashed={node.fdr_retracted}
            dashSize={0.08}
            gapSize={0.06}
          />
        </Billboard>
      )}

      {/* hover label — mono, no scale-bloom */}
      {isHovered && (
        <Html position={[0, ringR + 0.06, 0]} center distanceFactor={10}>
          <div
            style={{
              fontFamily: FONT_FAMILY_MONO,
              fontSize: 10,
              lineHeight: 1.3,
              whiteSpace: 'nowrap',
              padding: '2px 6px',
              backgroundColor: 'rgba(244,244,245,0.9)',
              border: `1px solid ${color}`,
              borderRadius: 2,
              color: COLOR.text.primary,
              userSelect: 'none',
              pointerEvents: 'none',
              fontVariantNumeric: 'tabular-nums',
            }}
            className="mono tabular"
          >
            {node.id} · {node.status}
            {node.fdr_tested
              ? ` · FDR ${node.fdr_discovery ? 'discovery' : 'tested'}${
                  node.fdr_retracted ? ' retracted' : ''
                }`
              : ''}
          </div>
        </Html>
      )}
    </group>
  );
}

/** Adapt a static export node into the InterpNode shape (no animation). */
function staticNode(n: {
  id: string;
  status: string;
  pattern_id: string;
  subject_kind: string | null;
  strength: StrengthVector | null;
  is_representation_revision: boolean;
  fdr_tested?: boolean;
  fdr_discovery?: boolean;
  fdr_retracted?: boolean;
  fdr_index?: number | null;
  fdr_e_value?: number | null;
  fdr_alpha_allocated?: number | null;
  independence_tier?: string | null;
  severity_provenance?: string | null;
  position: Vec3;
}): InterpNode {
  return {
    id: n.id,
    status: n.status,
    prevStatus: n.status,
    statusT: 1,
    pattern_id: n.pattern_id,
    subject_kind: n.subject_kind,
    strength: n.strength,
    is_representation_revision: n.is_representation_revision,
    fdr_tested: n.fdr_tested ?? false,
    fdr_discovery: n.fdr_discovery ?? false,
    fdr_retracted: n.fdr_retracted ?? false,
    fdr_index: n.fdr_index ?? null,
    fdr_e_value: n.fdr_e_value ?? null,
    fdr_alpha_allocated: n.fdr_alpha_allocated ?? null,
    independence_tier: n.independence_tier ?? null,
    severity_provenance: n.severity_provenance ?? null,
    position: n.position,
    scale: 1,
    opacity: 1,
  };
}

export default function Nodes() {
  const data = useViewer((s) => s.data);
  const timeline = useViewer((s) => s.timeline);
  const frame = useViewer((s) => s.frame);
  const filters = useViewer((s) => s.filters);

  const interp = useInterpolatedFrame(timeline, frame);

  // Timeline drives the scene when loaded; else fall back to the static export.
  const nodes: InterpNode[] = useMemo(() => {
    if (interp) return interp.nodes;
    if (data) return data.nodes.map(staticNode);
    return [];
  }, [interp, data]);

  if (nodes.length === 0) return null;

  return (
    <group>
      {nodes
        .filter((n) => filters.statuses.has(n.status))
        .map((n) => (
          <NodeMesh key={n.id} node={n} />
        ))}
    </group>
  );
}
