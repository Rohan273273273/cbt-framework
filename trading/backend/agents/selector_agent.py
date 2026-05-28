from agents.state import AgentState
from ml.feature_builder import build_features
from ml.selector_service import select
from data.market_data_service import get_latest_candles
from screeners.screener_models import ScreenerResult


def run(state: AgentState) -> AgentState:
    if not state["available_strategies"]:
        state["selection"] = None
        state["agent_logs"].append("SelectorAgent: no valid signals — FLAT")
        return state

    symbol = state.get("top_symbol")
    candles = get_latest_candles(symbol, "1h", 100) if symbol else None

    screener_data = state["screener_results"][0] if state["screener_results"] else None
    screener_obj = ScreenerResult(**screener_data) if screener_data else None

    features = build_features(
        candles_1h=candles if candles is not None else __import__("polars").DataFrame(),
        screener_result=screener_obj,
        news_sentiment_score=state["news_sentiment_avg"],
        high_impact_news=state["high_impact_news"],
    )

    selection = select(features, available_signals=state["available_strategies"])
    if selection:
        sig = state["strategy_signals"].get(selection.strategy, {})
        state["selection"] = {
            "strategy": selection.strategy,
            "confidence": selection.confidence,
            "lgbm_prob": selection.lgbm_prob,
            "river_prob": selection.river_prob,
            "size_multiplier": selection.size_multiplier,
            "reason": selection.reason,
            "all_probs": selection.all_probs,
            "signal": sig,
        }
        state["agent_logs"].append(
            f"SelectorAgent: chose {selection.strategy} "
            f"conf={selection.confidence:.3f} size_mult={selection.size_multiplier}"
        )
    else:
        state["selection"] = None
        state["agent_logs"].append("SelectorAgent: confidence below threshold — FLAT")

    return state
