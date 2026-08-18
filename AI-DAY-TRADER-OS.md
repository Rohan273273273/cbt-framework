# THE SYSTEM

## AI DAY TRADER OS

**Scan → Analyze → Plan → Execute → Manage → Review**

_by @seb.ai_

> **Read this first:** Day trading is the hardest way to trade — most day traders lose money, and no AI changes that math by itself. This doc is education, not financial advice, and promises nothing. Backtest and paper trade every strategy for at least 30 trades before risking real money. US stock accounts under $25K are limited by the Pattern Day Trader rule (max 3 day trades per 5 business days on margin accounts). All numbers below are labeled examples, not real results.

---

## 1️⃣ How the AI Day Trader Works

The AI is your analyst and discipline coach — not your finger on the buy button. The loop:

| Stage | AI does | You do |
|---|---|---|
| 🔍 **Scan** | Builds your pre-market watchlist criteria | Run the scanner |
| 🧠 **Analyze** | Scores each setup vs YOUR rules | Provide charts/data |
| 📋 **Plan** | Writes the trade plan: entry, stop, target, size | Approve or skip |
| ⚡ **Execute** | Nothing — AI never clicks buy | You place the trade (paper first) |
| 🛡️ **Manage** | Reminds you what YOUR plan says | Follow the plan |
| 📊 **Review** | Finds patterns in your trade log | Journal honestly |

**Why this split works:** the AI is immune to FOMO, revenge trading, and "just this once." Your biggest enemy in day trading is you at 10:47am after two losses. The AI holds the plan when you won't.

---

## 2️⃣ SCAN — Market Scanning Workflow

**Pre-market routine (30–45 min before open):**

- [ ] Check overall market direction (index futures up/down? big news?)
- [ ] Run your scanner for gappers: stocks up/down big pre-market on high volume
- [ ] Filter for YOUR criteria — an example filter set (illustration only): price $5–$50, pre-market volume 500K+, gap 4%+, has a news catalyst
- [ ] Pick a MAX of 3 tickers to watch. More = scattered attention = bad entries
- [ ] For each: mark yesterday's high/low, pre-market high/low, and key levels
- [ ] Feed the watchlist to Claude with prompt #4 to build trade plans BEFORE the open

**Free scanner sources:** TradingView screener, your broker's built-in scanner, or finviz.com. The tool matters less than using the same criteria every single day.

---

## 3️⃣ PLAN — Entry, Stop-Loss & Take-Profit System

No plan written down = no trade. Example numbers are illustrations:

```
DAY TRADE PLAN
Ticker: ____ | Long/Short | Setup name: ____

Entry trigger: break above pre-market high at $10.50 WITH volume — not before
Stop-loss:     $10.20 — below the consolidation low (risk: $0.30/share)
Target 1:      $11.10 (2R) — sell half, move stop to breakeven
Target 2:      trail the rest or exit at next resistance
Size:          (Account × 1%) ÷ $0.30 risk per share
Invalid if:    loses the level, volume dies, market flips red
Time stop:     if it goes nowhere in 15 min, exit — capital has better uses
```

**The three rules that make this work:**

- [ ] Stop goes where the setup is WRONG, not at a pain threshold
- [ ] Size comes from the stop distance — never "how much can I buy"
- [ ] Risk:reward under 1:2 = skip the trade. You don't need every trade; you need good ones

---

## 4️⃣ Risk Management Rules

Day trading survival is 90% risk management. Non-negotiables:

- [ ] Max 1% of account risked per trade (beginners: 0.5%)
- [ ] Daily max loss: 2% — hit it, close the platform, walk away. The market opens again tomorrow
- [ ] Two losses in a row = mandatory 30-min break away from screens
- [ ] Max 3 trades per day while learning — overtrading is the #1 account killer
- [ ] No trades in the first 5 minutes after open unless your tested plan says otherwise — the open is chop
- [ ] Flat by close. Day traders don't hold overnight — that's a different (riskier) game
- [ ] PDT rule: under $25K in a US margin account = 3 day trades per rolling 5 days. Plan around it; don't try to dodge it
- [ ] 30+ paper trades on any new setup before a single real dollar

---

## 5️⃣ MANAGE — In-Trade Checklist

Once you're in, your only job is to execute the plan you already wrote:

- [ ] Stop-loss order placed IMMEDIATELY after entry (not mental — real)
- [ ] At Target 1: take partial profit, move stop to breakeven — now it's a free trade
- [ ] Price stalls before target? Consult the plan's time stop, not your feelings
- [ ] NEVER widen the stop. NEVER average down on a day trade
- [ ] News hits mid-trade? Unclear = exit. Clarity is cheap; hope is expensive
- [ ] After exit: screenshot the chart, log the trade while it's fresh (Section 6)

---

## 6️⃣ REVIEW — Performance Tracking Dashboard

One spreadsheet row per trade. Example row is fictional:

