#!/usr/bin/env python3
"""Run the full study: TradingView-measured edge -> probability of $100 -> $1,000.

Usage (numbers come off the TradingView Performance Summary):

    python3 run_study.py --win-rate 0.44 --avg-win 3.8 --avg-loss -2.1 \
        --bars-held 2.5 --atr-pct 2.5

Every number printed is produced by simulation, not assumed.
"""
from __future__ import annotations

import argparse
import csv
import os

from option_trade_sim import OptionRules, SignalEdge, simulate_option_trades, summarize
from path_sim import AccountRules, simulate_paths

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(HERE), "results")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--win-rate", type=float, default=0.44,
                    help="STRIKE signal win rate on the underlying (TradingView)")
    ap.add_argument("--avg-win", type=float, default=3.8, help="avg winning trade, %%")
    ap.add_argument("--avg-loss", type=float, default=-2.1, help="avg losing trade, %% (negative)")
    ap.add_argument("--bars-held", type=float, default=2.5, help="avg daily bars held")
    ap.add_argument("--atr-pct", type=float, default=2.5,
                    help="underlying daily ATR%% - the honest realized-vol input")
    ap.add_argument("--core-win-rate", type=float, default=0.45)
    ap.add_argument("--core-win", type=float, default=4.0, help="CORE avg win, %%")
    ap.add_argument("--core-loss", type=float, default=-2.0, help="CORE avg loss, %%")
    ap.add_argument("--vrp", type=float, default=0.15, help="IV premium over realized vol")
    ap.add_argument("--paths", type=int, default=20000)
    ap.add_argument("--opt-samples", type=int, default=20000)
    args = ap.parse_args()

    edge = SignalEdge(args.win_rate, args.avg_win, args.avg_loss, args.bars_held,
                      realized_daily_vol=args.atr_pct / 100.0)

    print("=" * 78)
    print("MEASURED SIGNAL EDGE (from TradingView)")
    print("=" * 78)
    print(f"  win rate            {edge.win_rate:.1%}")
    print(f"  expectancy / trade  {edge.expectancy_pct:+.3f}% of underlying")
    print(f"  implied daily drift {edge.daily_drift * 100:+.3f}%")
    print(f"  realized daily vol  {edge.daily_sigma * 100:.2f}%  "
          f"(annualized {edge.daily_sigma * 252 ** 0.5:.0%})")
    print(f"  IV you pay          {edge.daily_sigma * 252 ** 0.5 * (1 + args.vrp):.0%}")
    if edge.expectancy_pct <= 0:
        print("\n  !! The signal has no edge on the underlying. Nothing downstream can")
        print("     fix that. Re-measure or discard the setup before trading it.")

    # ---------- 1. option-level ----------
    print()
    print("=" * 78)
    print("STEP 1 - OPTION TRADE RETURNS (same signal, bought as calls)")
    print("=" * 78)
    print(f"{'rule set':<26}{'win%':>7}{'avg W':>8}{'avg L':>8}{'EV/trade':>10}{'p95':>8}")
    variants = {
        "7DTE, +80% target": OptionRules(dte=7, profit_target=0.80, max_hold_days=3,
                                         variance_risk_premium=args.vrp),
        "7DTE, +150% target": OptionRules(dte=7, profit_target=1.50, max_hold_days=4,
                                          variance_risk_premium=args.vrp),
        "14DTE, +250% target": OptionRules(dte=14, profit_target=2.50, max_hold_days=6,
                                           variance_risk_premium=args.vrp),
        "7DTE, into IV crush": OptionRules(dte=7, profit_target=1.50, max_hold_days=3,
                                           crush_on_day=1, iv_crush_mult=0.65,
                                           variance_risk_premium=args.vrp),
    }
    opt_dists = {}
    for name, ru in variants.items():
        rets = simulate_option_trades(edge, ru, n=args.opt_samples)
        opt_dists[name] = (rets, ru)
        s = summarize(rets)
        print(f"{name:<26}{s['win_rate']:>6.1%}{s['avg_win']:>+8.2f}{s['avg_loss']:>+8.2f}"
              f"{s['expectancy']:>+10.3f}{s['p95']:>+8.2f}")

    # ---------- 2. account-level ----------
    print()
    print("=" * 78)
    print("STEP 2 - P($100 REACHES $1,000 IN 15 SESSIONS)")
    print("=" * 78)
    print(f"{'sizing':>8}{'option rule':>22}{'P(hit $1k)':>12}{'P(ruin)':>10}"
          f"{'median end':>12}{'P(profit)':>11}")

    rows = []
    for frac in (0.25, 0.40, 0.60, 1.00):
        for name in ("7DTE, +80% target", "7DTE, +150% target", "14DTE, +250% target"):
            rets, ru = opt_dists[name]
            acc = AccountRules(strike_fraction=frac, strike_hold_days=ru.max_hold_days)
            res = simulate_paths(args.core_win_rate, args.core_win, args.core_loss,
                                 rets, acc, n_paths=args.paths)
            print(f"{frac:>7.0%}{name:>22}{res['p_hit_target']:>11.2%}"
                  f"{res['p_ruin']:>10.1%}{res['median_final']:>11.2f}"
                  f"{res['p_profit']:>11.1%}")
            rows.append({"sizing": f"{frac:.0%}", "option_rule": name,
                         "p_hit_1000": round(res["p_hit_target"], 5),
                         "p_ruin": round(res["p_ruin"], 4),
                         "median_final": round(res["median_final"], 2),
                         "p95_final": round(res["p95_final"], 2),
                         "p_profit": round(res["p_profit"], 4),
                         "p_under_25": round(res["p_under_25"], 4)})

    os.makedirs(RESULTS, exist_ok=True)
    out = os.path.join(RESULTS, "study.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    best = max(rows, key=lambda r: r["p_hit_1000"])
    print()
    print("=" * 78)
    print("VERDICT")
    print("=" * 78)
    print(f"  Best case found: {best['sizing']} sizing, {best['option_rule']}")
    print(f"    P(touch $1,000) = {best['p_hit_1000']:.2%}")
    print(f"    P(ruin)         = {best['p_ruin']:.1%}")
    print(f"    median outcome  = ${best['median_final']:.2f}")
    print(f"\n  Written: {out}")


if __name__ == "__main__":
    main()
