'use client';

import { useState } from 'react';
import { useAircraftStore } from '@/store/aircraft';
import { altitudeColor } from '@/lib/altitude';

type SortKey = 'callsign' | 'altitude_ft' | 'speed_kt' | 'anomaly_score';

const COLS: { label: string; key: SortKey }[] = [
  { label: 'CALLSIGN', key: 'callsign' },
  { label: 'ALT (ft)', key: 'altitude_ft' },
  { label: 'SPD (kt)', key: 'speed_kt' },
  { label: 'SCORE',    key: 'anomaly_score' },
];

export default function AircraftTable() {
  const aircraft       = useAircraftStore((s) => s.aircraft);
  const selected       = useAircraftStore((s) => s.selected);
  const selectAircraft = useAircraftStore((s) => s.selectAircraft);
  const [sortKey, setSortKey] = useState<SortKey>('altitude_ft');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const sorted = [...aircraft].sort((a, b) => {
    const av = (a[sortKey] as string | number | null) ?? '';
    const bv = (b[sortKey] as string | number | null) ?? '';
    const cmp = typeof av === 'string' ? (av as string).localeCompare(bv as string) : (av as number) - (bv as number);
    return sortDir === 'desc' ? -cmp : cmp;
  });

  const toggle = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    else { setSortKey(key); setSortDir('desc'); }
  };

  return (
    <div className="h-full overflow-y-auto">
      <table className="w-full border-collapse" style={{ fontSize: 11 }}>
        <thead style={{ position: 'sticky', top: 0, zIndex: 1 }}>
          <tr style={{
            background: 'rgba(5,10,30,0.95)',
            backdropFilter: 'blur(8px)',
            borderBottom: '1px solid rgba(34,211,238,0.12)',
          }}>
            <th className="px-2 py-2 text-left" style={{ color: 'rgba(34,211,238,0.4)', fontSize: 9, letterSpacing: '0.1em', fontWeight: 700 }}>
              HEX
            </th>
            {COLS.map(({ label, key }) => (
              <th
                key={key}
                onClick={() => toggle(key)}
                className="px-2 py-2 text-right cursor-pointer select-none transition-colors"
                style={{
                  color: sortKey === key ? '#22d3ee' : 'rgba(34,211,238,0.4)',
                  fontSize: 9, letterSpacing: '0.08em', fontWeight: 700,
                }}
              >
                {label}{sortKey === key ? (sortDir === 'desc' ? ' ▼' : ' ▲') : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((ac, i) => {
            const isSelected = ac.icao24 === selected;
            const altColor   = altitudeColor(ac.altitude_ft);
            const rowBg = isSelected
              ? 'rgba(249,115,22,0.12)'
              : ac.is_anomaly
              ? 'rgba(239,68,68,0.07)'
              : i % 2 === 0 ? 'rgba(34,211,238,0.02)' : 'transparent';

            return (
              <tr
                key={ac.icao24}
                onClick={() => selectAircraft(ac.icao24 === selected ? null : ac.icao24)}
                className="cursor-pointer transition-all"
                style={{
                  background: rowBg,
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                  borderLeft: isSelected ? '2px solid #f97316' : ac.is_anomaly ? '2px solid rgba(239,68,68,0.5)' : '2px solid transparent',
                  boxShadow: isSelected ? 'inset 0 0 20px rgba(249,115,22,0.05)' : ac.is_anomaly ? 'inset 0 0 16px rgba(239,68,68,0.05)' : undefined,
                }}
              >
                <td className="px-2 py-1.5" style={{ color: 'rgba(148,163,184,0.5)', fontFamily: 'monospace', fontSize: 10 }}>
                  {ac.icao24}
                </td>
                <td className="px-2 py-1.5 text-right" style={{ color: '#f97316', fontFamily: 'monospace', fontWeight: 700, fontSize: 11 }}>
                  {ac.callsign || <span style={{ color: 'rgba(148,163,184,0.3)' }}>—</span>}
                </td>
                <td className="px-2 py-1.5 text-right" style={{ color: altColor, fontFamily: 'monospace', fontWeight: 600 }}>
                  {ac.altitude_ft?.toLocaleString() ?? '—'}
                </td>
                <td className="px-2 py-1.5 text-right" style={{ color: '#fb923c', fontFamily: 'monospace' }}>
                  {ac.speed_kt ?? '—'}
                </td>
                <td
                  className="px-2 py-1.5 text-right"
                  style={{ color: (ac.anomaly_score ?? 1) < 0 ? '#f87171' : 'rgba(52,211,153,0.6)', fontFamily: 'monospace', fontSize: 10 }}
                >
                  {ac.anomaly_score?.toFixed(3) ?? '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
