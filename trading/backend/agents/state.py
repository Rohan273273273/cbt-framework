from typing import TypedDict, List, Dict, Any, Optional
from dataclasses import dataclass, field


class AgentState(TypedDict):
    cycle_id: str
    timestamp: str
    symbols: List[str]

    # Populated by ScreenerAgent
    screener_results: List[Dict]

    # Populated by NewsAgent
    news_events: List[Dict]
    news_sentiment_avg: float
    high_impact_news: bool

    # Populated by StrategyAgents
    strategy_signals: Dict[str, Dict]   # {strategy_name: Signal.__dict__}
    available_strategies: List[str]     # strategies with direction != 0

    # Populated by SelectorAgent
    selection: Optional[Dict]           # StrategySelection.__dict__ or None
    top_symbol: Optional[str]

    # Populated by RiskAgent
    risk_approved: bool
    risk_reason: str
    order_qty: float
    order_entry: float
    order_tp: float
    order_sl: float

    # Populated by execution
    order_result: Optional[Dict]

    # Populated by WatchdogAgent
    watchdog_states: Dict[str, str]

    # Populated by MemoryAgent
    similar_past_trades: List[Dict]
    memory_written: bool

    # Running agent log (appended by each node)
    agent_logs: List[str]
