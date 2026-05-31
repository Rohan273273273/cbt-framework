#!/usr/bin/env python3
"""Pre-flight check. Prints READY or lists failures."""
import sys
sys.path.insert(0, "/app")

failures = []

print("Running health checks...")

# 1. TimescaleDB
try:
    import psycopg2
    from config import settings
    conn = psycopg2.connect(settings.timescale_url)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ohlcv")
    count = cur.fetchone()[0]
    conn.close()
    print(f"  ✓ TimescaleDB: {count:,} OHLCV rows")
except Exception as e:
    print(f"  ✗ TimescaleDB: {e}")
    failures.append("TimescaleDB")

# 2. Redis
try:
    import redis
    r = redis.from_url(settings.redis_url)
    r.ping()
    print("  ✓ Redis: connected")
except Exception as e:
    print(f"  ✗ Redis: {e}")
    failures.append("Redis")

# 3. Neo4j
try:
    from knowledge.neo4j_client import run_query
    result = run_query("MATCH (s:Strategy) RETURN count(s) as n")
    n = result[0]["n"] if result else 0
    print(f"  ✓ Neo4j: {n} Strategy nodes")
except Exception as e:
    print(f"  ✗ Neo4j: {e}")
    failures.append("Neo4j")

# 4. LightGBM model
try:
    import os
    if os.path.exists(settings.ml_lgbm_model_path):
        import joblib
        m = joblib.load(settings.ml_lgbm_model_path)
        print(f"  ✓ LightGBM model: loaded")
    else:
        print(f"  ⚠ LightGBM model: not found (run pretrain_lgbm.py first)")
except Exception as e:
    print(f"  ✗ LightGBM: {e}")

# 5. Alpaca paper API
try:
    from gateway.alpaca_gateway import gateway
    acc = gateway.get_account()
    print(f"  ✓ Alpaca: equity=${acc['equity']:,.2f} (paper={settings.paper})")
except Exception as e:
    print(f"  ✗ Alpaca: {e}")
    failures.append("Alpaca")

# 6. Ollama
try:
    import httpx
    resp = httpx.get(f"{settings.ollama_host}/api/tags", timeout=5)
    models = [m["name"] for m in resp.json().get("models", [])]
    if settings.ollama_model in models or any(settings.ollama_model in m for m in models):
        print(f"  ✓ Ollama: {settings.ollama_model} available")
    else:
        print(f"  ⚠ Ollama: model {settings.ollama_model} not yet pulled (will pull on first use)")
except Exception as e:
    print(f"  ⚠ Ollama: {e} (agents will use fallback reasoning)")

print()
if failures:
    print(f"FAILED: {failures}")
    sys.exit(1)
else:
    print("✓ READY FOR PAPER TRADING")
