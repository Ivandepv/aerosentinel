# AeroSentinel — Changelog

All notable changes to the project, newest first.

---

## [Phase 3 complete] — 2026-05-10

### Next.js Frontend — `frontend/`

**Stack:** Next.js 14 · TypeScript · Leaflet.js · Zustand · Recharts · Tailwind CSS

#### Layout
- 3-column dashboard: Flight Details (left 218 px) | Live Map (center, flex) | Aircraft Table + Anomaly Log (right 332 px)
- Floating anomaly banner slides in from top on new detection, auto-dismisses after 8 s
- Fully responsive height — panels fill viewport with internal scroll

#### Map (`components/Map/MapClient.tsx`)
- Leaflet map centered on Tainan Airport (22.9508°N, 120.2061°E), zoom 10
- CartoDB Dark Matter tiles
- Aircraft rendered as ✈️ emoji inside altitude-colored glowing ring; ring rotates with track heading
- Anomaly aircraft rendered with red pulsing ring (`box-shadow` animation)
- Position trail polylines per aircraft (last 20 points), colored by altitude
- Tainan Airport (RCNN) fixed marker
- Altitude color bar overlay at map bottom — rainbow scale from red (0 ft) to purple (40k+ ft)

#### State (`store/aircraft.ts`)
- Zustand store: `aircraft[]`, `trails{}` (last 20 positions), `altHistory{}` (last 150 readings for chart), `anomalies[]`, `selected`, `connected`
- `setAircraft()` updates trails and altitude history incrementally on every WebSocket push

#### WebSocket (`hooks/useLiveAircraft.ts`)
- Dual persistent connections: `/ws/live` (aircraft updates) + `/ws/alerts` (anomaly alerts)
- Auto-reconnect with 3 s backoff on disconnect

#### Components
| Component | Description |
|---|---|
| `StatsBar` | Gradient logo (purple→cyan→orange), LIVE/OFFLINE pill, colored stat chips |
| `FlightPanel` | Selected aircraft: gradient callsign, altitude progress bar, data rows colored by type, Recharts altitude history chart |
| `AircraftTable` | Sortable by any column; altitude values colored by spectrum; orange left-border on selected row; red tint on anomaly rows |
| `AnomalyLog` | Severity-colored left border per entry (red/orange/blue); timestamps in monospace |
| `AnomalyBanner` | Gradient red glass banner, slides in from top, auto-dismisses |
| `AltitudeColorBar` | Rainbow gradient bar with altitude labels, overlaid at map bottom |

#### Visual design
- **Background:** deep navy gradient (`#050b1f → #080f28`) + subtle cyan dot-grid texture
- **Panels:** glassmorphism — `rgba(6,12,36,0.88)` + `backdrop-filter: blur(20px)` with colored glowing borders
- **Altitude color scale:** `lib/altitude.ts` — 9-stop rainbow from `#ef4444` (0 ft) to `#c084fc` (40k+ ft)
- **Data colors:** cyan = altitude, orange = speed/callsign, purple = track, green/red = score/vr

---

## [Phase 2 complete] — 2026-05-10

### FastAPI Backend — `backend/`

**Stack:** FastAPI · uvicorn · aiosqlite · httpx · scikit-learn · joblib · python-dotenv

#### ADS-B Collector (`collector.py`)
- Async loop polls `readsb` JSON endpoint every `POLL_INTERVAL_SEC` seconds (default 2 s)
- Validates each aircraft record (filters `speed < 30 kt`, `alt ≤ 0`, missing position)
- Calls `InferenceEngine.build_features()` then `predict()` for every aircraft per tick
- Writes all records to `flights` table; anomaly records also written to `anomalies` table
- Broadcasts aircraft list to all `/ws/live` subscribers every poll
- Broadcasts anomaly alerts to all `/ws/alerts` subscribers immediately on detection

#### Inference Engine (`inference.py`)
- `InferenceEngine` class loads `model.pkl`, `scaler.pkl`, `features.pkl` on startup
- Maintains per-aircraft rolling state (`prev_alt`, `prev_speed`) for delta features
- Builds all 10 features including `near_airport` (missing from legacy `live_detection.py`)
- Applies rule-based layer first; ML score used only when no rule fires
- `predict()` returns `(is_anomaly: bool, score: float, reason: str | None)`

#### Database (`database.py`)
- SQLite with WAL journal mode for concurrent read performance
- `init_db()` creates tables and indices on startup; called in FastAPI lifespan
- `get_db()` async generator used as FastAPI `Depends()` in route handlers
- Tables: `flights` (all records), `anomalies` (flagged events only)
- Indices on `timestamp`, `icao24`, `is_anomaly`, `detected_at`

