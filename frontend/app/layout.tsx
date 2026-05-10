import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AeroSentinel',
  description: 'Autonomous Airspace Anomaly Detection — Tainan, Taiwan',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-900 text-white">{children}</body>
    </html>
  );
}
