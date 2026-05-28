import numpy as np
import polars as pl
from strategies.base_strategy import BaseStrategy, Signal


class VolumeProfileStrategy(BaseStrategy):
    name = "volume_profile"

    def generate_signal(self, candles: pl.DataFrame, params: dict = None) -> Signal:
        params = params or {}
        bins = params.get("bins", 50)
        window = params.get("window", 100)
        proximity_pct = params.get("proximity_pct", 0.003)

        if len(candles) < window:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        df = candles.tail(window)
        closes = df["close"].to_numpy()
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        volumes = df["volume"].fill_null(0).to_numpy()

        price_min, price_max = lows.min(), highs.max()
        if price_max <= price_min:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        # Build volume profile
        edges = np.linspace(price_min, price_max, bins + 1)
        bucket_size = edges[1] - edges[0]
        vol_by_bucket = np.zeros(bins)

        for i in range(len(df)):
            low_i, high_i = lows[i], highs[i]
            vol_i = volumes[i]
            for b in range(bins):
                bucket_low = edges[b]
                bucket_high = edges[b + 1]
                overlap = max(0, min(high_i, bucket_high) - max(low_i, bucket_low))
                span = max(high_i - low_i, 1e-10)
                vol_by_bucket[b] += vol_i * (overlap / span)

        # POC = bucket with highest volume
        poc_idx = np.argmax(vol_by_bucket)
        poc = (edges[poc_idx] + edges[poc_idx + 1]) / 2

        # Value area: 70% of total volume around POC
        total_vol = vol_by_bucket.sum()
        target = total_vol * 0.70
        lower_idx, upper_idx = poc_idx, poc_idx
        accumulated = vol_by_bucket[poc_idx]
        while accumulated < target:
            expand_lower = lower_idx > 0
            expand_upper = upper_idx < bins - 1
            if not expand_lower and not expand_upper:
                break
            add_lower = vol_by_bucket[lower_idx - 1] if expand_lower else 0
            add_upper = vol_by_bucket[upper_idx + 1] if expand_upper else 0
            if add_lower >= add_upper and expand_lower:
                lower_idx -= 1
                accumulated += add_lower
            elif expand_upper:
                upper_idx += 1
                accumulated += add_upper
            else:
                lower_idx -= 1
                accumulated += add_lower

        val = (edges[lower_idx] + edges[lower_idx + 1]) / 2
        vah = (edges[upper_idx] + edges[upper_idx + 1]) / 2

        current_price = float(closes[-1])
        atr = self._atr(candles)
        rsi = self._rsi(candles)

        # Signal: price near POC with momentum confirmation
        near_poc = abs(current_price - poc) / poc < proximity_pct
        near_val = abs(current_price - val) / val < proximity_pct * 1.5

        direction = 0
        confidence = 0.0
        reasoning = ""

        if near_val and current_price < poc and 40 < rsi < 65:
            direction = 1
            confidence = 0.60 + min(0.20, (poc - current_price) / poc * 10)
            reasoning = f"Price near VAL ({val:.2f}), POC at {poc:.2f}, RSI {rsi:.1f}"
        elif near_poc and current_price > val and current_price < vah:
            direction = 1 if rsi < 55 else -1
            confidence = 0.55
            reasoning = f"Price at POC ({poc:.2f}), RSI {rsi:.1f}"

        if direction == 0 or atr == 0:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        sl_dist = atr * 1.5
        tp_dist = sl_dist * 2.5
        entry = current_price
        tp = entry + tp_dist if direction == 1 else entry - tp_dist
        sl = entry - sl_dist if direction == 1 else entry + sl_dist
        rr = tp_dist / sl_dist

        return Signal(
            direction=direction, confidence=confidence,
            entry=entry, tp=tp, sl=sl, rr_ratio=rr,
            strategy=self.name, reasoning=reasoning,
            metadata={"poc": poc, "vah": vah, "val": val,
                      "atr": atr, "rsi": rsi},
        )
