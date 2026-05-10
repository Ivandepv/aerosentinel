from pydantic import BaseModel
from typing import Optional


class AircraftOut(BaseModel):
    icao24: str
    callsign: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_ft: Optional[float] = None
    speed_kt: Optional[float] = None
    vertical_rate: Optional[float] = None
    track: Optional[float] = None
    is_anomaly: bool
    anomaly_score: Optional[float] = None
    anomaly_reason: Optional[str] = None
    timestamp: str


class AnomalyOut(BaseModel):
    id: int
    flight_id: Optional[int] = None
    detected_at: str
    icao24: Optional[str] = None
    callsign: Optional[str] = None
    reason: Optional[str] = None
    screenshot_path: Optional[str] = None
    notified: bool


class StatsOut(BaseModel):
    aircraft_count: int
    anomaly_count_24h: int
    anomaly_rate_24h: float
    uptime_seconds: float
