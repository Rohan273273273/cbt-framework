"""
AMD — Accumulation / Manipulation / Distribution (ICT concept).
Asia session builds a range. London manipulates (false breakout).
NY distributes in the real direction.
"""
from datetime import timezone
import polars as pl
from strategies.base_strategy import BaseStrategy, Signal


SESSION_WINDOWS = {
    "asia":   (20, 0),    # 20:00 – 00:00 UTC
    "london": (2,  5),    # 02:00 – 05:00 UTC
    "ny":     (13, 17),   # 09:00 – 13:00 UTC (NY open to lunch)
}


def _session_of(hour: int) -> str:
    if 20 <= hour or hour < 0:
        return "asia"
    if 2 <= hour < 5:
        return "london"
    if 13 <= hour < 17:
        return "ny"
    return "transition"


class AMDStrategy(BaseStrategy):
    name = "amd_session"

    def generate_signal(self, candles: pl.DataFrame, params: dict = None) -> Signal:
        params = params or {}
        sweep_pct = params.get("sweep_pct", 0.002)   # 0.2% beyond range = sweep

        if len(candles) < 50:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        ts_col = candles["ts"]
        try:
            hours = [t.hour if hasattr(t, "hour") else 0 for t in ts_col.to_list()]
        except Exception:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        current_hour = hours[-1]
        if _session_of(current_hour) != "ny":
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        closes = candles["close"].to_numpy()
        highs = candles["high"].to_numpy()
        lows = candles["low"].to_numpy()

        # Find Asia session bars from the most recent Asia window
        asia_highs, asia_lows = [], []
        london_highs, london_lows = [], []

        for i, h in enumerate(hours[-96:], start=max(0, len(hours) - 96)):
            session = _session_of(h)
            if session == "asia":
                asia_highs.append(highs[i])
                asia_lows.append(lows[i])
            elif session == "london":
                london_highs.append(highs[i])
                london_lows.append(lows[i])

        if not asia_highs or not london_highs:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        asia_high = max(asia_highs)
        asia_low = min(asia_lows)
        london_high = max(london_highs)
        london_low = min(london_lows)

        # Detect manipulation sweep:
        # Bullish: London swept below Asia low then closed back above it
        # Bearish: London swept above Asia high then closed back below it
        current_price = float(closes[-1])
        atr = self._atr(candles)
        rsi = self._rsi(candles)

        bullish_sweep = (london_low < asia_low * (1 - sweep_pct)
                         and current_price > asia_low)
        bearish_sweep = (london_high > asia_high * (1 + sweep_pct)
                         and current_price < asia_high)

        direction = 0
        confidence = 0.0
        reasoning = ""

        if bullish_sweep and rsi < 60:
            direction = 1
            sweep_depth = (asia_low - london_low) / asia_low
            confidence = min(0.85, 0.60 + sweep_depth * 10)
            reasoning = (f"Bullish AMD: Asia low {asia_low:.2f} swept to {london_low:.2f}, "
                         f"price recovered to {current_price:.2f}")
        elif bearish_sweep and rsi > 40:
            direction = -1
            sweep_depth = (london_high - asia_high) / asia_high
            confidence = min(0.85, 0.60 + sweep_depth * 10)
            reasoning = (f"Bearish AMD: Asia high {asia_high:.2f} swept to {london_high:.2f}, "
                         f"price fell to {current_price:.2f}")

        if direction == 0 or atr == 0:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        sl_dist = atr * 1.5
        tp_dist = sl_dist * 2.5
        entry = current_price
        tp = entry + tp_dist if direction == 1 else entry - tp_dist
        sl = entry - sl_dist if direction == 1 else entry + sl_dist

        return Signal(
            direction=direction, confidence=confidence,
            entry=entry, tp=tp, sl=sl, rr_ratio=tp_dist / sl_dist,
            strategy=self.name, reasoning=reasoning,
            metadata={
                "asia_high": asia_high, "asia_low": asia_low,
                "london_high": london_high, "london_low": london_low,
                "atr": atr, "rsi": rsi,
            },
        )
