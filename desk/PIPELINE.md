# Daily Pipeline — Plus500 Morning Desk

This is the runbook the scheduled session follows every morning. It is written to be
executed by Claude Code in a fresh session with no prior context.

## Schedule
- Routine fires at **22:00 UTC Sun–Thu** = **7:30 am Mon–Fri Adelaide (ACST, UTC+9:30)**
  so the report is delivered by **7:40 am Adelaide** on trading days.
- ⚠️ **Daylight saving**: when Adelaide switches to ACDT (UTC+10:30, first Sunday of
  October → first Sunday of April), the cron must move to **21:00 UTC**. See
  `SCHEDULE.md`.
- At that hour the US market closed ~2 hours earlier; picks target the US session
  that opens later the same Adelaide day (13:30 UTC winter / 14:30 UTC when the US
  is off DST).

## Steps

1. **Setup**: `git checkout claude/plus500-trading-agents-4xn7wc && git pull`.
   Read `desk/ORGANIZATION.md` for roles and the output contract.

2. **Deploy scouts in parallel** (Agent tool, general-purpose, background):
   - **Momentum Scout** — prior-session top gainers, unusual volume, breakouts,
     sector leadership. 8–12 liquid Plus500-tradeable candidates with closing prices.
   - **Catalyst Scout** — earnings due today / after-hours reactions, upgrades/
     downgrades, company news, macro calendar for the session.

   Both scouts must use **WebSearch/WebFetch only** for web data (the sandbox proxy
   blocks direct curl to finance sites). Use Alpha Vantage MCP tools first if quota
   allows (free key = 25 requests/day; budget them for quotes, not scans).

3. **Merge & score** candidates per the rubric in `ORGANIZATION.md`.

4. **Risk & levels pass** on the top ~5: verify last close / after-hours price,
   find support/resistance, set buy-at, sell-at target, stop-loss with
   reward:risk ≥ 1.5:1. Drop anything unverifiable or already over-extended.

5. **Plus500 universe check** (see `desk/PLUS500_UNIVERSE.md`): every Top-3 candidate
   must be verified as a Plus500 instrument — check the cached tables first, otherwise
   WebSearch `site:plus500.com instruments <TICKER> <Company>`. Not listed ⇒ promote
   the next verified candidate. Append newly checked tickers to the cache tables.

6. **Publish**:
   - Write `desk/reports/YYYY-MM-DD.md` (Adelaide date) using
     `desk/templates/report-template.md`.
   - Commit with message `desk: daily picks YYYY-MM-DD` and push to
     `claude/plus500-trading-agents-4xn7wc` (`git push -u origin <branch>`,
     retry on network errors with backoff).
   - **The final chat message must contain the full top-3 table** (ticker, buy at,
     sell at, stop, confidence) — this text is what reaches the user's phone/email
     notification. Do not just link the report.

## Hard rules
- Never fabricate prices. Unverifiable price ⇒ label approximate or drop the pick.
- Always 3 picks unless the market gives fewer than 3 defensible setups — then say so
  explicitly rather than padding.
- Every pick has a stop-loss. No exceptions.
- Demo-account research only; include the not-financial-advice note in the report.
