'use client';

import { useMemo } from 'react';
import { Line } from '@react-three/drei';
import { EDGE_COLOR, COLOR } from '@/config/theme';
import { useViewer, edgeBucket } from '@/store';
import type { TopologyEdge, Vec3 } from '@/lib/topology';

function edgeColor(kind: string): string {
  return EDGE_COLOR[kind] ?? COLOR.border.strong;
}

export default function Edges() {
  const data = useViewer((s) => s.data);
  const filters = useViewer((s) => s.filters);

  const positions = useMemo(() => {
    const map = new Map<string, Vec3>();
    if (data) for (const n of data.nodes) map.set(n.id, n.position);
    return map;
  }, [data]);

  if (!data) return null;

  return (
    <group>
      {data.edges.map((e: TopologyEdge, i) => {
        const a = positions.get(e.source);
        const b = positions.get(e.target);
        if (!a || !b) return null;

        // filter: by edge-kind bucket, by provisional toggle, and hide if an
        // endpoint node is filtered out by status.
        const bucket = edgeBucket(e.kind);
        if (!filters.edgeKinds.has(bucket)) return null;
        if (e.provisional && !filters.showProvisional) return null;

        const src = data.nodes.find((n) => n.id === e.source);
        const tgt = data.nodes.find((n) => n.id === e.target);
        if (src && !filters.statuses.has(src.status)) return null;
        if (tgt && !filters.statuses.has(tgt.status)) return null;

        const color = edgeColor(e.kind);

        // provisional → dashed, ghosted; effective → solid full; else faint solid
        const provisional = e.provisional;
        const opacity = provisional ? 0.35 : e.effective ? 0.9 : 0.45;

        return (
          <Line
            key={`${e.source}-${e.target}-${e.kind}-${i}`}
            points={[a, b]}
            color={color}
            lineWidth={1}
            transparent
            opacity={opacity}
            dashed={provisional}
            dashSize={0.12}
            gapSize={0.08}
          />
        );
      })}
    </group>
  );
}
