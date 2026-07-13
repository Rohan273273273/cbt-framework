# Daily Pipeline — Plus500 Morning Desk

This is the runbook the scheduled session follows every morning. It is written to be
executed by Claude Code in a fresh session with no prior context.

## Schedule
- Routine fires at **22:00 UTC Sun–Thu** = **7:30 am Mon–Fri Adelaide (ACST, UTC+9:30)**
  so the report is delivered by **7:40 am Adelaide** on trading days.
- ⚠️ **Daylight saving**: when Adelaide switches to ACDT (UTC+10:30, first Sunday of
  October → first Sunday of April), the cron must move to **21:00 UTC**. See
  `SCHEDULE.md`.
- **Target market: ASX.** The ASX opens at 9:30 am Adelaide (10:00 am AEST) — the
  report lands ~2 hours pre-open. Available inputs at fire time: yesterday's full ASX
  session, the just-closed US session (~2h earlier), overnight commodities (oil, iron
  ore, gold), SPI 200 futures, AUD/USD, and the morning's company announcements.
- Buy-at levels are set relative to yesterday's ASX close with explicit gap guidance
  (e.g., "buy at $X limit; if it gaps above $Y at open, stand aside").

## Steps

1. **Setup**: `git checkout claude/plus500-trading-agents-4xn7wc && git pull`.
   Read `desk/ORGANIZATION.md` for roles and the output contract.

2. **Scout research — LEAN MODE (default).** ⚠️ This section supersedes any older
   instruction (including the trigger prompt) that says to deploy scout subagents.
   Scheduled runs from 9–13 July 2026 died mid-run on account usage limits because
   each subagent burns 50–70k tokens; the desk now researches inline.
   - Do the Momentum and Catalyst research YOURSELF with a budget of **max ~12
     WebSearch queries + ~4 WebFetch calls total**, covering: prior ASX session
     (index close, top gainers, sector leaders), overnight leads (US close, oil/iron
     ore/gold, SPI 200 futures), today's company announcements/broker moves, and the
     RBA/AU macro calendar.
   - Useful sources via WebSearch snippets: marketindex.com.au, fool.com.au,
     kalkinemedia.com/au, stockhead.com.au, afr.com, investing.com AU. Most of these
     403-block WebFetch — rely on search snippets and fetchable article pages.
   - Subagents are allowed ONLY if everything above succeeded quickly and quota is
     clearly plentiful. Never run more than one.

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

## Fail-safe (added 2026-07-13 after three silent scheduled-run failures)
- **Never end a scheduled run silently.** If usage/rate limits, tool failures, or
  data gaps strike mid-run, stop researching and immediately send the final message
  with whatever is verified so far — even if that is only "the desk could not
  produce picks today because X". A degraded report beats no report.
- Budget discipline exists to survive account usage limits: if any tool starts
  returning limit errors, skip straight to publishing with what you have.
- Commit whatever report you produced before the final message; if git push fails
  after retries, still send the final message with the picks inline.

## Hard rules
- Never fabricate prices. Unverifiable price ⇒ label approximate or drop the pick.
- Always 3 picks unless the market gives fewer than 3 defensible setups — then say so
  explicitly rather than padding.
- Every pick has a stop-loss. No exceptions.
- Demo-account research only; include the not-financial-advice note in the report.
