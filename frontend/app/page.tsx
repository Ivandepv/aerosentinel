'use client';

import dynamic from 'next/dynamic';
import { useLiveAircraft } from '@/hooks/useLiveAircraft';
import StatsBar from '@/components/StatsBar';
import FlightPanel from '@/components/FlightPanel';
import AircraftTable from '@/components/AircraftTable';
import AnomalyLog from '@/components/AnomalyLog';
import AnomalyBanner from '@/components/AnomalyBanner';

const MapClient = dynamic(() => import('@/components/Map/MapClient'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center dot-grid" style={{ background: '#050d1f', color: 'rgba(34,211,238,0.25)', fontSize: 12, letterSpacing: '0.1em' }}>
      LOADING MAP…
    </div>
  ),
});

/* Shared panel style helpers */
const GLASS: React.CSSProperties = {
  background: 'rgba(6, 12, 36, 0.88)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
};

function SectionHeader({ label, color = '#22d3ee' }: { label: string; color?: string }) {
  return (
    <div style={{
      color: `${color}70`,
      fontSize: 9,
      fontWeight: 700,
      letterSpacing: '0.12em',
      padding: '7px 12px 6px',
      borderBottom: `1px solid ${color}18`,
      background: `linear-gradient(90deg, ${color}08, transparent)`,
      borderLeft: `2px solid ${color}50`,
    }}>
      {label}
    </div>
  );
}

export default function Home() {
  useLiveAircraft();

  return (
    /* Outer wrapper: deep navy dot-grid background */
    <div
      className="flex flex-col h-screen overflow-hidden dot-grid"
      style={{ background: 'linear-gradient(135deg, #050b1f 0%, #080f28 50%, #060d22 100%)' }}
    >
      <StatsBar />
      <AnomalyBanner />

      {/* 3-column body */}
      <div className="flex flex-1 overflow-hidden" style={{ gap: 1, padding: 6, paddingTop: 4 }}>

        {/* ── Left: Flight Details ────────────────────────────── */}
        <div
          className="flex flex-col shrink-0 overflow-hidden rounded-lg"
          style={{
            width: 218,
            ...GLASS,
            border: '1px solid rgba(34,211,238,0.12)',
            boxShadow: '0 0 0 1px rgba(34,211,238,0.04), 0 4px 24px rgba(0,0,0,0.5)',
          }}
        >
          <SectionHeader label="FLIGHT DETAILS" color="#22d3ee" />
          <div className="flex-1 overflow-hidden">
            <FlightPanel />
          </div>
        </div>

        {/* ── Center: Map ─────────────────────────────────────── */}
        <div
          className="flex-1 relative overflow-hidden rounded-lg"
          style={{
            border: '1px solid rgba(34,211,238,0.1)',
            boxShadow: '0 0 0 1px rgba(34,211,238,0.03), 0 4px 24px rgba(0,0,0,0.5)',
          }}
        >
          <MapClient />
        </div>

        {/* ── Right: Table + Log ──────────────────────────────── */}
        <div
          className="flex flex-col shrink-0 overflow-hidden rounded-lg"
          style={{
            width: 332,
            ...GLASS,
            border: '1px solid rgba(249,115,22,0.12)',
            boxShadow: '0 0 0 1px rgba(249,115,22,0.04), 0 4px 24px rgba(0,0,0,0.5)',
          }}
        >
          {/* Aircraft table — 62% */}
          <div className="flex flex-col overflow-hidden" style={{ flex: '0 0 62%', borderBottom: '1px solid rgba(249,115,22,0.1)' }}>
            <SectionHeader label="LIVE AIRCRAFT" color="#f97316" />
            <div className="flex-1 overflow-hidden">
              <AircraftTable />
            </div>
          </div>

          {/* Anomaly log — 38% */}
          <div className="flex flex-col flex-1 overflow-hidden">
            <SectionHeader label="ANOMALY LOG" color="#ef4444" />
            <div className="flex-1 overflow-hidden">
              <AnomalyLog />
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
