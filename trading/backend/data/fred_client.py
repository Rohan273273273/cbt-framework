import logging
from datetime import datetime, timedelta
from typing import List, Dict
from config import settings

logger = logging.getLogger(__name__)

SERIES = {
    "FEDFUNDS": "Fed Funds Rate",
    "CPIAUCSL": "CPI",
    "M2SL": "M2 Money Supply",
    "DTWEXBGS": "DXY (USD Index)",
}


def fetch_fred_series(series_id: str, start_date: str = "2018-01-01") -> List[Dict]:
    if not settings.fred_api_key:
        logger.warning("FRED_API_KEY not set — skipping macro data")
        return []
    try:
        import fredapi
        fred = fredapi.Fred(api_key=settings.fred_api_key)
        data = fred.get_series(series_id, observation_start=start_date)
        return [
            {"ts": ts.to_pydatetime().replace(tzinfo=__import__("datetime").timezone.utc),
             "series_id": series_id, "value": float(v)}
            for ts, v in data.items() if v == v  # drop NaN
        ]
    except Exception as e:
        logger.error(f"FRED fetch failed for {series_id}: {e}")
        return []


def fetch_all_macro() -> List[Dict]:
    rows = []
    for series_id in SERIES:
        rows.extend(fetch_fred_series(series_id))
    return rows
