# Schedule — Plus500 Morning Desk

## Delivery target
Report in hand by **7:40 am Adelaide time, every day**.

## How it runs
A Claude Code Remote **Routine** fires a fresh session in this repo's environment on a
cron schedule. The session follows `desk/PIPELINE.md`, commits the report to
`desk/reports/`, pushes, and its final message (containing the top-3 table) is
delivered by push notification and email.

## Cron (the Routine scheduler runs in UTC)

| Adelaide period | Adelaide offset | Fire time (UTC) | Cron |
|---|---|---|---|
| **ACST** (Apr → Oct, current) | UTC+9:30 | 22:00 Sun–Thu (= 7:30 am Mon–Fri Adelaide) | `0 22 * * 0-4` |
| **ACDT** (first Sun Oct → first Sun Apr) | UTC+10:30 | 21:00 Sun–Thu (= 7:30 am Mon–Fri Adelaide) | `0 21 * * 0-4` |

Runs Monday–Friday Adelaide mornings only: each run targets the US session that opens
later that same Adelaide day, and there is no US session to target on Adelaide
Saturday/Sunday mornings.

Fires 10 minutes early (7:30) so the pipeline has time to run and deliver by 7:40.

⚠️ **DST changeover**: the scheduler does not follow Adelaide DST automatically.
Around the **first Sunday of October** and the **first Sunday of April**, update the
Routine's cron per the table above (ask Claude: "update the morning desk routine for
Adelaide DST").

## Market-hours context at fire time (7:30 am Adelaide)
- US market (NYSE/Nasdaq): closed ~2 hours earlier — full prior-session data available.
- Picks target the US session opening later the same Adelaide day
  (11:00 pm Adelaide during ACST/US-DST overlap).
- Monday's run uses Friday's US close plus weekend news.
