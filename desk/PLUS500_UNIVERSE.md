# Plus500 Instrument Universe — verification rule

The tradeable universe is defined by Plus500's own instrument list:
https://www.plus500.com/en-au/instruments

**Hard rule: no stock enters the Top 3 unless it is verified to exist as a Plus500
instrument.** Unverified names may appear only in the watchlist, clearly flagged.

## How to verify (plus500.com returns 403 to direct fetches)

Use **WebSearch** with a site-scoped query — individual instrument pages follow the
pattern `plus500.com/<locale>/instruments/<ticker>`:

```
site:plus500.com instruments <TICKER> <Company Name>
```

- Result links like `plus500.com/en-.../instruments/xom` ⇒ **listed** ✅
- No instrument-page results for the ticker ⇒ treat as **not listed** ❌ and replace
  the pick with the next-ranked verified candidate.

## Verified listed (checked 2026-07-08)
| Ticker | Company | Evidence |
|---|---|---|
| XOM | ExxonMobil | plus500.com/en/instruments/xom |
| NET | Cloudflare | plus500.com/en-SG/Instruments/NET |
| FISV | Fiserv | plus500.com/en-es/instruments/fisv |
| FSLR | First Solar | plus500.com/en-ZA/Instruments/FSLR |

## Verified NOT listed (checked 2026-07-08)
| Ticker | Company | Note |
|---|---|---|
| PENG | Penguin Solutions | No instrument page found — watchlist-only, never a pick |

## Practical notes
- Plus500 lists most S&P 500 / Nasdaq-100 constituents and popular US names; gaps are
  usually mid/small caps and recent IPOs — exactly the names that most need checking.
- Plus500 share CFDs track the exchange price but include the platform's spread;
  entries/targets/stops in reports use exchange prices — confirm on the platform.
- Cache results here: append newly verified tickers (either table) with the check date
  so future runs skip re-checking common names.
