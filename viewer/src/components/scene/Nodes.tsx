'use client';

import { useMemo } from 'react';
import { Billboard, Line, Html } from '@react-three/drei';
import { ThreeEvent } from '@react-three/fiber';
import { COLOR, STATUS_COLOR, FONT_FAMILY_MONO } from '@/config/theme';
import { useViewer } from '@/store';
import type { TopologyNode } from '@/lib/topology';

const BASE_RADIUS = 0.28;
const RING_SEGMENTS = 48;

function statusColor(status: string): string {
  return STATUS_COLOR[status] ?? COLOR.text.muted;
}

// strength axis 2 = evidence_against_null — drives a subtle radius scale.
function nodeRadius(node: TopologyNode): number {
  const ean = node.strength ? node.strength[2] : 0.5;
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

function NodeMesh({ node }: { node: TopologyNode }) {
  const hoveredId = useViewer((s) => s.hoveredId);
  const selectedId = useViewer((s) => s.selectedId);
  const setHovered = useViewer((s) => s.setHovered);
  const setSelected = useViewer((s) => s.setSelected);

  const color = statusColor(node.status);
  const r = nodeRadius(node);
  const isHovered = hoveredId === node.id;
  const isSelected = selectedId === node.id;
  const ringR = r * 1.7;
  const ring = useMemo(() => ringPoints(ringR), [ringR]);

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
    <group position={node.position}>
      <mesh onPointerOver={onOver} onPointerOut={onOut} onClick={onClick}>
        {node.is_representation_revision ? (
          <octahedronGeometry args={[r * 1.25, 0]} />
        ) : (
          <sphereGeometry args={[r, 24, 24]} />
        )}
        {/* matte — metalness 0, roughness 0.9, NO emissive */}
        <meshStandardMaterial color={color} metalness={0} roughness={0.9} />
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
          </div>
        </Html>
      )}
    </group>
  );
}

export default function Nodes() {
  const data = useViewer((s) => s.data);
  const filters = useViewer((s) => s.filters);

  if (!data) return null;

  return (
    <group>
      {data.nodes
        .filter((n) => filters.statuses.has(n.status))
        .map((n) => (
          <NodeMesh key={n.id} node={n} />
        ))}
    </group>
  );
}
