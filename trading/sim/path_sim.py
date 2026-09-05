"""Account-path simulator for the $100 -> $1,000 mandate.

The Strategy Tester answers "does the signal have an edge?".
It does NOT answer "what is the probability this $100 account touches $1,000
in 15 sessions under 25%-of-equity sizing, a -35% daily stop and a $35 kill
switch?" — that is a path-dependent question and it is the only one that
matters here. This module answers it by Monte Carlo.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass
class AccountRules:
    start_equity: float = 100.0
    target: float = 1000.0
    horizon_days: int = 15
    core_share: float = 0.60          # CORE sleeve as a share of equity
    strike_fraction: float = 0.25     # risk per STRIKE bet, as a share of RISK equity
    max_concurrent_strike: int = 2
    daily_stop: float = -0.35         # halt entries after this intraday drawdown
    kill_switch: float = 35.0         # stop the experiment entirely below this
    lock_on_double: bool = True       # bank 50% of gains each time equity doubles
    core_trades_per_day: float = 0.6  # probability a CORE setup qualifies on a day
    strike_hold_days: int = 3


def simulate_paths(core_win_rate: float, core_win_pct: float, core_loss_pct: float,
                   option_returns: list[float], rules: AccountRules,
                   n_paths: int = 20000, seed: int = 11) -> dict:
    rng = random.Random(seed)
    n_opt = len(option_returns)

    hits, ruins, finals, peaks = 0, 0, [], []

    strike_gap = max(rules.strike_hold_days + 1, 1)
    strike_days = set(range(1, rules.horizon_days + 1, strike_gap))

    for _ in range(n_paths):
        equity = rules.start_equity
        locked = 0.0            # banked, never risked again
        next_double = rules.start_equity * 2.0
        peak = equity
        dead = False

        for day in range(1, rules.horizon_days + 1):
            if dead:
                break
            day_open = equity
            risk_equity = max(equity - locked, 0.0)

            # ---- CORE sleeve ----
            if rng.random() < rules.core_trades_per_day:
                r = (core_win_pct if rng.random() < core_win_rate else core_loss_pct) / 100.0
                equity += risk_equity * rules.core_share * r

            # ---- STRIKE sleeve ----
            if day in strike_days and equity > rules.kill_switch:
                if (equity / day_open - 1.0) > rules.daily_stop:
                    stake = max(equity - locked, 0.0) * rules.strike_fraction
                    stake = min(stake, equity)
                    equity += stake * option_returns[rng.randrange(n_opt)]

            # ---- risk controls ----
            if rules.lock_on_double and equity >= next_double:
                gain = equity - next_double / 2.0
                locked += 0.5 * gain
                next_double = equity * 2.0

            peak = max(peak, equity)
            if equity < rules.kill_switch:
                dead = True

        if peak >= rules.target:
            hits += 1
        if equity < rules.kill_switch:
            ruins += 1
        finals.append(equity)
        peaks.append(peak)

    finals.sort()
    n = len(finals)
    return {
        "p_hit_target": hits / n_paths,
        "p_ruin": ruins / n_paths,
        "median_final": finals[n // 2],
        "mean_final": sum(finals) / n,
        "p05_final": finals[int(0.05 * n)],
        "p95_final": finals[int(0.95 * n)],
        "p_profit": sum(1 for f in finals if f > rules.start_equity) / n,
        "p_under_25": sum(1 for f in finals if f < 25) / n,
    }
