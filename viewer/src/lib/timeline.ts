/**
 * TypeScript mirror of the protocol's TopologyTimeline contract
 * (polymer_protocol/timeline.py). The viewer plays this JSON back across
 * run_cycle iterations; the export is the binding interface, so these
 * interfaces match it field-for-field.
 */

import { type TopologyExport, checkContractVersion } from '@/lib/topology';

/** Per-cycle summary derived from the CycleResult + post-cycle corpus + topology. */
export interface FrameStats {
  cycle_index: number;
  n_nodes: number;
  n_licensed: number;
  n_pending: number;
  n_conjectured: number;
  n_rejected: number;
  n_edges: number;
  n_effective_edges: number;
  n_provisional_edges: number;
  n_frontier: number;
  /** claims generated this cycle (len of generation.admitted) */
  n_added: number;
  /** licensed delta vs the prior frame */
  n_newly_licensed: number;
}

export interface TimelineFrame {
  topology: TopologyExport;
  stats: FrameStats;
}

export interface TopologyTimeline {
  frames: TimelineFrame[];
  n_cycles: number;
  contract_version?: string;
}

/** Load the sample timeline from /public. */
export async function loadTimeline(
  url = '/sample-timeline.json',
): Promise<TopologyTimeline> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`failed to load timeline: ${res.status} ${res.statusText}`);
  }
  const data = (await res.json()) as TopologyTimeline;
  checkContractVersion(data.contract_version, 'timeline');
  return data;
}
