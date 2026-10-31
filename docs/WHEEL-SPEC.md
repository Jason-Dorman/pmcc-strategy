# Wheel Strategy Backtest — Spec

Oct 26, 2026 · the source of truth for the wheel, as amended by PO answers in [DECISIONS](DECISIONS.md). The PMCC's docs are archived in [archive/pmcc/](archive/pmcc/README.md) and are not requirements here (WD-01).

> No section waits on the PO now: weekly tenor was confirmed on 2026-10-27 (PO, WD-02), and the pages settled on 2026-10-28 (PO, WD-22).

## Assignment

> Sell cash-secured puts; if assigned, sell covered calls against the shares; if called away, restart. Build and run it inside the GitHub Pages system you already have. Report exact trades in your blotter, include your ledger, and include relevant metrics.
>
> 1. Accurate historical backtest with a full blotter and ledger of every trade (opens, closes, assignments, rolls).
> 2. Ability to view the exact portfolio (cash, shares, short puts, covered calls) at any point in time.
> 3. Any fill-price assumptions must be stated and justified with data.
> 4. State your thesis for why this should make money/beat a benchmark/improve Sharpe, then show whether it actually did.

Each requirement maps to a section below: (1) Accounting, (2) Ledger and portfolio view, (3) Fill model, (4) Thesis and Benchmarks.

## Scope

**In:** one wheel strategy with fixed rules (WD-05) on NVDA, weekly options (WD-02), over Mon Mar 30 – Fri Sep 25 2026 (WD-04), LSEG hourly data; its blotter, ledger, NAV and metrics; a fill-friction sensitivity to justify the fill model; a benchmark comparison against the baseline PMCC and the S&P 500 (WD-03); new wheel pages on the existing site, in its existing look.

