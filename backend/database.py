import os
import aiosqlite
from typing import AsyncGenerator

_DB_PATH: str = "./data/aerosentinel.db"

_CREATE_FLIGHTS = """
CREATE TABLE IF NOT EXISTS flights (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp      TEXT NOT NULL,
    icao24         TEXT NOT NULL,
    callsign       TEXT,
    altitude_ft    REAL,
    speed_kt       REAL,
    vertical_rate  REAL,
    latitude       REAL,
    longitude      REAL,
    track          REAL,
    is_anomaly     INTEGER DEFAULT 0,
    anomaly_score  REAL,
    anomaly_reason TEXT
);
"""

_CREATE_ANOMALIES = """
CREATE TABLE IF NOT EXISTS anomalies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id       INTEGER REFERENCES flights(id),
    detected_at     TEXT NOT NULL,
    icao24          TEXT,
    callsign        TEXT,
    reason          TEXT,
    screenshot_path TEXT,
    notified        INTEGER DEFAULT 0
);
"""

_INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_flights_timestamp  ON flights(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_flights_icao24     ON flights(icao24);",
    "CREATE INDEX IF NOT EXISTS idx_flights_is_anomaly ON flights(is_anomaly);",
    "CREATE INDEX IF NOT EXISTS idx_anomalies_time     ON anomalies(detected_at);",
]


def get_db_path() -> str:
    return _DB_PATH


async def init_db(db_path: str | None = None) -> None:
    global _DB_PATH
    if db_path:
        _DB_PATH = db_path
    os.makedirs(os.path.dirname(os.path.abspath(_DB_PATH)), exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute(_CREATE_FLIGHTS)
        await db.execute(_CREATE_ANOMALIES)
        for idx in _INDICES:
            await db.execute(idx)
        await db.commit()


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        yield db
