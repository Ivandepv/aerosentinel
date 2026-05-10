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
| 2 — FastAPI Backend | ✅ Done | `backend/` — REST + WebSockets + SQLite WAL + ADS-B simulator |
| 3 — Next.js Frontend | ✅ Done | `frontend/` — live map, flight panel, anomaly log, vivid UI |
| 4 — Telegram Alerts | 🔲 Not started | **← NEXT** |
| 5 — Pi Deployment | 🔲 Not started | — |

---

## Immediate Next Step — Telegram Alerts (Phase 4)

Build `backend/alerts/`. Requires:
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` set in `backend/.env`
- Playwright (headless Chromium) for map screenshots
- 5-minute per-aircraft cooldown to avoid spam

```bash
cd backend && source venv/bin/activate
pip install playwright httpx
playwright install chromium
```

See `docs/AEROSENTINEL_ROADMAP.md` §Phase 4 for full implementation spec.

> **To run the full dev stack:**
> ```bash
> # Terminal 1 — ADS-B simulator (mimics readsb on port 30047)
> cd backend && source venv/bin/activate && python simulator.py
>
> # Terminal 2 — FastAPI backend
> cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
>
> # Terminal 3 — Next.js frontend
> cd frontend && npm run dev
> ```
> Dashboard: http://localhost:3000 · API: http://localhost:8000

> **Rebuild model artifacts anytime with:**
> ```bash
> python ml/train_model.py
> ```

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

### Rule-based hybrid layer (`backend/inference.py`)

Applied on top of ML predictions. Any rule hit → `ANOMALY` regardless of ML score.

| Rule | Condition | Reason tag |
|---|---|---|
| High speed, low altitude | speed > 450 kt AND alt < 3000 ft | `HIGH_SPEED_LOW_ALT` |
| Extreme descent | alt_change < -2000 ft/cycle | `EXTREME_DESCENT` |
| Extreme climb | alt_change > 2000 ft/cycle | `EXTREME_CLIMB` |
| Stall at altitude | alt > 45000 ft AND speed < 200 kt | `STALL_AT_ALTITUDE` |
| Hypersonic speed | speed > 600 kt | `HYPERSONIC_SPEED` |

---

## Phase 2 — FastAPI Backend ✅

### Directory structure (built)
```
backend/
├── main.py          ← FastAPI app, lifespan startup (DB → model → collector task)
├── collector.py     ← Async loop: polls readsb every 2s, runs inference, writes DB, broadcasts WS
├── inference.py     ← InferenceEngine with per-aircraft rolling state; includes near_airport fix
├── database.py      ← SQLite WAL via aiosqlite, get_db() dependency
├── schemas.py       ← Pydantic models for all API responses
├── simulator.py     ← Local dev: mimics readsb on port 30047 with 6 aircraft (2 anomalies)
├── routes/
│   ├── aircraft.py  ← GET /api/aircraft, GET /api/aircraft/{icao24}
│   ├── anomalies.py ← GET /api/anomalies, GET /api/stats
│   └── websocket.py ← WS /ws/live, WS /ws/alerts + ConnectionManager
├── requirements.txt
└── .env             ← copy and fill TELEGRAM_* before Phase 4
```

### REST endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{"status":"ok"}` |
| GET | `/api/aircraft` | All aircraft seen in last 30 s |
| GET | `/api/aircraft/{icao24}` | Position history for one aircraft (last 10 min) |
| GET | `/api/anomalies` | All anomaly events in last 24 h |
| GET | `/api/stats` | Aircraft count, anomaly rate, uptime |
| WS  | `/ws/live` | Aircraft update every 2 s |
| WS  | `/ws/alerts` | Anomaly alert pushed immediately on detection |

### Simulator aircraft

| ICAO | Callsign | Behavior |
|---|---|---|
| 899076 | EVA384 | Normal cruise, 29,000 ft / 456 kt |
| b80211 | CAL102 | Normal approach, 3,500 ft / 200 kt |
| 7c1234 | MDA878 | Normal climb, 12,000 ft / 320 kt |
| 4ca100 | UNI666 | Normal high cruise, 35,000 ft / 500 kt |
| cf0077 | TTW007 | **ANOMALY: HIGH_SPEED_LOW_ALT** — 520 kt @ 1,500 ft (fires every poll) |
| 899177 | CAL177 | **ANOMALY: EXTREME_DESCENT** — drops 2,100 ft/tick (fires from 2nd poll) |

---

## Phase 3 — Next.js Frontend ✅

