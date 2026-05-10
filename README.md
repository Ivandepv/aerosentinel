# AeroSentinel

Autonomous airspace anomaly detection system running on a Raspberry Pi 5 + RTL-SDR dongle. Captures live ADS-B signals from aircraft over Tainan, Taiwan, runs an on-device Isolation Forest model to flag anomalous flight behavior, and serves a real-time map dashboard with Telegram alerts.

> Edge AIoT project — no cloud dependency, fully local inference.

---

## What It Does

1. **Captures** ADS-B signals at 1090 MHz from commercial aircraft using an RTL-SDR Blog V4 dongle
2. **Decodes** raw signals via `readsb` into structured JSON (callsign, altitude, speed, position)
3. **Detects anomalies** using a trained Isolation Forest model + physics-based rule layer
4. **Displays** live aircraft positions on an interactive map dashboard (Next.js + Leaflet)
5. **Alerts** via Telegram bot with a map screenshot when a flight anomaly is detected

---

## Hardware Requirements

| Component | Spec |
|---|---|
| Edge device | Raspberry Pi 5 (4 GB RAM minimum) |
| SDR dongle | RTL-SDR Blog V4 |
| Antenna | 1090 MHz ADS-B antenna |
| Storage | 32 GB microSD (Class 10 or better) |

---

## Software Stack

| Layer | Technology |
|---|---|
| Signal decoder | `readsb` (systemd service) |
| ML model | scikit-learn Isolation Forest |
| Backend API | Python · FastAPI · WebSockets · SQLite |
| Frontend | Next.js 14 · TypeScript · Leaflet.js · Tailwind |
| Notifications | Telegram Bot API · Playwright (screenshots) |

---

## Project Structure

```
aerosentinel/
├── ml/
│   ├── train_model.py          # Full training pipeline (run this first)
│   └── requirements.txt
├── backend/                    # FastAPI server (Phase 2 — in progress)
│   ├── main.py
│   ├── collector.py
│   ├── inference.py
│   ├── database.py
│   ├── routes/
│   └── alerts/
├── frontend/                   # Next.js dashboard (Phase 3 — in progress)
├── data/
│   └── training_data/
│       └── flights_dataset.csv # 7-day ADS-B dataset (~260K records)
├── data_recolection/
│   └── dataset_collector.py    # Original ADS-B data logger
├── models/                     # Trained artifacts (gitignored — rebuild locally)
│   ├── model.pkl
│   ├── scaler.pkl
│   └── features.pkl
├── docs/
│   ├── DEV_STATE.md            # Current development state & next steps
│   └── AEROSENTINEL_ROADMAP.md # Full technical roadmap
├── live_detection.py           # Standalone edge inference script
├── stress_test_model.py        # Model sanity check
└── .env                        # Secrets — never commit (see .env section below)
```

---

## Quickstart

### 1. Clone

```bash
git clone https://github.com/Ivandepv/aerosentinel.git
cd aerosentinel
```

### 2. Train the Model

> Run this on a machine with a decent CPU (or GPU with RAPIDS cuML).
> You need `data/training_data/flights_dataset.csv` — already in the repo.

```bash
pip install pandas numpy scikit-learn joblib matplotlib
python ml/train_model.py
```

The script will:
- Clean and filter the ADS-B dataset
- Engineer 9 features from the raw 4 columns
- Run a contamination sweep and print anomaly counts
- Save `models/model.pkl`, `models/scaler.pkl`, `models/features.pkl`
- Save a 3-panel validation plot to `reports/anomaly_validation.png`

Override contamination (default 0.02):
```bash
python ml/train_model.py 0.03
```

### 3. Run Standalone Edge Inference (Pi only)

This requires `readsb` running and decoding signals from the RTL-SDR dongle.

```bash
python live_detection.py
```

Reads from `/run/readsb/aircraft.json` every 2 seconds and saves predictions to `data/flight_data/live_predictions.csv`.

### 4. Backend API (Phase 2)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Frontend Dashboard (Phase 3)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## Environment Variables

Create a `.env` file in `backend/` (never commit this):

```env
READSB_URL=http://localhost:30047/data/aircraft.json
POLL_INTERVAL_SEC=2
DB_PATH=./data/aerosentinel.db
MODEL_PATH=../models/model.pkl
SCALER_PATH=../models/scaler.pkl
FEATURES_PATH=../models/features.pkl
ANOMALY_COOLDOWN_SEC=300
DASHBOARD_URL=http://localhost:3000
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

---

## Anomaly Detection

The model combines two approaches:

**Isolation Forest (ML):** trained on 9 features extracted from 7 days of Tainan airspace data. Flags statistically unusual flight behavior.

**Rule-based layer (physics):** hard rules that catch obvious violations regardless of ML score.

| Rule | Condition | Severity |
|---|---|---|
| High speed, low altitude | speed > 450 kt AND alt < 3000 ft | HIGH |
| Extreme descent | altitude drop > 2000 ft per 2s cycle | HIGH |
| Extreme climb | altitude gain > 2000 ft per 2s cycle | HIGH |
| Stall at altitude | alt > 45000 ft AND speed < 200 kt | HIGH |
| Hypersonic speed | speed > 600 kt | HIGH |

---

## Dataset

- **Source:** RTL-SDR Blog V4 + `readsb` over Tainan airspace
- **Period:** April 8–15, 2026 (7 days continuous)
- **Records:** ~260,000 ADS-B messages
- **Fields:** `Timestamp, Flight, Altitude_ft, Speed_kt, Latitude, Longitude`
- **Coverage:** lat 21.5–23.5°N, lon 119.5–121.5°E (Tainan bounding box)

---

## Development Status

See [`docs/DEV_STATE.md`](docs/DEV_STATE.md) for the current phase status and next steps.

---

## Team

Alan Romo · Guillermo Portillo · Jorge Coronado — Team 5

Edge AIoT Project 2026 · Tainan, Taiwan
