'use client';

import { useMemo } from 'react';
import { Line } from '@react-three/drei';
import { EDGE_COLOR, COLOR } from '@/config/theme';
import { useViewer, edgeBucket } from '@/store';
import { useInterpolatedFrame } from '@/lib/useInterpolatedFrame';
import { staticInterpNode, type InterpEdge, type InterpNode } from '@/lib/interpolate';
import type { Vec3 } from '@/lib/topology';

function edgeColor(kind: string): string {
  return EDGE_COLOR[kind] ?? COLOR.border.strong;
}

export default function Edges() {
  const data = useViewer((s) => s.data);
  const timeline = useViewer((s) => s.timeline);
  const frame = useViewer((s) => s.frame);
  const filters = useViewer((s) => s.filters);

  const interp = useInterpolatedFrame(timeline, frame);

  // Resolve the active node set (interpolated when a timeline is loaded) so
  // edge endpoints track the same animated positions + status filtering.
  const nodes: InterpNode[] = useMemo(() => {
    if (interp) return interp.nodes;
    if (data) return data.nodes.map(staticInterpNode);
    return [];
  }, [interp, data]);

  const edges: InterpEdge[] = useMemo(() => {
    if (interp) return interp.edges;
    if (data) {
      return data.edges.map((e) => ({
        source: e.source,
        target: e.target,
        kind: e.kind,
        effective: e.effective,
        provisional: e.provisional,
        opacity: 1,
        tier: e.tier,
        signed_weight: e.signed_weight,
        relation_status: e.relation_status,
      }));
    }
    return [];
  }, [interp, data]);

  const positions = useMemo(() => {
    const map = new Map<string, Vec3>();
    for (const n of nodes) map.set(n.id, n.position);
    return map;
  }, [nodes]);

  const statusOf = useMemo(() => {
    const map = new Map<string, string>();
    for (const n of nodes) map.set(n.id, n.status);
    return map;
  }, [nodes]);

  if (edges.length === 0) return null;

  return (
    <group>
      {edges.map((e, i) => {
        const a = positions.get(e.source);
        const b = positions.get(e.target);
        if (!a || !b) return null;

        // filter: by edge-kind bucket, by provisional toggle, and hide if an
        // endpoint node is filtered out by status.
        const bucket = edgeBucket(e.kind);
        if (!filters.edgeKinds.has(bucket)) return null;
        if (e.provisional && !filters.showProvisional) return null;

        const srcStatus = statusOf.get(e.source);
        const tgtStatus = statusOf.get(e.target);
        if (srcStatus && !filters.statuses.has(srcStatus)) return null;
        if (tgtStatus && !filters.statuses.has(tgtStatus)) return null;

        const color = edgeColor(e.kind);

        // relation edges (Task 6+) carry tier/signed_weight/relation_status;
        // base defeat/equivalence/entails edges leave all three undefined, so
        // every branch below is a no-op for them and rendering is unchanged.
        const conjectured = e.relation_status === 'conjectured';
        const isTension = e.signed_weight != null && e.signed_weight < 0;
        const biological = e.tier === 'biological';

        // provisional or conjectured → dashed, ghosted; effective → solid full;
        // else faint solid — then scaled by the enter/exit fade opacity of the frame.
        const dashed = e.provisional || conjectured;
        const baseOpacity = dashed ? 0.35 : e.effective ? 0.9 : 0.45;
        const opacity = baseOpacity * e.opacity;

        // sign styles line weight (tension reads heavier/warmer); tier styles
        // the dash cadence when dashed (biological = finer dash than computational).
        const lineWidth = 1 + (biological ? 0.4 : 0) + (isTension ? 0.4 : 0);
        const dashSize = biological ? 0.06 : 0.12;
        const gapSize = biological ? 0.045 : 0.08;

        return (
          <Line
            key={`${e.source}-${e.target}-${e.kind}-${i}`}
            points={[a, b]}
            color={color}
            lineWidth={lineWidth}
            transparent
            opacity={opacity}
            dashed={dashed}
            dashSize={dashSize}
            gapSize={gapSize}
          />
        );
      })}
    </group>
  );
}
