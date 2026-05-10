# 🛫 AeroSentinel — Project Roadmap
**Autonomous Airspace Anomaly Detection System**
*Edge AIoT · Raspberry Pi 5 · RTL-SDR Blog V4 · Tainan, Taiwan*

---

## Project Overview

AeroSentinel is a fully local, cloud-independent airspace monitoring system. It captures live ADS-B signals from commercial aircraft over Tainan at 1090 MHz, decodes them into structured data, runs an Isolation Forest anomaly detection model on-device, and serves a real-time Google Maps-style dashboard with instant anomaly alerts (including screenshots sent via notification service).

**Stack:**
- **Hardware:** Raspberry Pi 5 + RTL-SDR Blog V4
- **Signal decoder:** `readsb` / `dump1090`
- **Backend:** Python (FastAPI + WebSockets)
- **ML:** scikit-learn Isolation Forest (trained on your 260K-record dataset)
- **Frontend:** Next.js 14 + React + TypeScript + Leaflet.js / MapLibre
- **Notifications:** Telegram Bot API (screenshots + anomaly metadata)
- **Data:** CSV → SQLite (edge-friendly, no Postgres needed)

---

## Repository Structure

```
aerosentinel/
├── hardware/                   # SDR setup scripts & systemd services
│   ├── setup_readsb.sh
│   └── services/
├── backend/                    # Python FastAPI data server
│   ├── collector/              # ADS-B JSON → CSV/SQLite pipeline
│   ├── ml/                     # Isolation Forest training & inference
│   ├── api/                    # REST + WebSocket endpoints
│   ├── alerts/                 # Telegram notification service
│   └── requirements.txt
├── frontend/                   # Next.js dashboard
│   ├── app/
│   ├── components/
│   │   ├── Map/
│   │   ├── FlightPanel/
│   │   ├── AnomalyAlert/
│   │   └── StatsBar/
│   └── package.json
├── ml/                         # Notebooks & model artifacts
│   ├── train_isolation_forest.ipynb
│   ├── model.pkl
│   └── scaler.pkl
├── data/                       # CSV datasets (gitignored if large)
│   └── flights_tainan_*.csv
├── docs/
│   └── architecture.md
└── docker-compose.yml          # Optional: containerize backend
```

---

## Milestones

### ✅ Phase 0 — Data Collection (DONE)
**Status:** Complete · ~260,000 flight records collected (April 8–15, 2026)

**What you have:**
- CSV with fields: `timestamp`, `callsign`, `icao24`, `altitude_ft`, `speed_kt`, `latitude`, `longitude`, `vertical_rate`
- 7 days of continuous ADS-B monitoring over Tainan airspace

**What to do now (cleanup before training):**
- [ ] Remove records with `altitude_ft = 0` and `speed_kt = 0` simultaneously (ground noise)
- [ ] Drop rows where `latitude` or `longitude` is null
- [ ] Remove extreme outlier noise: `altitude_ft > 55000` or `speed_kt > 700`
- [ ] Filter to Tainan bounding box: lat `21.5–23.5`, lon `119.5–121.5`
- [ ] Export a clean CSV: `data/flights_clean.csv`

---

### 🔲 Phase 1 — ML Model Training
**Goal:** Train and validate the Isolation Forest anomaly detector
**Estimated time:** 2–3 days
**Tooling:** Python, scikit-learn, pandas, Google Colab (for speed) or local

#### 1.1 — Feature Engineering

```python
# Features to use for training:
FEATURES = [
    'altitude_ft',
    'speed_kt',
    'vertical_rate',    # ft/min — key for detecting nose-dives
    'latitude',
    'longitude',
    'alt_speed_ratio',  # altitude_ft / (speed_kt + 1) — physics correlation
]
```

**Derived features to compute:**
- `alt_speed_ratio`: captures the altitude/speed physics correlation
- `speed_change`: rolling diff of speed (detect sudden acceleration)
- `alt_change`: rolling diff of altitude (detect sudden drop/climb)

#### 1.2 — Train the Model

```python
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[FEATURES])

model = IsolationForest(
    n_estimators=200,
    contamination=0.02,   # expect ~2% anomalies in training data
    random_state=42,
    n_jobs=-1
)
model.fit(X_scaled)

# Save artifacts
joblib.dump(model, 'ml/model.pkl')
joblib.dump(scaler, 'ml/scaler.pkl')
```

