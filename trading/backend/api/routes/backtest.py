from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from data.timescale_writer import fetch_ohlcv
import polars as pl
import sys, os
sys.path.insert(0, "/app/cbt_engine")
from metrics import calculate_all_metrics, calculate_trade_stats, Trade

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    symbol: str
    strategy: str
    timeframe: str = "1h"
    date_from: str
    date_to: str


@router.post("/run")
def run_backtest(req: BacktestRequest):
    rows = fetch_ohlcv(req.symbol, req.timeframe, limit=5000)
    if not rows:
        raise HTTPException(404, f"No data for {req.symbol} {req.timeframe}")

    df = pl.DataFrame(rows)
    df = df.filter(
        (pl.col("ts").cast(pl.Utf8) >= req.date_from) &
        (pl.col("ts").cast(pl.Utf8) <= req.date_to)
    )

    if len(df) < 50:
        raise HTTPException(400, "Insufficient data for backtest range")

    # Import strategy
    strategy_map = {
        "volume_profile": "strategies.volume_profile.VolumeProfileStrategy",
        "amd_session": "strategies.amd_session.AMDStrategy",
        "liquidity_sweep": "strategies.liquidity_sweep.LiquiditySweepStrategy",
        "order_blocks_fvg": "strategies.order_blocks_fvg.OrderBlockFVGStrategy",
    }
    if req.strategy not in strategy_map:
        raise HTTPException(400, f"Unknown strategy: {req.strategy}")

    module_path, cls_name = strategy_map[req.strategy].rsplit(".", 1)
    import importlib
    mod = importlib.import_module(module_path)
    strategy = getattr(mod, cls_name)()

    # Simple replay — bar by bar
    trades = []
    equity = 1000.0  # base for metrics
    in_trade = False
    entry_price = 0.0
    direction = 0
    entry_time = None
    tp = sl = 0.0

    closes = df["close"].to_numpy()

    for i in range(100, len(df)):
        window = df.slice(0, i)
        sig = strategy.generate_signal(window)
        cur_price = float(closes[i])

        if in_trade:
            won = (direction == 1 and cur_price >= tp) or (direction == -1 and cur_price <= tp)
            lost = (direction == 1 and cur_price <= sl) or (direction == -1 and cur_price >= sl)
            if won or lost:
                pnl = (tp - entry_price if won else sl - entry_price) * direction
                pnl_pct = pnl / entry_price * 100
                trades.append(Trade(
                    entry_time=str(entry_time), exit_time=str(df["ts"][i]),
                    direction=direction, entry_price=entry_price,
                    exit_price=tp if won else sl,
                    size=1.0, pnl=pnl, pnl_percent=pnl_pct,
                    exit_reason="tp" if won else "sl",
                    duration_seconds=3600, fees=0.0,
                ))
                in_trade = False

        if not in_trade and sig.is_valid:
            in_trade = True
            direction = sig.direction
            entry_price = sig.entry
            entry_time = df["ts"][i]
            tp = sig.tp
            sl = sig.sl

    if not trades:
        return {"trades": [], "metrics": {}, "message": "No trades generated"}

    equity_curve = [1000.0]
    for t in trades:
        equity_curve.append(equity_curve[-1] + t.pnl * 100)

    from metrics import calculate_returns
    returns = calculate_returns(equity_curve)
    metrics = calculate_all_metrics(returns, trades, equity_curve)
    trade_stats = calculate_trade_stats(trades)

    trade_rects = [
        {
            "entry_time": t.entry_time, "exit_time": t.exit_time,
            "entry_price": t.entry_price, "exit_price": t.exit_price,
            "direction": t.direction, "pnl": t.pnl,
            "color": "green" if t.pnl > 0 else "red",
        }
        for t in trades
    ]

    return {
        "trades": trade_rects,
        "metrics": {**metrics, **trade_stats},
        "equity_curve": equity_curve,
    }
