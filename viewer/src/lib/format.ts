/** zero-pad a frame index to a stable 2-digit mono width. */
export function pad(n: number): string {
  return String(n).padStart(2, '0');
}
