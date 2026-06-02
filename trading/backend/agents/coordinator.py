from agents.state import AgentState
from agents.llm_client import reason


def run(state: AgentState) -> AgentState:
    log = f"[{state['timestamp']}] Coordinator: cycle {state['cycle_id'][:8]} — scanning {state['symbols']}"
    state["agent_logs"].append(log)
    return state
