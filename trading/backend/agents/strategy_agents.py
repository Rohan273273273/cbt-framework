from agents.state import AgentState
from data.market_data_service import get_latest_candles
from strategies.volume_profile import VolumeProfileStrategy
from strategies.amd_session import AMDStrategy
from strategies.liquidity_sweep import LiquiditySweepStrategy
from strategies.order_blocks_fvg import OrderBlockFVGStrategy

_strategies = {
    "volume_profile": VolumeProfileStrategy(),
    "amd_session": AMDStrategy(),
    "liquidity_sweep": LiquiditySweepStrategy(),
    "order_blocks_fvg": OrderBlockFVGStrategy(),
}


def run_all(state: AgentState) -> AgentState:
    symbol = state.get("top_symbol")
    if not symbol:
        state["agent_logs"].append("StrategyAgents: no top symbol — skipping")
        return state

    candles = get_latest_candles(symbol, "1h", 200)
    if candles.is_empty():
        state["agent_logs"].append(f"StrategyAgents: no candles for {symbol}")
        return state

    signals = {}
    available = []

    for name, strategy in _strategies.items():
        try:
            sig = strategy.generate_signal(candles)
            signals[name] = {
                "direction": sig.direction,
                "confidence": sig.confidence,
                "entry": sig.entry,
                "tp": sig.tp,
                "sl": sig.sl,
                "rr_ratio": sig.rr_ratio,
                "reasoning": sig.reasoning,
                "metadata": sig.metadata,
                "is_valid": sig.is_valid,
            }
            if sig.is_valid:
                available.append(name)
                state["agent_logs"].append(
                    f"{name}: {'LONG' if sig.direction==1 else 'SHORT'} "
                    f"conf={sig.confidence:.2f} RR={sig.rr_ratio:.1f} — {sig.reasoning[:80]}"
                )
            else:
                state["agent_logs"].append(f"{name}: no valid signal")
        except Exception as e:
            state["agent_logs"].append(f"{name}: ERROR — {e}")

    state["strategy_signals"] = signals
    state["available_strategies"] = available
    return state
