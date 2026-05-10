from fastapi import APIRouter, Depends
from typing import List
import aiosqlite
from database import get_db
from schemas import AircraftOut

router = APIRouter(prefix="/api", tags=["aircraft"])


@router.get("/aircraft", response_model=List[AircraftOut])
async def get_live_aircraft(db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("""
        SELECT icao24, callsign, latitude, longitude, altitude_ft, speed_kt,
               vertical_rate, track, is_anomaly, anomaly_score, anomaly_reason, timestamp
        FROM flights
        WHERE timestamp >= datetime('now', '-30 seconds')
        GROUP BY icao24
        HAVING timestamp = MAX(timestamp)
        ORDER BY timestamp DESC
    """)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/aircraft/{icao24}", response_model=List[AircraftOut])
async def get_aircraft_history(icao24: str, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("""
        SELECT icao24, callsign, latitude, longitude, altitude_ft, speed_kt,
               vertical_rate, track, is_anomaly, anomaly_score, anomaly_reason, timestamp
        FROM flights
        WHERE icao24 = ? AND timestamp >= datetime('now', '-10 minutes')
        ORDER BY timestamp DESC
    """, (icao24,))
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
