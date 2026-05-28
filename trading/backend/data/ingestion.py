"""
Historical OHLCV ingestion via CCXT + Binance public API.
Idempotent: checks last stored timestamp before fetching.
Resumable: saves checkpoint to /app/data/ingest_checkpoint.json
"""

import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

import ccxt
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_exponential

from data.timescale_writer import upsert_ohlcv, get_last_ohlcv_ts

logger = logging.getLogger(__name__)

CHECKPOINT_PATH = Path("/app/data/ingest_checkpoint.json")
TIMEFRAMES = ["15m", "1h", "4h"]
DEFAULT_SINCE_DAYS = 2555   # ~7 years


def _load_checkpoint() -> Dict:
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {}


def _save_checkpoint(state: Dict):
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps(state, indent=2))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=16))
def _fetch_batch(exchange: ccxt.Exchange, symbol: str, timeframe: str,
                 since_ms: int, limit: int = 1000) -> List:
    return exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)


def ingest_symbol(exchange: ccxt.Exchange, symbol: str, timeframe: str,
                  since_days: int = DEFAULT_SINCE_DAYS) -> int:
    """Fetch and store all bars for one symbol/timeframe. Returns rows written."""
    checkpoint = _load_checkpoint()
    key = f"{symbol}:{timeframe}"

    # Start from last stored bar, or from `since_days` ago
    last_ts = get_last_ohlcv_ts(symbol, timeframe)
    if last_ts:
        since_ms = int(last_ts.timestamp() * 1000) + 1
    else:
        since_ms = int((time.time() - since_days * 86400) * 1000)

    if key in checkpoint and not last_ts:
        since_ms = checkpoint[key]

    now_ms = int(time.time() * 1000)
    total_written = 0

    tf_ms = exchange.parse_timeframe(timeframe) * 1000
    estimated_batches = max(1, (now_ms - since_ms) // (tf_ms * 1000))

    with tqdm(total=estimated_batches, desc=f"{symbol} {timeframe}", unit="batch") as pbar:
        while since_ms < now_ms:
            try:
                candles = _fetch_batch(exchange, symbol, timeframe, since_ms)
            except Exception as e:
                logger.error(f"Failed fetching {symbol} {timeframe}: {e}")
                break

            if not candles:
                break

            rows = [
                {
                    "ts": datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc),
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "open": c[1], "high": c[2], "low": c[3], "close": c[4],
                    "volume": c[5],
                }
                for c in candles
            ]
            written = upsert_ohlcv(rows)
            total_written += written

            since_ms = candles[-1][0] + tf_ms
            checkpoint[key] = since_ms
            _save_checkpoint(checkpoint)

            pbar.update(1)
            time.sleep(exchange.rateLimit / 1000)

    logger.info(f"Ingested {total_written} rows for {symbol} {timeframe}")
    return total_written


def ingest_all(symbols: List[str], timeframes: List[str] = TIMEFRAMES,
               since_days: int = DEFAULT_SINCE_DAYS) -> Dict:
    exchange = ccxt.binance({"enableRateLimit": True})
    results = {}
    for symbol in symbols:
        for tf in timeframes:
            ccxt_symbol = symbol.replace("/USD", "/USDT")
            count = ingest_symbol(exchange, ccxt_symbol, tf, since_days)
            results[f"{symbol}:{tf}"] = count
    return results
