import importlib
import sys

import polars as pl
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from data.timescale_writer import fetch_ohlcv

# engine/metrics.py is mounted at /app/cbt_engine inside Docker
sys.path.insert(0, "/app/cbt_engine")

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

STRATEGY_MAP = {
    "volume_profile": "strategies.volume_profile.VolumeProfileStrategy",
    "amd_session": "strategies.amd_session.AMDStrategy",
    "liquidity_sweep": "strategies.liquidity_sweep.LiquiditySweepStrategy",
    "order_blocks_fvg": "strategies.order_blocks_fvg.OrderBlockFVGStrategy",
}


class BacktestRequest(BaseModel):
    symbol: str
    strategy: str
    timeframe: str = "1h"
    date_from: str
    date_to: str


def _load_strategy(name: str):
    if name not in STRATEGY_MAP:
        raise HTTPException(400, f"Unknown strategy: {name}")
    module_path, cls_name = STRATEGY_MAP[name].rsplit(".", 1)
    mod = importlib.import_module(module_path)
    return getattr(mod, cls_name)()


@router.post("/run")
def run_backtest(req: BacktestRequest):
    rows = fetch_ohlcv(req.symbol, req.timeframe, limit=5000)
    if not rows:
        raise HTTPException(404, f"No data for {req.symbol} {req.timeframe}")

    df = pl.DataFrame(rows).with_columns(
        pl.col("ts").cast(pl.Utf8)
    ).filter(
        (pl.col("ts") >= req.date_from) & (pl.col("ts") <= req.date_to)
    )

    if len(df) < 50:
        raise HTTPException(400, "Insufficient data for backtest range")

    strategy = _load_strategy(req.strategy)
    closes = df["close"].to_numpy()
    timestamps = df["ts"].to_list()

    # Import engine Trade dataclass at call time (path already inserted above)
    from metrics import Trade, calculate_all_metrics  # type: ignore

    trades: list[Trade] = []
    in_trade = False
    entry_price = direction = 0.0
    entry_time = tp = sl = None

    for i in range(100, len(df)):
        window = df.slice(0, i)
        cur_price = float(closes[i])

        if in_trade:
            won = (direction == 1 and cur_price >= tp) or (direction == -1 and cur_price <= tp)
            lost = (direction == 1 and cur_price <= sl) or (direction == -1 and cur_price >= sl)
            if won or lost:
                exit_px = tp if won else sl
                pnl = (exit_px - entry_price) * direction
                trades.append(Trade(
                    entry_time=str(entry_time),
                    exit_time=str(timestamps[i]),
                    direction=int(direction),
                    entry_price=float(entry_price),
                    exit_price=float(exit_px),
                    size=1.0,
                    pnl=float(pnl),
                    pnl_percent=float(pnl / entry_price * 100),
                    exit_reason="tp" if won else "sl",
                    duration_seconds=3600,
                    fees=0.0,
                ))
                in_trade = False

        if not in_trade:
            sig = strategy.generate_signal(window)
            if sig.is_valid:
                in_trade = True
                direction = sig.direction
                entry_price = sig.entry
                entry_time = timestamps[i]
                tp = sig.tp
                sl = sig.sl

    if not trades:
        return {"trades": [], "metrics": {}, "message": "No trades generated"}

    initial_capital = 1000.0
    equity_curve = [initial_capital]
    for t in trades:
        equity_curve.append(equity_curve[-1] + t.pnl * 100)

    metrics = calculate_all_metrics(equity_curve, trades, initial_capital)

    trade_rects = [
        {
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "direction": t.direction,
            "pnl": t.pnl,
            "color": "green" if t.pnl > 0 else "red",
        }
        for t in trades
    ]

    return {
        "trades": trade_rects,
        "metrics": metrics,
        "equity_curve": equity_curve,
    }
