from agents.state import AgentState
from screeners.news_screener import get_cached_news


def run(state: AgentState) -> AgentState:
    events = get_cached_news()
    state["news_events"] = [
        {**e.__dict__, "timestamp": e.timestamp.isoformat(), "affected": e.affected}
        for e in events
    ]
    if events:
        avg_sent = sum(
            1 if e.sentiment == "bullish" else -1 if e.sentiment == "bearish" else 0
            for e in events
        ) / len(events)
    else:
        avg_sent = 0.0

    state["news_sentiment_avg"] = avg_sent
    state["high_impact_news"] = any(e.high_impact for e in events)

    state["agent_logs"].append(
        f"NewsAgent: {len(events)} events, sentiment_avg={avg_sent:.2f}, "
        f"high_impact={'YES' if state['high_impact_news'] else 'no'}"
    )
    return state
