import asyncio
import aiosqlite
import httpx
from datetime import datetime, timezone

from database import get_db_path
from inference import get_engine
from routes.websocket import live_manager, alert_manager

_SEVERITY = {
    "HIGH_SPEED_LOW_ALT":  "HIGH",
    "EXTREME_DESCENT":     "HIGH",
    "STALL_AT_ALTITUDE":   "HIGH",
    "HYPERSONIC_SPEED":    "HIGH",
    "EXTREME_CLIMB":       "MEDIUM",
    "ML_ISOLATION_FOREST": "MEDIUM",
}


async def _insert_flight(
    db: aiosqlite.Connection,
    ts: str, icao: str, callsign: str,
    alt: float, speed: float, vr: float,
    lat: float, lon: float, track: float,
    is_anomaly: bool, score: float, reason: str | None,
) -> int:
    cur = await db.execute(
        """INSERT INTO flights
           (timestamp, icao24, callsign, altitude_ft, speed_kt, vertical_rate,
            latitude, longitude, track, is_anomaly, anomaly_score, anomaly_reason)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (ts, icao, callsign, alt, speed, vr, lat, lon, track, int(is_anomaly), score, reason),
    )
    await db.commit()
    return cur.lastrowid


async def _insert_anomaly(
    db: aiosqlite.Connection,
    flight_id: int, ts: str,
    icao: str, callsign: str, reason: str,
) -> None:
    await db.execute(
        """INSERT INTO anomalies (flight_id, detected_at, icao24, callsign, reason)
           VALUES (?,?,?,?,?)""",
        (flight_id, ts, icao, callsign, reason),
    )
    await db.commit()


async def run_collector(readsb_url: str, poll_interval: int) -> None:
    engine = get_engine()
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                res = await client.get(readsb_url)
                aircraft_list: list[dict] = res.json().get("aircraft", [])
            except Exception as exc:
                print(f"[collector] readsb unavailable — {exc}")
                await asyncio.sleep(poll_interval)
                continue

            now = datetime.now(timezone.utc)
            ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            live_aircraft = []

            async with aiosqlite.connect(get_db_path()) as db:
                for ac in aircraft_list:
                    icao = ac.get("hex", "").strip()
                    callsign = (ac.get("flight") or "").strip()
                    alt = ac.get("alt_baro")
                    speed = ac.get("gs")
                    lat = ac.get("lat")
                    lon = ac.get("lon")
                    vr = float(ac.get("baro_rate") or 0.0)
                    track = float(ac.get("track") or 0.0)

                    if not (icao and alt and speed and lat and lon):
                        continue
                    if float(speed) < 30 or float(alt) <= 0:
                        continue

                    try:
                        alt, speed, lat, lon = float(alt), float(speed), float(lat), float(lon)
                        row = engine.build_features(icao, alt, speed, lat, lon, now)
                        is_anomaly, score, reason = engine.predict(row)
                    except Exception as exc:
                        print(f"[collector] inference error {icao}: {exc}")
                        continue

                    flight_id = await _insert_flight(
                        db, ts, icao, callsign, alt, speed, vr, lat, lon, track,
                        is_anomaly, score, reason,
                    )

                    if is_anomaly:
                        await _insert_anomaly(db, flight_id, ts, icao, callsign, reason or "UNKNOWN")
                        await alert_manager.broadcast({
                            "type":       "anomaly_alert",
                            "timestamp":  ts,
                            "icao24":     icao,
                            "callsign":   callsign,
                            "reason":     reason,
                            "altitude_ft": alt,
                            "speed_kt":   speed,
                            "latitude":   lat,
                            "longitude":  lon,
                            "severity":   _SEVERITY.get(reason or "", "MEDIUM"),
                        })

                    live_aircraft.append({
                        "icao24":        icao,
                        "callsign":      callsign,
                        "latitude":      lat,
                        "longitude":     lon,
                        "altitude_ft":   alt,
                        "speed_kt":      speed,
                        "vertical_rate": vr,
                        "track":         track,
                        "is_anomaly":    is_anomaly,
                        "anomaly_score": round(score, 4),
                        "anomaly_reason": reason,
                        "timestamp":     ts,
                    })

            if live_aircraft:
                await live_manager.broadcast({
                    "type":      "aircraft_update",
                    "timestamp": ts,
                    "aircraft":  live_aircraft,
                })

            await asyncio.sleep(poll_interval)
