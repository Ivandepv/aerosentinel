'use client';

import { ALT_SCALE } from '@/lib/altitude';

export default function AltitudeColorBar() {
  const gradient = ALT_SCALE.map((s) => s.color).join(', ');

  return (
    <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-[1000] pointer-events-none">
      <div
        className="rounded overflow-hidden"
        style={{
          width: 220,
          height: 10,
          background: `linear-gradient(to right, ${gradient})`,
          boxShadow: '0 0 8px rgba(0,0,0,0.8)',
        }}
      />
      <div className="flex justify-between mt-0.5 px-0.5">
        {ALT_SCALE.map((s) => (
          <span key={s.label} style={{ color: s.color, fontSize: 9, fontFamily: 'monospace' }}>
            {s.label}
          </span>
        ))}
      </div>
      <div className="text-center mt-0.5" style={{ color: '#55556a', fontSize: 9, fontFamily: 'monospace' }}>
        altitude (ft)
      </div>
    </div>
  );
}
