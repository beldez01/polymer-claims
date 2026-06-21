import type { TimelineFrame, TopologyTimeline } from '@/lib/timeline';
import type { ConsistencyReport } from './topology';

export interface LiveCallbacks {
  /** the accumulated timeline fetched once on connect (late-joiner catch-up) */
  onTimeline: (timeline: TopologyTimeline) => void;
  /** a single frame pushed from the SSE stream */
  onFrame: (frame: TimelineFrame) => void;
  /** connection status changed (open → true, error/close → false) */
  onStatus: (connected: boolean) => void;
}

export interface LiveHandle {
  disconnect: () => void;
}

export type ConsistencyResponse =
  | { available: false }
  | ({ available: true } & ConsistencyReport);

export async function fetchConsistency(baseUrl: string): Promise<ConsistencyResponse> {
  const res = await fetch(baseUrl.replace(/\/$/, '') + '/consistency');
  if (!res.ok) return { available: false };
  return (await res.json()) as ConsistencyResponse;
}

/** strip a trailing slash so `${base}/stream` is well-formed. */
function normalize(url: string): string {
  return url.replace(/\/+$/, '');
}

/**
 * Full claim detail served by `GET {liveUrl}/claim/{id}`. Mirrors the node's
 * serialized claim record — nullable fields stay null rather than absent.
 */
export interface ClaimDetail {
  id: string;
  title: string;
  status: string;
  pattern_id: string;
  subject_term: string | null;
  plan: { impl: string; value?: number } | null;
  criterion: { comparator: string; threshold: number | null; tolerance: number | null } | null;
  criterion_satisfied: boolean | null;
  strength: number[] | null;
  provenance: { generated_by: string; agent_id: string | null; method: string | null } | null;
  rationale: string | null;
  rejection_reason: string | null;
}

/**
 * Fetch one claim's detail from a connected node. Returns the parsed record on
 * 2xx, or null on a non-OK response or any thrown error — never throws, so the
 * rail can fall back to the thin static view.
 */
export async function fetchClaimDetail(
  liveUrl: string,
  id: string,
): Promise<ClaimDetail | null> {
  const base = normalize(liveUrl);
  try {
    const res = await fetch(`${base}/claim/${encodeURIComponent(id)}`);
    if (!res.ok) return null;
    return (await res.json()) as ClaimDetail;
  } catch {
    return null;
  }
}

/**
 * Connect to a running `polymer-claims serve` node: seed from /timeline, then
 * subscribe to /stream (named `frame` events). EventSource auto-reconnects on
 * drop. Returns a handle whose disconnect() closes the stream.
 */
export function connectLive(url: string, cb: LiveCallbacks): LiveHandle {
  const base = normalize(url);
  let closed = false;

  // 1) seed the accumulated frames (best-effort; the stream still works if this fails)
  fetch(`${base}/timeline`)
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`timeline ${r.status}`))))
    .then((tl: TopologyTimeline) => {
      if (!closed) cb.onTimeline(tl);
    })
    .catch(() => {
      /* ignore — the SSE stream's on-connect frame will still populate the view */
    });

  // 2) open the SSE stream
  const es = new EventSource(`${base}/stream`);
  es.addEventListener('frame', (ev: MessageEvent) => {
    if (closed) return;
    try {
      cb.onFrame(JSON.parse(ev.data) as TimelineFrame);
    } catch {
      /* skip a malformed frame rather than tear down the stream */
    }
  });
  es.onopen = () => {
    if (!closed) cb.onStatus(true);
  };
  es.onerror = () => {
    // EventSource auto-reconnects; surface a transient disconnect
    if (!closed) cb.onStatus(false);
  };

  return {
    disconnect() {
      closed = true;
      es.close();
      cb.onStatus(false);
    },
  };
}
