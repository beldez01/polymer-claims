'use client';

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useViewer } from '@/store';

/**
 * Advances the playback `frame` while `playing`, using R3F's frame clock as the
 * animation time source (client-side only — the engine never sees a wall
 * clock). Throttled to ~60 Hz via the rAF loop itself; on each tick it adds
 * `speed * dt` frames, clamps at the last frame, and auto-pauses at the end.
 *
 * Reads store fields imperatively via getState() so this component never
 * re-renders on frame changes (which would thrash React 60×/sec).
 */
export default function TimelineDriver() {
  const last = useRef<number>(0);

  useFrame((state) => {
    const s = useViewer.getState();
    if (!s.playing || !s.timeline) {
      last.current = state.clock.elapsedTime;
      return;
    }
    const now = state.clock.elapsedTime;
    const dt = now - last.current;
    last.current = now;
    if (dt <= 0) return;

    const lastFrame = s.timeline.frames.length - 1;
    const next = s.frame + s.speed * dt;
    if (next >= lastFrame) {
      useViewer.setState({ frame: lastFrame, playing: false });
    } else {
      useViewer.setState({ frame: next });
    }
  });

  return null;
}
