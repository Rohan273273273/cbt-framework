"""Turn a measured stock-signal edge into a realistic option-trade return distribution.

Why this exists
---------------
TradingView can backtest the SIGNAL on the underlying and tell you win rate,
average win %, average loss % and average bars held. It cannot tell you what
the 7-DTE call you actually bought would have returned, because theta and IV
crush live outside the price series. This module bridges that gap:

  measured stock edge  ->  daily drift  ->  simulated price path
                       ->  Black-Scholes option repricing (theta + IV decay)
                       ->  trade rules applied (profit target / -50% stop)
                       ->  distribution of option returns

Feed it the four numbers off the TradingView Performance Summary.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from bs import bs_price, strike_for_delta

TRADING_DAYS = 252


@dataclass
class SignalEdge:
    """The four numbers you read off the TradingView Performance Summary."""
    win_rate: float          # e.g. 0.44
    avg_win_pct: float       # avg winning trade, % of underlying, e.g. 3.8
    avg_loss_pct: float      # avg losing trade, negative, e.g. -2.1
    avg_bars_held: float     # in DAILY bars
    realized_daily_vol: float | None = None   # override: underlying ATR% / 100

    @property
    def expectancy_pct(self) -> float:
        return self.win_rate * self.avg_win_pct + (1 - self.win_rate) * self.avg_loss_pct

    @property
    def daily_drift(self) -> float:
        """Expected underlying drift per day while the signal is on."""
        return (self.expectancy_pct / 100.0) / max(self.avg_bars_held, 0.5)

    @property
    def daily_sigma(self) -> float:
        """Realized daily vol.

        Prefer the explicit override (the underlying's ATR% is the honest
        source). The fallback infers it from the win/loss spread, which
        UNDERSTATES true vol because those returns are truncated by the
        strategy's own stops and targets.
        """
        if self.realized_daily_vol is not None:
            return self.realized_daily_vol
        p, w, l = self.win_rate, self.avg_win_pct / 100.0, self.avg_loss_pct / 100.0
        mean = p * w + (1 - p) * l
        var = p * (w - mean) ** 2 + (1 - p) * (l - mean) ** 2
        per_trade_sigma = math.sqrt(max(var, 1e-9))
        return per_trade_sigma / math.sqrt(max(self.avg_bars_held, 0.5))


@dataclass
class OptionRules:
    dte: int = 7                 # days to expiry at entry
    delta: float = 0.35          # target entry delta (prompt says 0.30-0.45)
    iv: float | None = None      # implied vol paid at entry; None = auto-calibrate
    variance_risk_premium: float = 0.15  # IV sits this % above realized, typical for
                                         # liquid single names outside events
    iv_exit_mult: float = 0.92   # IV decay over the hold (1.0 = none)
    iv_crush_mult: float = 1.0   # extra multiplier applied after a catalyst day
    crush_on_day: int | None = None   # day index the catalyst prints (None = no event)
    profit_target: float = 0.80  # +80% -> exit  (prompt rule: +60-100%)
    stop: float = -0.50          # -50% of premium -> exit (prompt rule)
    max_hold_days: int = 3
    r: float = 0.04
    slippage_pct: float = 0.03   # round-trip cost as fraction of premium (wide spreads)
    vol_of_vol: float = 0.18     # randomness in IV path
    fat_tail_df: float = 4.0     # Student-t degrees of freedom for underlying moves


def _t_shock(rng: random.Random, df: float) -> float:
    """Standardised Student-t draw: fat tails, unit variance."""
    z = rng.gauss(0.0, 1.0)
    chi = sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(int(df)))
    t = z / math.sqrt(chi / df)
    return t * math.sqrt((df - 2.0) / df)


def simulate_option_trades(edge: SignalEdge, rules: OptionRules, n: int = 40000,
                           seed: int = 7) -> list[float]:
    """Return a list of option-trade returns as fractions (-1.0 = total loss)."""
    rng = random.Random(seed)
    out: list[float] = []
    mu, sig_d = edge.daily_drift, edge.daily_sigma

    # Calibrate the vol you PAY to the vol the underlying actually delivers.
    # Hard-coding IV independently of realized vol is the single easiest way
    # to make an option backtest lie in either direction.
    base_iv = rules.iv if rules.iv is not None else (
        sig_d * math.sqrt(TRADING_DAYS) * (1.0 + rules.variance_risk_premium))

    for _ in range(n):
        S = 100.0
        T = rules.dte / 365.0
        iv = base_iv * math.exp(rng.gauss(0.0, rules.vol_of_vol))
        K = strike_for_delta(S, T, rules.r, iv, rules.delta, call=True)
        entry = bs_price(S, K, T, rules.r, iv, call=True)
        entry *= (1.0 + rules.slippage_pct)   # you pay up to get filled
        if entry <= 0.01:
            continue

        ret = rules.stop
        iv_step = rules.iv_exit_mult ** (1.0 / max(rules.max_hold_days, 1))

        for day in range(1, rules.max_hold_days + 1):
            shock = _t_shock(rng, rules.fat_tail_df)
            S *= math.exp(mu - 0.5 * sig_d ** 2 + sig_d * shock)
            T = max(T - 1.0 / 365.0, 1e-6)
            iv *= iv_step
            if rules.crush_on_day is not None and day == rules.crush_on_day:
                iv *= rules.iv_crush_mult

            px = bs_price(S, K, T, rules.r, iv, call=True)
            px *= (1.0 - rules.slippage_pct)  # you sell into the bid
            r_now = px / entry - 1.0

            if r_now <= rules.stop:
                # a gap through the stop is real; you do not always get -50%
                gap = min(r_now, rules.stop if shock > -2.0 else r_now)
                ret = max(gap, -1.0)
                break
            if r_now >= rules.profit_target:
                ret = r_now
                break
            ret = max(r_now, -1.0)

        out.append(max(ret, -1.0))
    return out


def summarize(returns: list[float]) -> dict:
    n = len(returns)
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / n
    srt = sorted(returns)
    return {
        "n": n,
        "win_rate": len(wins) / n,
        "avg_win": (sum(wins) / len(wins)) if wins else 0.0,
        "avg_loss": (sum(losses) / len(losses)) if losses else 0.0,
        "expectancy": mean,
        "stdev": math.sqrt(var),
        "p05": srt[int(0.05 * n)],
        "median": srt[n // 2],
        "p95": srt[int(0.95 * n)],
        "total_loss_rate": sum(1 for r in returns if r <= -0.95) / n,
    }
