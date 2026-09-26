# Getting data from LSEG: a guide for the coding agent

This guide pairs with `lseg_client.py` (drop it into the repo, e.g. as `<package>/lseg_client.py`).
Everything below was learned against the live API during Assignments 1.1 and 2 of FinTech 535
(Aug–Sep 2026), mostly by getting it wrong first. **Treat each rule as measured fact, not
style.** If the new assignment's brief contradicts one, ask the user. Don't pick a side yourself.

---

## 1. Setup

| Item | Value |
|---|---|
| Library | `lseg-data` (version **2.1.1** worked), `import lseg.data as ld` |
| Python | 3.12 (conda env `algo` on this machine: `/c/Users/rjd61/anaconda3/envs/algo/python`). Conda `base` is 3.8 and is the wrong one. |
| Also needed | `pandas`, `numpy`; `pyarrow` if you write parquet. **Pin versions in `requirements.txt`.** pandas 3.0 changed datetime units and string dtypes, and an unpinned CI went red while local stayed green. |
| Session type | **Desktop** session: the LSEG Workspace app must be **running and signed in** on this machine. There is no cloud or platform session. |
| Credentials | `lseg-data.config.json` in the **repo root**. `open_session()` finds it from the CWD, so run scripts from the root. Shape: |

```json
{ "sessions": { "default": "desktop.workspace",
                "desktop": { "workspace": { "app-key": "<the user's app key>" } } } }
```

- **Add `lseg-data.config.json` to `.gitignore` before anything else.** Never print it, commit it, or copy it into anything that ships. The user copies it over from the old repo.
- **Do not install Playwright into the same env.** It bumps `pyee` past `lseg-data`'s pin and breaks `import lseg.data`. If you need a browser, use a throwaway venv.

## 2. The minimal working pull

```python
import datetime as dt
from lseg_client import lseg_session, fetch_universe, fetch_options, strike_band, to_wide

with lseg_session() as ld:                       # raises if the session did not really open
    # Stock: a RIC with an exchange suffix. QQQ.O and UUUU.K both worked. Check others in Workspace.
    stock_long, errs = fetch_universe(ld, ["QQQ.O"], ["TRDPRC_1", "HIGH_1", "LOW_1", "BID", "ASK"],
                                      "2026-07-06", "2026-09-12", interval="hourly")
    stock = to_wide(stock_long)

    # One weekly expiry's calls, banded around the stock's range that week
    strikes = strike_band(stock["LOW_1"].min(), stock["HIGH_1"].max(), step=1.0, pad=4)
    opts_long, diag = fetch_options(ld, "QQQ", dt.date(2026, 9, 11), strikes,
                                    ["TRDPRC_1", "BID", "ASK"], "2026-09-08", "2026-09-12",
                                    cp="C", interval="hourly")
    opts = to_wide(opts_long)
```

`interval` is `"daily"` or `"hourly"` (these two were used; LSEG accepts others). `end` is
effectively exclusive, so pass the day *after* the last one you want.

## 3. Option RICs: the grammar and the traps

```
{ROOT}{M}{DD}{YY}{SSSSS}.U^{M}{YY}      expired form, e.g. QQQG102662500.U^G26
{ROOT}{M}{DD}{YY}{SSSSS}.U              live form,    e.g. QQQI182671000.U
```

- **Month code:** calls `A`–`L` = Jan–Dec, puts `M`–`X` = Jan–Dec.
- **The caret suffix uses the *call* month letter for both calls and puts.** A June put is `UUUUR122601100.U^F26`. The course README implied `^R26`, and that form returned **zero puts**.
- **The day is always zero-padded** (`05`), even though the brief says "not zero-padded". The brief's own unpadded examples don't resolve.
- **Strike** is 5 digits of hundredths (`71000` = $710.00), so the max is **$999.99**. Above that, the builder raises: a 6-digit strike builds a RIC for a *different* contract, which returns nothing and fails silently. Stocks priced near $1,000+ need another approach. Ask the user.
- **The same contract answers to *either* form, depending on how long ago it expired, and the switch takes several days.** Two days after expiry, contracts answered only to the live form. Four days after, the same contracts answered only to the caret form. **Always ask both**, which `fetch_options` does, and record which form answered (`diag["ric_form_used"]`).
- **Strike steps differ by underlying.** QQQ weeklies near the money were $1.00 (712.50 returned nothing); UUUU used $0.50. Measure it with a small spike first; don't assume.
- **A stock split changes the option root** and makes the built RICs miss the adjusted contracts. Check for splits in the window before pulling.
- OCC symbol (if the brief wants one): `occ_symbol()` gives `QQQ   260918C00710000`. The root padding to 6 characters is part of the symbol.