**Out:** other symbols; ablations, parameter grids, entry-timing sweeps; rolls and early closes (WD-09); margin (it's a cash account, WD-10); charting the benchmarks (WD-03). The PMCC's pages and results stay on the site unchanged.

## Thesis (PO, WD-21, WD-33)

NVDA options tend to be priced for larger price movements than actually occur, creating an opportunity to profit by selling weekly options and collecting premiums. The strategy uses a cash-secured options wheel, trading one contract at a time without leverage.

The hypothesis is that the wheel will:

1. **(It makes money)** Generate a profit by collecting more in premiums than it loses from unfavorable stock movements.
2. **(It improves Sharpe on the baseline PMCC)** Improve risk-adjusted returns compared with the original PMCC strategy by generating income with less exposure to NVDA's price fluctuations.
3. **(It beats the S&P 500)** Outperform the S&P 500's price return over the same period.

The bold names are the claims' names in the Verdicts table; the site shows the thesis without them. Below the thesis, a **Results** line, built from the verdicts (for example "Two of the three objectives were met: The wheel generated a profit and achieved a higher Sharpe ratio than the PMCC, but it did not outperform the S&P 500."), then each claim's verdict, met or not, with the numbers.

The three claims and their tests (WD-29) were fixed on 2026-10-26, before the first run. The PO reworded the thesis on 2026-10-30, after the results; the claims and tests are unchanged, and WD-33 keeps the original wording. The site doesn't carry a note about the date.

## Data

- **Underlying:** NVDA's hourly stock tape, already cached (`data_cache/NVDA/stock.parquet`).
- **Calls:** the cached weekly calls, used for covered calls. On NVDA's run, every call and put the wheel sold had validly quoted strikes on both sides of it on its decision bar, so the fetched band never cut a pick short; no week was skipped under W-C3 (WD-26).
- **Puts:** a new pull of weekly puts, needed because the cache holds puts only for each week's first session near the money (WD-06). For each weekly expiry in the window: every session from the week's first through expiry, strikes from 80% of the first session's low up to two increments above its high, in two bands that each measure their own strike step (WD-11). `pmcc fetch --wheel` pulls them. Fetching ranges from the window's prices is allowed; selection only ever sees data up to its decision time.
- **Cache:** the wheel's puts go in their own folder with their own manifest (`data_cache/NVDA/wheel/`), so the PMCC's cache and its results' data hash are untouched (WD-11). Never overwritten; an outage aborts and writes nothing.
- **S&P 500:** FRED's `SP500` daily closes, Fri Mar 27 and Fri Sep 25 2026, price return, as a committed two-row file with its citation (PO, WD-17).
- **Risk-free rate:** 3.71% continuously compounded, from the 3-month Treasury yield (FRED DGS3MO, 3.73%) at the last close before the window (PO, WD-16).

## Conventions

- **Time:** America/New_York. LSEG stamps hourly bars at their start with end-of-bar quotes, so a bar is known at its end: every decision happens at a bar's end, using only data stamped at or before it. The engine's `MarketView` raises on any request for later data.
- **Week:** a week opens on its first trading session and its options expire on its last trading session.
- **Greeks:** Black-Scholes, implied vol solved from the bar's mid, dividend yield 0. A contract whose IV can't be solved on a bar can't be selected on that bar. A held option whose mid is under its no-arbitrage floor (S − K·e^(−rT) for a call, K·e^(−rT) − S for a put) has no IV there, and is shown at the deep in-the-money limit: delta +1 for a call, −1 for a put, gamma and vega 0 (PO, WD-27).
- **Dividends and interest:** NVDA's $0.01 quarterly dividend is ignored, and cash earns no interest. Both are stated on the site (PO, WD-18).
- **Early assignment:** none before expiry (PO, WD-15).

## Fill model

- **Base:** every option entry and exit fills at the decision bar's mid, (BID + ASK) ÷ 2 (PO, WD-23). No BID or no ASK on that bar means no fill; a print is never invented. Under hold-to-expiry (WD-09) the only option fills are the put and call sales: an option leaves the book by expiring at $0 or by assignment at its strike, never by a buy-back.
- **Friction:** a `spread_capture` parameter in [0, 1]: a sell fills at mid − capture × half-spread, a buy at mid + capture × half-spread. The reported run is at 0, so at mid; sensitivity runs at 0.25 and 0.50 only show how much of the result survives paying part of the spread (WD-23).
- **Fees:** a per-contract fee parameter, $0 in every run (PO, WD-19).
- **Justification with data (requirement 3):** for every option the wheel traded, each bar with a trade print plots the print against the bar's mid, with the fitted line, R², and where the prints fall within the spread. The friction runs show how much of the result survives paying part of the spread. Assignment and call-away fills are at the strike, which is contractual, not an assumption.

## Trade rules

The wheel is always in exactly one state. Each state allows one kind of short option at a time, one contract (WD-10).

| State | Holds | Next |
| --- | --- | --- |
| Cash | cash only | sell a put → Put |
| Put | cash, one short put, with cash ≥ strike × 100 reserved | expires OTM → Cash; assigned → Shares |
| Shares | cash, 100 shares | sell a call → Call |
| Call | cash, 100 shares, one short call covered by them | expires OTM → Shares; called away → Cash |

**Order each session:** expiries and assignments are settled at the week's last close; new options are sold on the next week's first session.

| ID | Rule | Definition |
| --- | --- | --- |
| W-T1 | Entry trigger | Sell on the first bar of the week's first session where the selected contract has a valid bid and ask and a spread ≤ 10% of its mid; if none passes, the week is skipped (PO, WD-14) |
| W-P1 | Put timing | Each week's first session, in the Cash state |
| W-P2 | Put expiry | That week's last trading session |
| W-P3 | Put strike | The OTM put whose delta is nearest −0.30 (WD-07) |
| W-P4 | Cash-secured | One contract, sold only if cash ≥ strike × 100. Otherwise no sale, logged |
| W-C1 | Call timing | Each week's first session, in the Shares state |
| W-C2 | Call expiry | That week's last trading session |
| W-C3 | Call strike | Among OTM calls with strike ≥ cost basis, the one whose delta is nearest 0.30. None → no call that week, logged (WD-08) |
| W-X1 | Put expires | Put OTM at expiry: `EXPIRE` at $0 → Cash |
| W-X2 | Put assigned | Put ITM at expiry: `ASSIGN` the put and buy 100 shares at the strike → Shares |
| W-X3 | Call expires | Call OTM at expiry: `EXPIRE` at $0 → Shares |
| W-X4 | Called away | Call ITM at expiry: `ASSIGN` the call and sell 100 shares at the strike → Cash |
| W-X5 | End of backtest | Mark everything at the final bar; no forced liquidation |

- **Picking (WD-25):** the pick is made afresh on each bar of the week's first session until one sells, so a put the cash couldn't secure on one bar may still sell on a later one; a tie in delta goes further out of the money (the lower put strike, the higher call strike).
- **Hold to expiry:** no option is bought back early, and there are no rolls (WD-09). The blotter's trade types are therefore opens, expiries, assignments and call-aways; a week's new sale is the next cycle, not a roll.
- **ITM at expiry:** judged by the stock's last trade in the bar ending at the session's close (16:00 ET, 13:00 on a half-day), or, if that bar had none, the session's last trade before it; a put is ITM if that price is below its strike, a call if above; at the strike, neither (PO, WD-15; the fallback, WD-25).
- **Cost basis:** the assigned put's strike, minus that put's credit and every call credit received since, per share, net of fees.
- **Skips:** a week with no sale gets one gate-log row with its reason: not enough cash (W-P4); no call at or above the cost basis with a quote on any bar (W-C3); otherwise no liquid bar (W-T1) (WD-25).

Every threshold lives in YAML under its rule ID, and every blotter and gate-log row carries the ID of the rule that produced it.

## Accounting

Cash moves only on blotter rows. Money is an integer count of $0.0001.

**Blotter:** Time (decision bar end) · Instrument (RIC, with OCC symbol; or the stock) · Side (`BUY` / `SELL` / `EXPIRE` / `ASSIGN`) · Qty · Limit (mid) · Fill · Cash Δ · Trade P&L · Rule · Notes. A put assignment is an `ASSIGN` row on the put plus a `BUY` 100 shares at the strike; a call-away is an `ASSIGN` row on the call plus a `SELL` 100 shares at the strike.

**Trade P&L (PO, WD-28)** is per instrument, on the row that closes a position, net of fees; blank on a row that opens one. An option's is its credit, on its `EXPIRE` or `ASSIGN` row; the shares' is their sale less their purchase × 100, on the call-away's `SELL` (the assignment's `BUY` is blank). The rows sum to the realized P&L; a cycle's total is in the cycle statistics.

