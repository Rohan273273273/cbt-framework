import logging
from datetime import datetime, timezone
from typing import Dict, List

from knowledge.neo4j_client import run_query

logger = logging.getLogger(__name__)

STRATEGY_NAMES = ["volume_profile", "amd_session", "liquidity_sweep", "order_blocks_fvg"]


def seed_strategies():
    for name in STRATEGY_NAMES:
        run_query(
            "MERGE (s:Strategy {name: $name}) "
            "ON CREATE SET s.win_rate=0.0, s.total_trades=0, s.created_at=$ts",
            {"name": name, "ts": datetime.now(timezone.utc).isoformat()}
        )


def write_cycle(state: Dict):
    """Write agent cycle decision to Neo4j."""
    cycle_id = state.get("cycle_id", "unknown")
    selection = state.get("selection")
    if not selection:
        return

    strategy = selection.get("strategy", "unknown")
    order = state.get("order_result")

    params = {
        "cycle_id": cycle_id,
        "ts": state.get("timestamp"),
        "symbol": state.get("top_symbol", ""),
        "strategy": strategy,
        "confidence": selection.get("confidence", 0),
        "approved": state.get("risk_approved", False),
        "risk_reason": state.get("risk_reason", ""),
        "news_sentiment": state.get("news_sentiment_avg", 0),
        "high_impact": state.get("high_impact_news", False),
        "order_placed": order is not None and order.get("status") == "accepted",
    }

    run_query("""
        MERGE (s:Strategy {name: $strategy})
        CREATE (c:Cycle {
            id: $cycle_id, ts: $ts, symbol: $symbol,
            confidence: $confidence, approved: $approved,
            risk_reason: $risk_reason, order_placed: $order_placed
        })
        CREATE (c)-[:USED_STRATEGY]->(s)
        CREATE (n:NewsSnapshot {sentiment: $news_sentiment, high_impact: $high_impact, ts: $ts})
        CREATE (c)-[:HAD_NEWS]->(n)
    """, params)


def write_trade_outcome(trade_id: str, strategy: str, symbol: str,
                        pnl: float, direction: int, won: bool,
                        entry: float, exit_price: float):
    """Called when a trade closes."""
    run_query("""
        MERGE (s:Strategy {name: $strategy})
        CREATE (t:Trade {
            id: $trade_id, symbol: $symbol, pnl: $pnl,
            direction: $direction, outcome: $outcome,
            entry: $entry, exit: $exit, ts: $ts
        })
        CREATE (t)-[:USED_STRATEGY]->(s)
        WITH s, t
        SET s.total_trades = coalesce(s.total_trades, 0) + 1,
            s.win_rate = CASE
                WHEN $won THEN (s.win_rate * (s.total_trades - 1) + 1.0) / s.total_trades
                ELSE (s.win_rate * (s.total_trades - 1)) / s.total_trades
            END
    """, {
        "trade_id": trade_id, "strategy": strategy, "symbol": symbol,
        "pnl": pnl, "direction": direction, "outcome": "win" if won else "loss",
        "entry": entry, "exit": exit_price,
        "ts": datetime.now(timezone.utc).isoformat(), "won": won,
    })


def query_similar(state: Dict, limit: int = 5) -> List[Dict]:
    """Find similar past trade cycles."""
    strategy = (state.get("selection") or {}).get("strategy", "")
    if not strategy:
        return []
    try:
        return run_query("""
            MATCH (t:Trade)-[:USED_STRATEGY]->(s:Strategy {name: $strategy})
            RETURN t.symbol as symbol, t.pnl as pnl, t.outcome as outcome,
                   t.entry as entry, t.ts as ts
            ORDER BY t.ts DESC
            LIMIT $limit
        """, {"strategy": strategy, "limit": limit})
    except Exception as e:
        logger.warning(f"Neo4j query failed: {e}")
        return []
