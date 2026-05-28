#!/usr/bin/env python3
"""
Pre-training pipeline entry point.
Runs all 4 strategies over 7yr OHLCV from TimescaleDB, builds 35-dim feature
vectors + strategy labels, trains LightGBM with walk-forward CV, saves pkl.

Usage:
    python scripts/pretrain_lgbm.py [--symbols BTC/USD ETH/USD] [--tfs 1h 4h]
"""
import argparse
import asyncio
import logging
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pretrain")

DEFAULT_SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", "LINK/USD"]
DEFAULT_TFS = ["1h", "4h"]
MODEL_PATH = Path(__file__).parent.parent / "backend" / "models" / "lgbm_selector.pkl"


async def load_ohlcv(symbol: str, timeframe: str, settings) -> np.ndarray:
    """Load OHLCV from TimescaleDB as numpy array (N×5: O H L C V)."""
    import asyncpg

    conn = await asyncpg.connect(settings.timescale_url)
    try:
        rows = await conn.fetch(
            """
            SELECT open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = $1 AND timeframe = $2
            ORDER BY ts ASC
            """,
            symbol,
            timeframe,
        )
        if not rows:
            logger.warning("No data for %s %s", symbol, timeframe)
            return np.empty((0, 5))
        return np.array([[r["open"], r["high"], r["low"], r["close"], r["volume"]] for r in rows])
    finally:
        await conn.close()


def run_strategy_replay(ohlcv: np.ndarray, strategy_name: str) -> list[dict]:
    """Run a strategy over OHLCV array and return trade list."""
    import pandas as pd

    from strategies.volume_profile import VolumeProfileStrategy
    from strategies.amd_session import AMDSessionStrategy
    from strategies.liquidity_sweep import LiquiditySweepStrategy
    from strategies.order_blocks_fvg import OrderBlocksFVGStrategy
    from backtest.replay_engine import replay

    strategy_map = {
        "volume_profile": VolumeProfileStrategy,
        "amd_session": AMDSessionStrategy,
        "liquidity_sweep": LiquiditySweepStrategy,
        "order_blocks_fvg": OrderBlocksFVGStrategy,
    }
    cls = strategy_map[strategy_name]
    instance = cls()

    result = replay(
        ohlcv=ohlcv,
        strategy_fn=lambda bars: instance.generate_signal(bars),
        symbol="UNKNOWN",
        strategy=strategy_name,
        timeframe="1h",
        initial_capital=10_000.0,
        risk_pct=0.01,
    )
    return result.trades


def build_features_and_labels(
    all_trades: dict[str, list[dict]],
    ohlcv: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    For each bar index where any strategy fired, build a 10-dim simplified feature
    vector and assign label = best Sharpe strategy in next 20 trades.
    """
    from ml.feature_builder import FeatureBuilder
    from ml.label_generator import compute_label, TradeOutcome

    STRATEGIES = ["volume_profile", "amd_session", "liquidity_sweep", "order_blocks_fvg"]
    trade_history: list[TradeOutcome] = []

    # Collect all unique exit indices across strategies
    exit_indices = sorted({t["exit_idx"] for trades in all_trades.values() for t in trades})

    X_rows, y_rows = [], []

    for exit_idx in exit_indices:
        for s_name, trades in all_trades.items():
            for t in trades:
                if t["exit_idx"] == exit_idx:
                    trade_history.append(
                        TradeOutcome(
                            trade_id=f"{s_name}_{exit_idx}",
                            strategy=s_name,
                            pnl=t["pnl"],
                            win=t["pnl"] > 0,
                            rr_actual=abs(t["pnl"]) / max(abs(t["entry_price"] * 0.01), 1e-9),
                            hold_bars=t["exit_idx"] - t["entry_idx"],
                            features={},
                        )
                    )

        label = compute_label(trade_history, window=20)
        if label is None:
            continue

        # Simple feature: last 10 close returns + volume ratio
        if exit_idx < 15:
            continue
        window = ohlcv[exit_idx - 14 : exit_idx + 1]
        if len(window) < 15:
            continue
        closes = window[:, 3]
        returns = np.diff(np.log(closes + 1e-9))
        vol_ratio = window[-1, 4] / (window[:, 4].mean() + 1e-9)
        features = np.append(returns, vol_ratio)
        X_rows.append(features)
        y_rows.append(label)

    if not X_rows:
        return np.empty((0, 14)), np.empty((0,))

    return np.array(X_rows), np.array(y_rows, dtype=np.int32)


def train_lgbm(X: np.ndarray, y: np.ndarray) -> object:
    """Walk-forward cross-validated LightGBM training."""
    import lightgbm as lgb
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import f1_score

    n_splits = 5
    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_scores = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]

        clf = lgb.LGBMClassifier(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            max_depth=6,
            class_weight="balanced",
            random_state=42,
            verbose=-1,
        )
        clf.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], callbacks=[lgb.early_stopping(20, verbose=False)])
        preds = clf.predict(X_te)
        score = f1_score(y_te, preds, average="weighted", zero_division=0)
        fold_scores.append(score)
        logger.info("Fold %d/%d — weighted F1: %.3f", fold + 1, n_splits, score)

    logger.info("Mean F1 across folds: %.3f ± %.3f", np.mean(fold_scores), np.std(fold_scores))

    # Final model on all data
    final = lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=6,
        class_weight="balanced",
        random_state=42,
        verbose=-1,
    )
    final.fit(X, y)
    return final


async def main(symbols: list[str], timeframes: list[str]) -> None:
    from config import get_settings

    settings = get_settings()
    STRATEGIES = ["volume_profile", "amd_session", "liquidity_sweep", "order_blocks_fvg"]

    all_X, all_y = [], []

    for symbol in symbols:
        for tf in timeframes:
            logger.info("Processing %s %s", symbol, tf)
            ohlcv = await load_ohlcv(symbol, tf, settings)
            if len(ohlcv) < 200:
                logger.warning("Skipping %s %s — only %d bars", symbol, tf, len(ohlcv))
                continue

            strategy_trades: dict[str, list[dict]] = {}
            for s in STRATEGIES:
                logger.info("  Replaying %s", s)
                trades = run_strategy_replay(ohlcv, s)
                strategy_trades[s] = trades
                logger.info("  → %d trades", len(trades))

            X, y = build_features_and_labels(strategy_trades, ohlcv)
            if len(X) > 0:
                all_X.append(X)
                all_y.append(y)
                logger.info("  → %d labeled samples", len(X))

    if not all_X:
        logger.error("No training data collected. Run ingest_historical.py first.")
        sys.exit(1)

    X_all = np.vstack(all_X)
    y_all = np.concatenate(all_y)
    logger.info("Total samples: %d", len(X_all))

    logger.info("Training LightGBM with walk-forward CV...")
    model = train_lgbm(X_all, y_all)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    logger.info("Model saved → %s", MODEL_PATH)
    logger.info("Pre-training complete. Start backend to begin paper trading.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--tfs", nargs="+", default=DEFAULT_TFS)
    args = parser.parse_args()
    asyncio.run(main(args.symbols, args.tfs))
