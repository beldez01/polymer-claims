/** Shared ring geometry for the scene (node hover/FDR rings + obstruction outline rings). */

/**
 * Base node radius; every ring/halo/label offset is a multiple of this, so it sets the whole
 * composition's scale. Tuned for the normalized signed-Laplacian eigenmap, whose extent is ~[-1, 1]
 * (≈2 units across): a refined instrument-mark dot (~7% of span), not a force-layout marble.
 */
export const BASE_RADIUS = 0.07;

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
