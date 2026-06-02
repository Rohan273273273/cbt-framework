"""
CFTC Commitment of Traders — free weekly CSV download.
https://www.cftc.gov/dea/newcot/deacot.zip
"""
import io
import logging
import zipfile
from datetime import datetime, timezone
from typing import List, Dict

import httpx

logger = logging.getLogger(__name__)

CFTC_URL = "https://www.cftc.gov/dea/newcot/deacot.zip"
TARGET_MARKETS = ["BITCOIN", "ETHER"]


def fetch_cot_data() -> List[Dict]:
    try:
        resp = httpx.get(CFTC_URL, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            name = [n for n in zf.namelist() if n.endswith(".txt")][0]
            content = zf.read(name).decode("latin-1")
    except Exception as e:
        logger.error(f"COT fetch failed: {e}")
        return []

    rows = []
    lines = content.splitlines()
    header = [h.strip().lower() for h in lines[0].split(",")]

    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < len(header):
            continue
        record = dict(zip(header, parts))
        market = record.get("market_and_exchange_names", "").upper()
        if not any(m in market for m in TARGET_MARKETS):
            continue
        try:
            report_date = datetime.strptime(
                record.get("as_of_date_in_form_yymmdd", ""), "%y%m%d"
            ).replace(tzinfo=timezone.utc)
            rows.append({
                "report_date": report_date.date(),
                "market": market[:50],
                "commercial_long": int(record.get("comm_positions_long_all", 0) or 0),
                "commercial_short": int(record.get("comm_positions_short_all", 0) or 0),
                "commercial_net": int(record.get("comm_positions_long_all", 0) or 0)
                                  - int(record.get("comm_positions_short_all", 0) or 0),
                "large_spec_long": int(record.get("noncomm_positions_long_all", 0) or 0),
                "large_spec_short": int(record.get("noncomm_positions_short_all", 0) or 0),
                "large_spec_net": int(record.get("noncomm_positions_long_all", 0) or 0)
                                  - int(record.get("noncomm_positions_short_all", 0) or 0),
            })
        except Exception:
            continue
    return rows
