import logging
import os
from typing import Dict, List, Optional

import joblib
import numpy as np

from config import settings
from ml.feature_builder import features_to_array

logger = logging.getLogger(__name__)

STRATEGY_CLASSES = ["volume_profile", "amd_session", "liquidity_sweep", "order_blocks_fvg"]

_model = None


def load_model():
    global _model
    path = settings.ml_lgbm_model_path
    if os.path.exists(path):
        _model = joblib.load(path)
        logger.info(f"LightGBM model loaded from {path}")
    else:
        logger.warning(f"LightGBM model not found at {path} — using uniform priors")
        _model = None


def predict(features: Dict[str, float]) -> Dict[str, float]:
    """Returns probability dict {strategy_name: prob}."""
    arr = np.array(features_to_array(features)).reshape(1, -1)
    if _model is None:
        return {s: 0.25 for s in STRATEGY_CLASSES}
    try:
        probs = _model.predict_proba(arr)[0]
        return {STRATEGY_CLASSES[i]: float(p) for i, p in enumerate(probs)}
    except Exception as e:
        logger.error(f"LightGBM predict failed: {e}")
        return {s: 0.25 for s in STRATEGY_CLASSES}


def get_best_strategy(features: Dict[str, float]) -> tuple:
    probs = predict(features)
    best = max(probs, key=probs.get)
    return best, probs
