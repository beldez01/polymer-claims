'use client';

import dynamic from 'next/dynamic';
import { COLOR, FONT_FAMILY_MONO } from '@/config/theme';
import Header from '@/components/chrome/Header';
import LegendRail from '@/components/chrome/LegendRail';
import RightRail from '@/components/chrome/RightRail';
import TransportBar from '@/components/chrome/TransportBar';
import EnergyHud from '@/components/chrome/EnergyHud';
import ReturnLink from '@/components/chrome/ReturnLink';

// The R3F scene is client-only (WebGL has no SSR). The loading fallback is the
// D2 mono register on the light canvas — no spinner, no glow.
const ClaimUniverse = dynamic(
  () => import('@/components/ClaimUniverse'),
  {
    ssr: false,
    loading: () => (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: COLOR.bg.primary,
          fontFamily: FONT_FAMILY_MONO,
          fontSize: 12,
          letterSpacing: '0.04em',
          color: COLOR.text.muted,
        }}
        className="mono tabular"
      >
        loading topology…
      </div>
    ),
  },
);

export default function Home() {
  return (
    <main
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: COLOR.bg.primary,
        overflow: 'hidden',
      }}
    >
      <ClaimUniverse />
      <Header />
      <LegendRail />
      <RightRail />
      {/* self-hides until a timeline is loaded */}
      <TransportBar />
      {/* self-hides when overlayOn=false or no consistency on current frame */}
      <EnergyHud />
      <ReturnLink />
    </main>
  );
}
