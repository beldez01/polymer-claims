'use client';

import { Line, Html } from '@react-three/drei';
import { COLOR, FONT_FAMILY_MONO } from '@/config/theme';
import type { Extent } from '@/lib/topology';

const AXIS = COLOR.border.strong; // #A1A1AA — hairline axis
const LABEL = COLOR.text.tertiary; // #52525B

function axisLabelStyle(): React.CSSProperties {
  return {
    fontFamily: FONT_FAMILY_MONO,
    fontSize: 11,
    lineHeight: 1,
    fontWeight: 600,
    letterSpacing: '0.08em',
    color: LABEL,
    userSelect: 'none',
    pointerEvents: 'none',
    transform: 'translate(-50%, -50%)',
  };
}

/**
 * Reference frame: three perpendicular X/Y/Z axes through the ORIGIN, projected symmetrically far
 * in both directions. The signed-Laplacian eigenmap coordinates are mean-centered (each eigenvector
 * sums to zero), so (0,0,0) is the true centroid — the axes cross there, spanning ± equally. Long
 * hairlines read as effectively infinite within any normal view; letters sit at the positive ends.
 * No bounding cube, no numeric ticks (eigenvector components aren't meaningful magnitudes).
 */
export default function ReferenceFrame({
  extent,
  layoutId,
}: {
  extent: Extent;
  layoutId: string;
}) {
  const { min, max, size } = extent;
  const span = Math.max(size[0], size[1], size[2]);

  const REACH = span * 25;   // effectively-infinite projection in each direction
  const gap = span * 0.06;   // letter sits just beyond the positive data edge

  // positive reach of the data per axis (so the letter clears the cloud, not the far tip)
  const rx = Math.max(Math.abs(min[0]), Math.abs(max[0])) + gap;
  const ry = Math.max(Math.abs(min[1]), Math.abs(max[1])) + gap;
  const rz = Math.max(Math.abs(min[2]), Math.abs(max[2])) + gap;

  return (
    <group>
      {/* perpendicular X / Y / Z axes through the origin, projected ± symmetrically */}
      <Line points={[[-REACH, 0, 0], [REACH, 0, 0]]} color={AXIS} lineWidth={1} transparent opacity={0.55} />
      <Line points={[[0, -REACH, 0], [0, REACH, 0]]} color={AXIS} lineWidth={1} transparent opacity={0.55} />
      <Line points={[[0, 0, -REACH], [0, 0, REACH]]} color={AXIS} lineWidth={1} transparent opacity={0.55} />

      {/* origin marker — small neutral node at the true centroid (0,0,0) */}
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[span * 0.007, 12, 12]} />
        <meshBasicMaterial color={AXIS} />
      </mesh>

      {/* axis letters at the positive ends, just past the data */}
      <Html position={[rx, 0, 0]} center distanceFactor={10}>
        <span style={axisLabelStyle()} className="mono">X</span>
      </Html>
      <Html position={[0, ry, 0]} center distanceFactor={10}>
        <span style={axisLabelStyle()} className="mono">Y</span>
      </Html>
      <Html position={[0, 0, rz]} center distanceFactor={10}>
        <span style={axisLabelStyle()} className="mono">Z</span>
      </Html>

      {/* layout_id caption below the cloud */}
      <Html position={[0, min[1] - gap * 2, 0]} center distanceFactor={10}>
        <span
          style={{
            fontFamily: FONT_FAMILY_MONO,
            fontSize: 9,
            color: COLOR.text.muted,
            fontVariantNumeric: 'tabular-nums',
            whiteSpace: 'nowrap',
            userSelect: 'none',
            pointerEvents: 'none',
            letterSpacing: '0.04em',
          }}
          className="mono tabular"
        >
          {layoutId}
        </span>
      </Html>
    </group>
  );
}