## 4. Things that will waste hours if you don't know them

1. **Never use the derivatives-chain endpoint for expired contracts.** It's a known dead end. Instead, *guess* RICs over an expiry × strike grid and let the API reject the ones that never existed. Most guesses failing is normal.
2. **`ld.open_session()` does not raise when it fails.** It leaves a closed session, and every request then looks like "no data". `lseg_session()` checks `open_state`. If it reports `Closed` with a handshake `ReadTimeout`, the Workspace proxy is up but the desktop isn't answering. Confirm Workspace is signed in (a quote loads in the app), and if it still hangs, **restart Workspace completely**. "Workspace is running" is not the check. Diagnose with:
   ```bash
   curl -s http://localhost:9000/api/status        # ST_PROXY_READY = proxy up (says nothing about login)
   python -c "import lseg.data as ld; ld.open_session(); print(ld.session.get_default().open_state); ld.close_session()"
   ```
3. **Never let an outage get recorded as a market fact.** If a request fails, the result is "unknown", not "no trade" or "skip". Fail loudly and write nothing.
4. **Batches:** request about 25 RICs at a time. A batch can fail *whole* over one bad RIC (you may also see `TypeError: 'UniverseContainer' object is not subscriptable`), and the fix is to retry each RIC alone, which `fetch_universe` does. A batch can also answer **partially** and raise nothing. Compare the RICs returned against the RICs requested (`diag["unanswered"]`), or missing contracts leave no trace.
5. **The response shape varies with the request:** MultiIndex `(RIC, field)` or `(field, RIC)`, flat fields for one RIC, flat RICs when only one field has data. `to_long()` handles all of them by matching the *requested* RICs. Don't index columns positionally.
6. **Asking for a field a RIC doesn't carry raises `LDError`** rather than returning an empty column. To probe whether a field exists, request it **paired with `TRDPRC_1`**.
7. **There is no `SETTLE` price for US listed equity options.** The exchanges, OPRA and the OCC don't publish one. The usable "mark" is **`MID_PRICE`** on daily bars. On hourly bars, compute mid = (BID+ASK)/2 from the bar's final bid and ask, and treat a zero or missing bid as "no valid mid".
8. **Intraday timestamps are tz-naive UTC, stamped at the bar's start.** A bar labelled 19:00 UTC is 15:00–16:00 ET under EDT (20:00 UTC under EST). Always `to_exchange_time()`, and never hardcode a UTC hour. Daily bars are plain dates, so leave them alone.
9. **"The last bar of the day" is not the close.** Hourly tapes run past 16:00 ET with real quotes: the stock ~04:00–20:00 ET, options through a 16:00 ET bar. `max(ts)` of a session is a post-close stub. For the closing hour, select the bar whose **ET start is 15:00**. Also filter regular-session hours explicitly (09:30–16:00) for anything statistical.
10. **Thin extended-hours bars carry bogus `HIGH_1`/`LOW_1` ticks.** One 17:00 ET QQQ bar printed a low of 667 with the stock at ~715. When banding strikes off high/low, err wide (a wasted request fails soft; a missing strike silently kills a trade). Anything that plots high/low must expect these ticks.
11. **Build strike ladders in integer cents** (`strike_band`). A float ladder drifts one cent off a real strike, and that returns nothing.
12. **Band strikes per expiry, not across the whole window.** A window-wide ladder asks every expiry for strikes it never listed, which is slow and floods the diagnostics.
13. **A live (unexpired) contract's hourly bid/ask *history* is available.** You can capture today's completed 15:00 bar after the close (~16:05 ET) through the same code path as a backtest. No race needed.
14. **`BID`/`ASK` on a `.U` RIC are not proven to be the NBBO**, and `C_SEC_OFST` timestamps the last *trade*, not the last quote. Claim "final bid/ask reported in the bar", nothing stronger.
15. **Speed:** real pulls took **~25 minutes** (about 1,100 RIC requests, hourly, 10 weeks). Tell the user before starting a long pull. A silent blocking pull looks like a hang.

## 5. Cache discipline (graded in past assignments)

