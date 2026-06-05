'use client';

import { useEffect, useMemo, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid } from '@react-three/drei';
import { COLOR, FONT_FAMILY_MONO } from '@/config/theme';
import {
  computeExtent,
  loadTopology,
  type TopologyExport,
} from '@/lib/topology';
import ReferenceFrame from '@/components/scene/ReferenceFrame';
import Nodes from '@/components/scene/Nodes';
import Edges from '@/components/scene/Edges';
import { useViewer } from '@/store';

function Scene({ data }: { data: TopologyExport }) {
  const extent = useMemo(() => computeExtent(data.nodes), [data.nodes]);
  const [cx, cy, cz] = extent.center;
  const radius = Math.max(extent.size[0], extent.size[1], extent.size[2]);
  const setSelected = useViewer((s) => s.setSelected);

  return (
    <>
      {/* soft, matte lighting — no specular hot-spots, no glow */}
      <ambientLight intensity={0.8} />
      <directionalLight position={[cx + radius, cy + radius * 1.5, cz + radius]} intensity={0.4} />

      {/* click empty space → deselect (invisible backing sphere behind all) */}
      <mesh position={[cx, cy, cz]} onClick={() => setSelected(null)} visible={false}>
        <sphereGeometry args={[radius * 100, 8, 8]} />
        <meshBasicMaterial side={2} />
      </mesh>

      <ReferenceFrame extent={extent} layoutId={data.layout_id} />
      <Edges />
      <Nodes />

      {/* ground grid at the floor plane (y = ymin) — hairline */}
      <Grid
        position={[cx, extent.min[1], cz]}
        args={[radius * 2.4, radius * 2.4]}
        cellSize={radius * 0.1}
        cellThickness={0.6}
        cellColor={COLOR.border.default}
        sectionSize={radius * 0.5}
        sectionThickness={1}
        sectionColor={COLOR.border.subtle}
        fadeDistance={radius * 8}
        fadeStrength={1}
        infiniteGrid={false}
        followCamera={false}
      />

      <OrbitControls
        target={[cx, cy, cz]}
        enableDamping
        dampingFactor={0.08}
        makeDefault
      />
    </>
  );
}

export default function ClaimUniverse() {
  const data = useViewer((s) => s.data);
  const setData = useViewer((s) => s.setData);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTopology()
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [setData]);

  if (error) {
    return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: FONT_FAMILY_MONO,
          fontSize: 12,
          color: COLOR.accent.rose,
        }}
        className="mono"
      >
        {error}
      </div>
    );
  }

  if (!data) return null;

  const extent = computeExtent(data.nodes);
  const [cx, cy, cz] = extent.center;
  const radius = Math.max(extent.size[0], extent.size[1], extent.size[2]) || 2;

  return (
    <Canvas
      style={{ position: 'absolute', inset: 0, background: COLOR.bg.primary }}
      camera={{
        fov: 50,
        near: 0.01,
        far: 1000,
        position: [cx + radius * 1.6, cy + radius * 1.1, cz + radius * 1.9],
      }}
      gl={{ antialias: true }}
    >
      <color attach="background" args={[COLOR.bg.primary]} />
      <Scene data={data} />
    </Canvas>
  );
}