**Ledger (one row per bar):** state; cash; reserved cash (strike × 100 while a put is open) and free cash; shares and their mark; short put (RIC, strike, expiry, mark, delta); short call (the same); cost basis; NAV.

```
NAV = cash + shares × stock price − short put MV − short call MV
```

Option and share marks at mid; a bar without a valid bid and ask carries the last valid mid, flagged stale, and a stale mark never fills. A holding with no mid yet on the bar it was filled is marked stale until one arrives: shares bought on assignment at the closing trade that assigned them, anything else at its fill (WD-25).

**Portfolio at any point in time (requirement 2):** the site lets a reader pick any bar and shows that bar's ledger row as a portfolio: cash (reserved and free), shares, the short put, the short call, each with its mark, and NAV. The reader picks the bar with a click on the NAV chart or on a ledger time, by stepping a bar, or with a session and bar select, and the URL keeps it, so a link opens the same portfolio (PO, WD-22).

## Metrics (PO, WD-20)

Per run, in its result's summary:

- **Performance:** P&L; return on starting cash over the window; max drawdown ($ and %); Sharpe on daily session-close NAV returns in excess of r, annualized by √252 and labelled with the sample length (the sessions). The same definitions as the baseline PMCC's, so the two compare.
- **Wheel cycles:** puts sold, assigned and expired; calls sold, called away and expired; weeks skipped by reason; total premium collected; complete cycles; whether a cycle is still open at the end; share of time (of bars) in each state. A complete cycle is a put assigned and its shares later called away; a put that expires is counted as expired, not as a cycle (PO, WD-29).
- **Benchmarks** (WD-03, a table, no chart): the wheel against the baseline PMCC on NVDA (return on starting cash, Sharpe, max drawdown %), from the baseline's committed result, and the S&P 500's price return over the same period.
- **Verdicts (PO, WD-29),** each from the numbers above, met when the wheel's is higher: (1) makes money: P&L > $0, shares still held at the end marked at their mid (W-X5); (2) improves Sharpe: the wheel's Sharpe > the baseline PMCC's; (3) beats the S&P 500: return on starting cash > the index's price return. A claim missing a number is not met.

Not reported (PO, WD-20): Sortino, time underwater, and a bootstrap CI on the mean weekly return.

## Site

The wheel's pages join the existing site in its existing look ([UI-SPEC](UI-SPEC.md)); the PMCC pages are untouched. Two pages join the nav (PO, WD-22): a Wheel page (readouts, NAV, portfolio at a point in time, cycle statistics, blotter, gate log, ledger) and a Wheel review page (thesis and verdicts, benchmark table, fill model and its evidence, friction runs, the rules rendered from the config). The landing page and the wordmark stay the PMCC's; the wheel is linked as `#/wheel/NVDA`. Rules are named in plain words outside ID columns, as on the PMCC's pages.

## Invariants

These must hold on every run and fail the build if they don't:

1. Cash changes only on blotter rows; the sum of Cash Δ equals the change in cash.
2. NAV reconciles on every bar.
3. No fill without a valid bid and ask on the decision bar (assignment fills at the strike excepted).
4. No decision reads data stamped after its decision time.
5. While a put is open, cash ≥ strike × 100.
6. While a call is open, shares ≥ 100 × calls.
7. The state is always one of the four; a put is never open with shares held, nor a call without them.
8. No option is open after its expiry session.
9. Every blotter and gate-log row carries a rule ID defined in the config.
10. Re-running on cached data gives byte-identical results, once the run timestamp and commit are dropped.