#### 1.3 — Validate Results

- [ ] Plot anomaly scatter: Altitude vs Speed (blue = normal, red = anomaly) — match your existing chart
- [ ] Inspect flagged records manually: do they make physical sense?
- [ ] Tune `contamination` param until false positives are minimal
- [ ] Benchmark inference time on Raspberry Pi 5 (target: < 50ms per record)

#### 1.4 — Define Anomaly Rules (Hybrid Approach)

Complement the ML model with hard physics rules to catch obvious cases:

```python
def is_rule_based_anomaly(row):
    if row['speed_kt'] > 450 and row['altitude_ft'] < 3000:
        return True, "HIGH_SPEED_LOW_ALT"
    if row['vertical_rate'] < -6000:
        return True, "EXTREME_DESCENT"
    if row['vertical_rate'] > 6000:
        return True, "EXTREME_CLIMB"
    if row['altitude_ft'] > 45000 and row['speed_kt'] < 200:
        return True, "STALL_AT_ALTITUDE"
    return False, None
```

**Milestone 1 deliverable:** `ml/model.pkl`, `ml/scaler.pkl`, validation notebook with confusion matrix and anomaly scatter plot

---

### 🔲 Phase 2 — Backend Data Server (Python / FastAPI)
**Goal:** Live ADS-B ingestion, ML inference, REST API + WebSockets
**Estimated time:** 4–6 days

#### 2.1 — ADS-B Live Collector

`readsb` runs as a systemd service decoding signals from the RTL-SDR dongle and exposes JSON at `localhost:30047`. Your Python collector polls this every 2 seconds:

```python
# backend/collector/adsb_collector.py
import httpx, asyncio, sqlite3
from datetime import datetime

READSB_URL = "http://localhost:30047/data/aircraft.json"

async def collect():
    async with httpx.AsyncClient() as client:
        while True:
            res = await client.get(READSB_URL)
            aircraft_list = res.json().get("aircraft", [])
            for ac in aircraft_list:
                if ac.get("lat") and ac.get("lon"):
                    store_to_db(ac)
                    run_inference(ac)   # anomaly check
            await asyncio.sleep(2)
```

#### 2.2 — SQLite Schema

```sql
CREATE TABLE flights (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    icao24      TEXT NOT NULL,
    callsign    TEXT,
    altitude_ft REAL,
    speed_kt    REAL,
    vertical_rate REAL,
    latitude    REAL,
    longitude   REAL,
    track       REAL,
    is_anomaly  INTEGER DEFAULT 0,
    anomaly_score REAL,
    anomaly_reason TEXT
);

CREATE TABLE anomalies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id   INTEGER REFERENCES flights(id),
    detected_at TEXT NOT NULL,
    icao24      TEXT,
    callsign    TEXT,
    reason      TEXT,
    screenshot_path TEXT,
    notified    INTEGER DEFAULT 0
);
```

#### 2.3 — FastAPI Endpoints

```
GET  /api/aircraft          → All live aircraft (last 30s)
GET  /api/aircraft/{icao24} → Single aircraft history (last 10 min)
GET  /api/anomalies         → Recent anomalies (last 24h)
GET  /api/stats             → Aircraft count, anomaly rate, uptime
WS   /ws/live               → WebSocket: push aircraft updates every 2s
WS   /ws/alerts             → WebSocket: push anomaly alerts immediately
```

**WebSocket message format (aircraft update):**
```json
{
  "type": "aircraft_update",
  "timestamp": "2026-04-15T14:22:00Z",
  "aircraft": [
    {
      "icao24": "899076",
      "callsign": "EVA384",
      "latitude": 22.874606,
      "longitude": 120.165558,
      "altitude_ft": 29000,
      "speed_kt": 456,
      "vertical_rate": 0,
      "track": 180,
      "is_anomaly": false,
      "anomaly_score": 0.12
    }
  ]
}
```

**WebSocket message format (anomaly alert):**
```json
{
  "type": "anomaly_alert",
  "timestamp": "2026-04-15T14:22:00Z",
  "icao24": "899076",
  "callsign": "EVA384",
  "reason": "HIGH_SPEED_LOW_ALT",
  "altitude_ft": 1200,
  "speed_kt": 520,
  "latitude": 22.99,
  "longitude": 120.20,
  "severity": "HIGH"
}
```

#### 2.4 — ML Inference Service

