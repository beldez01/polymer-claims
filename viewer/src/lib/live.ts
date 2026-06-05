import type { TimelineFrame, TopologyTimeline } from '@/lib/timeline';

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

/** strip a trailing slash so `${base}/stream` is well-formed. */
function normalize(url: string): string {
  return url.replace(/\/+$/, '');
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
