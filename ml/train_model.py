#!/usr/bin/env python3
"""
AeroSentinel — Anomaly Detection Training Pipeline
Arch Linux · RTX 4050 · Tainan Airspace (RCNN)

Features engineered from raw ADS-B data:
  Raw:     Altitude_ft, Speed_kt, Latitude, Longitude
  Derived: alt_speed_ratio, dist_from_RCNN, alt_change, speed_change, hour_of_day

GPU note: sklearn IsolationForest is CPU-only (uses all cores via n_jobs=-1).
          RAPIDS cuML is attempted first for GPU acceleration — falls back to
          sklearn automatically. Either way the saved .pkl is sklearn-compatible
          so it loads on Raspberry Pi without RAPIDS.
"""

import sys
import time
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
DATA_PATH   = ROOT / "data" / "training_data" / "flights_dataset.csv"
MODEL_OUT   = ROOT / "models" / "model.pkl"
SCALER_OUT  = ROOT / "models" / "scaler.pkl"
REPORTS_DIR = ROOT / "reports"

# ── Tainan constants ───────────────────────────────────────────────────────────
RCNN_LAT, RCNN_LON = 22.9508, 120.2061   # Tainan Airport
LAT_MIN, LAT_MAX   = 21.5,  23.5
LON_MIN, LON_MAX   = 119.5, 121.5

FEATURES = [
    "Altitude_ft",
    "Speed_kt",
    "Latitude",
    "Longitude",
    "alt_speed_ratio",
    "dist_from_RCNN",
    "alt_change",
    "speed_change",
    "hour_of_day",
]

# ── GPU detection ──────────────────────────────────────────────────────────────
try:
    import cudf
    import cuml
    from cuml.ensemble import IsolationForest as cuIsolationForest
    USE_GPU = True
    print("✅  RAPIDS cuML detected — GPU path ENABLED (RTX 4050)")
except ImportError:
    USE_GPU = False
    print("ℹ️   RAPIDS cuML not found — using sklearn (all CPU cores via n_jobs=-1)")
    print("    To install: conda install -c rapidsai -c conda-forge cuml cuda-version=12.x")

# ── Data loading & cleaning ────────────────────────────────────────────────────
def load_and_clean(path: Path) -> pd.DataFrame:
    print(f"\n{'─'*56}")
    print(f"  Loading  {path.name}")
    print(f"{'─'*56}")

    df = pd.read_csv(path, parse_dates=["Timestamp"])
    raw_count = len(df)
    print(f"  Raw records       : {raw_count:>10,}")

    df = df.dropna(subset=["Altitude_ft", "Speed_kt", "Latitude", "Longitude"])

    # Ground noise — parked/taxiing aircraft
    df = df[~((df["Altitude_ft"] == 0) & (df["Speed_kt"] == 0))]

    # Hard physics limits
    df = df[(df["Altitude_ft"] > 0)    & (df["Altitude_ft"] <= 55_000)]
    df = df[(df["Speed_kt"]    > 30)   & (df["Speed_kt"]    <= 700)]

    # Tainan geographic box
    df = df[
        (df["Latitude"]  >= LAT_MIN) & (df["Latitude"]  <= LAT_MAX) &
        (df["Longitude"] >= LON_MIN) & (df["Longitude"] <= LON_MAX)
    ]

    print(f"  After cleaning    : {len(df):>10,}  ({len(df)/raw_count*100:.1f}% retained)")
    return df.reset_index(drop=True)


