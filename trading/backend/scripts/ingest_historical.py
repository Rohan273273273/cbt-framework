#!/usr/bin/env python3
"""One-shot 7yr historical data ingestion. Resumable."""
import sys
sys.path.insert(0, "/app")
sys.path.insert(0, "/app/cbt_engine")

from data.ingestion import ingest_all
from config import settings

if __name__ == "__main__":
    symbols = settings.crypto_symbol_list
    print(f"Ingesting 7yr history for: {symbols}")
    results = ingest_all(symbols)
    total = sum(results.values())
    print(f"\nDone. Total rows written: {total:,}")
    for k, v in results.items():
        print(f"  {k}: {v:,} rows")
