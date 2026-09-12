"""Indoor Positioning — Machine Learning Inference Core.

Provides safe loading, schema validation, and prediction for
champion distance estimator models and zone classifiers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np

from .config import MODELS_DIR


def load_distance_model(model_dir: Optional[Path] = None) -> Tuple[Any, Any, Optional[Dict[str, Any]]]:
    """Load the trained distance estimator model, scaler, and metadata.
    
    Returns (model, scaler, metadata) or (None, None, None) on failure.
    """
    m_dir = Path(model_dir) if model_dir else MODELS_DIR
    model_path = m_dir / "distance_estimator.joblib"
    scaler_path = m_dir / "scaler.joblib"
    meta_path = m_dir / "model_metadata.json"

    if not (model_path.exists() and scaler_path.exists()):
        return None, None, None

    try:
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        metadata = None
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        return model, scaler, metadata
    except Exception:
        return None, None, None


def load_zone_model(model_dir: Optional[Path] = None) -> Tuple[Any, Any]:
    """Load the trained zone classifier and scaler.
    
    Returns (zone_model, zone_scaler) or (None, None) on failure.
    """
    m_dir = Path(model_dir) if model_dir else MODELS_DIR
    z_model_path = m_dir / "zone_classifier.joblib"
    z_scaler_path = m_dir / "zone_scaler.joblib"

    if not (z_model_path.exists() and z_scaler_path.exists()):
        return None, None

    try:
        zone_model = joblib.load(z_model_path)
        zone_scaler = joblib.load(z_scaler_path)
        return zone_model, zone_scaler
    except Exception:
        return None, None


def validate_feature_schema(feature_dict: Dict[str, Any], expected_cols: List[str]) -> Tuple[bool, List[str]]:
    """Check if all required features exist in the given feature dictionary.
    
    Returns (is_valid, missing_features).
    """
    missing = [col for col in expected_cols if col not in feature_dict]
    return len(missing) == 0, missing


def predict_distance(
    features: Dict[str, Any],
    model: Any,
    scaler: Any,
    feature_cols: List[str],
) -> Optional[float]:
    """Execute continuous distance estimation using the champion model."""
    if model is None or scaler is None or not feature_cols:
        return None

    is_valid, missing = validate_feature_schema(features, feature_cols)
    if not is_valid:
        return None

    try:
        X = np.array([[features[col] for col in feature_cols]], dtype=float)
        if not np.all(np.isfinite(X)):
            return None
        X_scaled = scaler.transform(X)
        pred = float(model.predict(X_scaled)[0])
        return round(max(0.1, min(30.0, pred)), 2)
    except Exception:
        return None
