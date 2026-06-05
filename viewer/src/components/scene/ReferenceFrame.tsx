'use client';

import { Line, Html } from '@react-three/drei';
import { COLOR, FONT_FAMILY_MONO } from '@/config/theme';
import type { Extent, Vec3 } from '@/lib/topology';

// Round a span into a "nice" tick step (1, 2, 5 × 10^k) targeting ~5 ticks.
function niceStep(span: number, target = 5): number {
  if (span <= 0) return 1;
  const raw = span / target;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  let step: number;
  if (norm < 1.5) step = 1;
  else if (norm < 3) step = 2;
  else if (norm < 7) step = 5;
  else step = 10;
  return step * mag;
}

function ticksFor(min: number, max: number): number[] {
  const step = niceStep(max - min);
  const start = Math.ceil(min / step) * step;
  const out: number[] = [];
  for (let v = start; v <= max + 1e-9; v += step) {
    out.push(Math.abs(v) < 1e-9 ? 0 : v);
  }
  return out;
}

function fmt(v: number): string {
  return v.toFixed(1);
}

const HAIRLINE = COLOR.border.subtle; // #D4D4D8
const AXIS = COLOR.border.strong; // #A1A1AA
const LABEL = COLOR.text.tertiary; // #52525B

function tickLabelStyle(): React.CSSProperties {
  return {
    fontFamily: FONT_FAMILY_MONO,
    fontSize: 9,
    lineHeight: 1,
    color: LABEL,
    fontVariantNumeric: 'tabular-nums',
    whiteSpace: 'nowrap',
    userSelect: 'none',
    pointerEvents: 'none',
    transform: 'translate(-50%, -50%)',
  };
}

export default function ReferenceFrame({
  extent,
  layoutId,
}: {
  extent: Extent;
  layoutId: string;
}) {
  const { min, max } = extent;
  const [x0, y0, z0] = min;
  const [x1, y1, z1] = max;

  // ── Wireframe bounding box (12 edges) ─────────────────────────────────────
  const boxCorners: Vec3[] = [
    [x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
    [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1],
  ];
  const boxEdges: [number, number][] = [
    [0, 1], [1, 2], [2, 3], [3, 0], // bottom-z face
    [4, 5], [5, 6], [6, 7], [7, 4], // top-z face
    [0, 4], [1, 5], [2, 6], [3, 7], // verticals
  ];

  // ── Axis lines along the lower-front-left corner of the box ───────────────
  const xTicks = ticksFor(x0, x1);
  const yTicks = ticksFor(y0, y1);
  const zTicks = ticksFor(z0, z1);

  const tickLen = Math.max(extent.size[0], extent.size[1], extent.size[2]) * 0.02;

  return (
    <group>
      {/* bounding box — hairline */}
      {boxEdges.map(([a, b], i) => (
        <Line
          key={`box-${i}`}
          points={[boxCorners[a], boxCorners[b]]}
          color={HAIRLINE}
          lineWidth={1}
          transparent
          opacity={0.9}
        />
      ))}

      {/* X axis (along y0, z0) */}
      <Line points={[[x0, y0, z0], [x1, y0, z0]]} color={AXIS} lineWidth={1} />
      {xTicks.map((tx) => (
        <group key={`xt-${tx}`}>
          <Line
            points={[[tx, y0, z0], [tx, y0 - tickLen, z0]]}
            color={AXIS}
            lineWidth={1}
          />
          <Html position={[tx, y0 - tickLen * 3, z0]} center distanceFactor={10}>
            <span style={tickLabelStyle()} className="mono tabular">{fmt(tx)}</span>
          </Html>
        </group>
      ))}

      {/* Y axis (along x0, z0) */}
      <Line points={[[x0, y0, z0], [x0, y1, z0]]} color={AXIS} lineWidth={1} />
      {yTicks.map((ty) => (
        <group key={`yt-${ty}`}>
          <Line
            points={[[x0, ty, z0], [x0 - tickLen, ty, z0]]}
            color={AXIS}
            lineWidth={1}
          />
          <Html position={[x0 - tickLen * 3, ty, z0]} center distanceFactor={10}>
            <span style={tickLabelStyle()} className="mono tabular">{fmt(ty)}</span>
          </Html>
        </group>
      ))}

      {/* Z axis (along x0, y0) */}
      <Line points={[[x0, y0, z0], [x0, y0, z1]]} color={AXIS} lineWidth={1} />
      {zTicks.map((tz) => (
        <group key={`zt-${tz}`}>
          <Line
            points={[[x0, y0, tz], [x0, y0 - tickLen, tz]]}
            color={AXIS}
            lineWidth={1}
          />
          <Html position={[x0, y0 - tickLen * 3, tz]} center distanceFactor={10}>
            <span style={tickLabelStyle()} className="mono tabular">{fmt(tz)}</span>
          </Html>
        </group>
      ))}

      {/* layout_id caption at the frame origin */}
      <Html position={[x0, y0 - tickLen * 6, z0]} center distanceFactor={10}>
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
