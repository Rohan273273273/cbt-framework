"""
Historical OHLCV ingestion.
Primary: yfinance (reliable, no auth)
  - 15m: last 59 days (API hard limit)
  - 1h/4h: last 729 days (resampled from 1h)
Fallback: CCXT Kraken for older 1h data
Idempotent: checks last stored timestamp before fetching.
Resumable: saves checkpoint to /app/data/ingest_checkpoint.json
"""

import json
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict

import pandas as pd

from data.timescale_writer import upsert_ohlcv, get_last_ohlcv_ts

logger = logging.getLogger(__name__)

CHECKPOINT_PATH = Path("/app/data/ingest_checkpoint.json")
TIMEFRAMES = ["15m", "1h", "4h"]
DEFAULT_SINCE_DAYS = 2555  # ~7 years

# yfinance interval map
YF_INTERVAL = {
    "15m": "15m",
    "1h": "1h",
    "4h": "1h",   # yfinance has no 4h; we resample from 1h
}

# yfinance only allows 60-day history for intraday < 1h; 730-day for 1h
YF_MAX_DAYS = {
    "15m": 59,
    "1h": 729,
    "4h": 729,
}

# CCXT tf string → pandas resample rule
RESAMPLE_RULE = {
    "15m": None,
    "1h": None,
    "4h": "4h",
}


def _load_checkpoint() -> Dict:
    if CHECKPOINT_PATH.exists():
        try:
            return json.loads(CHECKPOINT_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_checkpoint(state: Dict):
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps(state, indent=2))


def _yf_symbol(symbol: str) -> str:
    """BTC/USD → BTC-USD"""
    return symbol.replace("/", "-")


def _fetch_yfinance(symbol: str, timeframe: str, start: datetime, end: datetime) -> List[Dict]:
    """Fetch via yfinance in chunks respecting API limits."""
    import yfinance as yf

    yf_sym = _yf_symbol(symbol)
    interval = YF_INTERVAL[timeframe]
    max_days = YF_MAX_DAYS[timeframe]

    rows: List[Dict] = []
    chunk_start = start
    now = end

    while chunk_start < now:
        chunk_end = min(chunk_start + timedelta(days=max_days), now)
        print(f"  yfinance {yf_sym} {interval}  {chunk_start.date()} → {chunk_end.date()}", flush=True)
        try:
            df = yf.download(
                yf_sym,
                start=chunk_start.strftime("%Y-%m-%d"),
                end=chunk_end.strftime("%Y-%m-%d"),
                interval=interval,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        except Exception as e:
            print(f"  yfinance error: {e}", flush=True)
            chunk_start = chunk_end
            time.sleep(2)
            continue

        if df is None or df.empty:
            print(f"  yfinance returned empty", flush=True)
            chunk_start = chunk_end
            time.sleep(1)
            continue

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Resample 1h → 4h if needed
        rule = RESAMPLE_RULE.get(timeframe)
        if rule:
            df = df.resample(rule, closed="left", label="left").agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }).dropna()

        for ts, row in df.iterrows():
            if isinstance(ts, pd.Timestamp):
                dt = ts.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
            rows.append({
                "ts": dt,
                "symbol": symbol,
                "timeframe": timeframe,
                "open": float(row.get("Open", row.get("open", 0))),
                "high": float(row.get("High", row.get("high", 0))),
                "low": float(row.get("Low", row.get("low", 0))),
                "close": float(row.get("Close", row.get("close", 0))),
                "volume": float(row.get("Volume", row.get("volume", 0))),
            })

        print(f"  got {len(df)} rows this chunk", flush=True)
        chunk_start = chunk_end
        time.sleep(0.5)

    return rows


