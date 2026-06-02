#!/usr/bin/env python3
"""
Seeds Neo4j with Strategy/MacroRegime/MarketCondition nodes and Concept nodes
parsed from references/*.md.

Usage:
    python scripts/seed_neo4j.py [--references-dir ../../references]
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("seed_neo4j")


async def main(references_dir: Path) -> None:
    from knowledge.neo4j_client import driver as _driver  # ensure connected
    from knowledge.graph_builder import seed_strategies

    # Sync seed of strategy nodes
    seed_strategies()
    logger.info("Strategy nodes seeded")

    # Async seed via seeder module
    from knowledge.neo4j_client import run_query

    class _SyncClient:
        async def execute(self, cypher: str, params: dict):
            run_query(cypher, params)

    client = _SyncClient()

    from knowledge.seeder import seed_macro_regimes, seed_market_conditions
    await seed_macro_regimes(client)
    await seed_market_conditions(client)

    from knowledge.concept_parser import seed_concepts_from_references
    n = await seed_concepts_from_references(client, references_dir)
    logger.info("Seeded %d concept nodes from %s", n, references_dir)

    logger.info("Neo4j seed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--references-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent / "references",
    )
    args = parser.parse_args()
    asyncio.run(main(args.references_dir))
