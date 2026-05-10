import time
from fastapi import APIRouter, Depends
from typing import List
import aiosqlite
from database import get_db
from schemas import AnomalyOut, StatsOut

router = APIRouter(prefix="/api", tags=["anomalies"])

_start_time = time.time()


@router.get("/anomalies", response_model=List[AnomalyOut])
async def get_anomalies(db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("""
        SELECT id, flight_id, detected_at, icao24, callsign, reason, screenshot_path, notified
        FROM anomalies
        WHERE detected_at >= datetime('now', '-24 hours')
        ORDER BY detected_at DESC
    """)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/stats", response_model=StatsOut)
async def get_stats(db: aiosqlite.Connection = Depends(get_db)):
    cur = await db.execute("""
        SELECT COUNT(DISTINCT icao24) FROM flights
        WHERE timestamp >= datetime('now', '-30 seconds')
    """)
    row = await cur.fetchone()
    aircraft_count = row[0] if row else 0

    cur = await db.execute("""
        SELECT COUNT(*) FROM anomalies
        WHERE detected_at >= datetime('now', '-24 hours')
    """)
    row = await cur.fetchone()
    anomaly_count = row[0] if row else 0

    cur = await db.execute("""
        SELECT COUNT(*) FROM flights
        WHERE timestamp >= datetime('now', '-24 hours')
    """)
    row = await cur.fetchone()
    total_24h = row[0] if row else 0

    rate = anomaly_count / total_24h if total_24h > 0 else 0.0

    return StatsOut(
        aircraft_count=aircraft_count,
        anomaly_count_24h=anomaly_count,
        anomaly_rate_24h=round(rate, 4),
        uptime_seconds=round(time.time() - _start_time, 1),
    )
