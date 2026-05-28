import logging
from agents.state import AgentState
from knowledge.graph_builder import write_cycle, query_similar

logger = logging.getLogger(__name__)


def run(state: AgentState) -> AgentState:
    try:
        similar = query_similar(state)
        state["similar_past_trades"] = similar[:3]
        write_cycle(state)
        state["memory_written"] = True
        state["agent_logs"].append(
            f"MemoryAgent: cycle written to Neo4j, "
            f"{len(similar)} similar past trades found"
        )
    except Exception as e:
        logger.error(f"MemoryAgent failed: {e}")
        state["memory_written"] = False
        state["agent_logs"].append(f"MemoryAgent: write failed — {e}")
    return state
