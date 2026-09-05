# Backtesting the $100 → $1,000 plan on TradingView (free tier)

The split of labour matters. Get it wrong and you will "validate" a strategy
that cannot possibly hit the target.

| Question | Answered by |
|---|---|
| Does the setup have an edge on the underlying? | **TradingView Strategy Tester** |
| What would the *option* on that signal have returned? | `sim/option_trade_sim.py` |
| What is P(this $100 account touches $1,000 in 15 sessions)? | `sim/path_sim.py` |

TradingView has the price history. It does **not** have an options chain, and
its Strategy Tester reports total return — never the *distribution of paths*
under 25%-of-equity sizing. Those two gaps are what the local simulator fills.

---

## Step 1 — load a strategy

1. Open a chart → **Pine Editor** (bottom panel) → **Open → New blank strategy**.
2. Paste one `.pine` file from this folder, replacing everything.
3. **Save**, then **Add to chart**.
4. Open the **Strategy Tester** tab.

| Script | Chart timeframe | What it measures |
|---|---|---|
| `core_ema_pullback.pine` | Daily | CORE trend-pullback edge |
| `core_gap_and_go.pine` | 5 min | CORE opening-range continuation |
| `core_vwap_reclaim.pine` | 5 min | CORE intraday mean-reversion-to-trend |
| `strike_signal.pine` | Daily | STRIKE directional signal → feeds the option model |

## Step 2 — set the test up honestly

- **Symbols:** run each script across a *basket*, not one ticker. Suggested:
  `SPY, QQQ, IWM, NVDA, AMD, TSLA, META, AAPL, AMZN, COIN, PLTR`.
  A strategy that only works on NVDA in 2023 is a curve fit, not an edge.
- **Properties tab:** set *Initial capital* `100`, *Order size* leave as the
  script sets it, *Commission* `0` (your broker is commission-free), and
  **Slippage ≥ 2 ticks**. Slippage is not optional — a $100 account trading
  momentum gets filled badly, and zero-slippage backtests are the most common
  way small-account plans look profitable and aren't.
- **Date range:** as far back as the free tier gives you. Deep Backtesting is
  a paid feature, so on free you are limited to what the chart loads —
  roughly a few years on daily, a few months on 5-minute. Check the tier
  limits in your account; they change.
- Run each strategy over **at least two different market regimes** (a trending
  stretch and a chopping/declining stretch). A momentum system tested only on
  an uptrend tells you nothing about the next three weeks.

## Step 3 — record exactly four numbers

From the **Performance Summary** tab, for `strike_signal.pine`:

| Number | Where |
|---|---|
| Win rate % | "Percent Profitable" |
| Avg winning trade % | "Avg Winning Trade" (as % — switch the toggle) |
| Avg losing trade % | "Avg Losing Trade" |
| Avg bars held | "Avg # Bars in Trades" |

Plus the underlying's **ATR %** — it is plotted to the Data Window by
`strike_signal.pine`; hover a bar and read it.

The free tier does not export the trade list to CSV. You don't need it —
those four summary numbers plus ATR% are the whole input.

## Step 4 — convert edge into probability

```bash
cd trading/sim
python3 run_study.py \
    --win-rate 0.44 --avg-win 3.8 --avg-loss -2.1 \
    --bars-held 2.5 --atr-pct 2.5
```

This reprices the signal as a real option trade (theta, IV decay, bid/ask,
IV crush if there's an event) and then Monte-Carlos 20,000 fifteen-day account
paths under the prompt's risk rules. Output: `P(touch $1,000)`, `P(ruin)`, and
the median outcome.

```bash
python3 required_edge.py   # how good would the signal have to BE?
```

## What counts as a pass

Before a setup is allowed into live trading:

- **≥ 100 trades** in the sample. Below ~30, the win rate is noise.
- **Profit factor > 1.3** and a positive expectancy *after* 2-tick slippage.
- Holds up on **at least 6 of the 11 basket symbols** — not just the best one.
- Survives a **±25% change in every input**. If the edge dies when the
  breakout lookback moves from 20 to 25 bars, it was curve-fit to the past.

If a setup fails any of these, delete it from the playbook. Trading a setup you
could not validate is the expensive version of finding out.

## Known limits of this approach — read before trusting a number

- **Intraday history on free is short.** The 5-minute results are a sanity
  check, not proof.
- **Survivorship bias.** Testing today's liquid large caps over past years
  bakes in the fact that they *became* today's winners.
- **Fills.** Backtests fill at the bar close. Gap-and-go entries in real life
  fill worse, and on 25%-of-account option positions the spread alone can be
  several percent per round trip.
- **Options are modelled, not observed.** The option leg comes from
  Black-Scholes with a calibrated IV, not from real historical chains. It is
  directionally right about theta and crush; it is not a fill-accurate record.
- **The Pine here has not been compiled.** It was written offline in this
  environment. If a script throws a syntax error in the editor, the error line
  is shown in the console — fix or send it back to me.
