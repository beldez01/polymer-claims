'use client';

import { useMemo } from 'react';
import type { TopologyTimeline } from '@/lib/timeline';
import { interpolateFrame, type InterpFrame } from '@/lib/interpolate';

// Module-level single-entry cache: ~7 scene components call this hook with the same
// (timeline, frame) in one commit. The first computes; the rest reuse the cached object
// (keeping the returned reference stable across callers within a frame). Keyed by
// referential identity of `timeline` + value of `frame`; interpolateFrame is pure, so a
// matching key always yields the same result.
let _lastTimeline: TopologyTimeline | null = null;
let _lastFrame = NaN;
let _lastResult: InterpFrame | null = null;

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
    if (timeline === _lastTimeline && frame === _lastFrame) return _lastResult;
    _lastTimeline = timeline;
    _lastFrame = frame;
    _lastResult = interpolateFrame(timeline, frame);
    return _lastResult;
  }, [timeline, frame]);
}
