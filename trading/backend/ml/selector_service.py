"""
Strategy Selector — blends LightGBM + River, respects Watchdog state.
Blend ratio shifts from LightGBM-dominant to adaptive as River accumulates data.
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from ml import lgbm_selector, river_updater
from ml.feature_builder import build_features
from risk.watchdog import get_all_states, STATE_PAUSED, get_size_multiplier
from config import settings

logger = logging.getLogger(__name__)

STRATEGY_CLASSES = ["volume_profile", "amd_session", "liquidity_sweep", "order_blocks_fvg"]
MIN_PROB_FLOOR = 0.10   # Prevent any strategy from being at 0%


@dataclass
class StrategySelection:
    strategy: str
    confidence: float
    lgbm_prob: float
    river_prob: float
    blend_weight_lgbm: float
    size_multiplier: float
    reason: str
    all_probs: Dict[str, float]


def _get_blend_weights() -> tuple:
    """Returns (lgbm_weight, river_weight) based on River trade count."""
    count = river_updater.get_trade_count()
    if count < 30:
        return 0.85, 0.15
    elif count < 90:
        return 0.70, 0.30
    else:
        return 0.55, 0.45


def select(features: Dict[str, float],
           available_signals: Optional[List[str]] = None) -> Optional[StrategySelection]:
    """
    Returns the best strategy to trade, or None if confidence < threshold.
    available_signals: strategies that have a valid Signal (direction != 0).
    """
    lgbm_probs = lgbm_selector.predict(features)
    river_probs = river_updater.predict(features)
    watchdog_states = get_all_states()
    lgbm_w, river_w = _get_blend_weights()

    combined = {}
    for s in STRATEGY_CLASSES:
        # Skip PAUSED strategies
        if watchdog_states.get(s) == STATE_PAUSED:
            combined[s] = 0.0
            continue
        # Only consider strategies that have an actual signal right now
        if available_signals is not None and s not in available_signals:
            combined[s] = 0.0
            continue

        lgbm_p = max(MIN_PROB_FLOOR, lgbm_probs.get(s, 0.25))
        river_p = max(MIN_PROB_FLOOR, river_probs.get(s, 0.25))
        combined[s] = lgbm_w * lgbm_p + river_w * river_p

    if all(v == 0.0 for v in combined.values()):
        logger.info("Selector: all strategies unavailable — FLAT")
        return None

    best = max(combined, key=combined.get)
    best_score = combined[best]

    if best_score < settings.ml_confidence_threshold:
        logger.info(f"Selector: best={best} score={best_score:.3f} < threshold — FLAT")
        return None

    size_mult = get_size_multiplier(best)
    reason = (f"LightGBM={lgbm_probs.get(best, 0):.2f}, "
              f"River={river_probs.get(best, 0):.2f}, "
              f"blend={lgbm_w:.0%}/{river_w:.0%}, "
              f"watchdog={watchdog_states.get(best, 'NORMAL')}")

    return StrategySelection(
        strategy=best, confidence=best_score,
        lgbm_prob=lgbm_probs.get(best, 0),
        river_prob=river_probs.get(best, 0),
        blend_weight_lgbm=lgbm_w,
        size_multiplier=size_mult,
        reason=reason,
        all_probs=combined,
    )