def _fetch_ccxt(symbol: str, timeframe: str, start: datetime, end: datetime) -> List[Dict]:
    """Fetch via CCXT Kraken in 720-bar batches (Kraken max limit)."""
    import ccxt

    exchange = ccxt.kraken({"enableRateLimit": True})
    ccxt_symbol = symbol  # Kraken uses BTC/USD directly
    tf_seconds = exchange.parse_timeframe(timeframe)
    tf_ms = tf_seconds * 1000
    batch_size = 720

    since_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    rows: List[Dict] = []

    while since_ms < end_ms:
        print(f"  kraken {ccxt_symbol} {timeframe} since {datetime.fromtimestamp(since_ms/1000, tz=timezone.utc).date()}", flush=True)
        try:
            candles = exchange.fetch_ohlcv(ccxt_symbol, timeframe, since=since_ms, limit=batch_size)
        except Exception as e:
            print(f"  kraken error: {e}", flush=True)
            time.sleep(5)
            break

        if not candles:
            print(f"  kraken returned empty", flush=True)
            break

        print(f"  got {len(candles)} candles", flush=True)
        for c in candles:
            rows.append({
                "ts": datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc),
                "symbol": symbol,
                "timeframe": timeframe,
                "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5],
            })

        since_ms = candles[-1][0] + tf_ms
        time.sleep(max(1.0, exchange.rateLimit / 1000))

    return rows


def ingest_symbol(symbol: str, timeframe: str, since_days: int = DEFAULT_SINCE_DAYS) -> int:
    """Fetch and store all bars for one symbol/timeframe. Returns rows written."""
    print(f"\n=== {symbol} {timeframe} ===", flush=True)

    end = datetime.now(timezone.utc)

    # yfinance hard limits: 59 days for 15m, 729 days for 1h/4h
    yf_limit_days = YF_MAX_DAYS.get(timeframe, since_days)
    yf_earliest = end - timedelta(days=yf_limit_days)

    last_ts = get_last_ohlcv_ts(symbol, timeframe)
    if last_ts:
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        start = last_ts + timedelta(seconds=1)
        print(f"  resuming from {start.date()}", flush=True)
    else:
        # For yfinance, can't go further back than its limit
        start = max(
            end - timedelta(days=since_days),
            yf_earliest
        )
        print(f"  starting from {start.date()} (yfinance limit: {yf_limit_days}d)", flush=True)

    if start >= end:
        print(f"  already up to date", flush=True)
        return 0

    # Try yfinance (only works if start is within yf_earliest)
    if start >= yf_earliest - timedelta(days=1):
        rows = _fetch_yfinance(symbol, timeframe, start, end)
    else:
        print(f"  start {start.date()} beyond yfinance limit, using kraken directly", flush=True)
        rows = []
    if not rows:
        print(f"  yfinance returned 0 rows, trying ccxt...", flush=True)
        rows = _fetch_ccxt(symbol, timeframe, start, end)

    if not rows:
        print(f"  no data from any source", flush=True)
        return 0

    # Deduplicate by ts
    seen = set()
    unique_rows = []
    for r in rows:
        key = (r["ts"], r["symbol"], r["timeframe"])
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)

    # Batch upsert
    batch_size = 2000
    total_written = 0
    for i in range(0, len(unique_rows), batch_size):
        batch = unique_rows[i:i + batch_size]
        written = upsert_ohlcv(batch)
        total_written += written
        print(f"  upserted batch {i//batch_size + 1}: {written} rows", flush=True)

    print(f"  TOTAL written: {total_written}", flush=True)

    # Update checkpoint
    checkpoint = _load_checkpoint()
    checkpoint[f"{symbol}:{timeframe}"] = int(end.timestamp() * 1000)
    _save_checkpoint(checkpoint)

    return total_written


def ingest_all(symbols: List[str], timeframes: List[str] = TIMEFRAMES,
               since_days: int = DEFAULT_SINCE_DAYS) -> Dict:
    results = {}
    for symbol in symbols:
        for tf in timeframes:
            count = ingest_symbol(symbol, tf, since_days)
            results[f"{symbol}:{tf}"] = count
    return results
