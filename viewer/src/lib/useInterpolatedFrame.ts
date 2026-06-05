'use client';

import { useMemo } from 'react';
import type { TopologyTimeline } from '@/lib/timeline';
import { interpolateFrame, type InterpFrame } from '@/lib/interpolate';

/**
 * Memoized interpolated-frame hook. Returns the blended `{ nodes, edges, stats,
 * layoutId }` between floor(frame) and ceil(frame). Memoized on (timeline,
 * frame) so the scene only recomputes when the animation clock advances — and
 * so we never hand a fresh object straight out of a store selector.
 */
export function useInterpolatedFrame(
  timeline: TopologyTimeline | null,
  frame: number,
): InterpFrame | null {
  return useMemo(() => {
    if (!timeline || timeline.frames.length === 0) return null;
    return interpolateFrame(timeline, frame);
  }, [timeline, frame]);
}