- **Pull once, commit the data, never re-pull when the file exists.** Call `refuse_overwrite(path)` first. If a re-pull is truly needed, the user renames the old file.
- Split the code into a **fetch** function (the only network code, run by a human with Workspace up) and a **load** function that never touches the network. Tests, builds and CI use only `load`. CI has no credentials and no Workspace.
- Save a **sidecar** (JSON) beside the data: fields requested, window, interval, tz convention, strike step, `ric_form_used`, `unanswered`, `errors`, and the pull date. The same window pulled on two dates can come back under different RIC forms.
- Only write the data file after the pull succeeds. A half-written file blocks its own retry and renders as a plausible empty dataset.
- **Check the numbers add up:** answered + unanswered = contracts requested, counted per *contract* (one strike asked under both forms is one contract, not two).

## 6. Poor man's covered call: what the long call (LEAPS) adds

A PMCC swaps the 100 shares for a **long, deep-in-the-money, long-dated call**. The short-call leg
is the same as a covered call, and everything above still applies to it. The long leg breaks
four assumptions the kit was built on:

1. **Expiry selection.** `fetch_options` pulls one expiry you name. It doesn't find LEAPS
   expiries for you. Long-dated calls are **monthly** contracts (third Friday, or Thursday if
   Friday is a holiday), and true LEAPS usually expire in **January**. Decide the target
   expiry from the brief (e.g. "≥ 6/9/12 months out"), compute it, and confirm it lists with
   a small probe request before a full pull. Never ask the chain endpoint (§4.1).
2. **The strike band is not around spot.** `strike_band(low, high)` fed the stock's own range
   targets near-the-money strikes. A deep ITM long call sits well **below** spot (typically delta
   0.70–0.85, often 15–30% ITM), so build a separate band for it from a moneyness range, e.g.
   `strike_band(0.65 * spot, 0.90 * spot, step=...)`. **The strike step far from the money and
   far out in time is usually wider** ($5 is common, not $1). Measure it with a spike, as in §3.
3. **The long call is unexpired throughout the backtest**, so it answers to the **live** form
   (`...U`, no caret) if the LEAPS hasn't expired by the pull date. `fetch_options` still works,
   because it asks the caret form first and then falls back, but the caret requests are wasted.
   Record the form either way.
4. **Pick by delta? Decide the source.** The daily bars on expired RICs listed these fields in
   Assignment 1.1: `DELTA, GAMMA, THETA, VEGA, RHO, IMP_VOLT, IMP_VOLTA, IMP_VOLTB,
   THEO_VALUE`, alongside `BID/ASK/MID_PRICE/TRDPRC_1/OPINT_1`. **Listed is not populated:
   whether they carry values, and whether they exist on hourly bars, was never verified.**
   Probe first (paired with `TRDPRC_1`, §4.6). If they're empty, compute delta yourself with
   Black-Scholes from the mid, and write down the assumptions (rate, dividend yield,
   act/365, European pricing on an American contract). The old repo has `bs_price`,
   `implied_vol` and `iv_refusal` in `options_surface_lab/option_surface_utils.py`, which
   are worth copying.
5. **Liquidity is much thinner.** Deep ITM long-dated calls trade rarely. Expect many hourly
   bars with no print, wide spreads and sometimes no valid mid. Measure mid availability
   and spread for the chosen contract at your entry and exit bars *before* building the
   fill logic on top of it. The spread on this leg is where the fill assumption will be
   weakest.

**Other data the strategy may need, which a covered call didn't:**

- **Dividends.** A short call against a long call (not shares) can be **assigned early the day
  before an ex-dividend date**, leaving you short stock. Pull or record the underlying's
  ex-dividend dates and amounts in the window, even if you only name them in the write-up. Ask
  Workspace for the event data. The field or endpoint for this was **not explored** in the old repo.
- **The long call at every date the book is marked.** Pull it hourly over the whole window
  (it's one contract, so this is cheap), not just at entry and exit. NAV and margin need it
  on every row.
- **A risk-free rate**, if you compute Greeks yourself. The old repo fixed r = 4.00%.

## 7. Before trusting a pull

- Spot-check a few rows against the Workspace app by hand.
- Confirm a large majority of near-the-money option bars have a valid mid.
- Confirm weeks with holidays look right (a Friday holiday means a Thursday expiry, and the RIC's `DD` says so; a Monday holiday means the week starts Tuesday).
- Read `diag["errors"]`. `LDError ... No data` for a strike is usually "never listed" and is normal.
