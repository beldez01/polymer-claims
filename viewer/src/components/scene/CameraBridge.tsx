'use client';

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useViewer } from '@/store';

// Writes the live camera position into the store, throttled to ~6 Hz and only
// when it actually moved — so the mono readout updates without thrashing React.
export default function CameraBridge() {
  const setCamera = useViewer((s) => s.setCamera);
  const last = useRef({ x: NaN, y: NaN, z: NaN, t: 0 });

  useFrame((state) => {
    const now = state.clock.elapsedTime;
    if (now - last.current.t < 0.16) return;
    const p = state.camera.position;
    const x = Math.round(p.x * 100) / 100;
    const y = Math.round(p.y * 100) / 100;
    const z = Math.round(p.z * 100) / 100;
    if (x === last.current.x && y === last.current.y && z === last.current.z) return;
    last.current = { x, y, z, t: now };
    setCamera({ x, y, z });
  });

  return null;
}
