from fastapi import APIRouter
from screeners.crypto_screener import get_cached_results
from screeners.news_screener import get_cached_news

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("/results")
def get_screener():
    return [r.__dict__ for r in get_cached_results()]


@router.get("/news")
def get_news():
    events = get_cached_news()
    return [
        {**e.__dict__, "timestamp": e.timestamp.isoformat(), "affected": e.affected}
        for e in events
    ]
