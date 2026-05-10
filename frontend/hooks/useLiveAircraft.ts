'use client';

import { useEffect, useRef } from 'react';
import { useAircraftStore } from '@/store/aircraft';

const BASE = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000';

export function useLiveAircraft(): void {
  const setAircraft = useAircraftStore((s) => s.setAircraft);
  const addAnomaly = useAircraftStore((s) => s.addAnomaly);
  const setConnected = useAircraftStore((s) => s.setConnected);
  const liveRef = useRef<WebSocket | null>(null);
  const alertRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let liveTimer: ReturnType<typeof setTimeout>;
    let alertTimer: ReturnType<typeof setTimeout>;

    const connectLive = () => {
      const ws = new WebSocket(`${BASE}/ws/live`);
      liveRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        liveTimer = setTimeout(connectLive, 3000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'aircraft_update') setAircraft(msg.aircraft);
      };
    };

    const connectAlerts = () => {
      const ws = new WebSocket(`${BASE}/ws/alerts`);
      alertRef.current = ws;
      ws.onclose = () => { alertTimer = setTimeout(connectAlerts, 3000); };
      ws.onerror = () => ws.close();
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'anomaly_alert') addAnomaly(msg);
      };
    };

    connectLive();
    connectAlerts();

    return () => {
      clearTimeout(liveTimer);
      clearTimeout(alertTimer);
      liveRef.current?.close();
      alertRef.current?.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}
