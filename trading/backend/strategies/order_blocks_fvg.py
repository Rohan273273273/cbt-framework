"""
Order Blocks + Fair Value Gaps (FVG).
OB: Last opposing candle before a strong impulse move.
FVG: 3-candle imbalance — gap between candle[0] high and candle[2] low (bullish).
"""
import polars as pl
from strategies.base_strategy import BaseStrategy, Signal


class OrderBlockFVGStrategy(BaseStrategy):
    name = "order_blocks_fvg"

    def generate_signal(self, candles: pl.DataFrame, params: dict = None) -> Signal:
        params = params or {}
        impulse_mult = params.get("impulse_mult", 1.5)   # body > 1.5× ATR = impulse
        max_ob_age = params.get("max_ob_age", 30)        # bars before OB invalid

        if len(candles) < 20:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        opens = candles["open"].to_numpy()
        highs = candles["high"].to_numpy()
        lows = candles["low"].to_numpy()
        closes = candles["close"].to_numpy()
        atr = self._atr(candles)
        rsi = self._rsi(candles)

        if atr == 0:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        current_price = float(closes[-1])
        bullish_obs, bearish_obs, fvgs = [], [], []

        # Scan bars (excluding last 1 for no lookahead)
        for i in range(3, len(closes) - 1):
            body = abs(closes[i] - opens[i])

            # Bullish OB: bearish candle followed by strong bullish impulse
            if closes[i] < opens[i]:
                impulse = closes[i+1] - opens[i+1] if i+1 < len(closes) else 0
                if impulse > atr * impulse_mult:
                    age = len(closes) - 1 - i
                    if age <= max_ob_age:
                        ob_top = opens[i]
                        ob_bottom = closes[i]
                        # Valid if price hasn't closed through OB
                        if current_price > ob_bottom:
                            bullish_obs.append({
                                "top": ob_top, "bottom": ob_bottom,
                                "age": age, "index": i
                            })

            # Bearish OB: bullish candle followed by strong bearish impulse
            if closes[i] > opens[i]:
                impulse = opens[i+1] - closes[i+1] if i+1 < len(closes) else 0
                if impulse > atr * impulse_mult:
                    age = len(closes) - 1 - i
                    if age <= max_ob_age:
                        ob_top = closes[i]
                        ob_bottom = opens[i]
                        if current_price < ob_top:
                            bearish_obs.append({
                                "top": ob_top, "bottom": ob_bottom,
                                "age": age, "index": i
                            })

            # FVG detection (3-candle pattern)
            if i >= 2:
                # Bullish FVG: candle[i-2] high < candle[i] low
                if highs[i-2] < lows[i] and closes[i-1] > opens[i-1]:
                    fvgs.append({
                        "type": "bullish", "top": lows[i],
                        "bottom": highs[i-2], "age": len(closes) - 1 - i
                    })
                # Bearish FVG: candle[i-2] low > candle[i] high
                elif lows[i-2] > highs[i] and closes[i-1] < opens[i-1]:
                    fvgs.append({
                        "type": "bearish", "top": lows[i-2],
                        "bottom": highs[i], "age": len(closes) - 1 - i
                    })

        direction = 0
        confidence = 0.0
        reasoning = ""
        matched_zone = None

        # Check if price is inside a bullish OB or FVG
        for ob in sorted(bullish_obs, key=lambda x: x["age"]):
            if ob["bottom"] <= current_price <= ob["top"] and rsi < 60:
                direction = 1
                age_penalty = ob["age"] / max_ob_age * 0.15
                confidence = max(0.55, 0.78 - age_penalty)
                reasoning = f"Price inside bullish OB [{ob['bottom']:.2f}–{ob['top']:.2f}], age={ob['age']}bars"
                matched_zone = {"type": "ob", "top": ob["top"], "bottom": ob["bottom"]}
                break

        if direction == 0:
            for ob in sorted(bearish_obs, key=lambda x: x["age"]):
                if ob["bottom"] <= current_price <= ob["top"] and rsi > 40:
                    direction = -1
                    age_penalty = ob["age"] / max_ob_age * 0.15
                    confidence = max(0.55, 0.78 - age_penalty)
                    reasoning = f"Price inside bearish OB [{ob['bottom']:.2f}–{ob['top']:.2f}], age={ob['age']}bars"
                    matched_zone = {"type": "ob", "top": ob["top"], "bottom": ob["bottom"]}
                    break

        if direction == 0:
            recent_fvgs = [f for f in fvgs if f["age"] <= 20]
            for fvg in sorted(recent_fvgs, key=lambda x: x["age"]):
                if fvg["type"] == "bullish" and fvg["bottom"] <= current_price <= fvg["top"]:
                    direction = 1
                    confidence = 0.62
                    reasoning = f"Price in bullish FVG [{fvg['bottom']:.2f}–{fvg['top']:.2f}]"
                    matched_zone = fvg
                    break
                elif fvg["type"] == "bearish" and fvg["bottom"] <= current_price <= fvg["top"]:
                    direction = -1
                    confidence = 0.62
                    reasoning = f"Price in bearish FVG [{fvg['bottom']:.2f}–{fvg['top']:.2f}]"
                    matched_zone = fvg
                    break

        if direction == 0:
            return Signal(direction=0, confidence=0.0, strategy=self.name)

        entry = current_price
        sl_dist = atr * 1.5
        tp_dist = sl_dist * 2.5
        tp = entry + tp_dist if direction == 1 else entry - tp_dist
        sl = entry - sl_dist if direction == 1 else entry + sl_dist

        return Signal(
            direction=direction, confidence=confidence,
            entry=entry, tp=tp, sl=sl, rr_ratio=tp_dist / sl_dist,
            strategy=self.name, reasoning=reasoning,
            metadata={"zone": matched_zone, "atr": atr, "rsi": rsi,
                      "bullish_obs": len(bullish_obs), "bearish_obs": len(bearish_obs),
                      "fvgs": [f for f in fvgs if f["age"] <= 20][:5]},
        )
