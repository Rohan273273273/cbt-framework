import logging
import pickle
from pathlib import Path
from typing import Dict, Optional

from config import settings
from ml.feature_builder import features_to_array

logger = logging.getLogger(__name__)

RIVER_PATH = Path(settings.ml_lgbm_model_path).parent / "river_model.pkl"
STRATEGY_CLASSES = ["volume_profile", "amd_session", "liquidity_sweep", "order_blocks_fvg"]

_river_model = None
_trade_count = 0


def _init_model():
    from river.tree import HoeffdingTreeClassifier
    from river.preprocessing import StandardScaler
    from river import compose
    return compose.Pipeline(
        StandardScaler(),
        HoeffdingTreeClassifier(grace_period=50, delta=1e-5),
    )


def load_model():
    global _river_model
    if RIVER_PATH.exists():
        with open(RIVER_PATH, "rb") as f:
            _river_model = pickle.load(f)
        logger.info("River model loaded from disk")
    else:
        _river_model = _init_model()
        logger.info("River model initialized fresh")


def predict(features: Dict[str, float]) -> Dict[str, float]:
    """Returns probability dict from River model."""
    if _river_model is None:
        return {s: 0.25 for s in STRATEGY_CLASSES}
    try:
        arr = features_to_array(features)
        feat_dict = {f"f{i}": v for i, v in enumerate(arr)}
        probs = _river_model.predict_proba_one(feat_dict)
        result = {s: probs.get(s, 0.0) for s in STRATEGY_CLASSES}
        # Normalize
        total = sum(result.values())
        if total > 0:
            result = {k: v/total for k, v in result.items()}
        else:
            result = {s: 0.25 for s in STRATEGY_CLASSES}
        return result
    except Exception as e:
        logger.warning(f"River predict failed: {e}")
        return {s: 0.25 for s in STRATEGY_CLASSES}


def learn(features: Dict[str, float], actual_strategy: str):
    """Update River model with trade outcome."""
    global _trade_count
    if _river_model is None:
        load_model()
    try:
        arr = features_to_array(features)
        feat_dict = {f"f{i}": v for i, v in enumerate(arr)}
        _river_model.learn_one(feat_dict, actual_strategy)
        _trade_count += 1
        if _trade_count % 10 == 0:
            _save_model()
    except Exception as e:
        logger.error(f"River learn failed: {e}")


def _save_model():
    RIVER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RIVER_PATH, "wb") as f:
        pickle.dump(_river_model, f)


def get_trade_count() -> int:
    return _trade_count
