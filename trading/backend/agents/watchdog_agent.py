from agents.state import AgentState
from risk.watchdog import get_all_states, record_outcome


def run(state: AgentState) -> AgentState:
    state["watchdog_states"] = get_all_states()

    # If a trade was placed, outcome will be determined when fill closes
    # For now just report states
    states_str = ", ".join(f"{k}={v}" for k, v in state["watchdog_states"].items())
    state["agent_logs"].append(f"WatchdogAgent: {states_str}")
    return state


def record_trade_result(strategy: str, won: bool):
    """Called externally when a trade closes (fill received from Alpaca WS)."""
    record_outcome(strategy, won)
