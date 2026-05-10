import json
import time
import csv
import os
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

DATA_PATH        = "/run/readsb/aircraft.json"
MODEL_PATH       = "models/model.pkl"
SCALER_PATH      = "models/scaler.pkl"
FEATURES_PATH    = "models/features.pkl"
CSV_PREDICTIONS  = "data/flight_data/live_predictions.csv"

RCNN_LAT, RCNN_LON = 22.9508, 120.2061  # Tainan Airport

ANOMALY_RULES = [
    (lambda r: r["Speed_kt"] > 450 and r["Altitude_ft"] < 3_000,  "HIGH_SPEED_LOW_ALT"),
    (lambda r: r["alt_change"] < -2_000,                           "EXTREME_DESCENT"),
    (lambda r: r["alt_change"] > 2_000,                            "EXTREME_CLIMB"),
    (lambda r: r["Altitude_ft"] > 45_000 and r["Speed_kt"] < 200,  "STALL_AT_ALTITUDE"),
    (lambda r: r["Speed_kt"] > 600,                                "HYPERSONIC_SPEED"),
]

print("📡 Booting AeroSentinel Edge AI Inference ...")

try:
    model    = joblib.load(MODEL_PATH)
    scaler   = joblib.load(SCALER_PATH)
    features = joblib.load(FEATURES_PATH)
    print(f"✅ Model loaded  — features: {features}")
except FileNotFoundError as e:
    print(f"❌ Model files missing. Run ml/train_model.py first.\n{e}")
    exit(1)

# Per-aircraft state for rolling deltas
prev_alt   = {}
prev_speed = {}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6_371.0
    la1, lo1 = radians(lat1), radians(lon1)
    la2, lo2 = radians(lat2), radians(lon2)
    dlat, dlon = la2 - la1, lo2 - lo1
    a = sin(dlat / 2) ** 2 + cos(la1) * cos(la2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def build_features(icao, alt, speed, lat, lon, now):
    alt_change   = alt   - prev_alt.get(icao,   alt)
    speed_change = speed - prev_speed.get(icao, speed)
    prev_alt[icao]   = alt
    prev_speed[icao] = speed

    row = {
        "Altitude_ft":    alt,
        "Speed_kt":       speed,
        "Latitude":       lat,
        "Longitude":      lon,
        "alt_speed_ratio": alt / (speed + 1.0),
        "dist_from_RCNN": haversine_km(lat, lon, RCNN_LAT, RCNN_LON),
        "alt_change":     max(-5_000, min(5_000, alt_change)),
        "speed_change":   max(-200,   min(200,   speed_change)),
        "hour_of_day":    now.hour + now.minute / 60.0,
    }
    return row


def check_rules(row):
    for condition, reason in ANOMALY_RULES:
        try:
            if condition(row):
                return True, reason
        except Exception:
            pass
    return False, None


def predict(row):
    X = np.array([[row[f] for f in features]])
    X_scaled = scaler.transform(X)
    label = model.predict(X_scaled)[0]
    score = model.decision_function(X_scaled)[0]
    return label, score


file_exists = os.path.isfile(CSV_PREDICTIONS)
os.makedirs(os.path.dirname(CSV_PREDICTIONS), exist_ok=True)
with open(CSV_PREDICTIONS, mode="a", newline="") as f:
    w = csv.writer(f)
    if not file_exists:
        w.writerow(["Timestamp", "Flight", "ICAO24", "Altitude_ft", "Speed_kt",
                    "Latitude", "Longitude", "Status", "Reason", "Anomaly_Score"])

print(f"📁 Saving predictions to: {CSV_PREDICTIONS}")
print("--- RADAR ACTIVE ---\n")

while True:
    try:
        with open(DATA_PATH) as f:
            data = json.load(f)

        now = datetime.now()
        ts  = now.strftime("%Y-%m-%d %H:%M:%S")

        for ac in data.get("aircraft", []):
            flight = ac.get("flight", "").strip()
            icao   = ac.get("hex",    "").strip()
            alt    = ac.get("alt_baro")
            speed  = ac.get("gs")
            lat    = ac.get("lat")
            lon    = ac.get("lon")

            if not (flight and alt and speed and lat and lon):
                continue
            if speed < 30 or alt <= 0:
                continue

            row = build_features(icao, alt, speed, lat, lon, now)

            rule_hit, rule_reason = check_rules(row)
            label, score          = predict(row)

            is_anomaly = rule_hit or (label == -1)
            reason     = rule_reason or ("ML_ISOLATION_FOREST" if label == -1 else None)
            status     = "ANOMALY" if is_anomaly else "NORMAL"

            if is_anomaly:
                print(f"[{ts}] 🔴 {flight:<10} Alt:{alt:>6} ft  Spd:{speed:>5} kt  "
                      f"Score:{score:>7.3f}  ⚠ {reason}")
            else:
                print(f"[{ts}] 🟢 {flight:<10} Alt:{alt:>6} ft  Spd:{speed:>5} kt  "
                      f"Score:{score:>7.3f}")

            with open(CSV_PREDICTIONS, mode="a", newline="") as f:
                csv.writer(f).writerow(
                    [ts, flight, icao, alt, speed, lat, lon, status, reason, round(score, 4)]
                )

    except FileNotFoundError:
        print("⏳ Waiting for SDR data ...")

    time.sleep(2)
