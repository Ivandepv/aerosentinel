# AeroSentinel — Developer State & Next Steps

> This document is the source of truth for the current development state.
> It is written for any developer (or AI coding assistant) picking up the project.
> Update it when a phase is completed.

---

## Current State (2026-05-10)

| Phase | Status | Notes |
|---|---|---|
| 0 — Data Collection | ✅ Done | ~260K records, `data/training_data/flights_dataset.csv` |
| 1 — ML Model Training | ✅ Done | 10-feature Isolation Forest, 317,809 records, 3 data fixes applied |
| 2 — FastAPI Backend | 🔲 Not started | — |
| 3 — Next.js Frontend | 🔲 Not started | — |
| 4 — Telegram Alerts | 🔲 Not started | — |
| 5 — Pi Deployment | 🔲 Not started | — |

---

## Immediate Next Step — Build the FastAPI Backend

```bash
mkdir -p backend/routes backend/alerts
cd backend
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn[standard] httpx scikit-learn joblib pandas python-dotenv
```

Full spec in §Phase 2 below.

Expected outputs:
- `models/model.pkl` — trained Isolation Forest
- `models/scaler.pkl` — StandardScaler fitted on training data
- `models/features.pkl` — ordered feature name list
- `reports/anomaly_validation.png` — 3-panel validation plot

Review the contamination sweep output and the validation plot. If anomaly % looks wrong, re-run with a different contamination value:

```bash
python ml/train_model.py 0.03   # override contamination
```

---

## ML Architecture

### Model
- **Algorithm:** Isolation Forest (`sklearn.ensemble.IsolationForest`)
- **n_estimators:** 300
- **contamination:** 0.02 (2% of data expected to be anomalous)
- **n_jobs:** -1 (all CPU cores)
- **GPU:** RAPIDS cuML attempted at import, falls back to sklearn. Final `.pkl` is always sklearn-compatible for Pi deployment.

### Features (10 total)

| Feature | Source | Notes |
|---|---|---|
| `Altitude_ft` | Raw ADS-B | Barometric altitude |
| `Speed_kt` | Raw ADS-B | Ground speed |
| `Latitude` | Raw ADS-B | — |
| `Longitude` | Raw ADS-B | — |
| `alt_speed_ratio` | Derived | `Altitude_ft / (Speed_kt + 1)` — physics correlation |
| `dist_from_RCNN` | Derived | Haversine distance to Tainan Airport (22.9508°N, 120.2061°E) |
| `alt_change` | Derived | Per-aircraft rolling altitude delta, gap-corrected, clipped ±5000 ft |
| `speed_change` | Derived | Per-aircraft rolling speed delta, gap-corrected, clipped ±200 kt |
| `hour_of_day` | Derived | `hour + minute/60` — time context |
| `near_airport` | Derived | 1 if within 15 km of RCNN AND alt < 5,000 ft — approach/departure zone flag |

### Data cleaning pipeline (3 stages)

| Stage | What it removes | Records removed |
|---|---|---|
| Physics limits + nulls | Missing fields, speed 0–30 kt, alt ≤ 0 or > 55,000 ft | 82,957 |
| Bbox edge margin (0.1°) | Flights entering/exiting monitored zone — false delta spikes | 19,202 |
| SDR gap correction (> 30s) | Per-flight records after a receiver dropout — zeroes bad deltas | 2,669 corrected |

### Training results (final)

- **Records trained on:** 317,809
- **Normal:** 311,454 (98.00%)
- **Anomaly:** 6,355 (2.00%)
- **Training time:** ~5s (CPU, all cores)
- **Top anomaly:** CAL177 — 344.8 kt at 3,975 ft, −1,675 ft/cycle descent (score −0.11)

### Rule-based hybrid layer (in `live_detection.py`)

Applied on top of ML predictions. Any rule hit → `ANOMALY` regardless of ML score.

| Rule | Condition | Reason tag |
|---|---|---|
| High speed, low altitude | speed > 450 kt AND alt < 3000 ft | `HIGH_SPEED_LOW_ALT` |
| Extreme descent | alt_change < -2000 ft/cycle | `EXTREME_DESCENT` |
| Extreme climb | alt_change > 2000 ft/cycle | `EXTREME_CLIMB` |
| Stall at altitude | alt > 45000 ft AND speed < 200 kt | `STALL_AT_ALTITUDE` |
| Hypersonic speed | speed > 600 kt | `HYPERSONIC_SPEED` |

---

## Phase 2 — FastAPI Backend

Build `backend/` directory. Key components:

