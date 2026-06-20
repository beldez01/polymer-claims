/**
 * Frame interpolation — blends two adjacent timeline frames A=floor(frame) and
 * B=ceil(frame) at t = frame - floor(frame) so the universe animates smoothly
 * across run_cycle iterations. Warm-started positions keep persistent nodes
 * close, so lerping produces small coherent motion (no teleporting).
 *
 * Pure functions only. Call `interpolateFrame` inside a `useMemo` keyed on
 * (timeline, frame) — never return fresh objects straight from a zustand
 * selector (the useSyncExternalStore "cached snapshot" trap).
 */

import type {
  FrameStats,
  TopologyTimeline,
} from '@/lib/timeline';
import type {
  TopologyEdge,
  TopologyNode,
  Vec3,
} from '@/lib/topology';

/** A node resolved for a single animation instant. */
export interface InterpNode {
  id: string;
  status: string;
  /** crossfade-from status (frame A) when the status changed across A→B. */
  prevStatus: string;
  /** color crossfade fraction A→B in [0,1]; 0 = pure prevStatus, 1 = status. */
  statusT: number;
  pattern_id: string;
  subject_kind: string | null;
  strength: TopologyNode['strength'];
  is_representation_revision: boolean;
  fdr_tested: boolean;
  fdr_discovery: boolean;
  fdr_retracted: boolean;
  fdr_index: number | null;
  fdr_e_value: number | null;
  fdr_alpha_allocated: number | null;
  independence_tier: string | null;
  severity_provenance: string | null;
  shared_cause_overlap: number | null;
  position: Vec3;
  /** enter/exit growth in [0,1] — drives both mesh scale and material opacity. */
  scale: number;
  opacity: number;
}

/** An edge resolved for a single animation instant. */
export interface InterpEdge {
  source: string;
  target: string;
  kind: string;
  effective: boolean;
  provisional: boolean;
  opacity: number;
}