```python
# backend/ml/inference.py
import joblib, numpy as np

model = joblib.load("ml/model.pkl")
scaler = joblib.load("ml/scaler.pkl")

def predict(row: dict) -> tuple[bool, float, str | None]:
    features = extract_features(row)
    scaled = scaler.transform([features])
    score = model.decision_function(scaled)[0]   # negative = more anomalous
    label = model.predict(scaled)[0]             # -1 = anomaly
    
    rule_flag, rule_reason = is_rule_based_anomaly(row)
    
    is_anomaly = (label == -1) or rule_flag
    reason = rule_reason or ("ML_ISOLATION_FOREST" if label == -1 else None)
    
    return is_anomaly, float(score), reason
```

**Milestone 2 deliverable:** Working FastAPI server running on Pi, live WebSocket stream visible in browser console, anomaly detection firing correctly

---

### 🔲 Phase 3 — Frontend Dashboard (Next.js / React / TypeScript)
**Goal:** Google Maps-style live flight map with anomaly overlays
**Estimated time:** 5–8 days

#### 3.1 — Tech Stack

| Package | Purpose |
|---|---|
| `next` 14 | App Router + SSR |
| `react` 18 | UI framework |
| `typescript` | Type safety |
| `leaflet` + `react-leaflet` | Interactive map (offline tile support) |
| `shadcn/ui` | UI components |
| `tailwindcss` | Styling |
| `lucide-react` | Icons |
| `recharts` | Altitude/speed charts in side panel |
| `zustand` | Global state (aircraft list, selected flight, alerts) |

#### 3.2 — Map Layer Architecture

```
MapContainer (Leaflet)
├── TileLayer               ← OpenStreetMap (works offline with tile cache)
├── AircraftLayer           ← All aircraft markers (emoji ✈ rotated by track)
│   ├── AircraftMarker      ← Normal flight (blue icon)
│   └── AnomalyMarker       ← Anomalous flight (red pulsing icon)
├── TrailLayer              ← Last 20 position polyline per aircraft
├── SelectedFlightOverlay   ← Highlighted track + info
└── AirportMarker           ← Tainan Airport (RCNN) fixed marker
```

**Aircraft icon rotation (track-based):**
```tsx
const aircraftIcon = (track: number, isAnomaly: boolean) =>
  L.divIcon({
    html: `<div style="transform: rotate(${track}deg); font-size: 22px;">
             ${isAnomaly ? '🔴' : '✈️'}
           </div>`,
    className: 'aircraft-icon',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
```

#### 3.3 — UI Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  🛫 AEROSENTINEL        [●] LIVE   14 aircraft   2 anomalies    │
├────────────────────────────────────┬─────────────────────────────┤
│                                    │  ┌─ Selected Flight ──────┐ │
│                                    │  │ EVA384  B-16227         │ │
│         LIVE MAP                   │  │ A321 · Taiwan           │ │
│      (Leaflet / OpenStreetMap)     │  │ Alt:  29,000 ft         │ │
│                                    │  │ Speed: 456 kt           │ │
│   ✈ normal flights (blue)          │  │ Track: 180°             │ │
│   🔴 anomaly flights (red pulse)   │  │ [──────────────────]    │ │
│                                    │  │  Altitude chart (5min)  │ │
│                                    │  └─────────────────────────┘ │
│                                    │  ┌─ Anomaly Log ──────────┐ │
│                                    │  │ 🔴 14:22  CSN456        │ │
│                                    │  │    HIGH_SPEED_LOW_ALT   │ │
│                                    │  │ 🟡 14:18  UIA789        │ │
│                                    │  │    EXTREME_DESCENT      │ │
│                                    │  └─────────────────────────┘ │
├────────────────────────────────────┴─────────────────────────────┤
│  Aircraft  Callsign  Alt(ft)  Speed(kt)  Status   Anomaly Score  │
│  EVA384    EVA384    29,000   456        Normal   0.12           │
│  JJA2212   JJA2212   33,000   466        Normal   0.08           │
│  CSN456    CSN456    1,200    520        ⚠ ALERT  -0.45          │
└──────────────────────────────────────────────────────────────────┘
```

#### 3.4 — WebSocket Hook

```tsx
// hooks/useLiveAircraft.ts
import { useEffect, useRef } from 'react';
import { useAircraftStore } from '@/store/aircraft';

