from config import settings


def calculate_size(equity: float, atr: float, price: float,
                   risk_pct: float, watchdog_multiplier: float,
                   confidence: float) -> float:
    """
    ATR-based position sizing.
    risk_dollars = equity × risk_pct / 100
    SL distance  = 1.5 × ATR
    qty          = risk_dollars / SL_distance
    Then scale by watchdog_multiplier and confidence.
    """
    if price <= 0 or atr <= 0:
        return 0.0

    risk_dollars = equity * (risk_pct / 100)
    sl_distance = atr * 1.5
    raw_qty = risk_dollars / sl_distance

    # Scale by watchdog state and confidence
    confidence_mult = max(0.5, min(1.5, confidence / 0.6))
    qty = raw_qty * watchdog_multiplier * confidence_mult

    # Never risk more than CRO per-trade limit
    max_notional = equity * settings.cro_max_trade_risk_pct / 100
    if qty * price > max_notional:
        qty = max_notional / price

    return max(0.0, round(qty, 6))


def calculate_tp_sl(entry: float, direction: int, atr: float,
                    rr_ratio: float = 2.5) -> tuple:
    """Returns (take_profit_price, stop_loss_price)."""
    sl_dist = atr * 1.5
    tp_dist = sl_dist * rr_ratio
    if direction == 1:  # long
        return entry + tp_dist, entry - sl_dist
    else:               # short
        return entry - tp_dist, entry + sl_dist