export interface InterpFrame {
  nodes: InterpNode[];
  edges: InterpEdge[];
  stats: FrameStats;
  layoutId: string;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function lerpVec3(a: Vec3, b: Vec3, t: number): Vec3 {
  return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
}

function edgeKey(e: TopologyEdge): string {
  return `${e.source}\u0000${e.target}\u0000${e.kind}`;
}

/**
 * Blend two adjacent frames of the timeline.
 *
 * - present in A and B → lerp position; status color crossfades when changed;
 *   full scale + opacity.
 * - present only in B → enter: B position, scale t, opacity t.
 * - present only in A → exit: A position, scale 1-t, opacity 1-t.
 *
 * Edges: union of A and B. Edges present in both stay solid; edges entering
 * (B only) fade in with t; edges leaving (A only) fade out with 1-t. Styling
 * (kind/effective/provisional) is taken from the nearer/containing frame,
 * preferring B.
 */
export function interpolateFrame(
  timeline: TopologyTimeline,
  frame: number,
): InterpFrame {
  const frames = timeline.frames;
  const last = frames.length - 1;
  const clamped = Math.min(Math.max(frame, 0), last);
  const i = Math.floor(clamped);
  const j = Math.min(i + 1, last);
  const t = clamped - i;

  const fa = frames[i];
  const fb = frames[j];
  const A = fa.topology;
  const B = fb.topology;

  const aNodes = new Map<string, TopologyNode>();
  for (const n of A.nodes) aNodes.set(n.id, n);
  const bNodes = new Map<string, TopologyNode>();
  for (const n of B.nodes) bNodes.set(n.id, n);

  const nodes: InterpNode[] = [];

  // present in B (persistent or entering)
  for (const nb of B.nodes) {
    const na = aNodes.get(nb.id);
    if (na) {
      // persistent — lerp position, crossfade color when status changed
      const changed = na.status !== nb.status;
      nodes.push({
        id: nb.id,
        status: nb.status,
        prevStatus: na.status,
        statusT: changed ? t : 1,
        pattern_id: nb.pattern_id,
        subject_kind: nb.subject_kind,
        strength: nb.strength,
        is_representation_revision: nb.is_representation_revision,
        fdr_tested: nb.fdr_tested ?? false,
        fdr_discovery: nb.fdr_discovery ?? false,
        fdr_retracted: nb.fdr_retracted ?? false,
        fdr_index: nb.fdr_index ?? null,
        fdr_e_value: nb.fdr_e_value ?? null,
        fdr_alpha_allocated: nb.fdr_alpha_allocated ?? null,
        independence_tier: nb.independence_tier ?? null,
        severity_provenance: nb.severity_provenance ?? null,
        shared_cause_overlap: nb.shared_cause_overlap ?? null,
        position: lerpVec3(na.position, nb.position, t),
        scale: 1,
        opacity: 1,
      });
    } else {
      // entering — B position, grow in
      nodes.push({
        id: nb.id,
        status: nb.status,
        prevStatus: nb.status,
        statusT: 1,
        pattern_id: nb.pattern_id,
        subject_kind: nb.subject_kind,
        strength: nb.strength,
        is_representation_revision: nb.is_representation_revision,
        fdr_tested: nb.fdr_tested ?? false,
        fdr_discovery: nb.fdr_discovery ?? false,
        fdr_retracted: nb.fdr_retracted ?? false,
        fdr_index: nb.fdr_index ?? null,
        fdr_e_value: nb.fdr_e_value ?? null,
        fdr_alpha_allocated: nb.fdr_alpha_allocated ?? null,
        independence_tier: nb.independence_tier ?? null,
        severity_provenance: nb.severity_provenance ?? null,
        shared_cause_overlap: nb.shared_cause_overlap ?? null,
        position: nb.position,
        scale: t,
        opacity: t,
      });
    }
  }

  // present only in A (exiting)
  for (const na of A.nodes) {
    if (bNodes.has(na.id)) continue;
    nodes.push({
      id: na.id,
      status: na.status,
      prevStatus: na.status,
      statusT: 1,
      pattern_id: na.pattern_id,
      subject_kind: na.subject_kind,
      strength: na.strength,
      is_representation_revision: na.is_representation_revision,
      fdr_tested: na.fdr_tested ?? false,
      fdr_discovery: na.fdr_discovery ?? false,
      fdr_retracted: na.fdr_retracted ?? false,
      fdr_index: na.fdr_index ?? null,
      fdr_e_value: na.fdr_e_value ?? null,
      fdr_alpha_allocated: na.fdr_alpha_allocated ?? null,
      independence_tier: na.independence_tier ?? null,
      severity_provenance: na.severity_provenance ?? null,
      shared_cause_overlap: na.shared_cause_overlap ?? null,
      position: na.position,
      scale: 1 - t,
      opacity: 1 - t,
    });
  }

  // edges — union, styling prefers the containing frame (B first)
  const aEdges = new Map<string, TopologyEdge>();
  for (const e of A.edges) aEdges.set(edgeKey(e), e);
  const bEdges = new Map<string, TopologyEdge>();
  for (const e of B.edges) bEdges.set(edgeKey(e), e);

  const edges: InterpEdge[] = [];
  const seen = new Set<string>();
  for (const eb of B.edges) {
    const k = edgeKey(eb);
    seen.add(k);
    const inA = aEdges.has(k);
    edges.push({
      source: eb.source,
      target: eb.target,
      kind: eb.kind,
      effective: eb.effective,
      provisional: eb.provisional,
      opacity: inA ? 1 : t, // entering edge fades in
    });
  }
  for (const ea of A.edges) {
    const k = edgeKey(ea);
    if (seen.has(k)) continue; // already handled (present in B)
    edges.push({
      source: ea.source,
      target: ea.target,
      kind: ea.kind,
      effective: ea.effective,
      provisional: ea.provisional,
      opacity: 1 - t, // leaving edge fades out
    });
  }

  // stats + layout follow the dominant frame (B once we cross the midpoint),
  // so the live readout snaps to the cycle the universe has settled into.
  const dom = t < 0.5 ? fa : fb;

  return {
    nodes,
    edges,
    stats: dom.stats,
    layoutId: dom.topology.layout_id,
  };
}
