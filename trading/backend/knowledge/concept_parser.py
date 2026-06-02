"""Parses references/*.md into Concept nodes linked to Strategy nodes in Neo4j."""
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STRATEGY_KEYWORDS: dict[str, list[str]] = {
    "volume_profile": ["volume profile", "vpvr", "poc", "vah", "val", "value area", "point of control"],
    "amd_session": ["amd", "accumulation", "manipulation", "distribution", "ict", "session", "asia", "london", "new york"],
    "liquidity_sweep": ["liquidity", "sweep", "equal highs", "equal lows", "stop hunt", "inducement", "smart money"],
    "order_blocks_fvg": ["order block", "fair value gap", "fvg", "imbalance", "breaker", "mitigation"],
}


def _detect_strategies(text: str) -> list[str]:
    text_lower = text.lower()
    matched = []
    for strategy, keywords in STRATEGY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(strategy)
    return matched


def parse_markdown_file(path: Path) -> list[dict]:
    """
    Extracts Concept dicts from a markdown file.
    Each H2 section becomes one Concept node.
    Returns list of {name, source, description, strategies}.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    sections = re.split(r"^#{1,2}\s+", text, flags=re.MULTILINE)
    concepts = []

    for section in sections[1:]:  # skip preamble
        lines = section.strip().splitlines()
        if not lines:
            continue
        name = lines[0].strip().rstrip("#").strip()
        body = "\n".join(lines[1:]).strip()[:500]
        strategies = _detect_strategies(name + " " + body)
        if not strategies:
            continue
        concepts.append({
            "name": name,
            "source": path.name,
            "description": body[:200],
            "strategies": strategies,
        })

    return concepts


async def seed_concepts_from_references(neo4j_client, references_dir: Path) -> int:
    """
    Walk references_dir for *.md files, parse Concept nodes, write to Neo4j.
    """
    if not references_dir.exists():
        logger.warning("References dir not found: %s", references_dir)
        return 0

    all_concepts: list[dict] = []
    for md_file in references_dir.glob("*.md"):
        concepts = parse_markdown_file(md_file)
        all_concepts.extend(concepts)
        logger.info("Parsed %d concepts from %s", len(concepts), md_file.name)

    if not all_concepts:
        return 0

    for concept in all_concepts:
        await neo4j_client.execute(
            """
            MERGE (c:Concept {name: $name})
            SET c.source = $source, c.description = $description
            """,
            {"name": concept["name"], "source": concept["source"], "description": concept["description"]},
        )
        for strategy in concept["strategies"]:
            await neo4j_client.execute(
                """
                MATCH (c:Concept {name: $cname})
                MATCH (s:Strategy {name: $sname})
                MERGE (c)-[:INFORMS]->(s)
                """,
                {"cname": concept["name"], "sname": strategy},
            )

    logger.info("Seeded %d Concept nodes", len(all_concepts))
    return len(all_concepts)
