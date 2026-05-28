import psycopg2
import psycopg2.extras
from typing import List, Dict, Any
from config import settings


def get_connection():
    return psycopg2.connect(settings.timescale_url)


def upsert_ohlcv(rows: List[Dict[str, Any]]) -> int:
    """Upsert OHLCV rows. Returns count inserted/updated."""
    if not rows:
        return 0
    sql = """
        INSERT INTO ohlcv (ts, symbol, timeframe, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (ts, symbol, timeframe) DO UPDATE
            SET open=EXCLUDED.open, high=EXCLUDED.high,
                low=EXCLUDED.low, close=EXCLUDED.close,
                volume=EXCLUDED.volume
    """
    data = [
        (r["ts"], r["symbol"], r["timeframe"],
         r["open"], r["high"], r["low"], r["close"], r.get("volume"))
        for r in rows
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, data, page_size=500)
    return len(data)


def upsert_macro(rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    sql = """
        INSERT INTO macro_data (ts, series_id, value)
        VALUES %s
        ON CONFLICT (ts, series_id) DO UPDATE SET value=EXCLUDED.value
    """
    data = [(r["ts"], r["series_id"], r["value"]) for r in rows]
    with get_connection() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, data, page_size=500)
    return len(data)


def get_last_ohlcv_ts(symbol: str, timeframe: str):
    """Returns the most recent timestamp for a symbol+timeframe, or None."""
    sql = "SELECT MAX(ts) FROM ohlcv WHERE symbol=%s AND timeframe=%s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (symbol, timeframe))
            row = cur.fetchone()
    return row[0] if row else None


def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 500) -> List[Dict]:
    sql = """
        SELECT ts, open, high, low, close, volume
        FROM ohlcv
        WHERE symbol=%s AND timeframe=%s
        ORDER BY ts DESC
        LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (symbol, timeframe, limit))
            rows = cur.fetchall()
    return [dict(r) for r in reversed(rows)]
