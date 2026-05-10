# AeroSentinel — Changelog

All notable changes to the project, newest first.

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
