import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse

import feedparser
import httpx
import redis

from config import settings
from screeners.screener_models import NewsEvent

logger = logging.getLogger(__name__)
_redis = redis.from_url(settings.redis_url, decode_responses=True)

RSS_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
    "https://feeds.ap.org/rss/APFinance.rss",
]

CRYPTO_KEYWORDS = {
    "BTC/USD": ["bitcoin", "btc", "crypto"],
    "ETH/USD": ["ethereum", "eth", "ether"],
    "SOL/USD": ["solana", "sol"],
    "AVAX/USD": ["avalanche", "avax"],
    "LINK/USD": ["chainlink", "link"],
}

HIGH_IMPACT_KEYWORDS = [
    "fed", "federal reserve", "rate hike", "rate cut", "inflation", "cpi",
    "war", "sanctions", "ban", "hack", "sec", "regulation", "etf",
    "crash", "collapse", "bankrupt",
]

_finbert_pipeline: Optional[object] = None


def _get_finbert():
    global _finbert_pipeline
    if _finbert_pipeline is None:
        from transformers import pipeline
        _finbert_pipeline = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            max_length=512, truncation=True,
        )
    return _finbert_pipeline


def _map_finbert_label(label: str) -> str:
    mapping = {"positive": "bullish", "negative": "bearish", "neutral": "neutral"}
    return mapping.get(label.lower(), "neutral")


def _score_sentiment(text: str) -> tuple:
    try:
        pipe = _get_finbert()
        result = pipe(text[:512])[0]
        sentiment = _map_finbert_label(result["label"])
        score = float(result["score"])
        return sentiment, score
    except Exception as e:
        logger.warning(f"FinBERT failed: {e}")
        return "neutral", 0.5


def _map_to_symbols(text: str) -> List[str]:
    text_lower = text.lower()
    matched = []
    for symbol, keywords in CRYPTO_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(symbol)
    return matched


def _is_high_impact(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in HIGH_IMPACT_KEYWORDS)


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _fetch_rss() -> List[dict]:
    articles = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                articles.append({
                    "url": entry.get("link", ""),
                    "headline": entry.get("title", ""),
                    "source": urlparse(feed_url).netloc,
                    "published": entry.get("published", ""),
                })
        except Exception as e:
            logger.warning(f"RSS fetch failed {feed_url}: {e}")
    return articles


def _fetch_alpha_vantage() -> List[dict]:
    if not settings.alpha_vantage_key:
        return []
    try:
        url = (f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT"
               f"&topics=blockchain,cryptocurrency&apikey={settings.alpha_vantage_key}&limit=10")
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for item in data.get("feed", [])[:10]:
            articles.append({
                "url": item.get("url", ""),
                "headline": item.get("title", ""),
                "source": item.get("source", "alpha_vantage"),
                "published": item.get("time_published", ""),
            })
        return articles
    except Exception as e:
        logger.warning(f"Alpha Vantage news failed: {e}")
        return []


def _process_article(article: dict) -> Optional[NewsEvent]:
    url = article.get("url", "")
    headline = article.get("headline", "")
    if not headline or not url:
        return None

    # Skip already-processed articles
    cache_key = f"news:seen:{_url_hash(url)}"
    if _redis.exists(cache_key):
        return None
    _redis.setex(cache_key, 86400, "1")

    affected = _map_to_symbols(headline)
    if not affected:
        return None   # Only process crypto-relevant news

    sentiment, confidence = _score_sentiment(headline)
    high_impact = _is_high_impact(headline)
    impact_score = confidence * (1.5 if high_impact else 1.0)

    return NewsEvent(
        headline=headline, source=article["source"],
        url=url, timestamp=datetime.now(timezone.utc),
        sentiment=sentiment, confidence=confidence,
        impact_score=round(impact_score, 3),
        high_impact=high_impact, affected=affected,
    )


def run_news_screener() -> List[NewsEvent]:
    all_articles = _fetch_rss() + _fetch_alpha_vantage()
    all_articles = all_articles[:30]  # cap per cycle

    events: List[NewsEvent] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(_process_article, all_articles))

    for r in results:
        if r:
            events.append(r)

    events.sort(key=lambda e: e.impact_score, reverse=True)

    if events:
        serialized = json.dumps([
            {**e.__dict__, "timestamp": e.timestamp.isoformat(),
             "affected": e.affected}
            for e in events
        ])
        _redis.setex("news:latest", 300, serialized)

        # Flag high-impact to Watchdog channel
        if any(e.high_impact for e in events):
            _redis.publish("high_impact_news", "1")
            logger.warning(f"High-impact news detected: {[e.headline for e in events if e.high_impact]}")

    logger.info(f"News screener: {len(events)} relevant events processed")
    return events


def get_cached_news() -> List[NewsEvent]:
    raw = _redis.get("news:latest")
    if not raw:
        return []
    items = json.loads(raw)
    return [
        NewsEvent(**{**i, "timestamp": datetime.fromisoformat(i["timestamp"])})
        for i in items
    ]
