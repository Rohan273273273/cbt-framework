from neo4j import GraphDatabase
from config import settings

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=("neo4j", settings.neo4j_password),
        )
    return _driver


def run_query(cypher: str, params: dict = None):
    with get_driver().session() as session:
        result = session.run(cypher, params or {})
        return [dict(r) for r in result]


def close():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