# ── Feature engineering ────────────────────────────────────────────────────────
def haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: float, lon2: float) -> np.ndarray:
    R = 6_371.0
    la1, lo1 = np.radians(lat1), np.radians(lon1)
    la2, lo2 = np.radians(lat2), np.radians(lon2)
    dlat = la2 - la1
    dlon = lo2 - lo1
    a = np.sin(dlat / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    print(f"\n{'─'*56}")
    print("  Feature engineering")
    print(f"{'─'*56}")

    df["hour_of_day"]    = df["Timestamp"].dt.hour + df["Timestamp"].dt.minute / 60.0
    df["alt_speed_ratio"]= df["Altitude_ft"] / (df["Speed_kt"] + 1.0)
    df["dist_from_RCNN"] = haversine_km(
        df["Latitude"].values, df["Longitude"].values, RCNN_LAT, RCNN_LON
    )

    # Per-flight rolling deltas — must sort by (flight, time) first
    df = df.sort_values(["Flight", "Timestamp"]).reset_index(drop=True)
    grp = df.groupby("Flight", sort=False)
    df["alt_change"]   = grp["Altitude_ft"].diff().fillna(0).clip(-5_000, 5_000)
    df["speed_change"] = grp["Speed_kt"].diff().fillna(0).clip(-200, 200)

    print(f"  Features ({len(FEATURES)}): {', '.join(FEATURES)}")
    for f in FEATURES:
        print(f"    {f:<20}  min={df[f].min():>10.2f}  max={df[f].max():>10.2f}  "
              f"mean={df[f].mean():>10.2f}")
    return df


# ── Model training ─────────────────────────────────────────────────────────────
def train_sklearn(X: np.ndarray, contamination: float) -> IsolationForest:
    model = IsolationForest(
        n_estimators=300,
        contamination=contamination,
        max_samples="auto",
        max_features=1.0,
        bootstrap=False,
        random_state=42,
        n_jobs=-1,         # use all CPU cores
        warm_start=False,
    )
    model.fit(X)
    return model


def train_cuml(X: np.ndarray, contamination: float):
    X_gpu = cudf.DataFrame(X.astype(np.float32))
    model = cuIsolationForest(
        n_estimators=300,
        contamination=contamination,
        random_state=42,
    )
    model.fit(X_gpu)
    return model, X_gpu


# ── Contamination sweep ────────────────────────────────────────────────────────
def sweep_contamination(X: np.ndarray, candidates=(0.01, 0.02, 0.03, 0.05)) -> float:
    """
    Train a quick low-estimator model for each contamination value and print
    anomaly counts so the user can pick the right one.
    Automatically selects 0.02 unless the user overrides via CLI arg.
    """
    print(f"\n{'─'*56}")
    print("  Contamination sweep  (n_estimators=50 for speed)")
    print(f"{'─'*56}")
    print(f"  {'contamination':>15}  {'anomalies':>10}  {'% of total':>12}")
    for c in candidates:
        m = IsolationForest(n_estimators=50, contamination=c, random_state=42, n_jobs=-1)
        m.fit(X)
        lbl = m.predict(X)
        n_anom = (lbl == -1).sum()
        print(f"  {c:>15.3f}  {n_anom:>10,}  {n_anom/len(X)*100:>11.2f}%")
    return 0.02   # sensible default for commercial airspace


# ── Validation & plots ─────────────────────────────────────────────────────────
def validate(df: pd.DataFrame, labels: np.ndarray, scores: np.ndarray) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    normal_mask  = labels == 1
    anomaly_mask = labels == -1
    n_normal  = normal_mask.sum()
    n_anomaly = anomaly_mask.sum()

    print(f"\n{'─'*56}")
    print("  Validation results")
    print(f"{'─'*56}")
    print(f"  Normal   : {n_normal:>8,}  ({n_normal /len(df)*100:.2f}%)")
    print(f"  Anomaly  : {n_anomaly:>8,}  ({n_anomaly/len(df)*100:.2f}%)")

    # ── Plot 1: Altitude vs Speed ──────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    fig.suptitle(
        "AeroSentinel — Isolation Forest · Tainan Airspace Anomaly Detection",
        fontsize=13, fontweight="bold"
    )

    ax = axes[0]
    ax.scatter(df.loc[normal_mask,  "Speed_kt"], df.loc[normal_mask,  "Altitude_ft"],
               c="steelblue", alpha=0.25, s=2, label=f"Normal ({n_normal:,})")
    ax.scatter(df.loc[anomaly_mask, "Speed_kt"], df.loc[anomaly_mask, "Altitude_ft"],
               c="crimson",   alpha=0.85, s=8, label=f"Anomaly ({n_anomaly:,})")
    ax.set_xlabel("Speed (kt)")
    ax.set_ylabel("Altitude (ft)")
    ax.set_title("Altitude vs Speed")
    ax.legend(markerscale=4, fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── Plot 2: Lat/Lon map ────────────────────────────────────────────────────
    ax2 = axes[1]
    ax2.scatter(df.loc[normal_mask,  "Longitude"], df.loc[normal_mask,  "Latitude"],
                c="steelblue", alpha=0.15, s=1, label="Normal")
    ax2.scatter(df.loc[anomaly_mask, "Longitude"], df.loc[anomaly_mask, "Latitude"],
                c="crimson",   alpha=0.9,  s=8, label="Anomaly")
    ax2.scatter([RCNN_LON], [RCNN_LAT], c="gold", s=80, marker="*", zorder=5, label="RCNN")
    ax2.set_xlabel("Longitude")
    ax2.set_ylabel("Latitude")
    ax2.set_title("Geographic Distribution")
    ax2.legend(markerscale=4, fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ── Plot 3: Score distribution ─────────────────────────────────────────────
    ax3 = axes[2]
    ax3.hist(scores[normal_mask],  bins=100, color="steelblue", alpha=0.7,
             label="Normal",  density=True)
    ax3.hist(scores[anomaly_mask], bins=100, color="crimson",   alpha=0.8,
             label="Anomaly", density=True)
    ax3.axvline(0, color="black", linestyle="--", linewidth=1, label="Decision boundary")
    ax3.set_xlabel("Anomaly Score  (lower = more anomalous)")
    ax3.set_ylabel("Density")
    ax3.set_title("Score Distribution")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = REPORTS_DIR / "anomaly_validation.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Plot saved → {plot_path}")

    # ── Top anomalies ──────────────────────────────────────────────────────────
    top = df[anomaly_mask].copy()
    top["score"] = scores[anomaly_mask]
    top = top.nsmallest(15, "score")[
        ["Timestamp", "Flight", "Altitude_ft", "Speed_kt",
         "Latitude", "Longitude", "alt_change", "speed_change", "score"]
    ]
    print(f"\n  Top 15 most anomalous records:")
    pd.set_option("display.float_format", "{:.2f}".format)
    pd.set_option("display.max_columns", 10)
    pd.set_option("display.width", 120)
    print(top.to_string(index=False))


# ── Rule-based hybrid layer (saved alongside ML model) ────────────────────────
ANOMALY_RULES = [
    # (condition_fn, reason_string, severity)
    (lambda r: r["Speed_kt"] > 450 and r["Altitude_ft"] < 3_000,
     "HIGH_SPEED_LOW_ALT", "HIGH"),
    (lambda r: r["alt_change"] < -2_000,
     "EXTREME_DESCENT", "HIGH"),
    (lambda r: r["alt_change"] > 2_000,
     "EXTREME_CLIMB", "HIGH"),
    (lambda r: r["Altitude_ft"] > 45_000 and r["Speed_kt"] < 200,
     "STALL_AT_ALTITUDE", "HIGH"),
    (lambda r: r["Speed_kt"] > 600,
     "HYPERSONIC_SPEED", "HIGH"),
]

def check_rules(row: dict) -> tuple[bool, str | None, str | None]:
    for condition, reason, severity in ANOMALY_RULES:
        try:
            if condition(row):
                return True, reason, severity
        except Exception:
            continue
    return False, None, None


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    contamination = float(sys.argv[1]) if len(sys.argv) > 1 else None

    print("\n" + "═" * 56)
    print("  AeroSentinel — Model Training Pipeline")
    print("  Arch Linux · RTX 4050 · Tainan Airspace")
    print("═" * 56)

    # 1. Load & clean
    df = load_and_clean(DATA_PATH)

    # 2. Feature engineering
    df = engineer_features(df)
    X_raw = df[FEATURES].values

    # 3. Scale
    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)

    # 4. Contamination sweep (always on CPU — quick)
    if contamination is None:
        contamination = sweep_contamination(X)
        print(f"\n  → Using contamination = {contamination}  "
              f"(override: python train_model.py 0.03)")

    # 5. Train
    print(f"\n{'─'*56}")
    t0 = time.perf_counter()
    if USE_GPU:
        print(f"  Training on GPU  contamination={contamination}")
        gpu_model, X_gpu = train_cuml(X, contamination)
        labels = gpu_model.predict(X_gpu).to_numpy()
        scores = gpu_model.decision_function(X_gpu).to_numpy()
        # Re-train with sklearn for Pi-compatible .pkl
        print("  Re-training sklearn model for Raspberry Pi compatibility ...")
        model = train_sklearn(X, contamination)
    else:
        print(f"  Training on CPU  contamination={contamination}")
        model = train_sklearn(X, contamination)
        labels = model.predict(X)
        scores = model.decision_function(X)

    elapsed = time.perf_counter() - t0
    print(f"  Training time     : {elapsed:.1f}s")

    # 6. Validate
    validate(df, labels, scores)

    # 7. Save artifacts
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model,  MODEL_OUT)
    joblib.dump(scaler, SCALER_OUT)
    joblib.dump(FEATURES, ROOT / "models" / "features.pkl")

    print(f"\n{'═'*56}")
    print(f"  ✅  model.pkl   → {MODEL_OUT}")
    print(f"  ✅  scaler.pkl  → {SCALER_OUT}")
    print(f"  ✅  features.pkl→ {ROOT / 'models' / 'features.pkl'}")
    print(f"{'═'*56}")
    print("\n  Next: update live_detection.py to use the new 9-feature pipeline")
    print("        then move to Phase 2 — FastAPI backend\n")


if __name__ == "__main__":
    main()
