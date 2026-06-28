'use client';

import { COLOR, FONT_FAMILY_MONO } from '@/config/theme';
import { pad } from '@/lib/format';
import { useViewer } from '@/store';

const SPEEDS = [0.5, 1, 2] as const;

export default function TransportBar() {
  const timeline = useViewer((s) => s.timeline);
  const playing = useViewer((s) => s.playing);
  const frame = useViewer((s) => s.frame);
  const speed = useViewer((s) => s.speed);
  const play = useViewer((s) => s.play);
  const pause = useViewer((s) => s.pause);
  const seek = useViewer((s) => s.seek);
  const setSpeed = useViewer((s) => s.setSpeed);
  const connected = useViewer((s) => s.connected);
  const following = useViewer((s) => s.following);
  const jumpToLive = useViewer((s) => s.jumpToLive);

  if (!timeline) return null;

  const last = timeline.frames.length - 1;
  const current = Math.round(frame);

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        bottom: 18,
        transform: 'translateX(-50%)',
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        backgroundColor: 'rgba(250,250,250,0.94)',
        border: `1px solid ${COLOR.border.default}`,
        borderRadius: 2,
        padding: '8px 14px',
        zIndex: 16,
        pointerEvents: 'auto',
      }}
    >
      {/* § marker */}
      <span
        className="section-marker"
        style={{
          fontFamily: FONT_FAMILY_MONO,
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: COLOR.text.tertiary,
        }}
      >
        § Run
      </span>

      {/* play / pause */}
      <button
        onClick={() => (playing ? pause() : play())}
        aria-label={playing ? 'pause' : 'play'}
        style={{
          width: 26,
          height: 22,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: playing ? COLOR.primary.base : 'transparent',
          border: `1px solid ${playing ? COLOR.primary.base : COLOR.border.strong}`,
          borderRadius: 2,
          cursor: 'pointer',
          padding: 0,
        }}
      >
        {playing ? (
          // pause — two hairline bars
          <span style={{ display: 'flex', gap: 3 }}>
            <span style={{ width: 2, height: 10, background: COLOR.bg.white }} />
            <span style={{ width: 2, height: 10, background: COLOR.bg.white }} />
          </span>
        ) : (
          // play — triangle in electric blue
          <span
            style={{
              width: 0,
              height: 0,
              borderTop: '5px solid transparent',
              borderBottom: '5px solid transparent',
              borderLeft: `8px solid ${COLOR.primary.base}`,
              marginLeft: 2,
            }}
          />
        )}
      </button>

      {/* scrub slider — hairline track, blue thumb (styled in globals.css) */}
      <input
        type="range"
        min={0}
        max={last}
        step={0.001}
        value={frame}
        onChange={(e) => {
          pause();
          seek(parseFloat(e.target.value));
        }}
        className="transport-scrub"
        style={{ width: 240 }}
        aria-label="scrub timeline"
      />

      {/* frame counter */}
      <span
        style={{
          fontFamily: FONT_FAMILY_MONO,
          fontSize: 11,
          color: COLOR.text.primary,
          fontVariantNumeric: 'tabular-nums',
          whiteSpace: 'nowrap',
        }}
        className="mono tabular"
      >
        frame {pad(current)} / {pad(last)}
      </span>

      {/* speed toggle */}
      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
        {SPEEDS.map((s) => {
          const active = speed === s;
          return (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              style={{
                fontFamily: FONT_FAMILY_MONO,
                fontSize: 10,
                fontVariantNumeric: 'tabular-nums',
                color: active ? COLOR.bg.white : COLOR.text.secondary,
                background: active ? COLOR.primary.base : 'transparent',
                border: `1px solid ${active ? COLOR.primary.base : COLOR.border.strong}`,
                borderRadius: 2,
                padding: '1px 6px',
                cursor: 'pointer',
              }}
              className="mono tabular"
            >
              {s}×
            </button>
          );
        })}
      </div>

      {/* jump-to-live — shown only when connected and scrubbed off the live edge */}
      {connected && !following && (
        <button
          onClick={() => jumpToLive()}
          aria-label="jump to live"
          style={{
            fontFamily: FONT_FAMILY_MONO,
            fontSize: 10,
            fontVariantNumeric: 'tabular-nums',
            color: COLOR.bg.white,
            background: COLOR.primary.base,
            border: `1px solid ${COLOR.primary.base}`,
            borderRadius: 2,
            padding: '1px 6px',
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
          className="mono tabular"
        >
          ⇥ LIVE
        </button>
      )}
    </div>
  );
}
