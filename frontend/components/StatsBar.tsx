'use client';

import { useAircraftStore } from '@/store/aircraft';

export default function StatsBar() {
  const aircraft  = useAircraftStore((s) => s.aircraft);
  const anomalies = useAircraftStore((s) => s.anomalies);
  const connected = useAircraftStore((s) => s.connected);
  const activeAnom = aircraft.filter((a) => a.is_anomaly).length;

  return (
    <header
      className="h-12 flex items-center px-5 gap-4 shrink-0 select-none"
      style={{
        background: 'linear-gradient(180deg, #080f28 0%, #060d20 100%)',
        borderBottom: '1px solid rgba(34,211,238,0.15)',
        boxShadow: '0 1px 0 rgba(34,211,238,0.05), 0 4px 16px rgba(0,0,0,0.4)',
      }}
    >
      {/* Gradient logo */}
      <span
        style={{
          background: 'linear-gradient(90deg, #a78bfa 0%, #22d3ee 50%, #f97316 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          fontWeight: 900,
          fontSize: 15,
          letterSpacing: '0.16em',
          marginRight: 8,
        }}
      >
        AEROSENTINEL
      </span>

      {/* Live pill */}
      <div
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-full"
        style={{
          background: connected ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
          border: `1px solid ${connected ? 'rgba(34,197,94,0.35)' : 'rgba(239,68,68,0.35)'}`,
        }}
      >
        <span
          className={connected ? 'animate-pulse' : ''}
          style={{
            display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
            background: connected ? '#22c55e' : '#ef4444',
            boxShadow: connected ? '0 0 6px #22c55e' : '0 0 6px #ef4444',
          }}
        />
        <span style={{ color: connected ? '#22c55e' : '#ef4444', fontSize: 11, fontWeight: 700, letterSpacing: '0.06em' }}>
          {connected ? 'LIVE' : 'OFFLINE'}
        </span>
      </div>

      <div style={{ width: 1, height: 18, background: 'rgba(34,211,238,0.12)' }} />

      {/* Stats chips */}
      <StatChip value={aircraft.length}  label="AIRCRAFT"  color="#22d3ee" />
      <StatChip
        value={activeAnom}
        label="ANOMALIES"
        color={activeAnom > 0 ? '#ef4444' : '#34d399'}
        glow={activeAnom > 0}
      />
      <StatChip value={anomalies.length} label="ALERTS TODAY" color="#f97316" />

      <div className="ml-auto" style={{ color: 'rgba(34,211,238,0.3)', fontSize: 10, fontFamily: 'monospace', letterSpacing: '0.04em' }}>
        22.9508°N · 120.2061°E · Tainan, Taiwan
      </div>
    </header>
  );
}

function StatChip({ value, label, color, glow }: {
  value: number; label: string; color: string; glow?: boolean;
}) {
  return (
    <div
      className="flex items-baseline gap-1.5 px-3 py-1 rounded"
      style={{
        background: `${color}12`,
        border: `1px solid ${color}30`,
        boxShadow: glow ? `0 0 12px ${color}40` : undefined,
      }}
    >
      <span style={{ color, fontWeight: 800, fontSize: 16, fontFamily: 'monospace', lineHeight: 1 }}>
        {value}
      </span>
      <span style={{ color: `${color}80`, fontSize: 9, letterSpacing: '0.08em', fontWeight: 600 }}>
        {label}
      </span>
    </div>
  );
}
