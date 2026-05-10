'use client';

import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useAircraftStore } from '@/store/aircraft';
import { altitudeColor } from '@/lib/altitude';
import AltitudeColorBar from './AltitudeColorBar';

const RCNN: [number, number] = [22.9508, 120.2061];

const airportIcon = L.divIcon({
  html: `<div style="
    width:28px;height:28px;border-radius:50%;
    background:#f9731620;border:2px solid #f97316;
    display:flex;align-items:center;justify-content:center;
    font-size:14px;
  ">🛬</div>`,
  className: '',
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

function makeIcon(track: number, alt: number | null, isAnomaly: boolean): L.DivIcon {
  const color = isAnomaly ? '#ef4444' : altitudeColor(alt);
  const ring = isAnomaly ? 'anomaly-ring' : '';

  const html = `
    <div class="${ring}" style="
      width:30px;height:30px;border-radius:50%;
      background:${color}22;
      border:2px solid ${color};
      display:flex;align-items:center;justify-content:center;
      box-shadow:0 0 6px ${color}88;
    ">
      <div style="transform:rotate(${isAnomaly ? 0 : track}deg);font-size:16px;line-height:1">✈️</div>
    </div>`;

  return L.divIcon({ html, className: '', iconSize: [30, 30], iconAnchor: [15, 15] });
}

export default function MapClient() {
  const aircraft   = useAircraftStore((s) => s.aircraft);
  const trails     = useAircraftStore((s) => s.trails);
  const selectAc   = useAircraftStore((s) => s.selectAircraft);
  const selectedId = useAircraftStore((s) => s.selected);

  return (
    <div className="relative w-full h-full">
      <MapContainer center={RCNN} zoom={10} style={{ width: '100%', height: '100%' }} className="z-0">
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          maxZoom={19}
        />

        {/* RCNN airport */}
        <Marker position={RCNN} icon={airportIcon}>
          <Popup>
            <strong>Tainan Airport (RCNN)</strong><br />
            22.9508°N · 120.2061°E
          </Popup>
        </Marker>

        {/* Trails */}
        {aircraft.map((ac) => {
          const trail = trails[ac.icao24];
          if (!trail || trail.length < 2) return null;
          const isSelected = ac.icao24 === selectedId;
          return (
            <Polyline
              key={`t-${ac.icao24}`}
              positions={trail as [number, number][]}
              color={ac.is_anomaly ? '#ef4444' : altitudeColor(ac.altitude_ft)}
              weight={isSelected ? 3 : 1.5}
              opacity={isSelected ? 0.9 : 0.5}
            />
          );
        })}

        {/* Aircraft markers */}
        {aircraft.map((ac) => {
          if (ac.latitude == null || ac.longitude == null) return null;
          return (
            <Marker
              key={`m-${ac.icao24}`}
              position={[ac.latitude, ac.longitude]}
              icon={makeIcon(ac.track ?? 0, ac.altitude_ft, ac.is_anomaly)}
              eventHandlers={{ click: () => selectAc(ac.icao24) }}
            >
              <Popup>
                <div>
                  <div style={{ color: '#f97316', fontWeight: 700, marginBottom: 4 }}>
                    {ac.callsign || ac.icao24}
                  </div>
                  <div>ICAO: {ac.icao24}</div>
                  <div>Alt:   {ac.altitude_ft?.toLocaleString()} ft</div>
                  <div>Speed: {ac.speed_kt} kt</div>
                  <div>Track: {ac.track}°</div>
                  {ac.is_anomaly && (
                    <div style={{ color: '#ef4444', marginTop: 4, fontWeight: 600 }}>
                      ⚠ {ac.anomaly_reason}
                    </div>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      <AltitudeColorBar />
    </div>
  );
}
