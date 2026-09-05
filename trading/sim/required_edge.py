#!/usr/bin/env python3
"""Inverse question: how good would the signal have to BE for $1,000 to be likely?

Sweeps signal quality against position sizing and reports P(touch $1,000).
This is the number to check a strategy against BEFORE trading it.
"""
from option_trade_sim import OptionRules, SignalEdge, simulate_option_trades, summarize
from path_sim import AccountRules, simulate_paths

GRID = [
    ("weak    (edge +0.2%/trade)", 0.40, 3.0, -1.8),
    ("decent  (edge +0.5%/trade)", 0.44, 3.8, -2.1),
    ("strong  (edge +1.3%/trade)", 0.50, 5.0, -2.4),
    ("elite   (edge +2.6%/trade)", 0.55, 7.0, -2.8),
    ("fantasy (edge +5.6%/trade)", 0.65, 10.0, -3.5),
]

print(f"{'signal quality':<28}{'opt EV':>9}{'25% size':>11}{'50% size':>11}{'100% size':>11}{'ruin@100%':>11}")
print("-" * 81)
for label, wr, aw, al in GRID:
    edge = SignalEdge(wr, aw, al, 2.5, realized_daily_vol=0.025)
    rules = OptionRules(dte=14, profit_target=2.5, max_hold_days=6)
    rets = simulate_option_trades(edge, rules, n=25000)
    ev = summarize(rets)["expectancy"]
    cells, ruin = [], 0.0
    for frac in (0.25, 0.50, 1.00):
        acc = AccountRules(strike_fraction=frac, strike_hold_days=rules.max_hold_days)
        res = simulate_paths(0.45, 4.0, -2.0, rets, acc, n_paths=20000)
        cells.append(res["p_hit_target"])
        ruin = res["p_ruin"]
    print(f"{label:<28}{ev:>+9.3f}{cells[0]:>10.2%}{cells[1]:>11.2%}{cells[2]:>11.2%}{ruin:>11.1%}")
