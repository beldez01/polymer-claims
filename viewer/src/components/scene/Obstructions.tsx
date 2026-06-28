'use client';

/**
 * Obstructions — H¹ frustration-cycle overlay.
 *
 * Renders rose cycle-edges and node outline rings for each H¹ obstruction in
 * the consistency report. This is a SEPARATE pass from Edges.tsx — cycle pairs
 * are NOT topology edges. Draws only when `overlayOn === true`.
 *
 * Position resolution reuses the exact same interpolation path as Edges.tsx:
 *   useInterpolatedFrame(timeline, frame) → interp.nodes → Map<id, Vec3>
 * with an identical static-export fallback when no timeline is loaded.
 *
 * Safety: any pair whose endpoint id is absent from the current frame's
 * position map is silently skipped — no NaN, no crash.
 *
 * Focus: reads `focusedObstruction` from the store; when set, the focused
 * obstruction's lines+ring render at full opacity/width and all others are
 * dimmed. When null, all render uniformly.
 *
 * Obstruction key scheme (consistent with RightRail.tsx `obstructionKey`):
 *   key = ob.claim_ids[0] if non-empty, else String(index).
 */

import { useMemo, useRef } from 'react';
import { Billboard, Line } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { COLOR } from '@/config/theme';
import { useViewer } from '@/store';
import { useInterpolatedFrame } from '@/lib/useInterpolatedFrame';
import { staticInterpNode, type InterpNode } from '@/lib/interpolate';
import type { Vec3 } from '@/lib/topology';

// ── constants ──────────────────────────────────────────────────────────────

/** Rose — defeat / H¹ accent; mirrors EDGE_COLOR for the defeat family. */
const ROSE = COLOR.accent.rose; // '#BE123C'

/** Cycle-edge line width — bold to stand out from the topology edges (w=1). */
const CYCLE_LINE_WIDTH = 2.5;
const CYCLE_LINE_WIDTH_FOCUSED = 4.0;

/** Pulse: full period in seconds. */
const PULSE_PERIOD = 1.8;

/**
 * Outline ring sits between the hover ring (r·1.7) and the FDR ring (r·2.25),
 * so obstruction membership is visually distinct from both.
 */
const BASE_RADIUS = 0.28;
const OBSTRUCTION_RING_FACTOR = 1.95;
const RING_SEGMENTS = 48;

// Opacity levels for focus dimming.
const OPACITY_FOCUSED_LINE = 0.95;
const OPACITY_DIMMED_LINE = 0.18;
const OPACITY_FOCUSED_RING = 0.85;
const OPACITY_DIMMED_RING = 0.18;

// ── helpers ────────────────────────────────────────────────────────────────

function ringPoints(radius: number): [number, number, number][] {
  const pts: [number, number, number][] = [];
  for (let i = 0; i <= RING_SEGMENTS; i++) {
    const a = (i / RING_SEGMENTS) * Math.PI * 2;
    pts.push([Math.cos(a) * radius, Math.sin(a) * radius, 0]);
  }
  return pts;
}

/** Obstruction key — must match `obstructionKey` in RightRail.tsx. */
function obKey(ob: { claim_ids: string[] }, index: number): string {
  return ob.claim_ids.length > 0 ? ob.claim_ids[0] : String(index);
}

// ── sub-components ─────────────────────────────────────────────────────────

/**
 * Single rose ring rendered as a Billboard around a node, indicating it is a
 * member of at least one H¹ obstruction cycle. Static opacity.
 */
function ObstructionRing({
  position,
  ringR,
  opacity,
}: {
  position: Vec3;
  ringR: number;
  opacity: number;
}) {
  const ring = useMemo(() => ringPoints(ringR), [ringR]);

  return (
    <group position={position}>
      <Billboard>
        <Line
          points={ring}
          color={ROSE}
          lineWidth={1.5}
          transparent
          opacity={opacity}
          dashed
          dashSize={0.07}
          gapSize={0.05}
        />
      </Billboard>
    </group>
  );
}

/**
 * Single animated obstruction edge between two 3D positions.
 * Opacity pulses sinusoidally; phase offset staggers multiple obstructions.
 * When focused, renders brighter + wider; when dimmed, low opacity.
 */
