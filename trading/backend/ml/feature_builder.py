"""
Builds the 35-dim feature vector used by both LightGBM and River.
All features use only past data — zero lookahead.
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import numpy as np
import redis

from config import settings

_redis = redis.from_url(settings.redis_url, decode_responses=True)


def _safe(arr, idx=-1, default=0.0):
    try:
        val = arr[idx]
        return float(val) if val == val else default  # NaN check
    except Exception:
        return default


def build_features(
    candles_1h,  # polars DataFrame
    screener_result=None,
    news_sentiment_score: float = 0.0,
    high_impact_news: bool = False,
    macro_snapshot: Optional[Dict] = None,
) -> Dict[str, float]:
    closes = candles_1h["close"].to_numpy() if not candles_1h.is_empty() else np.array([])
    highs = candles_1h["high"].to_numpy() if not candles_1h.is_empty() else np.array([])
    lows = candles_1h["low"].to_numpy() if not candles_1h.is_empty() else np.array([])
    vols = candles_1h["volume"].fill_null(0).to_numpy() if not candles_1h.is_empty() else np.array([])

    n = len(closes)
    now = datetime.now(timezone.utc)
    macro = macro_snapshot or {}

    def rsi(period=14):
        if n < period + 1:
            return 50.0
        deltas = np.diff(closes[-period-1:])
        gains = deltas[deltas > 0].sum() / period
        losses = -deltas[deltas < 0].sum() / period
        if losses == 0:
            return 100.0
        return float(100 - 100 / (1 + gains / losses))

    def atr(period=14):
        if n < period + 1:
            return 0.0
        tr = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
              for i in range(max(1, n-period-1), n)]
        return float(sum(tr) / len(tr)) if tr else 0.0

    def sma(period):
        return float(closes[-period:].mean()) if n >= period else _safe(closes)

    atr_val = atr()
    price = _safe(closes)
    rsi_val = rsi()
    sma20 = sma(20)
    sma50 = sma(50)
    avg_vol = float(vols[-20:].mean()) if n >= 20 else 1.0
    cur_vol = _safe(vols)

    features = {
        # Time
        "hour_sin": float(np.sin(2 * np.pi * now.hour / 24)),
        "hour_cos": float(np.cos(2 * np.pi * now.hour / 24)),
        "dow_sin": float(np.sin(2 * np.pi * now.weekday() / 7)),
        "dow_cos": float(np.cos(2 * np.pi * now.weekday() / 7)),
        "is_ny_session": float(13 <= now.hour < 17),
        "is_london_session": float(2 <= now.hour < 5),
        "is_asia_session": float(now.hour >= 20 or now.hour < 0),

        # Price
        "rsi": rsi_val,
        "rsi_norm": (rsi_val - 50) / 50,
        "atr_pct": (atr_val / price * 100) if price > 0 else 0.0,
        "price_vs_sma20": ((price - sma20) / sma20 * 100) if sma20 > 0 else 0.0,
        "price_vs_sma50": ((price - sma50) / sma50 * 100) if sma50 > 0 else 0.0,
        "sma_cross": float(sma20 > sma50),
        "momentum_1h": float((closes[-1] - closes[-2]) / closes[-2] * 100) if n >= 2 else 0.0,
        "momentum_4h": float((closes[-1] - closes[-5]) / closes[-5] * 100) if n >= 5 else 0.0,
        "momentum_24h": float((closes[-1] - closes[-25]) / closes[-25] * 100) if n >= 25 else 0.0,
        "high_low_range_pct": float((highs[-1] - lows[-1]) / lows[-1] * 100) if _safe(lows) > 0 else 0.0,

        # Volume
        "rel_volume": float(cur_vol / avg_vol) if avg_vol > 0 else 1.0,
        "volume_trend": float((vols[-5:].mean() - vols[-20:-5].mean()) / vols[-20:-5].mean())
                        if n >= 20 else 0.0,

        # Screener
        "screener_score": float(screener_result.composite_score / 100) if screener_result else 0.5,
        "screener_trend_bull": float(getattr(screener_result, "trend", "") == "bullish"),
        "screener_trend_bear": float(getattr(screener_result, "trend", "") == "bearish"),

        # News
        "news_sentiment": news_sentiment_score,
        "high_impact_news": float(high_impact_news),

        # Macro (FRED / COT — 0 if unavailable)
        "fed_rate": float(macro.get("FEDFUNDS", 5.0)),
        "cpi_yoy": float(macro.get("CPIAUCSL", 3.0)),
        "m2_growth": float(macro.get("M2SL_growth", 0.0)),
        "dxy": float(macro.get("DTWEXBGS", 100.0)),

        # COT
        "cot_commercial_net": float(macro.get("cot_commercial_net", 0.0)),
        "cot_large_spec_net": float(macro.get("cot_large_spec_net", 0.0)),
    }

    return features


def features_to_array(features: Dict[str, float]) -> list:
    FEATURE_ORDER = [
        "hour_sin", "hour_cos", "dow_sin", "dow_cos",
        "is_ny_session", "is_london_session", "is_asia_session",
        "rsi", "rsi_norm", "atr_pct",
        "price_vs_sma20", "price_vs_sma50", "sma_cross",
        "momentum_1h", "momentum_4h", "momentum_24h", "high_low_range_pct",
        "rel_volume", "volume_trend",
        "screener_score", "screener_trend_bull", "screener_trend_bear",
        "news_sentiment", "high_impact_news",
        "fed_rate", "cpi_yoy", "m2_growth", "dxy",
        "cot_commercial_net", "cot_large_spec_net",
    ]
    return [features.get(k, 0.0) for k in FEATURE_ORDER]