export function useLiveAircraft() {
  const ws = useRef<WebSocket | null>(null);
  const { setAircraft, addAnomaly } = useAircraftStore();

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws/live');

    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'aircraft_update') setAircraft(msg.aircraft);
      if (msg.type === 'anomaly_alert') addAnomaly(msg);
    };

    return () => ws.current?.close();
  }, []);
}
```

#### 3.5 — Key UI Components

- **`<AnomalyBanner />`** — Full-width red alert banner that slides in when anomaly is detected
- **`<FlightPanel />`** — Right sidebar showing selected flight: callsign, registration, altitude/speed chart (recharts), anomaly score gauge
- **`<AnomalyLog />`** — Scrollable list of recent anomalies with timestamp, reason, severity
- **`<StatsBar />`** — Top bar: live aircraft count, anomaly count today, system uptime, SDR signal status
- **`<AircraftTable />`** — Bottom sortable table of all visible aircraft

**Milestone 3 deliverable:** Dashboard running at `http://raspberrypi.local:3000`, live aircraft visible on map, anomaly highlighting working, flight panel opening on click

---

### 🔲 Phase 4 — Anomaly Notification System (Telegram)
**Goal:** Send automatic alert with screenshot when anomaly is detected
**Estimated time:** 2–3 days

#### 4.1 — Telegram Bot Setup

1. Message `@BotFather` on Telegram → `/newbot` → get `BOT_TOKEN`
2. Add bot to your group/channel → get `CHAT_ID`
3. Store in `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

#### 4.2 — Screenshot Capture (Playwright)

Use Playwright (headless Chromium) to screenshot the map centered on the anomalous aircraft:

```python
# backend/alerts/screenshot.py
from playwright.async_api import async_playwright

async def capture_anomaly_screenshot(icao24: str, lat: float, lon: float) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        # Navigate to dashboard focused on anomaly
        url = f"http://localhost:3000?focus={icao24}&lat={lat}&lon={lon}&zoom=10"
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(2000)  # Wait for map tiles to load

        path = f"/tmp/anomaly_{icao24}_{int(time.time())}.png"
        await page.screenshot(path=path, full_page=False)
        await browser.close()
        return path
```

#### 4.3 — Telegram Notification

```python
# backend/alerts/telegram.py
import httpx, os
from pathlib import Path

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

async def send_anomaly_alert(anomaly: dict, screenshot_path: str):
    caption = (
        f"🚨 *AIRSPACE ANOMALY DETECTED*\n\n"
        f"✈️ Flight: `{anomaly['callsign']}` ({anomaly['icao24']})\n"
        f"⚠️ Reason: `{anomaly['reason']}`\n"
        f"📍 Position: `{anomaly['latitude']:.4f}, {anomaly['longitude']:.4f}`\n"
        f"📏 Altitude: `{anomaly['altitude_ft']:,.0f} ft`\n"
        f"💨 Speed: `{anomaly['speed_kt']} kt`\n"
        f"🕐 Time: `{anomaly['timestamp']}`\n"
        f"📊 Anomaly Score: `{anomaly['anomaly_score']:.3f}`"
    )

    async with httpx.AsyncClient() as client:
        with open(screenshot_path, "rb") as photo:
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
                files={"photo": photo},
            )
```

#### 4.4 — Alert Deduplication

Avoid spamming: same aircraft flagged → cooldown of 5 minutes before re-alerting.

```python
# In-memory cooldown tracker
alert_cooldown: dict[str, float] = {}  # icao24 → last_alert_timestamp

def should_alert(icao24: str) -> bool:
    last = alert_cooldown.get(icao24, 0)
    if time.time() - last > 300:  # 5 minutes
        alert_cooldown[icao24] = time.time()
        return True
    return False
```

**Milestone 4 deliverable:** Telegram bot sends formatted message + map screenshot within 10 seconds of anomaly detection

---

### 🔲 Phase 5 — Raspberry Pi 5 Deployment
**Goal:** Stable, auto-starting production system on the edge device
**Estimated time:** 2–3 days

#### 5.1 — Services Architecture on Pi

```
systemd services:
├── readsb.service          ← Decode ADS-B from RTL-SDR dongle (always running)
├── aerosentinel-backend.service  ← FastAPI + collector + ML inference
└── aerosentinel-frontend.service ← Next.js production build
```

#### 5.2 — readsb Setup

```bash
# Install readsb
sudo apt install readsb

