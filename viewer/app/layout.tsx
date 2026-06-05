import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

// next/font/google self-hosts the optimized fonts and exposes them as CSS
// variables on <html>. Any component using var(--font-inter) /
// var(--font-jetbrains-mono) reads the optimized family automatically.
const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
  weight: ['400', '500', '600', '700'],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-jetbrains-mono',
  weight: ['400', '500', '700'],
});

export const metadata: Metadata = {
  title: 'Claims Universe — Polymer Claims',
  description:
    'A metrological instrument for the Polymer Claims topology: status-colored nodes, defeat / equivalence / entails edges, and the strength 6-vector — measured, not glowing.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
