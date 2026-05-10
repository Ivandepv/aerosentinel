import { create } from 'zustand';
import { Aircraft, AnomalyAlert } from '@/types';

const MAX_TRAIL = 20;
const MAX_ALT_HISTORY = 150;
const MAX_ANOMALY_LOG = 50;

interface AircraftState {
  aircraft: Aircraft[];
  trails: Record<string, [number, number][]>;
  altHistory: Record<string, { t: string; alt: number }[]>;
  selected: string | null;
  anomalies: AnomalyAlert[];
  connected: boolean;

  setAircraft: (aircraft: Aircraft[]) => void;
  addAnomaly: (alert: AnomalyAlert) => void;
  selectAircraft: (icao24: string | null) => void;
  setConnected: (v: boolean) => void;
}

export const useAircraftStore = create<AircraftState>((set) => ({
  aircraft: [],
  trails: {},
  altHistory: {},
  selected: null,
  anomalies: [],
  connected: false,

  setAircraft: (aircraft) =>
    set((state) => {
      const trails = { ...state.trails };
      const altHistory = { ...state.altHistory };

      for (const ac of aircraft) {
        if (ac.latitude != null && ac.longitude != null) {
          const prev = trails[ac.icao24] ?? [];
          trails[ac.icao24] = [
            ...prev.slice(-(MAX_TRAIL - 1)),
            [ac.latitude, ac.longitude],
          ];
        }
        if (ac.altitude_ft != null) {
          const prev = altHistory[ac.icao24] ?? [];
          altHistory[ac.icao24] = [
            ...prev.slice(-(MAX_ALT_HISTORY - 1)),
            { t: ac.timestamp, alt: ac.altitude_ft },
          ];
        }
      }

      return { aircraft, trails, altHistory };
    }),

  addAnomaly: (alert) =>
    set((state) => ({
      anomalies: [alert, ...state.anomalies].slice(0, MAX_ANOMALY_LOG),
    })),

  selectAircraft: (selected) => set({ selected }),
  setConnected: (connected) => set({ connected }),
}));
