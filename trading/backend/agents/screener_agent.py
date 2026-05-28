from agents.state import AgentState
from screeners.crypto_screener import get_cached_results


def run(state: AgentState) -> AgentState:
    results = get_cached_results()
    state["screener_results"] = [r.__dict__ for r in results]
    top = results[0].symbol if results else "none"
    state["top_symbol"] = top
    state["agent_logs"].append(
        f"ScreenerAgent: {len(results)} assets ranked, top={top} "
        f"(score={results[0].composite_score if results else 0})"
    )
    return state
