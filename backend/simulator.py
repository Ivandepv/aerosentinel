"""
AeroSentinel — ADS-B Simulator
Mimics readsb's  GET /data/aircraft.json  on port 30047.

Run alongside the backend to test all endpoints without SDR hardware:
    python simulator.py          # terminal 1
    uvicorn main:app --reload    # terminal 2

Aircraft included:
    EVA384  — normal cruise, 29 000 ft, 456 kt, southbound
    CAL102  — normal approach to RCNN, 3 500 ft, 200 kt
    MDA878  — normal climb, 12 000 ft, 320 kt
    UNI666  — normal high cruise, 35 000 ft, 500 kt
    TTW007  — ANOMALY: HIGH_SPEED_LOW_ALT (520 kt @ 1 500 ft) — fires on first poll
    CAL177  — ANOMALY: EXTREME_DESCENT (-2 100 ft/cycle) — fires on second poll
"""

import math
import time
import threading
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# ── Tainan Airport (RCNN) ────────────────────────────────────────────────────
RCNN_LAT = 22.9508
RCNN_LON = 120.2061

# ── Aircraft definition ──────────────────────────────────────────────────────
_FLEET: list[dict] = [
    # Normal flights
    dict(hex="899076", flight="EVA384",  lat=22.874, lon=120.165, alt=29000, gs=456, track=180, vr=0,      anomaly_descent=False),
    dict(hex="b80211", flight="CAL102",  lat=22.980, lon=120.195, alt=3500,  gs=200, track=270, vr=-300,   anomaly_descent=False),
    dict(hex="7c1234", flight="MDA878",  lat=22.760, lon=120.310, alt=12000, gs=320, track=90,  vr=1500,   anomaly_descent=False),
    dict(hex="4ca100", flight="UNI666",  lat=23.200, lon=119.900, alt=35000, gs=500, track=135, vr=0,      anomaly_descent=False),
    # Anomaly 1: HIGH_SPEED_LOW_ALT — rule fires immediately every poll
    dict(hex="cf0077", flight="TTW007",  lat=22.920, lon=120.100, alt=1500,  gs=520, track=90,  vr=0,      anomaly_descent=False),
    # Anomaly 2: EXTREME_DESCENT — alt drops 2 100 ft per tick; rule fires on 2nd poll
    dict(hex="899177", flight="CAL177",  lat=22.960, lon=120.190, alt=7000,  gs=345, track=270, vr=-6000,  anomaly_descent=True),
]

# Runtime state — mutated by the ticker thread
_state: list[dict] = [{**ac} for ac in _FLEET]
_lock = threading.Lock()


def _deg_per_sec(speed_kt: float, track_deg: float, lat: float) -> tuple[float, float]:
    """Return (dlat, dlon) per second for a given speed and track."""
    speed_km_s = speed_kt * 1.852 / 3600.0
    rad = math.radians(track_deg)
    dlat = speed_km_s * math.cos(rad) / 111.32
    dlon = speed_km_s * math.sin(rad) / (111.32 * math.cos(math.radians(lat)))
    return dlat, dlon


def _tick(dt: float = 2.0) -> None:
    """Advance all aircraft positions by dt seconds."""
    with _lock:
        for ac in _state:
            dlat, dlon = _deg_per_sec(ac["gs"], ac["track"], ac["lat"])
            ac["lat"] += dlat * dt
            ac["lon"] += dlon * dt

            # EXTREME_DESCENT: drop altitude by a fixed step each tick
            if ac["anomaly_descent"]:
                ac["alt"] = max(100.0, ac["alt"] - 2100.0)
            else:
                ac["alt"] += ac["vr"] / 60.0 * dt
                ac["alt"] = max(100.0, ac["alt"])

            # Bounce back if aircraft drifts outside Tainan bbox
            if abs(ac["lat"] - RCNN_LAT) > 1.2 or abs(ac["lon"] - RCNN_LON) > 1.2:
                ac["lat"] = RCNN_LAT + (ac["lat"] - RCNN_LAT) * -0.5
                ac["lon"] = RCNN_LON + (ac["lon"] - RCNN_LON) * -0.5
                ac["track"] = (ac["track"] + 180) % 360


def _snapshot() -> list[dict]:
    with _lock:
        return [
            {
                "hex":      ac["hex"],
                "flight":   ac["flight"].ljust(8),
                "lat":      round(ac["lat"], 6),
                "lon":      round(ac["lon"], 6),
                "alt_baro": round(ac["alt"]),
                "gs":       round(ac["gs"], 1),
                "baro_rate": round(ac["vr"]),
                "track":    round(ac["track"], 1),
                "seen":     0,
                "seen_pos": 0,
            }
            for ac in _state
        ]


# ── Background ticker (advances positions every 2 s) ─────────────────────────
def _ticker_loop() -> None:
    while True:
        time.sleep(2.0)
        _tick(dt=2.0)


_ticker = threading.Thread(target=_ticker_loop, daemon=True)
_ticker.start()

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="AeroSentinel ADS-B Simulator")


@app.get("/data/aircraft.json")
def get_aircraft():
    return JSONResponse({
        "now":      time.time(),
        "messages": 999999,
        "aircraft": _snapshot(),
    })


@app.get("/health")
def health():
    return {"status": "simulator running", "aircraft": len(_state)}


if __name__ == "__main__":
    print("=" * 56)
    print("  AeroSentinel ADS-B Simulator")
    print(f"  Serving  http://localhost:30047/data/aircraft.json")
    print(f"  Aircraft : {len(_state)} ({sum(1 for a in _FLEET if not a['anomaly_descent'] and a['gs'] < 450)} normal, 2 anomaly)")
    print("  TTW007   → HIGH_SPEED_LOW_ALT  (fires every poll)")
    print("  CAL177   → EXTREME_DESCENT     (fires from 2nd poll)")
    print("=" * 56)
    uvicorn.run(app, host="127.0.0.1", port=30047, log_level="warning")
