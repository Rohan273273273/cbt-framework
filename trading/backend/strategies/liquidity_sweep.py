"""
Liquidity Sweep — detects stop hunts at equal highs/lows,
fires counter-trend entry after confirmed reversal.
"""
import numpy as np
import polars as pl
from strategies.base_strategy import BaseStrategy, Signal


class LiquiditySweepStrategy(BaseStrategy):
    name = "liquidity_sweep"

    def generate_signal(self, candles: pl.DataFrame, params: dict = None) -> Signal:
        params = params or {}
        scan_bars = params.get("scan_bars", 50)
        tolerance_pct = params.get("tolerance_pct", 0.0015)   # 0.15%
        vol_multiplier = params.get("vol_multiplier", 1.8)
        min_touches = params.get("min_touches", 2)

        if len(candles) < scan_bars + 3:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        df = candles.tail(scan_bars + 3)
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        closes = df["close"].to_numpy()
        volumes = df["volume"].fill_null(0).to_numpy()

        # Use all bars except last 2 for level detection (no lookahead)
        detect_highs = highs[:-2]
        detect_lows = lows[:-2]
        avg_vol = volumes[:-2].mean() if volumes[:-2].mean() > 0 else 1

        # Find equal highs (within tolerance)
        equal_high_levels = []
        for i in range(len(detect_highs)):
            touches = sum(
                1 for j in range(len(detect_highs))
                if i != j and abs(detect_highs[i] - detect_highs[j]) / detect_highs[i] < tolerance_pct
            )
            if touches >= min_touches - 1:
                equal_high_levels.append(detect_highs[i])

        # Find equal lows
        equal_low_levels = []
        for i in range(len(detect_lows)):
            touches = sum(
                1 for j in range(len(detect_lows))
                if i != j and abs(detect_lows[i] - detect_lows[j]) / detect_lows[i] < tolerance_pct
            )
            if touches >= min_touches - 1:
                equal_low_levels.append(detect_lows[i])

        # Check last bar for sweep
        sweep_bar_high = highs[-2]
        sweep_bar_low = lows[-2]
        sweep_bar_close = closes[-2]
        sweep_bar_vol = volumes[-2]
        current_close = closes[-1]
        atr = self._atr(candles)
        rsi = self._rsi(candles)

        direction = 0
        confidence = 0.0
        sweep_level = None
        reasoning = ""

        # Bearish sweep of equal highs: wick above level, close back below
        if equal_high_levels:
            nearest_high = max(equal_high_levels)
            if (sweep_bar_high > nearest_high * (1 + tolerance_pct * 0.5)
                    and sweep_bar_close < nearest_high
                    and sweep_bar_vol > avg_vol * vol_multiplier
                    and current_close < sweep_bar_close):
                direction = -1
                sweep_level = nearest_high
                vol_ratio = sweep_bar_vol / avg_vol
                confidence = min(0.85, 0.60 + (vol_ratio - vol_multiplier) * 0.05)
                reasoning = (f"Bearish sweep: equal highs at {nearest_high:.2f} swept, "
                             f"vol {vol_ratio:.1f}x avg, reversal confirmed")

        # Bullish sweep of equal lows
        if direction == 0 and equal_low_levels:
            nearest_low = min(equal_low_levels)
            if (sweep_bar_low < nearest_low * (1 - tolerance_pct * 0.5)
                    and sweep_bar_close > nearest_low
                    and sweep_bar_vol > avg_vol * vol_multiplier
                    and current_close > sweep_bar_close):
                direction = 1
                sweep_level = nearest_low
                vol_ratio = sweep_bar_vol / avg_vol
                confidence = min(0.85, 0.60 + (vol_ratio - vol_multiplier) * 0.05)
                reasoning = (f"Bullish sweep: equal lows at {nearest_low:.2f} swept, "
                             f"vol {vol_ratio:.1f}x avg, reversal confirmed")

        if direction == 0 or atr == 0:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        entry = float(current_close)
        sl_dist = atr * 1.5
        tp_dist = sl_dist * 2.5
        tp = entry + tp_dist if direction == 1 else entry - tp_dist
        sl = entry - sl_dist if direction == 1 else entry + sl_dist

        return Signal(
            direction=direction, confidence=confidence,
            entry=entry, tp=tp, sl=sl, rr_ratio=tp_dist / sl_dist,
            strategy=self.name, reasoning=reasoning,
            metadata={"sweep_level": sweep_level, "atr": atr, "rsi": rsi,
                      "equal_highs": equal_high_levels[:5],
                      "equal_lows": equal_low_levels[:5]},
        )
