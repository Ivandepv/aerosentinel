'use client';

import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { useAircraftStore } from '@/store/aircraft';
import { AnomalyAlert } from '@/types';

export default function AnomalyBanner() {
  const anomalies = useAircraftStore((s) => s.anomalies);
  const [visible, setVisible]   = useState(false);
  const [current, setCurrent]   = useState<AnomalyAlert | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (anomalies.length === 0) return;
    const latest = anomalies[0];
    if (current?.timestamp === latest.timestamp && current?.icao24 === latest.icao24) return;
    setCurrent(latest);
    setVisible(true);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setVisible(false), 8000);
  }, [anomalies]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!visible || !current) return null;

  return (
    <div className="fixed top-12 left-1/2 z-[9999] animate-slide-down" style={{ pointerEvents: 'auto' }}>
      <div
        className="flex items-center gap-3 px-4 py-2.5 rounded-lg"
        style={{
          background: 'linear-gradient(135deg, rgba(30,6,6,0.97), rgba(20,5,10,0.97))',
          border: '1px solid rgba(239,68,68,0.5)',
          boxShadow: '0 0 0 1px rgba(239,68,68,0.1), 0 0 30px rgba(239,68,68,0.25), 0 8px 32px rgba(0,0,0,0.7)',
          backdropFilter: 'blur(16px)',
          minWidth: 360,
        }}
      >
        <span className="animate-pulse shrink-0" style={{ fontSize: 20 }}>🔴</span>
        <div className="flex-1 min-w-0">
          <div style={{
            background: 'linear-gradient(90deg, #ef4444, #f97316)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            backgroundClip: 'text', fontWeight: 800, fontSize: 11, letterSpacing: '0.12em',
          }}>
            ANOMALY DETECTED
          </div>
          <div style={{ color: '#fca5a5', fontSize: 12, fontFamily: 'monospace', marginTop: 1 }}>
            <span style={{ color: '#f97316', fontWeight: 700 }}>{current.callsign || current.icao24}</span>
            {' · '}{current.reason}
            {current.altitude_ft != null && ` · ${current.altitude_ft.toLocaleString()} ft`}
            {current.speed_kt != null && ` · ${current.speed_kt} kt`}
          </div>
        </div>
        <button onClick={() => setVisible(false)} style={{ color: 'rgba(239,68,68,0.4)' }} className="hover:text-red-400 transition-colors shrink-0">
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