### Directory structure (built)
```
frontend/
├── app/
│   ├── layout.tsx      ← Root layout, dark navy background
│   ├── page.tsx        ← 3-column layout (flight details | map | table+log)
│   └── globals.css     ← Tailwind + glass panels + leaflet overrides + dot-grid bg
├── components/
│   ├── Map/
│   │   ├── MapClient.tsx        ← Leaflet map (dynamic, ssr:false), altitude-colored markers
│   │   └── AltitudeColorBar.tsx ← Rainbow altitude scale at map bottom
│   ├── StatsBar.tsx     ← Gradient logo, live pill, colored stat chips
│   ├── FlightPanel.tsx  ← Left panel: selected AC details + altitude bar + recharts chart
│   ├── AircraftTable.tsx← Right panel: sortable table, altitude-colored values, orange highlights
│   ├── AnomalyLog.tsx   ← Right panel: severity-colored anomaly entries with left border
│   └── AnomalyBanner.tsx← Floating slide-in alert banner, auto-dismiss 8 s
├── hooks/
│   └── useLiveAircraft.ts ← Dual WS: /ws/live + /ws/alerts, auto-reconnect
├── store/
│   └── aircraft.ts     ← Zustand: aircraft[], trails[], altHistory[], anomalies[], selected
├── lib/
│   └── altitude.ts     ← altitudeColor(ft) → rainbow hex, ALT_SCALE constant
├── types/
│   └── index.ts        ← Aircraft, AnomalyAlert TypeScript interfaces
├── .env.local          ← NEXT_PUBLIC_API_URL, NEXT_PUBLIC_WS_URL
└── package.json
```

### UI design notes
- **Background:** Deep navy gradient `#050b1f → #080f28` + cyan dot-grid texture
- **Panels:** Glassmorphism (`rgba + backdrop-blur`) with colored glowing borders
  - Left panel: cyan border (`#22d3ee`)
  - Right panel: orange border (`#f97316`)
- **Logo:** Gradient text (purple → cyan → orange)
- **Aircraft markers:** ✈️ emoji inside altitude-colored glowing ring
- **Trails:** Polylines colored by altitude spectrum
- **Altitude colors:** Red (low) → Orange → Yellow → Green → Cyan → Blue → Purple (high)
- **Anomaly markers:** Red pulsing ring with `box-shadow` glow animation

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
- SQLite WAL mode (already implemented)
- Keep last 20 positions per aircraft in memory (already implemented in Zustand store)
- ML inference on separate thread pool
- Next.js `output: 'standalone'` (already set in `next.config.js`)

---

## Key File Map

| File | Purpose |
|---|---|
| `ml/train_model.py` | Full training pipeline — run this first |
| `ml/requirements.txt` | Training dependencies |
| `backend/main.py` | FastAPI entry point — start here |
| `backend/simulator.py` | Local ADS-B simulator (no Pi needed for dev) |
| `backend/inference.py` | ML inference engine with rolling per-aircraft state |
| `backend/collector.py` | Async ADS-B poll loop → DB → WebSocket broadcast |
| `frontend/app/page.tsx` | Main dashboard layout |
| `frontend/store/aircraft.ts` | Global state (Zustand) |
| `live_detection.py` | Legacy edge inference script (Pi standalone, pre-backend) |
| `data/training_data/flights_dataset.csv` | 7-day ADS-B dataset, ~260K records |
| `models/` | Trained artifacts (gitignored, rebuild with `ml/train_model.py`) |
| `reports/` | Validation plots (gitignored, generated by train_model.py) |

---

## Hardware

- **Edge device:** Raspberry Pi 5
- **SDR dongle:** RTL-SDR Blog V4
- **Signal:** ADS-B at 1090 MHz
- **Decoder:** `readsb` systemd service
- **Location:** Tainan, Taiwan (RCNN airport: 22.9508°N, 120.2061°E)

---

## Environment Variables (`backend/.env`)

```env
READSB_URL=http://localhost:30047/data/aircraft.json
POLL_INTERVAL_SEC=2
DB_PATH=./data/aerosentinel.db
MODEL_PATH=../models/model.pkl
SCALER_PATH=../models/scaler.pkl
FEATURES_PATH=../models/features.pkl
ANOMALY_COOLDOWN_SEC=300
DASHBOARD_URL=http://localhost:3000
TELEGRAM_BOT_TOKEN=          ← fill before Phase 4
TELEGRAM_CHAT_ID=            ← fill before Phase 4
```
