"""Wraps templates/fast/backtest.py run_backtest_loop for strategy pre-training."""
import sys
import logging
from pathlib import Path
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# Mount path set in Docker: ../../engine -> /app/cbt_engine
_CBT_ENGINE = Path("/app/cbt_engine")
if _CBT_ENGINE.exists() and str(_CBT_ENGINE) not in sys.path:
    sys.path.insert(0, str(_CBT_ENGINE))

_TEMPLATES = Path("/app/cbt_engine/../templates/fast")
if _TEMPLATES.exists() and str(_TEMPLATES.resolve()) not in sys.path:
    sys.path.insert(0, str(_TEMPLATES.resolve()))


@dataclass
class ReplayResult:
    symbol: str
    strategy: str
    timeframe: str
    trades: list[dict]
    equity_curve: np.ndarray
    metrics: dict


def replay(
    ohlcv: np.ndarray,
    strategy_fn,
    symbol: str,
    strategy: str,
    timeframe: str,
    initial_capital: float = 10_000.0,
    risk_pct: float = 0.01,
) -> ReplayResult:
    """
    Replay a strategy over OHLCV numpy array (shape: N×5, cols: O H L C V).
    Falls back to pure-Python replay when Numba is unavailable.
    """
    try:
        from backtest import run_backtest_loop  # type: ignore

        signals = _build_signal_array(ohlcv, strategy_fn)
        equity, trade_log = run_backtest_loop(
            ohlcv.astype(np.float64),
            signals.astype(np.int8),
            initial_capital,
            risk_pct,
        )
        trades = _parse_trade_log(trade_log)
        metrics = _compute_metrics(equity, trades)
        return ReplayResult(symbol, strategy, timeframe, trades, equity, metrics)

    except ImportError:
        logger.warning("Numba backtest not available — using pure-Python replay")
        return _python_replay(ohlcv, strategy_fn, symbol, strategy, timeframe, initial_capital, risk_pct)


def _build_signal_array(ohlcv: np.ndarray, strategy_fn) -> np.ndarray:
    """Call strategy_fn bar-by-bar, collecting direction signals."""
    import pandas as pd

    n = len(ohlcv)
    signals = np.zeros(n, dtype=np.int8)
    cols = ["open", "high", "low", "close", "volume"]
    for i in range(50, n):
        bars = pd.DataFrame(ohlcv[:i], columns=cols)
        sig = strategy_fn(bars)
        if sig is not None:
            signals[i] = sig.direction
    return signals


def _python_replay(
    ohlcv: np.ndarray,
    strategy_fn,
    symbol: str,
    strategy: str,
    timeframe: str,
    initial_capital: float,
    risk_pct: float,
) -> ReplayResult:
    import pandas as pd

    cols = ["open", "high", "low", "close", "volume"]
    n = len(ohlcv)
    equity = np.full(n, initial_capital)
    trades: list[dict] = []
    in_trade = False
    entry_price = 0.0
    direction = 0
    entry_idx = 0

    for i in range(50, n):
        bars = pd.DataFrame(ohlcv[:i], columns=cols)
        close = ohlcv[i, 3]

        if in_trade:
            atr = float(bars["high"].rolling(14).max().iloc[-1] - bars["low"].rolling(14).min().iloc[-1]) / 14
            tp = entry_price + direction * atr * 3.75
            sl = entry_price - direction * atr * 1.5
            hit_tp = (direction == 1 and close >= tp) or (direction == -1 and close <= tp)
            hit_sl = (direction == 1 and close <= sl) or (direction == -1 and close >= sl)

            if hit_tp or hit_sl:
                exit_price = tp if hit_tp else sl
                pnl_pct = direction * (exit_price - entry_price) / entry_price
                pnl = equity[i - 1] * risk_pct * (pnl_pct / (atr * 1.5 / entry_price))
                equity[i] = equity[i - 1] + pnl
                trades.append({
                    "entry_idx": entry_idx,
                    "exit_idx": i,
                    "direction": direction,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "color": "green" if pnl > 0 else "red",
                })
                in_trade = False
            else:
                equity[i] = equity[i - 1]
        else:
            sig = strategy_fn(bars)
            if sig is not None and sig.direction != 0 and sig.is_valid:
                in_trade = True
                entry_price = close
                direction = sig.direction
                entry_idx = i
            equity[i] = equity[i - 1] if i > 0 else initial_capital

    metrics = _compute_metrics(equity, trades)
    return ReplayResult(symbol, strategy, timeframe, trades, equity, metrics)


def _parse_trade_log(trade_log) -> list[dict]:
    trades = []
    if trade_log is None:
        return trades
    for row in trade_log:
        trades.append({
            "entry_idx": int(row[0]),
            "exit_idx": int(row[1]),
            "direction": int(row[2]),
            "entry_price": float(row[3]),
            "exit_price": float(row[4]),
            "pnl": float(row[5]),
            "color": "green" if float(row[5]) > 0 else "red",
        })
    return trades


def _compute_metrics(equity: np.ndarray, trades: list[dict]) -> dict:
    if len(trades) == 0:
        return {"win_rate": 0.0, "profit_factor": 0.0, "sharpe_ratio": 0.0, "max_drawdown": 0.0}

    pnls = np.array([t["pnl"] for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    win_rate = len(wins) / len(trades) if trades else 0.0
    profit_factor = wins.sum() / abs(losses.sum()) if len(losses) > 0 and losses.sum() != 0 else float("inf")

    returns = np.diff(equity) / equity[:-1]
    returns = returns[~np.isnan(returns)]
    sharpe = (returns.mean() / (returns.std() + 1e-9)) * (252 ** 0.5) if len(returns) > 1 else 0.0

    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_drawdown = float(abs(dd.min()))

    return {
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "sharpe_ratio": float(sharpe),
        "max_drawdown": float(max_drawdown),
        "total_trades": len(trades),
        "avg_win": float(wins.mean()) if len(wins) > 0 else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) > 0 else 0.0,
        "net_pnl": float(pnls.sum()),
        "expectancy": float(pnls.mean()),
    }
