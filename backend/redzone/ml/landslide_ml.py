"""Inference wrapper for the trained landslide-susceptibility model.

`is_available()` reports whether a trained model is on disk; callers (`hazard/__init__.py`)
fall back to the heuristic field cleanly when it isn't, so training is optional, not a
hard dependency of the pipeline.
"""

from __future__ import annotations

import json

import geopandas as gpd
import numpy as np

from redzone.config import MODELS_DIR
from redzone.hazard import grid as G
from redzone.ml.features import FEATURE_NAMES, grid_features

MODEL_PATH = MODELS_DIR / "landslide_rf.joblib"
METADATA_PATH = MODELS_DIR / "landslide_rf_metadata.json"

_model_cache = None


def is_available() -> bool:
    return MODEL_PATH.exists()


def load_metadata() -> dict | None:
    if not METADATA_PATH.exists():
        return None
    return json.loads(METADATA_PATH.read_text())


def _model():
    global _model_cache
    if _model_cache is None:
        import joblib

        _model_cache = joblib.load(MODEL_PATH)
    return _model_cache


def predict_field(habitations: gpd.GeoDataFrame, rivers: gpd.GeoDataFrame,
                  faults: gpd.GeoDataFrame) -> np.ndarray:
    """Grid-shaped landslide-susceptibility probability, 0..1, from the trained model."""
    feat = grid_features(habitations, rivers, faults)
    ny, nx = feat["slope"].shape
    X = np.column_stack([feat[k].ravel() for k in FEATURE_NAMES]).astype("float64")
    proba = _model().predict_proba(X)[:, 1].reshape(ny, nx).astype("float32")
    return G.smooth(proba, sigma_km=0.6)
