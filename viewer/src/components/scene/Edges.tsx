'use client';

import { useMemo } from 'react';
import { Line } from '@react-three/drei';
import { EDGE_COLOR, COLOR } from '@/config/theme';
import { useViewer, edgeBucket } from '@/store';
import { useInterpolatedFrame } from '@/lib/useInterpolatedFrame';
import type { InterpEdge, InterpNode } from '@/lib/interpolate';
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
    if (data) {
      return data.nodes.map((n) => ({
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
        shared_cause_overlap: n.shared_cause_overlap ?? null,
        position: n.position,
        scale: 1,
        opacity: 1,
      }));
    }
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

        // provisional → dashed, ghosted; effective → solid full; else faint
        // solid — then scaled by the enter/exit fade opacity of the frame.
        const provisional = e.provisional;
        const baseOpacity = provisional ? 0.35 : e.effective ? 0.9 : 0.45;
        const opacity = baseOpacity * e.opacity;

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
