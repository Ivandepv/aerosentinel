export interface Aircraft {
  icao24: string;
  callsign: string | null;
  latitude: number | null;
  longitude: number | null;
  altitude_ft: number | null;
  speed_kt: number | null;
  vertical_rate: number | null;
  track: number | null;
  is_anomaly: boolean;
  anomaly_score: number | null;
  anomaly_reason: string | null;
  timestamp: string;
}

export interface AnomalyAlert {
  type: 'anomaly_alert';
  timestamp: string;
  icao24: string;
  callsign: string | null;
  reason: string;
  altitude_ft: number | null;
  speed_kt: number | null;
  latitude: number | null;
  longitude: number | null;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
}
