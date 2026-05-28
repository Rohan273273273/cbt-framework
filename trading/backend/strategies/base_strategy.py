from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any
import polars as pl


@dataclass
class Signal:
    direction: int          # 1=long, -1=short, 0=no trade
    confidence: float       # 0.0 – 1.0
    entry: float = 0.0
    tp: float = 0.0
    sl: float = 0.0
    rr_ratio: float = 0.0
    strategy: str = ""
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return (
            self.direction != 0
            and self.confidence > 0
            and self.entry > 0
            and self.tp > 0
            and self.sl > 0
            and self.rr_ratio >= 2.0
        )


class BaseStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def generate_signal(self, candles: pl.DataFrame, params: dict = None) -> Signal:
        """
        candles: Polars DataFrame with columns [ts, open, high, low, close, volume]
                 sorted ascending, all values from CLOSED bars only.
        Returns: Signal with all fields populated.
        """
        ...

    def _atr(self, candles: pl.DataFrame, period: int = 14) -> float:
        if len(candles) < period + 1:
            return 0.0
        h = candles["high"].to_numpy()
        l = candles["low"].to_numpy()
        c = candles["close"].to_numpy()
        tr = [max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1]))
              for i in range(1, len(c))]
        return float(sum(tr[-period:]) / period)

    def _rsi(self, candles: pl.DataFrame, period: int = 14) -> float:
        closes = candles["close"].to_numpy()
        if len(closes) < period + 1:
            return 50.0
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d for d in deltas[-period:] if d > 0]
        losses = [-d for d in deltas[-period:] if d < 0]
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
