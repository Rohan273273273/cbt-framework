# $100 → $1,000 — strategy validation toolkit

Companion to the operating prompt. The prompt says *how to trade*. This says
*whether the plan can work* — and answers it with numbers instead of vibes.

```
trading/
├── tradingview/           Pine v6 strategies + free-tier backtest guide
│   ├── core_ema_pullback.pine     CORE setup 3 (daily)
│   ├── core_gap_and_go.pine       CORE setup 1 (5 min)
│   ├── core_vwap_reclaim.pine     CORE setup 2 (5 min)
│   ├── strike_signal.pine         STRIKE signal harness -> feeds the sim
│   └── BACKTEST_GUIDE.md          exact steps, and what counts as a pass
├── sim/
│   ├── bs.py                 Black-Scholes, no dependencies
│   ├── option_trade_sim.py   stock edge -> real option P&L (theta, IV crush)
│   ├── path_sim.py           15-day account Monte Carlo under the risk rules
│   ├── run_study.py          end-to-end study
│   └── required_edge.py      inverse: how good must the signal be?
└── results/                  generated CSVs
```

## Why it is split this way

TradingView owns the price history and the Strategy Tester — it can tell you
whether a setup has an edge. It cannot tell you two things that decide this
mandate:

1. **What the option returned.** There is no options chain in Pine. A signal
   that makes +3.8% on the stock can still lose money as a 7-DTE call, because
   theta and the bid/ask take their cut first.
2. **The probability of the path.** The Strategy Tester reports total return
   over years. The mandate is a 15-session sprint with 25%-of-equity bets, a
   -35% daily stop and a $35 kill switch. That is a path-dependent question and
   only Monte Carlo answers it.

So: measure the edge in TradingView, then convert edge → option returns →
distribution of account outcomes locally.

## Quick start

```bash
cd trading/sim
python3 run_study.py            # uses placeholder edge numbers
python3 required_edge.py        # how strong would the signal need to be?
```

Replace the placeholders with your own TradingView measurements
(`BACKTEST_GUIDE.md` step 3) before believing any of it.

## The finding

Run with a *realistic* measured edge (44% win rate, +3.8%/-2.1%, 2.5-day hold,
2.5% ATR), the simulator returns:

| Sizing per STRIKE bet | P(touch $1,000) | P(ruin) | Median outcome |
|---|---|---|---|
| 25% (the prompt's own rule) | **0.0%** | 0% | $87 |
| 40% | 0.1% | 6% | $76 |
| 60% | 0.5% | 40% | $51 |
| 100% (all-in, every bet) | 2.2% | 62% | $30 |

And from `required_edge.py`, holding sizing at the prompt's 25% rule, the target
stays out of reach *at every level of skill* — including a signal far better
than any retail system realistically achieves:

| Signal quality | P($1,000) @ 25% | @ 50% | @ 100% |
|---|---|---|---|
| decent (+0.5%/trade) | 0.01% | 0.24% | 2.3% |
| strong (+1.3%/trade) | 0.01% | 0.42% | 5.8% |
| elite (+2.6%/trade) | 0.03% | 2.8% | 21.3% |

**The binding constraint is not skill. It is the interaction of 10x, 15 days,
and any position size small enough to survive a loss.** The risk rules in the
operating prompt and its $1,000 target are mutually exclusive: obey the rules
and you cannot get there; break them and ruin becomes the base case.

That is a result worth having *before* funding the account, not after.
