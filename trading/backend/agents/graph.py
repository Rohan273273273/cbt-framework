"""
LangGraph StateGraph — wires all 8 agents into a single execution cycle.
"""
import uuid
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents import (
    coordinator, screener_agent, news_agent,
    strategy_agents, selector_agent, risk_agent,
    watchdog_agent, memory_agent,
)
from config import settings


def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("coordinator", coordinator.run)
    g.add_node("screener", screener_agent.run)
    g.add_node("news", news_agent.run)
    g.add_node("strategies", strategy_agents.run_all)
    g.add_node("selector", selector_agent.run)
    g.add_node("risk", risk_agent.run)
    g.add_node("execute", risk_agent.execute_if_approved)
    g.add_node("watchdog", watchdog_agent.run)
    g.add_node("memory", memory_agent.run)

    g.set_entry_point("coordinator")

    g.add_edge("coordinator", "screener")
    g.add_edge("coordinator", "news")
    g.add_edge("screener", "strategies")
    g.add_edge("news", "strategies")
    g.add_edge("strategies", "selector")
    g.add_edge("selector", "risk")

    g.add_conditional_edges(
        "risk",
        lambda s: "execute" if s["risk_approved"] else "watchdog",
        {"execute": "execute", "watchdog": "watchdog"},
    )

    g.add_edge("execute", "watchdog")
    g.add_edge("watchdog", "memory")
    g.add_edge("memory", END)

    return g.compile()


agent_graph = _build_graph()


def run_cycle() -> AgentState:
    initial: AgentState = {
        "cycle_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbols": settings.crypto_symbol_list,
        "screener_results": [],
        "news_events": [],
        "news_sentiment_avg": 0.0,
        "high_impact_news": False,
        "strategy_signals": {},
        "available_strategies": [],
        "selection": None,
        "top_symbol": None,
        "risk_approved": False,
        "risk_reason": "",
        "order_qty": 0.0,
        "order_entry": 0.0,
        "order_tp": 0.0,
        "order_sl": 0.0,
        "order_result": None,
        "watchdog_states": {},
        "similar_past_trades": [],
        "memory_written": False,
        "agent_logs": [],
    }
    return agent_graph.invoke(initial)
