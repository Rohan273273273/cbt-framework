import logging

from agents.state import AgentState
from gateway.alpaca_gateway import gateway
from gateway.order_types import BracketOrder
from risk.cro import check_order, record_trade_open
from risk.position_sizer import calculate_size, calculate_tp_sl

logger = logging.getLogger(__name__)


def run(state: AgentState) -> AgentState:
    selection = state.get("selection")
    if not selection:
        state["risk_approved"] = False
        state["risk_reason"] = "No strategy selected"
        state["agent_logs"].append("RiskAgent: no selection — skipping")
        return state

    # High-impact news blackout
    if state.get("high_impact_news"):
        state["risk_approved"] = False
        state["risk_reason"] = "High-impact news event — blackout active"
        state["agent_logs"].append("RiskAgent: BLOCKED — high-impact news blackout")
        return state

    try:
        account = gateway.get_account()
        equity = account["equity"]
    except Exception as e:
        state["risk_approved"] = False
        state["risk_reason"] = f"Account fetch failed: {e}"
        return state

    sig = selection.get("signal", {})
    entry = sig.get("entry", 0.0)
    direction = sig.get("direction", 0)

    if not entry or not direction:
        state["risk_approved"] = False
        state["risk_reason"] = "Invalid signal entry/direction"
        return state

    atr = sig.get("metadata", {}).get("atr", entry * 0.01)
    size_mult = selection.get("size_multiplier", 1.0)
    confidence = selection.get("confidence", 0.5)

    qty = calculate_size(
        equity=equity, atr=atr, price=entry,
        risk_pct=1.0,
        watchdog_multiplier=size_mult,
        confidence=confidence,
    )
    tp, sl = calculate_tp_sl(entry, direction, atr)

    # RR check
    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
    if rr < 2.0:
        state["risk_approved"] = False
        state["risk_reason"] = f"RR={rr:.2f} < minimum 2.0"
        state["agent_logs"].append(f"RiskAgent: BLOCKED — RR {rr:.2f} < 2.0")
        return state

    notional = qty * entry
    approved, reason = check_order(
        symbol=state["top_symbol"], side="buy" if direction == 1 else "sell",
        notional=notional, account_equity=equity,
    )

    state["risk_approved"] = approved
    state["risk_reason"] = reason
    state["order_qty"] = qty
    state["order_entry"] = entry
    state["order_tp"] = tp
    state["order_sl"] = sl

    state["agent_logs"].append(
        f"RiskAgent: {'APPROVED' if approved else 'BLOCKED'} — {reason} "
        f"qty={qty:.6f} notional=${notional:.2f} RR={rr:.2f}"
    )
    return state


def execute_if_approved(state: AgentState) -> AgentState:
    if not state["risk_approved"]:
        return state

    selection = state["selection"]
    sig = selection["signal"]
    direction = sig["direction"]
    symbol = state["top_symbol"]

    order = BracketOrder(
        symbol=symbol,
        qty=state["order_qty"],
        side="buy" if direction == 1 else "sell",
        tp_pct=abs(state["order_tp"] - state["order_entry"]) / state["order_entry"],
        sl_pct=abs(state["order_sl"] - state["order_entry"]) / state["order_entry"],
        strategy=selection["strategy"],
        confidence=selection["confidence"],
    )

    result = gateway.submit_bracket_order(order)
    state["order_result"] = {
        "order_id": result.order_id,
        "status": result.status,
        "symbol": result.symbol,
        "side": result.side,
        "qty": result.qty,
        "error": result.error,
    }

    if result.status == "accepted":
        record_trade_open(symbol)
        state["agent_logs"].append(
            f"Execution: ORDER PLACED {symbol} "
            f"{'LONG' if direction==1 else 'SHORT'} "
            f"qty={result.qty:.6f} id={result.order_id}"
        )
    else:
        state["agent_logs"].append(f"Execution: ORDER FAILED — {result.error}")

    return state