#### REST API
| Endpoint | Description |
|---|---|
| `GET /health` | Liveness check |
| `GET /api/aircraft` | Latest position per aircraft seen in last 30 s |
| `GET /api/aircraft/{icao24}` | Full position history for one aircraft (last 10 min) |
| `GET /api/anomalies` | All anomaly events in last 24 h |
| `GET /api/stats` | Live aircraft count, 24 h anomaly count + rate, uptime |
| `WS /ws/live` | Pushes `aircraft_update` JSON every poll cycle |
| `WS /ws/alerts` | Pushes `anomaly_alert` JSON immediately on detection |

#### WebSocket `ConnectionManager` (`routes/websocket.py`)
- Set-based connection tracking (O(1) add/remove)
- Dead connection cleanup on broadcast failure
- Separate manager instances for `/ws/live` and `/ws/alerts`

#### ADS-B Simulator (`simulator.py`)
- Standalone FastAPI app on port 30047 — drop-in replacement for `readsb` during local dev
- Background thread advances all aircraft positions every 2 s
- 6 aircraft: 4 normal flights, 2 hard-coded anomalies for end-to-end testing
  - **TTW007:** HIGH_SPEED_LOW_ALT (520 kt @ 1,500 ft) — fires every poll
  - **CAL177:** EXTREME_DESCENT (−2,100 ft/tick) — fires from 2nd poll

---

## [Phase 1 complete] — 2026-05-10

### ML Training Pipeline — 3 fixes applied to `ml/train_model.py`

- **Added bounding box edge margin filter**
  - Removed records within 0.1° (~11 km) of the geographic zone boundary
  - Eliminated 19,202 records that caused false altitude/speed delta spikes when aircraft entered or exited the monitored zone
  - Removed high-altitude transit flights (CPA566, KAL458, CAL5832) that were dominating the top anomalies for the wrong reason

- **Added `near_airport` feature (10th feature)**
  - Boolean flag: 1 when aircraft is within 15 km of RCNN AND below 5,000 ft
  - Teaches the model that low-altitude, low-speed behavior near the airport is an expected approach/departure pattern
  - Reduced false anomaly scores for landing approach records

- **Added SDR gap correction**
  - Detects consecutive records of the same flight separated by more than 30 seconds
  - Zeros out `alt_change` and `speed_change` for those records — the delta is a measurement artifact (aircraft dropped out of SDR range), not a real rate of change
  - Corrected 2,669 records; eliminated clipped −5000 ft false extremes from top anomalies
  - `alt_change` range improved from ±5000 (clipped) to −3700/+3475 (real values)

### Results after fixes

- Top anomaly before: UIA8675 with `alt_change = -5000` (SDR dropout artifact, same flight every day)
- Top anomaly after: CAL177 — 344.8 kt at 3,975 ft, −1,675 ft descent (genuine unusual flight behavior)
- Top 15 now contains 8 different flights instead of 3 repeated flights
- Anomaly scores shifted from −0.14/−0.16 to −0.08/−0.11 (model is more calibrated, less dominated by artifacts)

### Docs

- Updated `docs/DEV_STATE.md`: Phase 1 marked complete, feature table updated to 10 features, data cleaning pipeline documented with record counts, training results added
- Created `docs/CHANGELOG.md` (this file)

---

## [Phase 0 complete] — 2026-04-08 to 2026-04-15

### Data Collection

- Deployed RTL-SDR Blog V4 dongle + `readsb` on Raspberry Pi 5 in Tainan, Taiwan
- Collected 7 days of continuous ADS-B traffic at 1090 MHz over Tainan airspace
- Coverage: lat 21.5–23.5°N, lon 119.5–121.5°E (RCNN bounding box)
- Raw dataset: ~400,766 records → `data/training_data/flights_dataset.csv`
- Fields: `Timestamp, Flight, Altitude_ft, Speed_kt, Latitude, Longitude`

---

## [Project initialized] — 2026-05-10

### Repository setup

- Initial commit: project structure, `.gitignore`, `README.md`
- Written `ml/train_model.py` — full Isolation Forest training pipeline with contamination sweep, feature engineering, validation plots, and artifact export
- Written `live_detection.py` — standalone edge inference script for Raspberry Pi
- Written `stress_test_model.py` — model sanity check script
- Written `docs/AEROSENTINEL_ROADMAP.md` — full technical roadmap for all 5 phases
- Written `docs/DEV_STATE.md` — living developer state document
