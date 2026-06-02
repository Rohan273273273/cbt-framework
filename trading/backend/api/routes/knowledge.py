from fastapi import APIRouter, Query

from knowledge.graph_builder import query_similar

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/similar")
def get_similar(strategy: str = Query(...), limit: int = Query(5, ge=1, le=20)):
    trades = query_similar({"selection": {"strategy": strategy}}, limit=limit)
    return {"trades": trades}


@router.get("/strategies")
def get_strategies():
    from knowledge.neo4j_client import run_query
    rows = run_query(
        "MATCH (s:Strategy) RETURN s.name as name, s.win_rate as win_rate, s.total_trades as total_trades",
        {}
    )
    return {"strategies": rows or []}
