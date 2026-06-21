import { useEffect } from 'react';
import { useViewer } from '../store';   // match the store's hook export name

const N = 5;   // refetch at most every N followed frames

export function useConsistencySync(): void {
  const overlayOn = useViewer((s) => s.overlayOn);
  const latestCycle = useViewer((s) => s.timeline?.frames.at(-1)?.stats.cycle_index ?? -1);
  const lastFetched = useViewer((s) => s.lastConsistencyCycle);
  const inFlight = useViewer((s) => s.consistencyInFlight);
  const fetchConsistency = useViewer((s) => s.fetchConsistency);

  useEffect(() => {
    if (!overlayOn || inFlight) return;
    if (lastFetched < 0 || latestCycle - lastFetched >= N) {
      void fetchConsistency();
    }
  }, [overlayOn, latestCycle, lastFetched, inFlight, fetchConsistency]);
}