### 2.1 Directory structure to create
```
backend/
├── main.py              ← FastAPI app entry point
├── collector.py         ← ADS-B poller (replaces live_detection.py)
├── inference.py         ← Load model artifacts, run predict()
├── database.py          ← SQLite setup (WAL mode)
├── routes/
│   ├── aircraft.py      ← GET /api/aircraft, /api/aircraft/{icao24}
│   ├── anomalies.py     ← GET /api/anomalies, /api/stats
│   └── websocket.py     ← WS /ws/live, WS /ws/alerts
├── schemas.py           ← Pydantic models
└── requirements.txt
```

### 2.2 SQLite schema (implement in `database.py`)
```sql
CREATE TABLE flights (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT NOT NULL,
    icao24        TEXT NOT NULL,
    callsign      TEXT,
    altitude_ft   REAL,
    speed_kt      REAL,
    vertical_rate REAL,
    latitude      REAL,
    longitude     REAL,
    track         REAL,
    is_anomaly    INTEGER DEFAULT 0,
    anomaly_score REAL,
    anomaly_reason TEXT
);

CREATE TABLE anomalies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id       INTEGER REFERENCES flights(id),
    detected_at     TEXT NOT NULL,
    icao24          TEXT,
    callsign        TEXT,
    reason          TEXT,
    screenshot_path TEXT,
    notified        INTEGER DEFAULT 0
);
```

### 2.3 WebSocket message formats
See `docs/AEROSENTINEL_ROADMAP.md` §2.3 for full JSON schemas.

### 2.4 Key requirements
```
fastapi uvicorn[standard] httpx scikit-learn joblib pandas sqlite3 python-dotenv
```

### 2.5 ADS-B source
On Raspberry Pi: `readsb` exposes JSON at `http://localhost:30047/data/aircraft.json`
For local dev/testing: simulate with a static JSON file from the dataset.

---

## Phase 3 — Next.js Frontend

Build `frontend/` directory. Stack: Next.js 14, React 18, TypeScript, Leaflet.js, shadcn/ui, Tailwind, Zustand, Recharts.

Key components: `<Map>`, `<AircraftMarker>`, `<AnomalyMarker>`, `<FlightPanel>`, `<AnomalyLog>`, `<StatsBar>`, `<AnomalyBanner>`.

WebSocket hook connects to `ws://[PI_IP]:8000/ws/live`.

See `docs/AEROSENTINEL_ROADMAP.md` §3 for full layout spec and code snippets.

---

## Phase 4 — Telegram Alerts

Build `backend/alerts/` directory. Requires:
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
- Playwright (headless Chromium) for map screenshots
- 5-minute per-aircraft cooldown to avoid spam

See `docs/AEROSENTINEL_ROADMAP.md` §4 for full implementation.

---

## Phase 5 — Raspberry Pi 5 Deployment

Three systemd services: `readsb.service`, `aerosentinel-backend.service`, `aerosentinel-frontend.service`.

Performance notes for Pi 5:
- SQLite WAL mode
- Keep last 20 positions per aircraft in memory
- ML inference on separate thread pool
- Next.js `output: 'standalone'`

---

## Key File Map

| File | Purpose |
|---|---|
| `ml/train_model.py` | Full training pipeline — run this first |
| `ml/requirements.txt` | Training dependencies |
| `live_detection.py` | Edge inference script (Pi, replaces the backend collector in prod) |
| `data_recolection/dataset_collector.py` | Original ADS-B data logger |
| `stress_test_model.py` | Quick model sanity check |
| `data/training_data/flights_dataset.csv` | 7-day ADS-B dataset, ~260K records |
| `models/` | Trained artifacts (gitignored, rebuild with train_model.py) |
| `reports/` | Validation plots (gitignored, generated by train_model.py) |

---

## Hardware

- **Edge device:** Raspberry Pi 5
- **SDR dongle:** RTL-SDR Blog V4
- **Signal:** ADS-B at 1090 MHz
- **Decoder:** `readsb` systemd service
- **Location:** Tainan, Taiwan (RCNN airport: 22.9508°N, 120.2061°E)

---

## Environment Variables (create `.env` in `backend/` before Phase 2)

```env
READSB_URL=http://localhost:30047/data/aircraft.json
POLL_INTERVAL_SEC=2
DB_PATH=./data/aerosentinel.db
MODEL_PATH=../models/model.pkl
SCALER_PATH=../models/scaler.pkl
FEATURES_PATH=../models/features.pkl
ANOMALY_COOLDOWN_SEC=300
DASHBOARD_URL=http://localhost:3000
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```
