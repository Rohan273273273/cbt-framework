# Plus500 Morning Desk — Organization

A multi-agent research desk that produces one deliverable every morning:
**the top 3 US stocks to buy today, each with a buy-at price, a sell-at (target) price,
and a stop-loss** — delivered by **7:40 am Adelaide time**.

> ⚠️ For use with a **Plus500 demo account** only. This is automated research, not
> financial advice. CFD prices on Plus500 can differ slightly from exchange prices
> (spread). Always confirm levels on the platform before entering.

## Org chart

```
                 ┌──────────────────────┐
                 │   DESK CHIEF (lead)  │  synthesizes, ranks, prices, publishes
                 └──────────┬───────────┘
        ┌───────────────────┼────────────────────┐
        ▼                   ▼                    ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────────┐
│ MOMENTUM      │  │ CATALYST       │  │ RISK & LEVELS    │
│ SCOUT         │  │ SCOUT          │  │ ANALYST          │
└───────────────┘  └────────────────┘  └──────────────────┘
```

## Roles

### 1. Momentum Scout (subagent)
Scans the prior US session for top gainers, unusual volume, breakouts, and sector
leadership. Returns 8–12 liquid candidates with closing prices and reasons.
Universe: S&P 500 / Nasdaq 100 constituents and high-profile liquid names —
i.e., stocks actually tradeable as CFDs on Plus500 (https://www.plus500.com/en-au/instruments).
No microcaps, no OTC. Final picks are verified per `desk/PLUS500_UNIVERSE.md`.

### 2. Catalyst Scout (subagent)
Finds event-driven setups for the upcoming session: earnings (pre-open and the
prior evening's after-hours reactions), analyst upgrades/downgrades, M&A and
company news, and the macro calendar (CPI, Fed, FOMC minutes, jobs data).

### 3. Risk & Levels Analyst (subagent or lead)
Takes the merged candidate list and works out entries and exits: recent
support/resistance, prior close / after-hours prices, average true range for
realistic targets, and flags anything untradeable (already gapped too far,
binary event risk, illiquid).

### 4. Desk Chief (lead session)
Merges the scouts' findings, scores candidates, and picks the **top 3**.
Scoring rubric (each 0–5, higher is better):

| Factor | Weight | What it measures |
|---|---|---|
| Catalyst strength | 30% | Fresh, concrete reason to move today |
| Momentum / trend | 25% | Multi-day strength, closed near highs |
| Liquidity & tradeability | 20% | Large cap, tight spread, on Plus500 |
| Risk/reward | 25% | ≥ 1.5:1 reward-to-stop at the proposed levels |

Publishes the daily report (see `templates/report-template.md`), commits it to
`desk/reports/YYYY-MM-DD.md` (Adelaide date), and pushes.

## Output contract (every day, no exceptions)

For each of the 3 picks:
- **Ticker + company**
- **Buy at** — limit price near/below last close, or "market at open" if gapping with the trade
- **Sell at (target)** — realistic intraday-to-2-day target
- **Stop loss** — always included; risk per trade must not exceed reward ÷ 1.5
- **Why** — 1–3 sentences (catalyst + momentum + level)
- **Confidence** — High / Medium / Speculative

Plus a market-tone header (index levels, macro events due today) and a
data-freshness note (which sources, what timestamp).

## Data sources (in priority order)
1. Alpha Vantage MCP tools (when daily quota available — free key is 25 req/day)
2. WebSearch / WebFetch (financial news sites, Yahoo Finance pages, exchange sites)
3. Never fabricate a price. If a price can't be verified, label it approximate
   and widen the stop, or drop the candidate.
