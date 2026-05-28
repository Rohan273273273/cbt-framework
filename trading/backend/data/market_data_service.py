import json
import redis
import polars as pl
from typing import List, Optional
from datetime import datetime, timezone
from config import settings
from data.timescale_writer import fetch_ohlcv

_redis = redis.from_url(settings.redis_url, decode_responses=True)
CACHE_TTL = 90  # seconds


def get_latest_candles(symbol: str, timeframe: str, n: int = 200) -> pl.DataFrame:
    key = f"ohlcv:{symbol}:{timeframe}:{n}"
    cached = _redis.get(key)
    if cached:
        rows = json.loads(cached)
    else:
        rows = fetch_ohlcv(symbol, timeframe, limit=n)
        _redis.setex(key, CACHE_TTL, json.dumps(rows, default=str))
    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows).with_columns(
        pl.col("ts").cast(pl.Datetime("us", "UTC"))
    )


def cache_live_bar(symbol: str, timeframe: str, bar: dict):
    """Push a live bar from Alpaca WS into Redis and invalidate cache."""
    _redis.setex(f"live:{symbol}:{timeframe}", 120, json.dumps(bar, default=str))
    for n in [50, 100, 200]:
        _redis.delete(f"ohlcv:{symbol}:{timeframe}:{n}")


def get_live_price(symbol: str) -> Optional[float]:
    raw = _redis.get(f"price:{symbol}")
    return float(raw) if raw else None


def set_live_price(symbol: str, price: float):
    _redis.set(f"price:{symbol}", price, ex=10)
