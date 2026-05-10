import numpy as np
import joblib
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

RCNN_LAT, RCNN_LON = 22.9508, 120.2061

_RULES = [
    (lambda r: r["Speed_kt"] > 450 and r["Altitude_ft"] < 3_000, "HIGH_SPEED_LOW_ALT"),
    (lambda r: r["alt_change"] < -2_000,                          "EXTREME_DESCENT"),
    (lambda r: r["alt_change"] > 2_000,                           "EXTREME_CLIMB"),
    (lambda r: r["Altitude_ft"] > 45_000 and r["Speed_kt"] < 200, "STALL_AT_ALTITUDE"),
    (lambda r: r["Speed_kt"] > 600,                               "HYPERSONIC_SPEED"),
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371.0
    la1, lo1, la2, lo2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = la2 - la1, lo2 - lo1
    a = sin(dlat / 2) ** 2 + cos(la1) * cos(la2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


class InferenceEngine:
    def __init__(self, model_path: str, scaler_path: str, features_path: str):
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.features: list[str] = joblib.load(features_path)
        self._prev_alt: dict[str, float] = {}
        self._prev_speed: dict[str, float] = {}

    def build_features(
        self, icao: str, alt: float, speed: float, lat: float, lon: float, now: datetime
    ) -> dict:
        alt_change = alt - self._prev_alt.get(icao, alt)
        speed_change = speed - self._prev_speed.get(icao, speed)
        self._prev_alt[icao] = alt
        self._prev_speed[icao] = speed

        dist = _haversine_km(lat, lon, RCNN_LAT, RCNN_LON)

        return {
            "Altitude_ft":    alt,
            "Speed_kt":       speed,
            "Latitude":       lat,
            "Longitude":      lon,
            "alt_speed_ratio": alt / (speed + 1.0),
            "dist_from_RCNN": dist,
            "alt_change":     max(-5_000.0, min(5_000.0, alt_change)),
            "speed_change":   max(-200.0,   min(200.0,   speed_change)),
            "hour_of_day":    now.hour + now.minute / 60.0,
            "near_airport":   float(dist < 15.0 and alt < 5_000.0),
        }

    def _check_rules(self, row: dict) -> tuple[bool, str | None]:
        for condition, reason in _RULES:
            try:
                if condition(row):
                    return True, reason
            except Exception:
                pass
        return False, None

    def predict(self, row: dict) -> tuple[bool, float, str | None]:
        X = np.array([[row[f] for f in self.features]])
        X_scaled = self.scaler.transform(X)
        label = self.model.predict(X_scaled)[0]
        score = float(self.model.decision_function(X_scaled)[0])

        rule_hit, rule_reason = self._check_rules(row)
        is_anomaly = rule_hit or (label == -1)
        reason = rule_reason or ("ML_ISOLATION_FOREST" if label == -1 else None)

        return is_anomaly, score, reason


_engine: InferenceEngine | None = None


def init_engine(model_path: str, scaler_path: str, features_path: str) -> None:
    global _engine
    _engine = InferenceEngine(model_path, scaler_path, features_path)
    print(f"[inference] model loaded — features: {_engine.features}")


def get_engine() -> InferenceEngine:
    assert _engine is not None, "init_engine() must be called before get_engine()"
    return _engine
