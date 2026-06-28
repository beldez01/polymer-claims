'use client';

import { useMemo } from 'react';
import { Billboard, Line, Html } from '@react-three/drei';
import { Color } from 'three';
import { ThreeEvent } from '@react-three/fiber';
import { COLOR, STATUS_COLOR, FONT_FAMILY_MONO, tensionScale } from '@/config/theme';
import { useViewer } from '@/store';
import { useInterpolatedFrame } from '@/lib/useInterpolatedFrame';
import { staticInterpNode, type InterpNode } from '@/lib/interpolate';
import type { StrengthVector } from '@/lib/topology';

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

// Tension halo disc radius — between node body and hover ring (r·1.7).
// Hover ring: r·1.7 | Halo disc: r·1.35 | FDR ring: r·2.25 — no collision.
const HALO_RADIUS_FACTOR = 1.35;

function NodeMesh({ node }: { node: InterpNode }) {
  const hoveredId = useViewer((s) => s.hoveredId);
  const selectedId = useViewer((s) => s.selectedId);
  const setHovered = useViewer((s) => s.setHovered);
  const setSelected = useViewer((s) => s.setSelected);

  // Consistency overlay data
  const overlayOn = useViewer((s) => s.overlayOn);
  const tensionByClaimId = useViewer((s) => s.tensionByClaimId);
  const maxTension = useViewer((s) => s.maxTension);

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

  // Tension halo — only computed when the overlay is on and this node has tension data.
  const rawTension = overlayOn ? tensionByClaimId[node.id] : undefined;
  const hasTension = overlayOn && rawTension !== undefined;
  // t01 ∈ [0,1]; guard against maxTension === 0 (all nodes at rest → no halo).
  const t01 = hasTension && maxTension > 0 ? rawTension / maxTension : 0;
  const haloColor = hasTension && maxTension > 0 ? tensionScale(t01) : '#000000';
  // Opacity: min 0.15 so even low-tension nodes show a faint halo; max 0.72.
  const haloOpacity = hasTension && maxTension > 0
    ? 0.15 + t01 * 0.57
    : 0;
  const haloR = r * HALO_RADIUS_FACTOR;

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
      {/* Tension halo — soft billboarded disc, radius r·1.35 (between node and hover ring r·1.7).
          Fully gated: renders ONLY when overlayOn && node has a tension entry && maxTension > 0. */}
      {hasTension && maxTension > 0 && (
        <Billboard>
          <mesh position={[0, 0, -0.001]}>
            <circleGeometry args={[haloR, 48]} />
            <meshBasicMaterial
              color={haloColor}
              transparent
              opacity={haloOpacity * node.opacity}
              depthWrite={false}
            />
          </mesh>
        </Billboard>
      )}

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

export default function Nodes() {
  const data = useViewer((s) => s.data);
  const timeline = useViewer((s) => s.timeline);
  const frame = useViewer((s) => s.frame);
  const filters = useViewer((s) => s.filters);

  const interp = useInterpolatedFrame(timeline, frame);

  // Timeline drives the scene when loaded; else fall back to the static export.
  const nodes: InterpNode[] = useMemo(() => {
    if (interp) return interp.nodes;
    if (data) return data.nodes.map(staticInterpNode);
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
