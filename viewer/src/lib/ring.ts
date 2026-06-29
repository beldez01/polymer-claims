/** Shared ring geometry for the scene (node hover/FDR rings + obstruction outline rings). */

/** Base node radius; ring radii are computed as multiples of this. */
export const BASE_RADIUS = 0.28;

/** Segments per ring loop — higher = smoother circle. */
export const RING_SEGMENTS = 48;

/** A closed circle of `RING_SEGMENTS` points at the given radius, in the z=0 plane. */
export function ringPoints(radius: number): [number, number, number][] {
  const pts: [number, number, number][] = [];
  for (let i = 0; i <= RING_SEGMENTS; i++) {
    const a = (i / RING_SEGMENTS) * Math.PI * 2;
    pts.push([Math.cos(a) * radius, Math.sin(a) * radius, 0]);
  }
  return pts;
}
