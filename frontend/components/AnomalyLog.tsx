'use client';

import { useAircraftStore } from '@/store/aircraft';

const SEV: Record<string, { color: string; bg: string }> = {
  HIGH:   { color: '#f87171', bg: 'rgba(239,68,68,0.08)' },
  MEDIUM: { color: '#fb923c', bg: 'rgba(249,115,22,0.08)' },
  LOW:    { color: '#38bdf8', bg: 'rgba(56,189,248,0.08)' },
};

export default function AnomalyLog() {
  const anomalies = useAircraftStore((s) => s.anomalies);

  if (anomalies.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p style={{ color: 'rgba(34,211,238,0.2)', fontSize: 11, textAlign: 'center' }}>
          No anomalies detected
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto h-full">
      {anomalies.map((a, i) => {
        const sev = SEV[a.severity] ?? SEV.MEDIUM;
        return (
          <div
            key={i}
            className="px-3 py-2"
            style={{
              background: sev.bg,
              borderBottom: '1px solid rgba(255,255,255,0.04)',
              borderLeft: `2px solid ${sev.color}`,
            }}
          >
            <div className="flex items-center gap-2">
              <span style={{ color: sev.color, fontSize: 9 }}>◆</span>
              <span style={{ color: '#f97316', fontWeight: 700, fontSize: 12, fontFamily: 'monospace' }}>
                {a.callsign || a.icao24}
              </span>
              <span className="ml-auto" style={{ color: 'rgba(148,163,184,0.4)', fontSize: 10, fontFamily: 'monospace' }}>
                {new Date(a.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
              </span>
            </div>
            <div style={{ color: sev.color, fontSize: 10, fontWeight: 600, paddingLeft: 15, marginTop: 1 }}>
              {a.reason}
            </div>
            {a.altitude_ft != null && (
              <div style={{ color: 'rgba(148,163,184,0.4)', fontSize: 10, fontFamily: 'monospace', paddingLeft: 15 }}>
                {a.altitude_ft.toLocaleString()} ft · {a.speed_kt} kt
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
