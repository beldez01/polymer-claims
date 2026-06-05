/**
 * TypeScript mirror of the protocol's TopologyExport contract
 * (polymer_protocol/topology.py). The viewer consumes this JSON; the export
 * is the binding interface, so these interfaces match it field-for-field.
 */

export type Vec3 = [number, number, number];

/** strength 6-vector, ordered as polymer_grammar.AXES:
 *  magnitude, certainty, evidence_against_null, severity, world_contact, explanatory_virtue. */
export type StrengthVector = [number, number, number, number, number, number];

export interface TopologyNode {
  id: string;
  status: string;
  pattern_id: string;
  subject_kind: string | null;
  strength: StrengthVector | null;
  is_representation_revision: boolean;
  position: Vec3;
}

export interface TopologyEdge {
  source: string;
  target: string;
  kind: string;
  effective: boolean;
  provisional: boolean;
}

export interface TopologyCluster {
  id: string;
  label: string;
  member_ids: string[];
}

export interface TopologyExport {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  clusters: TopologyCluster[];
  layout_id: string;
}

/** Per-axis extent of the node positions — drives the reference frame + ticks. */
export interface Extent {
  min: Vec3;
  max: Vec3;
  center: Vec3;
  size: Vec3;
}

export function computeExtent(nodes: TopologyNode[]): Extent {
  if (nodes.length === 0) {
    return { min: [-1, -1, -1], max: [1, 1, 1], center: [0, 0, 0], size: [2, 2, 2] };
  }
  const min: Vec3 = [Infinity, Infinity, Infinity];
  const max: Vec3 = [-Infinity, -Infinity, -Infinity];
  for (const n of nodes) {
    for (let i = 0; i < 3; i++) {
      if (n.position[i] < min[i]) min[i] = n.position[i];
      if (n.position[i] > max[i]) max[i] = n.position[i];
    }
  }
  // pad slightly so nodes do not sit on the bounding-box faces
  const pad: Vec3 = [0, 0, 0];
  for (let i = 0; i < 3; i++) {
    const span = max[i] - min[i];
    pad[i] = span > 1e-6 ? span * 0.08 : 0.5;
    min[i] -= pad[i];
    max[i] += pad[i];
  }
  const center: Vec3 = [
    (min[0] + max[0]) / 2,
    (min[1] + max[1]) / 2,
    (min[2] + max[2]) / 2,
  ];
  const size: Vec3 = [max[0] - min[0], max[1] - min[1], max[2] - min[2]];
  return { min, max, center, size };
}

/** Load the sample export from /public. */
export async function loadTopology(
  url = '/sample-topology.json',
): Promise<TopologyExport> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`failed to load topology: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as TopologyExport;
}
