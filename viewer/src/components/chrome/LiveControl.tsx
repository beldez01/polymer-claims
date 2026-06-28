'use client';

import { useState } from 'react';
import { COLOR, FONT_FAMILY_MONO } from '@/config/theme';
import { pad } from '@/lib/format';
import { useViewer } from '@/store';

/**
 * Live-node control — an inline D2 instrument cluster that lives in the header
 * bar (right-aligned). Owns the node URL input, Connect/Disconnect, the ● LIVE
 * indicator and a mono status readout. Matte, hairline, no glow.
 */
export default function LiveControl() {
  const connected = useViewer((s) => s.connected);
  const following = useViewer((s) => s.following);
  const frame = useViewer((s) => s.frame);
  const liveUrl = useViewer((s) => s.liveUrl);
  const connectLive = useViewer((s) => s.connectLive);
  const disconnectLive = useViewer((s) => s.disconnectLive);
  const overlayOn = useViewer((s) => s.overlayOn);
  const setOverlayOn = useViewer((s) => s.setOverlayOn);

  const [url, setUrl] = useState('http://localhost:8000');

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        pointerEvents: 'auto',
      }}
    >
      {/* ● LIVE dot — only when connected. Filled = following, hollow = scrubbed back. */}
      {connected && (
        <span
          aria-label={following ? 'live' : 'live (scrubbed)'}
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: following ? COLOR.primary.base : 'transparent',
            border: `1.5px solid ${COLOR.primary.base}`,
            boxShadow: 'none',
            flexShrink: 0,
          }}
        />
      )}

      {!connected ? (
        <>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            aria-label="node url"
            className="mono"
            style={{
              fontFamily: FONT_FAMILY_MONO,
              fontSize: 11,
              color: COLOR.text.primary,
              background: COLOR.bg.white,
              border: `1px solid ${COLOR.border.strong}`,
              borderRadius: 2,
              padding: '2px 6px',
              width: 190,
            }}
          />
          <button
            onClick={() => connectLive(url)}
            className="mono"
            style={{
              fontFamily: FONT_FAMILY_MONO,
              fontSize: 10,
              color: COLOR.bg.white,
              background: COLOR.primary.base,
              border: `1px solid ${COLOR.primary.base}`,
              borderRadius: 2,
              padding: '1px 6px',
              cursor: 'pointer',
            }}
          >
            Connect
          </button>
          <span
            className="mono"
            style={{
              fontFamily: FONT_FAMILY_MONO,
              fontSize: 10,
              color: COLOR.text.muted,
            }}
          >
            disconnected
          </span>
        </>
      ) : (
        <>
          <span
            className="mono"
            style={{
              fontFamily: FONT_FAMILY_MONO,
              fontSize: 11,
              color: COLOR.text.secondary,
            }}
          >
            {liveUrl ?? url}
          </span>
          <span
            className="mono tabular"
            style={{
              fontFamily: FONT_FAMILY_MONO,
              fontSize: 10,
              color: COLOR.text.tertiary,
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            live · frame {pad(Math.round(frame))}
          </span>
          <button
            onClick={() => disconnectLive()}
            className="mono"
            style={{
              fontFamily: FONT_FAMILY_MONO,
              fontSize: 10,
              color: COLOR.text.secondary,
              background: 'transparent',
              border: `1px solid ${COLOR.border.strong}`,
              borderRadius: 2,
              padding: '1px 6px',
              cursor: 'pointer',
            }}
          >
            Disconnect
          </button>
          <button
            onClick={() => setOverlayOn(!overlayOn)}
            className="mono"
            aria-pressed={overlayOn}
            style={{
              fontFamily: FONT_FAMILY_MONO,
              fontSize: 10,
              color: overlayOn ? COLOR.bg.white : COLOR.text.secondary,
              background: overlayOn ? COLOR.primary.base : 'transparent',
              border: `1px solid ${overlayOn ? COLOR.primary.base : COLOR.border.strong}`,
              borderRadius: 2,
              padding: '1px 6px',
              cursor: 'pointer',
            }}
          >
            Consistency overlay
          </button>
        </>
      )}
    </div>
  );
}
