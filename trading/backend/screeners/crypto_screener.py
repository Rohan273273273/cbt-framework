import json
import logging
from typing import List

import redis

from config import settings
from data.market_data_service import get_latest_candles
from screeners.screener_models import ScreenerResult

logger = logging.getLogger(__name__)
_redis = redis.from_url(settings.redis_url, decode_responses=True)

CACHE_KEY = "screener:results"
CACHE_TTL = 90


def _relative_volume(candles) -> float:
    if len(candles) < 21:
        return 1.0
    vols = candles["volume"].fill_null(0).to_numpy()
    avg = vols[-21:-1].mean()
    current = vols[-1]
    return float(current / avg) if avg > 0 else 1.0


def _atr_pct(candles) -> float:
    h = candles["high"].to_numpy()
    l = candles["low"].to_numpy()
    c = candles["close"].to_numpy()
    if len(c) < 15:
        return 0.0
    tr = [max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])) for i in range(1, len(c))]
    atr = sum(tr[-14:]) / 14
    return float(atr / c[-1] * 100)


def _rsi(candles, period=14) -> float:
    closes = candles["close"].to_numpy()
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i]-closes[i-1] for i in range(1, len(closes))]
    gains = [d for d in deltas[-period:] if d > 0]
    losses = [-d for d in deltas[-period:] if d < 0]
    avg_gain = sum(gains)/period if gains else 0
    avg_loss = sum(losses)/period if losses else 0.0001
    rs = avg_gain / avg_loss
    return float(100 - 100/(1+rs))


def _momentum(candles) -> float:
    c = candles["close"].to_numpy()
    if len(c) < 20:
        return 0.0
    return float((c[-1] - c[-20]) / c[-20] * 100)


def run_screener() -> List[ScreenerResult]:
    results = []
    for symbol in settings.crypto_symbol_list:
        try:
            candles = get_latest_candles(symbol, "1h", 100)
            if candles.is_empty() or len(candles) < 25:
                continue

            rel_vol = _relative_volume(candles)
            atr_pct = _atr_pct(candles)
            rsi = _rsi(candles)
            momentum = _momentum(candles)

            # Filters
            if atr_pct < 1.0 or rel_vol < 0.8:
                continue

            # Score 0-100
            vol_score = min(30, rel_vol * 10)
            atr_score = min(25, atr_pct * 5)
            mom_score = min(25, abs(momentum) * 2)
            rsi_score = 20 if 35 < rsi < 65 else 10 if 25 < rsi < 75 else 0
            composite = vol_score + atr_score + mom_score + rsi_score

            trend = "bullish" if momentum > 0 and rsi > 50 else \
                    "bearish" if momentum < 0 and rsi < 50 else "neutral"

            results.append(ScreenerResult(
                symbol=symbol, rel_volume=round(rel_vol, 2),
                atr_pct=round(atr_pct, 2), rsi=round(rsi, 1),
                momentum_score=round(momentum, 2),
                composite_score=round(composite, 1), trend=trend,
            ))
        except Exception as e:
            logger.warning(f"Screener failed for {symbol}: {e}")

    results.sort(key=lambda x: x.composite_score, reverse=True)

    serialized = json.dumps([r.__dict__ for r in results])
    _redis.setex(CACHE_KEY, CACHE_TTL, serialized)
    logger.info(f"Screener: {len(results)} assets ranked")
    return results


def get_cached_results() -> List[ScreenerResult]:
    raw = _redis.get(CACHE_KEY)
    if not raw:
        return run_screener()
    data = json.loads(raw)
    return [ScreenerResult(**d) for d in data]
