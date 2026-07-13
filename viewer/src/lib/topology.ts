/**
 * TypeScript mirror of the protocol's TopologyExport contract
 * (polymer_protocol/topology.py). The viewer consumes this JSON; the export
 * is the binding interface, so these interfaces match it field-for-field.
 */

export type Vec3 = [number, number, number];

/** strength 6-vector, ordered as polymer_grammar.AXES:
 *  magnitude, certainty, evidence_against_null, severity, world_contact, explanatory_virtue.
 *  The protocol enforces this exact length/order on export (audit #10). */
export type StrengthVector = [number, number, number, number, number, number];

/** The topology/timeline wire contract this viewer was built against
 *  (polymer_protocol.CONTRACT_VERSION). Loaders warn on a mismatch. */
export const SUPPORTED_CONTRACT_VERSION = '1.0';

/** Soft drift check — warns (does not throw) so an older/newer node still renders. */
export function checkContractVersion(version: string | undefined, source: string): void {
  if (version !== undefined && version !== SUPPORTED_CONTRACT_VERSION) {
    console.warn(
      `[polymer-claims] ${source} contract_version ${version} != viewer ${SUPPORTED_CONTRACT_VERSION}; ` +
        'fields may be missing or reshaped.',
    );
  }
}

export interface TopologyNode {
  id: string;
  status: string;
  pattern_id: string;
  subject_kind: string | null;
  strength: StrengthVector | null;
  is_representation_revision: boolean;
  fdr_tested: boolean;
  fdr_discovery: boolean;
  fdr_retracted: boolean;
  fdr_index: number | null;
  fdr_e_value: number | null;
  fdr_alpha_allocated: number | null;
  independence_tier?: string | null;
  severity_provenance?: string | null;
  shared_cause_overlap?: number | null;
  position: Vec3;
  /** Which arm produced this claim (pharmaco/synbio/immuno/polymergenomics) — a FACET
   *  the merged-universe bundler tags onto each node, never a separate universe. Absent
   *  (undefined) on bundles that predate the merge (e.g. the single-arm pharmaco-only export). */
  arm?: string | null;
  /** The claim's realized measurement space (e.g. methylation_genebody, literature) — the
   *  other merge facet, carried alongside `arm`. */
  modality?: string | null;
}

export interface TopologyEdge {
  source: string;
  target: string;
  kind: string;
  effective: boolean;
  provisional: boolean;
  /** Relation-claim facets (Task 6+): "computational" | "biological". Present only
   *  on edges projected from a relation claim (kind coheres/tension/restriction_map);
   *  absent on base defeat/equivalence/entails edges. */
  tier?: string | null;
  /** Severity-derived weight; sign encodes coherence (+) vs tension (-). Relation-only. */
  signed_weight?: number | null;
  /** The relation claim's own lifecycle status (e.g. "conjectured"). Relation-only. */
  relation_status?: string | null;
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
  contract_version?: string;
  consistency?: ConsistencyHeadline | null;
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

export interface ConsistencyHeadline {
  inconsistency_energy: number;
  spectral_gap: number | null;   // null on the live headline; populated only by the full report
}

export interface ClaimTension { claim_id: string; tension: number; }
export interface Obstruction {
  claim_ids: string[];
  edges: [string, string][];
  magnitude: number;
}
export interface ConsistencyReport {
  inconsistency_energy: number;
  equivalence_energy: number;
  defeat_energy: number;
  spectral_gap: number;
  h0_dim: number;
  h1_obstructions: Obstruction[];
  per_claim_tension: ClaimTension[];
  flags: { kind: string; claim_ids: [string, string]; detail: string }[];
}

/** Load the sample export from /public. */
export async function loadTopology(
  url = '/sample-topology.json',
): Promise<TopologyExport> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`failed to load topology: ${res.status} ${res.statusText}`);
  }
  const data = (await res.json()) as TopologyExport;
  checkContractVersion(data.contract_version, 'topology');
  return data;
}
