"""Seeds Neo4j with Strategy nodes and Trade history from backtest results."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

STRATEGIES = [
    {"name": "volume_profile", "description": "VPVR — POC/VAH/VAL reversion"},
    {"name": "amd_session", "description": "ICT AMD — Asia accumulate, London sweep, NY distribution"},
    {"name": "liquidity_sweep", "description": "Equal highs/lows sweep with reversal confirmation"},
    {"name": "order_blocks_fvg", "description": "Order blocks + Fair Value Gaps retest"},
]

MACRO_REGIMES = ["Bull", "Bear", "Ranging", "HighVol", "LowVol"]

MARKET_CONDITIONS = [
    {"session": "asia", "regime": "ranging"},
    {"session": "london", "regime": "trending"},
    {"session": "newyork", "regime": "trending"},
    {"session": "newyork", "regime": "ranging"},
    {"session": "overlap", "regime": "highvol"},
]


async def seed_strategies(neo4j_client) -> None:
    """Create Strategy nodes (idempotent via MERGE)."""
    for s in STRATEGIES:
        await neo4j_client.execute(
            "MERGE (s:Strategy {name: $name}) SET s.description = $desc",
            {"name": s["name"], "desc": s["description"]},
        )
    logger.info("Seeded %d Strategy nodes", len(STRATEGIES))


async def seed_macro_regimes(neo4j_client) -> None:
    for regime in MACRO_REGIMES:
        await neo4j_client.execute(
            "MERGE (m:MacroRegime {name: $name})",
            {"name": regime},
        )
    logger.info("Seeded %d MacroRegime nodes", len(MACRO_REGIMES))


async def seed_market_conditions(neo4j_client) -> None:
    for mc in MARKET_CONDITIONS:
        await neo4j_client.execute(
            "MERGE (mc:MarketCondition {session: $session, regime: $regime})",
            mc,
        )
    logger.info("Seeded %d MarketCondition nodes", len(MARKET_CONDITIONS))


async def seed_trades_batch(neo4j_client, trades: list[dict], batch_size: int = 500) -> int:
    """
    Bulk-insert Trade nodes and relationships.
    trades: list of dicts with keys: id, symbol, strategy, direction, entry, exit,
            pnl, outcome, session, regime, timestamp
    """
    total = 0
    for i in range(0, len(trades), batch_size):
        batch = trades[i : i + batch_size]
        cypher = """
        UNWIND $trades AS t
        MERGE (tr:Trade {id: t.id})
        SET tr.symbol = t.symbol,
            tr.direction = t.direction,
            tr.entry = t.entry,
            tr.exit = t.exit,
            tr.pnl = t.pnl,
            tr.outcome = t.outcome,
            tr.timestamp = t.timestamp
        WITH tr, t
        MATCH (s:Strategy {name: t.strategy})
        MERGE (tr)-[:USED_STRATEGY]->(s)
        WITH tr, t
        MATCH (mc:MarketCondition {session: t.session, regime: t.regime})
        MERGE (tr)-[:OCCURRED_DURING]->(mc)
        """
        await neo4j_client.execute(cypher, {"trades": batch})
        total += len(batch)
        logger.info("Seeded %d/%d trades", total, len(trades))

    return total


async def run_seed(neo4j_client, backtest_trades: Optional[list[dict]] = None) -> None:
    """Full seed: strategies + regimes + market conditions + optional trades."""
    await seed_strategies(neo4j_client)
    await seed_macro_regimes(neo4j_client)
    await seed_market_conditions(neo4j_client)

    if backtest_trades:
        n = await seed_trades_batch(neo4j_client, backtest_trades)
        logger.info("Seeded %d total Trade nodes", n)
    else:
        logger.info("No backtest trades provided — skipping trade seed")