# Configure /etc/default/readsb:
RECEIVER="rtlsdr"
DECODER="--device-index 0 --gain -10 --ppm 0"
NET="--net --net-ro-size 500 --net-ro-interval 0 --net-heartbeat 60"
NET_PORT="--net-ri-port 30001 --net-ro-port 30002 --net-sbs-port 30003 --net-bi-port 30004,30104 --net-bo-port 30005"
EXTRA="--json-location-accuracy 2 --lat 22.9908 --lon 120.2133"  # Tainan coords
```

#### 5.3 — systemd Service Files

**Backend service:**
```ini
[Unit]
Description=AeroSentinel Backend
After=network.target readsb.service

[Service]
WorkingDirectory=/home/pi/aerosentinel/backend
ExecStart=/home/pi/aerosentinel/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
User=pi

[Install]
WantedBy=multi-user.target
```

**Frontend service:**
```ini
[Unit]
Description=AeroSentinel Frontend
After=aerosentinel-backend.service

[Service]
WorkingDirectory=/home/pi/aerosentinel/frontend
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=5
User=pi
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
```

#### 5.4 — Performance Tuning for Pi 5

- Use **SQLite WAL mode** for concurrent reads/writes
- Limit trail history: keep last 20 positions per aircraft in memory, persist every 60s
- Run ML inference on a separate thread pool (Pi 5 has 4 cores — use them)
- Next.js: `output: 'standalone'` in `next.config.js` for minimal runtime footprint
- Playwright: run with `--no-sandbox` on Pi

#### 5.5 — Offline Map Tiles (Optional but Recommended)

Use `mbtiles` with a local tile server so the map works without internet:

```bash
pip install mbutil
# Download Tainan region tiles from openstreetmap
# Serve locally: python -m http.server 8080
```

Or use Leaflet's offline tile caching via `leaflet.offline` package.

**Milestone 5 deliverable:** Full system boots automatically on Pi power-on, survives 24h stress test, map accessible from any browser on the local network at `http://aerosentinel.local:3000`

---

## Environment Variables

```env
# .env (backend)
READSB_URL=http://localhost:30047/data/aircraft.json
POLL_INTERVAL_SEC=2
DB_PATH=./data/aerosentinel.db
MODEL_PATH=./ml/model.pkl
SCALER_PATH=./ml/scaler.pkl
ANOMALY_COOLDOWN_SEC=300
DASHBOARD_URL=http://localhost:3000
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

```env
# .env.local (frontend)
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MAP_CENTER_LAT=22.9908
NEXT_PUBLIC_MAP_CENTER_LON=120.2133
```

---

## Anomaly Severity Classification

| Severity | Condition | Color | Alert |
|---|---|---|---|
| 🔴 HIGH | `speed > 450 kt AND alt < 3000 ft` OR `vertical_rate < -6000 fpm` | Red pulse | Immediate Telegram |
| 🟡 MEDIUM | ML score < -0.3 AND no hard rule triggered | Amber | Telegram after 30s |
| 🔵 LOW | ML score < -0.1 | Blue outline | Dashboard only |

---

## Recommended Development Order

```
Week 1: Phase 0 (data cleanup) + Phase 1 (ML training)
Week 2: Phase 2 (backend API + WebSockets)
Week 3: Phase 3 (frontend map dashboard)
Week 4: Phase 4 (Telegram alerts) + Phase 5 (Pi deployment)
```

---

## Quick Start (Development)

```bash
# Clone and setup
git clone https://github.com/youruser/aerosentinel
cd aerosentinel

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn httpx scikit-learn pandas joblib playwright sqlite3
playwright install chromium
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → http://localhost:3000

# Train model (separate terminal, first time)
cd ml
jupyter notebook train_isolation_forest.ipynb
```

---

## Success Criteria

- [ ] Live aircraft appear on map within 5 seconds of boot
- [ ] Anomaly detection triggers in < 2 seconds of threshold breach
- [ ] Telegram notification arrives within 10 seconds including screenshot
- [ ] Dashboard handles 30+ simultaneous aircraft without lag
- [ ] System uptime > 99% over a 7-day test period on Pi 5
- [ ] False positive rate < 5% (manually verified over 24h)
- [ ] Map remains usable during local network outages (offline tiles)

---

*AeroSentinel Team 5 — Alan Romo · Guillermo Portillo · Jorge Coronado*
*Built for Tainan, Taiwan airspace — Edge AIoT Project 2026*
