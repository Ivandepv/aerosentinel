'use client';

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { X, Radar } from 'lucide-react';
import { useAircraftStore } from '@/store/aircraft';
import { altitudeColor } from '@/lib/altitude';

export default function FlightPanel() {
  const aircraft       = useAircraftStore((s) => s.aircraft);
  const selected       = useAircraftStore((s) => s.selected);
  const altHistory     = useAircraftStore((s) => s.altHistory);
  const selectAircraft = useAircraftStore((s) => s.selectAircraft);

  const ac      = aircraft.find((a) => a.icao24 === selected);
  const history = selected ? (altHistory[selected] ?? []) : [];

  if (!ac) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 px-4">
        <Radar size={28} strokeWidth={1.5} style={{ color: 'rgba(34,211,238,0.25)' }} />
        <p style={{ color: 'rgba(34,211,238,0.3)', fontSize: 11, textAlign: 'center', lineHeight: 1.5 }}>
          Click any aircraft<br />on the map or table
        </p>
      </div>
    );
  }

  const altColor   = ac.is_anomaly ? '#ef4444' : altitudeColor(ac.altitude_ft);
  const altPct     = Math.min(100, ((ac.altitude_ft ?? 0) / 45000) * 100);
  const chartData  = history.map((h) => ({
    t:   new Date(h.t).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }),
    alt: Math.round(h.alt),
  }));

  return (
    <div className="flex flex-col h-full overflow-hidden text-sm">

      {/* Aircraft ID header */}
      <div
        className="px-3 py-2.5 shrink-0 flex items-start justify-between"
        style={{ borderBottom: '1px solid rgba(34,211,238,0.1)' }}
      >
        <div>
          <div style={{
            background: 'linear-gradient(90deg, #f97316, #fbbf24)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            backgroundClip: 'text', fontWeight: 800, fontSize: 17, letterSpacing: '0.06em',
          }}>
            {ac.callsign || ac.icao24}
          </div>
          <div style={{ color: 'rgba(34,211,238,0.45)', fontSize: 10, fontFamily: 'monospace', marginTop: 1 }}>
            {ac.icao24}
          </div>
        </div>
        <button onClick={() => selectAircraft(null)}
          style={{ color: 'rgba(255,255,255,0.2)' }}
          className="hover:text-white transition-colors mt-0.5"
        >
          <X size={13} />
        </button>
      </div>

      {/* Anomaly badge */}
      {ac.is_anomaly && (
        <div
          className="mx-3 mt-2 px-2.5 py-1.5 rounded shrink-0 text-[11px] font-bold"
          style={{
            background: 'linear-gradient(90deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05))',
            border: '1px solid rgba(239,68,68,0.4)',
            color: '#fca5a5',
            boxShadow: '0 0 12px rgba(239,68,68,0.15)',
          }}
        >
          ⚠ {ac.anomaly_reason}
        </div>
      )}

      {/* Altitude progress bar */}
      <div className="mx-3 mt-2.5 shrink-0">
        <div className="flex justify-between mb-1" style={{ fontSize: 9, color: 'rgba(34,211,238,0.4)', letterSpacing: '0.06em' }}>
          <span>ALTITUDE</span>
          <span style={{ color: altColor, fontFamily: 'monospace' }}>{ac.altitude_ft?.toLocaleString() ?? '—'} ft</span>
        </div>
        <div style={{ height: 5, background: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{
            width: `${altPct}%`, height: '100%', borderRadius: 3,
            background: `linear-gradient(90deg, #ef4444, ${altColor})`,
            boxShadow: `0 0 6px ${altColor}`,
            transition: 'width 1s ease',
          }} />
        </div>
      </div>

      {/* Data rows */}
      <div className="flex-1 overflow-y-auto px-3 pt-2 pb-1 space-y-0.5">
        <DataRow label="Groundspeed"   value={`${ac.speed_kt ?? '—'} kt`}       color="#f97316" />
        <DataRow label="Vert rate"     value={vrLabel(ac.vertical_rate)}          color={vrColor(ac.vertical_rate)} />
        <DataRow label="Track"         value={`${ac.track ?? '—'}°`}              color="#a78bfa" />
        <DataRow label="Position"      value={`${ac.latitude?.toFixed(3) ?? '—'}, ${ac.longitude?.toFixed(3) ?? '—'}`} color="rgba(34,211,238,0.7)" small />
        <DataRow
          label="Anomaly score"
          value={ac.anomaly_score?.toFixed(4) ?? '—'}
          color={(ac.anomaly_score ?? 1) < 0 ? '#f87171' : '#34d399'}
        />
      </div>

      {/* Altitude chart */}
      {chartData.length > 2 && (
        <div
          className="px-2 pb-2 shrink-0"
          style={{ borderTop: '1px solid rgba(34,211,238,0.08)' }}
        >
          <div style={{ color: 'rgba(34,211,238,0.35)', fontSize: 9, letterSpacing: '0.08em', padding: '6px 4px 2px' }}>
            ALTITUDE HISTORY
          </div>
          <ResponsiveContainer width="100%" height={76}>
            <LineChart data={chartData} margin={{ top: 2, right: 4, bottom: 0, left: 0 }}>
              <XAxis dataKey="t" hide />
              <YAxis
                tick={{ fontSize: 9, fill: 'rgba(34,211,238,0.35)' }}
                width={32}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                contentStyle={{ background: 'rgba(8,16,40,0.95)', border: '1px solid rgba(34,211,238,0.2)', fontSize: 11, padding: '4px 8px' }}
                labelStyle={{ color: 'rgba(34,211,238,0.5)' }}
                formatter={(v: number) => [`${v.toLocaleString()} ft`, 'Alt']}
              />
              <Line type="monotone" dataKey="alt" stroke={altColor} dot={false} strokeWidth={2} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function DataRow({ label, value, color, small }: { label: string; value: string; color: string; small?: boolean }) {
  return (
    <div className="flex justify-between items-baseline py-1" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      <span style={{ color: 'rgba(148,163,184,0.5)', fontSize: 10, letterSpacing: '0.04em' }}>{label}</span>
      <span style={{ color, fontFamily: 'monospace', fontSize: small ? 10 : 12, fontWeight: 600 }}>{value}</span>
    </div>
  );
}

function vrLabel(vr: number | null): string {
  if (vr == null) return '—';
  return `${vr > 0 ? '+' : ''}${vr} ft/m`;
}

function vrColor(vr: number | null): string {
  if (vr == null) return '#94a3b8';
  if (vr < -500) return '#f87171';
  if (vr > 500)  return '#34d399';
  return '#94a3b8';
}
