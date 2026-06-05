'use client';

import { create } from 'zustand';
import type { TopologyExport, TopologyNode } from '@/lib/topology';
import { STATUS_ORDER, DEFEAT_KINDS } from '@/config/theme';

export interface Filters {
  statuses: Set<string>;
  // edge-kind buckets: 'defeat' (rose family) | 'equivalence' | 'entails'
  edgeKinds: Set<string>;
  showProvisional: boolean;
}

export interface Counts {
  total: number;
  byStatus: Record<string, number>;
  edgeTotal: number;
  edgeEffective: number;
  edgeProvisional: number;
}

export interface CameraCoords {
  x: number;
  y: number;
  z: number;
}

interface ViewerState {
  data: TopologyExport | null;
  selectedId: string | null;
  hoveredId: string | null;
  filters: Filters;
  camera: CameraCoords;

  setData: (data: TopologyExport) => void;
  setHovered: (id: string | null) => void;
  setSelected: (id: string | null) => void;
  toggleStatus: (status: string) => void;
  toggleEdgeKind: (bucket: string) => void;
  setShowProvisional: (v: boolean) => void;
  setCamera: (c: CameraCoords) => void;

  // derived helpers
  counts: () => Counts;
  isNodeVisible: (node: TopologyNode) => boolean;
  selectedNode: () => TopologyNode | null;
}

/** Map a raw edge kind to its filter bucket. */
export function edgeBucket(kind: string): 'defeat' | 'equivalence' | 'entails' {
  if ((DEFEAT_KINDS as readonly string[]).includes(kind)) return 'defeat';
  if (kind === 'equivalence') return 'equivalence';
  return 'entails';
}

export const EDGE_BUCKETS = ['defeat', 'equivalence', 'entails'] as const;

export const useViewer = create<ViewerState>((set, get) => ({
  data: null,
  selectedId: null,
  hoveredId: null,
  filters: {
    statuses: new Set<string>(STATUS_ORDER),
    edgeKinds: new Set<string>(EDGE_BUCKETS),
    showProvisional: true,
  },
  camera: { x: 0, y: 0, z: 0 },

  setData: (data) => set({ data }),
  setHovered: (id) => set({ hoveredId: id }),
  setSelected: (id) => set({ selectedId: id }),

  toggleStatus: (status) =>
    set((s) => {
      const next = new Set(s.filters.statuses);
      if (next.has(status)) next.delete(status);
      else next.add(status);
      return { filters: { ...s.filters, statuses: next } };
    }),

  toggleEdgeKind: (bucket) =>
    set((s) => {
      const next = new Set(s.filters.edgeKinds);
      if (next.has(bucket)) next.delete(bucket);
      else next.add(bucket);
      return { filters: { ...s.filters, edgeKinds: next } };
    }),

  setShowProvisional: (v) =>
    set((s) => ({ filters: { ...s.filters, showProvisional: v } })),

  setCamera: (c) => set({ camera: c }),

  counts: () => {
    const data = get().data;
    const byStatus: Record<string, number> = {};
    for (const st of STATUS_ORDER) byStatus[st] = 0;
    let edgeEffective = 0;
    let edgeProvisional = 0;
    if (!data) {
      return { total: 0, byStatus, edgeTotal: 0, edgeEffective: 0, edgeProvisional: 0 };
    }
    for (const n of data.nodes) {
      byStatus[n.status] = (byStatus[n.status] ?? 0) + 1;
    }
    for (const e of data.edges) {
      if (e.effective) edgeEffective++;
      if (e.provisional) edgeProvisional++;
    }
    return {
      total: data.nodes.length,
      byStatus,
      edgeTotal: data.edges.length,
      edgeEffective,
      edgeProvisional,
    };
  },

  isNodeVisible: (node) => {
    return get().filters.statuses.has(node.status);
  },

  selectedNode: () => {
    const { data, selectedId } = get();
    if (!data || !selectedId) return null;
    return data.nodes.find((n) => n.id === selectedId) ?? null;
  },
}));
