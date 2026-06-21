'use client';

/**
 * EnergyHud — consistency overlay HUD.
 *
 * Renders only when `overlayOn === true` AND the current interpolated frame
 * carries a non-null `consistency` headline.  Shows:
 *   • live inconsistency_energy (coloured by tensionScale)
 *   • a sparkline of per-frame energy history
 *   • λ₂ (spectral_gap) from the pulled consistency report, when available
 *
 * Positioned top-right, inside the chrome z-stack, pointer-events: none so
 * it never blocks orbit controls.  Matches the D2 metrological aesthetic
 * (FONT_FAMILY_MONO, COLOR tokens, hairline borders — no glow, no neon).
 */

import { useMemo } from 'react';
import { useViewer } from '@/store';
import { useInterpolatedFrame } from '@/lib/useInterpolatedFrame';
import { COLOR, FONT_FAMILY_MONO, LAYOUT, tensionScale } from '@/config/theme';

// ── Sparkline ───────────────────────────────────────────────────────────────

/** Maximum recent frames to show in the sparkline. */
const SPARK_MAX = 40;

/** Width × height of the SVG sparkline canvas (px). */
const SPARK_W = 120;
const SPARK_H = 28;

function Sparkline({ values, accentColor }: { values: number[]; accentColor: string }) {
  if (values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * SPARK_W;
    const y = SPARK_H - ((v - min) / range) * (SPARK_H - 3) - 1;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const polyline = pts.join(' ');

  return (
    <svg
      width={SPARK_W}
      height={SPARK_H}
      viewBox={`0 0 ${SPARK_W} ${SPARK_H}`}
      style={{ display: 'block', overflow: 'visible' }}
    >
      {/* baseline */}
      <line
        x1={0}
        y1={SPARK_H - 1}
        x2={SPARK_W}
        y2={SPARK_H - 1}
        stroke={COLOR.border.default}
        strokeWidth={0.75}
      />
      {/* energy trace */}
      <polyline
        points={polyline}
        fill="none"
        stroke={accentColor}
        strokeWidth={1.25}
        strokeLinejoin="round"
        strokeLinecap="round"
        opacity={0.85}
      />
      {/* current-frame dot */}
      {pts.length > 0 && (
        <circle
          cx={parseFloat(pts[pts.length - 1].split(',')[0])}
          cy={parseFloat(pts[pts.length - 1].split(',')[1])}
          r={2}
          fill={accentColor}
        />
      )}
    </svg>
  );
}

// ── EnergyHud ───────────────────────────────────────────────────────────────

export default function EnergyHud() {
  const overlayOn        = useViewer((s) => s.overlayOn);
  const timeline         = useViewer((s) => s.timeline);
  const frame            = useViewer((s) => s.frame);
  const consistencyReport = useViewer((s) => s.consistencyReport);

  const interp = useInterpolatedFrame(timeline, frame);

  // Current-frame headline energy (live, every tick).
  const energy = interp?.consistency?.inconsistency_energy ?? null;

  // λ₂ from the pulled report (may lag a few frames; null until a report is fetched).
  const spectralGap = consistencyReport?.spectral_gap ?? null;

  // Sparkline history: walk the timeline frames and collect per-frame energies.
  const sparkValues = useMemo<number[]>(() => {
    if (!timeline) return [];
    const vals: number[] = [];
    for (const fr of timeline.frames) {
      const e = fr.topology.consistency?.inconsistency_energy;
      if (e !== null && e !== undefined) vals.push(e);
    }
    return vals.slice(-SPARK_MAX);
  }, [timeline]);

  // Hide when overlay is off OR no consistency on the current frame.
  if (!overlayOn || energy === null) return null;

  // Normalise energy to [0, 1] for the heat scale, using the sparkline range
  // as context.  When there's only one value, it maps to 0.
  const sparkMin = sparkValues.length > 0 ? Math.min(...sparkValues) : 0;
  const sparkMax = sparkValues.length > 0 ? Math.max(...sparkValues) : 1;
  const t01 = sparkMax > sparkMin ? (energy - sparkMin) / (sparkMax - sparkMin) : 0;
  const heatColor = tensionScale(t01);

  const fmtEnergy = energy.toFixed(4);
  const fmtLambda = spectralGap !== null ? spectralGap.toFixed(4) : null;

  return (
    <div
      style={{
        position: 'absolute',
        top: LAYOUT.headerHeight + 12,
        right: LAYOUT.inspectorWidth + 12,
        zIndex: 18,
        pointerEvents: 'none',
        // Panel shell — matches the chrome panels: light elevated bg, hairline border.
        backgroundColor: COLOR.bg.elevated,
        border: `1px solid ${COLOR.border.subtle}`,
        borderRadius: 2,
        padding: '10px 12px',
        minWidth: 152,
      }}
    >
      {/* §§ section marker */}
      <div
        style={{
          fontFamily: FONT_FAMILY_MONO,
          fontSize: 9,
          fontWeight: 500,
          letterSpacing: '0.10em',
          textTransform: 'uppercase',
          color: COLOR.text.faint,
          marginBottom: 6,
        }}
      >
        § Consistency Energy
      </div>

      {/* Live energy headline */}
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: 5,
          marginBottom: 6,
        }}
      >
        {/* coloured left-edge accent bar */}
        <span
          style={{
            width: 2,
            alignSelf: 'stretch',
            backgroundColor: heatColor,
            borderRadius: 1,
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontFamily: FONT_FAMILY_MONO,
            fontSize: 18,
            lineHeight: 1,
            fontVariantNumeric: 'tabular-nums',
            letterSpacing: '-0.02em',
            color: heatColor,
          }}
        >
          {fmtEnergy}
        </span>
      </div>

      {/* Sparkline */}
      <div style={{ marginBottom: fmtLambda !== null ? 8 : 0 }}>
        <Sparkline values={sparkValues} accentColor={heatColor} />
      </div>

      {/* λ₂ — shown only when the report has been fetched */}
      {fmtLambda !== null && (
        <div
          style={{
            borderTop: `1px solid ${COLOR.border.default}`,
            paddingTop: 6,
            marginTop: 4,
          }}
        >
          <div
            style={{
              fontFamily: FONT_FAMILY_MONO,
              fontSize: 9,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: COLOR.text.faint,
              marginBottom: 2,
            }}
          >
            λ₂ spectral gap
          </div>
          <div
            style={{
              fontFamily: FONT_FAMILY_MONO,
              fontSize: 12,
              fontVariantNumeric: 'tabular-nums',
              color: COLOR.text.secondary,
            }}
          >
            {fmtLambda}
          </div>
        </div>
      )}
    </div>
  );
}