function ObstructionLine({
  a,
  b,
  phaseOffset,
  focused,
  dimmed,
}: {
  a: Vec3;
  b: Vec3;
  phaseOffset: number;
  focused: boolean;
  dimmed: boolean;
}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const lineRef = useRef<any>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    let opacity: number;
    if (dimmed) {
      opacity = OPACITY_DIMMED_LINE;
    } else if (focused) {
      // Focused: pulse between 0.80 and 1.0 for extra emphasis.
      const raw = Math.sin(((t + phaseOffset) / PULSE_PERIOD) * Math.PI * 2);
      opacity = 0.80 + (raw * 0.5 + 0.5) * 0.20;
    } else {
      // Uniform (no focus): original pulse range [0.40, 0.95].
      const raw = Math.sin(((t + phaseOffset) / PULSE_PERIOD) * Math.PI * 2);
      opacity = 0.4 + (raw * 0.5 + 0.5) * 0.55;
    }
    if (lineRef.current?.material) {
      lineRef.current.material.opacity = opacity;
    }
  });

  return (
    <Line
      ref={lineRef}
      points={[a, b]}
      color={ROSE}
      lineWidth={focused ? CYCLE_LINE_WIDTH_FOCUSED : CYCLE_LINE_WIDTH}
      transparent
      opacity={focused ? OPACITY_FOCUSED_LINE : dimmed ? OPACITY_DIMMED_LINE : 0.72}
    />
  );
}

// ── main component ─────────────────────────────────────────────────────────

export default function Obstructions() {
  const overlayOn = useViewer((s) => s.overlayOn);
  const obstructions = useViewer((s) => s.obstructions);
  const focusedObstruction = useViewer((s) => s.focusedObstruction);
  const data = useViewer((s) => s.data);
  const timeline = useViewer((s) => s.timeline);
  const frame = useViewer((s) => s.frame);

  const interp = useInterpolatedFrame(timeline, frame);

  // Resolve node positions — identical pattern to Edges.tsx / Nodes.tsx.
  // ALL hooks must be called unconditionally (before any early return).
  const positions = useMemo(() => {
    const map = new Map<string, Vec3>();
    let nodes: InterpNode[] = [];

    if (interp) {
      nodes = interp.nodes;
    } else if (data) {
      nodes = data.nodes.map(staticInterpNode);
    }

    for (const n of nodes) map.set(n.id, n.position);
    return map;
  }, [interp, data]);

  // Collect member node ids per obstruction key — for per-obstruction ring opacity.
  const membersByKey = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (let oi = 0; oi < obstructions.length; oi++) {
      const ob = obstructions[oi];
      const key = obKey(ob, oi);
      map.set(key, new Set(ob.claim_ids));
    }
    return map;
  }, [obstructions]);

  // Collect all unique member node ids — for placing rings.
  const memberIds = useMemo(() => {
    const ids = new Set<string>();
    for (const ob of obstructions) {
      for (const id of ob.claim_ids) ids.add(id);
    }
    return ids;
  }, [obstructions]);

  // Gate: render nothing when overlay is off or there are no obstructions.
  // Early return AFTER all hooks have been called.
  if (!overlayOn || obstructions.length === 0) return null;

  const ringR = BASE_RADIUS * OBSTRUCTION_RING_FACTOR;
  const hasFocus = focusedObstruction !== null;

  // Phase-stagger obstructions so they don't all pulse in lockstep.
  const phaseStep = PULSE_PERIOD / Math.max(obstructions.length, 1);

  // Determine which node ids belong to the focused obstruction (for ring emphasis).
  const focusedMemberIds: Set<string> =
    hasFocus && focusedObstruction !== null
      ? (membersByKey.get(focusedObstruction) ?? new Set())
      : new Set();

  return (
    <group>
      {/* ── Cycle edges ─────────────────────────────────────────────────── */}
      {obstructions.flatMap((ob, oi) => {
        const key = obKey(ob, oi);
        const isFocused = hasFocus && key === focusedObstruction;
        const isDimmed = hasFocus && !isFocused;
        return ob.edges.map(([srcId, tgtId], ei) => {
          const a = positions.get(srcId);
          const b = positions.get(tgtId);
          // Skip any pair whose endpoint is not in the current frame — no NaN.
          if (!a || !b) return null;
          return (
            <ObstructionLine
              key={`ob-${oi}-edge-${ei}`}
              a={a}
              b={b}
              phaseOffset={oi * phaseStep}
              focused={isFocused}
              dimmed={isDimmed}
            />
          );
        });
      })}

      {/* ── Member-node outline rings ────────────────────────────────────── */}
      {Array.from(memberIds).map((id) => {
        const pos = positions.get(id);
        // Skip if node not in current frame.
        if (!pos) return null;
        const isFocusedMember = hasFocus && focusedMemberIds.has(id);
        const isDimmedMember = hasFocus && !isFocusedMember;
        return (
          <ObstructionRing
            key={`ob-ring-${id}`}
            position={pos}
            ringR={ringR}
            opacity={
              !hasFocus
                ? 0.65
                : isFocusedMember
                  ? OPACITY_FOCUSED_RING
                  : OPACITY_DIMMED_RING
            }
          />
        );
      })}
    </group>
  );
}
