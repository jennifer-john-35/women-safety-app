"""
risk_engine.py — ML-based risk prediction engine.

Trains a RandomForest model once on synthetic data and persists it to disk.
On subsequent starts, loads from disk instead of retraining.
"""
import logging
import os

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler

import config

logger = logging.getLogger(__name__)

# Module-level references to loaded model and scaler
_model: RandomForestClassifier | None = None
_scaler: MinMaxScaler | None = None


def _generate_training_data() -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic training data with features [lat, lon, hour]."""
    rng = np.random.default_rng(42)
    n_samples = 2000

    # Synthetic hotspot centres (high-risk areas)
    hotspot_lats = [28.6, 19.07, 12.97, 22.57, 13.08]
    hotspot_lons = [77.2, 72.87, 77.59, 88.36, 80.27]

    lats = rng.uniform(-90, 90, n_samples)
    lons = rng.uniform(-180, 180, n_samples)
    hours = rng.integers(0, 24, n_samples)

    labels = np.zeros(n_samples, dtype=int)
    for i in range(n_samples):
        for hlat, hlon in zip(hotspot_lats, hotspot_lons):
            dist = ((lats[i] - hlat) ** 2 + (lons[i] - hlon) ** 2) ** 0.5
            if dist < 5.0 and hours[i] in range(20, 24):
                labels[i] = 1
                break
            elif dist < 10.0 and hours[i] in range(18, 24):
                labels[i] = 1 if rng.random() > 0.5 else 0
                break

    X = np.column_stack([lats, lons, hours])
    return X, labels


def _train_and_save() -> tuple[RandomForestClassifier, MinMaxScaler]:
    """Train model and scaler, persist to disk, return both."""
    X, y = _generate_training_data()

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)

    joblib.dump(model, config.MODEL_PATH)
    joblib.dump(scaler, config.SCALER_PATH)
    logger.info("Model trained and saved to %s / %s", config.MODEL_PATH, config.SCALER_PATH)
    return model, scaler


def initialize_model() -> None:
    """Load model from disk if available; otherwise train and persist.

    If model files are corrupt or missing, retrains and overwrites them.
    Safe to call multiple times — only loads/trains once per process.
    """
    global _model, _scaler

    model_exists = os.path.exists(config.MODEL_PATH)
    scaler_exists = os.path.exists(config.SCALER_PATH)

    if model_exists and scaler_exists:
        try:
            _model = joblib.load(config.MODEL_PATH)
            _scaler = joblib.load(config.SCALER_PATH)
            logger.info("Model loaded from disk.")
            return
        except Exception as exc:
            logger.warning("Failed to load model from disk (%s); retraining.", exc)

    try:
        _model, _scaler = _train_and_save()
    except Exception as exc:
        logger.error("Model training failed: %s", exc)
        _model = None
        _scaler = None


def predict_risk(lat: float, lon: float, hour: int) -> float:
    """Return a risk score in [0.0, 1.0] for the given location and hour.

    Falls back to 0.5 if the model is unavailable.
    """
    try:
        if _model is None or _scaler is None:
            logger.warning("Model not initialised; returning default risk score.")
            return 0.5

        features = np.array([[lat, lon, hour]], dtype=float)
        features_scaled = _scaler.transform(features)

        # Use predict_proba to get a continuous score in [0, 1]
        proba = _model.predict_proba(features_scaled)
        # Index of class '1' (high-risk)
        classes = list(_model.classes_)
        if 1 in classes:
            risk_score = float(proba[0][classes.index(1)])
        else:
            risk_score = 0.0

        # Clamp to [0.0, 1.0] for safety
        return max(0.0, min(1.0, risk_score))
    except Exception as exc:
        logger.error("predict_risk error: %s", exc)
        return 0.5


def classify_risk(score: float) -> str:
    """Classify a risk score into 'HIGH', 'MODERATE', or 'LOW'.

    Thresholds:
        HIGH     — score > 0.75
        MODERATE — 0.5 <= score <= 0.75
        LOW      — score < 0.5
    """
    try:
        if score > 0.75:
            return "HIGH"
        elif score >= 0.5:
            return "MODERATE"
        else:
            return "LOW"
    except Exception as exc:
        logger.error("classify_risk error: %s", exc)
        return "LOW"
