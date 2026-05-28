"""Generates training labels from closed trade outcomes for ML model retraining."""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

STRATEGIES = ["volume_profile", "amd_session", "liquidity_sweep", "order_blocks_fvg"]
STRATEGY_TO_IDX = {s: i for i, s in enumerate(STRATEGIES)}


@dataclass
class TradeOutcome:
    trade_id: str
    strategy: str
    pnl: float
    win: bool
    rr_actual: float
    hold_bars: int
    features: dict


def compute_label(outcomes: list[TradeOutcome], window: int = 20) -> Optional[int]:
    """
    Label = index of strategy with best Sharpe over the last `window` trades.
    Returns None if insufficient data.
    """
    if len(outcomes) < window:
        return None

    recent = outcomes[-window:]
    by_strategy: dict[str, list[float]] = {s: [] for s in STRATEGIES}
    for o in recent:
        if o.strategy in by_strategy:
            by_strategy[o.strategy].append(o.pnl)

    best_strategy = None
    best_sharpe = float("-inf")

    for strategy, pnls in by_strategy.items():
        if len(pnls) < 3:
            continue
        import numpy as np
        arr = np.array(pnls)
        mean = arr.mean()
        std = arr.std()
        if std < 1e-9:
            sharpe = mean / 1e-9
        else:
            sharpe = mean / std * (252 ** 0.5)

        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_strategy = strategy

    if best_strategy is None:
        return None

    return STRATEGY_TO_IDX[best_strategy]


def label_for_trade(
    completed_trade: TradeOutcome,
    history: list[TradeOutcome],
    window: int = 20,
) -> Optional[int]:
    """
    Returns label integer (0-3) for a just-closed trade, using history buffer.
    Call river_updater.learn_one() with this label.
    """
    history.append(completed_trade)
    label = compute_label(history, window)
    if label is not None:
        logger.debug(
            "Label for %s: %d (%s)",
            completed_trade.trade_id,
            label,
            STRATEGIES[label],
        )
    return label