| Date | Ticker | Setup | Risk ($) | Result (R) | Plan followed? | Emotion note |
|---|---|---|---|---|---|---|
| 3/1 (ex.) | ABC | Gap & go | $25 | −1R | Yes | Calm — good loss |

**Weekly scoreboard:** win rate, average R, biggest loss vs allowed loss, trades per day, and plan-adherence % — the only metric you fully control. Grade the process; the P&L follows the process (or doesn't — but you'll know why).

---

## 7️⃣ Claude Code Project Structure

Run this as a real project so Claude keeps your context between sessions:

```
day-trader/
├── CLAUDE.md              ← your rules, risk limits, setups (Claude reads this every session)
├── strategy/
│   ├── setups.md          ← each setup's exact entry/exit rules
│   └── risk-rules.md      ← the non-negotiables from Section 4
├── journal/
│   ├── 2026-08-01.md      ← daily plan + trade log + review
│   └── ...
├── watchlists/
│   └── premarket.md       ← today's 3 tickers with levels
└── tracking/
    └── trades.csv         ← the dashboard from Section 6
```

In `CLAUDE.md`, paste your Master Prompt (Section 9) plus your risk rules. Now every session starts with Claude already knowing your system — "morning, build my watchlist plans" just works.

---

## 8️⃣ 20 Copy-and-Paste Claude Prompts

### Scan

1. "Build me a pre-market scanning checklist for [setup type] with exact filter criteria I can enter into TradingView's screener."
2. "Here are today's pre-market gappers: [paste list + %]. Rank them against my criteria [paste] and tell me which 3 deserve watchlist spots and why."
3. "What's the news catalyst on [ticker]? Here's the headline: [paste]. Is this the kind of catalyst that sustains momentum or fades by 10am? Explain the mechanism, no predictions."

### Analyze

4. "For each watchlist ticker [list + key levels], draft a full trade plan using my template: entry trigger, stop at invalidation, 2R target, size at 1% risk on [$X]."
5. "Score this setup 1–10 against my rules [paste rules + chart description]. List what matches, what's missing, and the strongest reason to skip it."
6. "Play the bear: give me the 3 most likely ways this long fails, and the earliest warning sign for each."
7. "The market is [conditions]. Which of my setups historically work in this environment and which should I bench today?"

### Plan

8. "Calculate my share size: account [$X], risk 1%, entry [$A], stop [$B]. Show the math."
9. "Rewrite this trade idea as an if-then plan with zero judgment calls: [idea]."
10. "I have 3 A-setups but only [N] day trades left under PDT. Help me rank which one plan has the best risk:reward and cleanest invalidation."

### Execute + Manage

11. "I'm in [ticker] at [entry], stop [X], target [Y], now trading at [Z]. Read my plan back to me and tell me what it says to do right now. Do not improvise."
12. "I want to move my stop because [reason]. Challenge me hard — is this risk management or loss avoidance?"
13. "I just hit my daily max loss. Write me the shutdown script: what to log, what to review, and why walking away preserves my edge."
14. "Volume died on my position. My plan's time stop says [rule]. Walk me through the exit decision."

### Review

15. "Here's today's journal: [paste]. Grade my plan-adherence per trade, and flag every deviation with what it cost or saved."
16. "Here are my last 30 paper trades: [paste log]. Which setups, times of day, and market conditions correlate with my wins vs losses?"
17. "I keep making this mistake: [pattern]. Design one specific process guardrail — a rule, checklist item, or friction step — that makes it harder to repeat."
18. "My win rate is [X]% and average winner/loser is [Y/Z]. Is this math sustainable? Show the expectancy calculation."
19. "Write my weekly review: [paste stats + journal]. Lead with process, not P&L. What's the one thing to fix next week?"
20. "Am I ready for real money? Here's my paper record: [stats]. Judge it against: 30+ trades, positive expectancy, plan-adherence above 90%, max drawdown handled calmly. Be brutally honest."

---

## 9️⃣ THE MASTER PROMPT

```
You are my AI Day Trader — my analyst and discipline coach. You never place
trades; you make my process sharper and hold me to my own rules.

My rules: max 1% risk per trade, daily stop at −2%, max 3 trades/day, stops at
invalidation only, never widened, flat by close, minimum 1:2 risk:reward, 30+
paper trades before any new setup goes live.

Your jobs: (1) Turn my watchlist into written if-then trade plans before the
open. (2) Score setups only against MY written rules. (3) Calculate position
sizes from stop distance — show the math. (4) When I'm in a trade, read my plan
back to me instead of giving new opinions. (5) Challenge every rule deviation
immediately — this is your most important job. (6) Analyze my journal for
behavioral patterns weekly.

Hard limits: Never predict prices. Never say buy/sell/hold — present analysis
and what MY plan dictates. Never invent data — ask for what's missing. Remind me
that day trading is high-risk, most day traders lose money, and everything
untested goes to paper trading first.

Start by asking for: my account size, my written setups, whether I'm under PDT,
and today's watchlist.
```
