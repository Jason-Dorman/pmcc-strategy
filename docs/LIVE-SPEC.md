# Live Wheel — Spec

Nov 13, 2026 · the source of truth for the live assignment, as amended by PO answers in [DECISIONS](DECISIONS.md) (`LD-nn`). The PMCC's and the wheel's docs are archived in [archive/pmcc/](archive/pmcc/README.md) and [archive/wheel/](archive/wheel/README.md) and are not requirements here (LD-01).

## Assignment

> 1. Set up a GitHub action that runs nightly, modelled on the course's nightly refresh, which runs every evening at 10pm.
> 2. Your nightly refresh should run a Python script that runs a trading algorithm of any kind. It can pull data from anywhere on the internet as well as LSEG, run a model, and do whatever it needs to, but its end effect should be that it **updates an open-order file named `open_orders.json` that lives at your directory's root**, in the course's order language, Sanji.
> 3. Document what you did (your algo, why you chose it, how it works) in a website, as usual, and submit that.
>
> "An algorithm is a function that accepts inputs and outputs a set of open orders."

Each requirement maps to a section below: (1) Nightly job, (2) Trade rules and Orders, (3) Site.

## The course's side

These are the professor's systems; we read their output and never write it, with one exception the course provides for: adding an instrument to `price_history.json` (LD-12). Sources: the order language page (<https://jakevestal.github.io/server-logic-533/order.html>), the course's repo (its workflows, `SETUP.md` and price job), and the class of Nov 10.

- **Sanji isn't resolving orders yet** (checked 2026-11-14). The order page: "Sanji does not resolve these orders yet. Write them in this shape now, so the file is already right when he does." No start date is given. So the live wheel writes correct orders now, and its book stays cash until Sanji fills something.

- **Robin** is the course's price database, on the professor's server. It holds daily equity history and, gathered continuously, option chains for the equities in it. It isn't offered to students: our data comes from LSEG directly, through the PO's headless credentials (LD-11).
- **Sanji** reads our `open_orders.json` through the repo access the PO gave the professor. After a session closes (from about 16:30 ET), it takes every order whose `for` is that session and whose `id` hasn't filled, fills it against Robin's prices, applies expiries and assignments at the close, and writes the results to our repo: `fills.json` (appended) and `positions.json` (rewritten), under `mkt/` on the order page. Their formats aren't published.
- **The price job** (16:00 ET on weekdays, the course's `SETUP.md`) reads our `price_history.json` (at the root), fetches the daily bars of every instrument marked `"tracked": true` in it (30 days back for a new one), and writes it back. Our file was seeded with SPY; "the student edits price_history.json" to add instruments, so NVDA was added on 2026-11-14 (PO, LD-12). Otherwise Sanji's files are read, never edited.
- **Fills:** a market order fills at the resolved contract's open. A limit sell fills at the open if the open is already through the limit, otherwise at the limit if the day's high reaches it; else it is `unfilled`. Fills are all or nothing. Sanji doesn't check buying power.
- **Order language:** a JSON array of orders with the fields `id`, `for`, `order_type`, `action`, `qty`, `underlying` (an IBKR conid), `contract`, `expiry`, `strike`, `ref` and `lmt_prc`; anything unknown is `rejected`. The page's tokens (`otm:1`, `delta:30`, `5DTE+`, `mid`, …) are resolved by Sanji against Robin.
- **Where the file goes:** the assignment says the repo root; the order page says `mkt/open_orders.json`. The live wheel writes the same file at both (PO, LD-04).

## Scope

**In:** the wheel (LD-03), live, on NVDA, one contract at a time, with the same states as the backtest; a nightly GitHub Action that reads Sanji's book, pulls NVDA's data from LSEG, picks the week's option and writes `open_orders.json` at the repo root and under `mkt/` (LD-04, LD-05); a committed log of each night's run; one new page on the existing site (LD-10); a second nightly Action that pulls NVDA's volatility from LSEG for two charts on that page (PO, LD-33).

**Out:** other symbols; rolls, early closes and buy-backs; any order type besides a limit sell to open; explaining the pipeline on the site (PO, LD-10); changing the PMCC's or the wheel's code paths, results or pages.

## Why the wheel (LD-03)

It's the strategy already built and tested here: its backtest on NVDA over Mar 30 – Sep 25 2026 made +$4,171.50 (16.69%) on $25,000, with a Sharpe of 1.574 against the baseline PMCC's 1.242 (the wheel's archived spec, WD-29). It also suits Sanji: Sanji settles expiries and assignments itself, so the algorithm only has to sell one option at the start of each week.

**Earnings weeks** are traded like any other, as in the backtest, which had no event filter (PO, LD-23): the premium is richer and assignment likelier. NVDA's Nov 20 weekly priced about a 10% move at Nov 13's close, likely its earnings; the page says so.

## Nightly job

- **Schedule:** cron `17 3 * * *` (03:17 UTC: 22:17 EST, 23:17 EDT), the course's 03:00 moved off the top of the hour, plus a manual run (`workflow_dispatch`). It runs after Sanji has resolved the day's session. GitHub can start it hours late; a run before the next open still plans that session (PO, LD-31).
- **Steps:** check out `main`; install from `uv.lock`; run the algorithm with the LSEG credentials from the repo's GitHub secrets `LSEG_APP_KEY`, `LSEG_USERNAME` and `LSEG_PASSWORD` (a platform session: no Workspace, LD-05); commit `open_orders.json` and the run log as the Actions bot, after pulling, because Sanji pushes to the same branch (LD-06).
- **Deploy:** the site redeploys after every successful nightly run through CI's existing deploy (LD-06). Sanji's own pushes already trigger CI.
- **Failure:** if LSEG fails or Sanji's files can't be read, the run writes no new order, logs why, and fails visibly (LD-14). A failed request is never treated as "no data".

## Data

- **From Sanji:** `positions.json` (the book) and `fills.json` (every fill), looked for under `mkt/` and then at the root; `price_history.json` (the latest priced session) at the root. Until our first order resolves, neither `positions.json` nor `fills.json` exists, which means the Cash state. Their formats were never seen, so either file appearing makes the book unreadable (L-B2) until it is read (L5-01).
- **From LSEG, on each night that plans a week's first session** (Friday, Saturday and Sunday for a Monday, each re-placing the order; PO, LD-25): NVDA's last close; the listed expiry on that week's last session; its strikes within the strike rule's band (L-P3's or L-C3's: 10% of the close, $2.50 apart); each one's bid and ask at the close. One platform session per run; other nights ask LSEG nothing.
- **Delta:** Black-Scholes, implied vol solved from the close's mid, dividend yield 0, the risk-free rate in the config, the time from the close to the expiry session's close. The pricer is the one the backtests use.
- **Risk-free rate (PO, LD-13):** FRED DGS3MO, 4.32% on 2026-11-12 (its latest when the rules were built), continuously compounded as the backtests' rate was: 4.297%. Fixed in `configs/live.yaml` with its date.
- **Calendar:** NYSE sessions from the repo's session calendar (2025–2027).
- **When:** the run decides from the last close, for the session after it: a run during a session, from its open to its close, is refused and writes nothing (LD-24, PO, LD-31).

## Trade rules

The wheel is always in one of four states, read from Sanji's book (`positions.json`) each night:

| State | Holds | Next order |
| --- | --- | --- |
| Cash | no NVDA shares, no NVDA options | sell a put, at the start of a week |
| Put | one short NVDA put | none; Sanji expires or assigns it |
| Shares | 100 NVDA shares | sell a call, at the start of a week |
| Call | 100 NVDA shares, one short NVDA call | none; Sanji expires it or calls the shares away |

Any other book (long options, more than one short option, an odd lot) is unreadable (L-B2).

| ID | Rule | Definition |
| --- | --- | --- |
| L-B1 | Book is current | The latest date in `price_history.json`, over every instrument in it, is the last completed NYSE session; otherwise no new order, the run logged as failed and red (PO, LD-14). While Sanji has written neither `positions.json` nor `fills.json`, it has resolved nothing, so a stale price file is a warning in the run's reason instead, and the night goes ahead (PO, LD-32) |
| L-B2 | Book is readable | Sanji's book maps to one of the four states, and every order already in `open_orders.json` is valid in the order language; otherwise no new order, the run logged as failed and red (PO, LD-14) |
| L-S1 | Next session | The order is for the first NYSE session after the last close: after the close, the next one; before the open, that day's (PO, LD-31) |
| L-P1 | Put timing | Only when the next session is its week's first, in the Cash state |
| L-P2 | Put expiry | The listed expiry on that week's last session; none listed → no order that week, logged |
| L-P3 | Put strike | The OTM put whose delta at the close is nearest −0.30; a tie goes further out of the money (LD-11) |
| L-P4 | Cash-secured | One contract, only if cash ≥ the strike picked at the close × 100 × 1.10, room for a 10% gap at the open, where Sanji sets the strike; otherwise no order, logged (LD-09, PO, LD-29) |
| L-C1 | Call timing | Only when the next session is its week's first, in the Shares state |
| L-C2 | Call expiry | As L-P2 |
| L-C3 | Call strike | Among OTM calls with strike ≥ cost basis, the one whose delta at the close is nearest 0.30; a tie goes further out of the money. None → no order that week, logged |
| L-T1 | Liquidity | The picked contract has a bid > 0 and an ask ≥ the bid at the close, and its spread is ≤ 10% of its mid; otherwise no order that week, logged |
| L-O1 | Order | `SHT` 1 contract, limit at `mid`, `ref` `open`, the expiry as a date; a put's strike as its percent from the close in whole percents (`pct:-5`), which Sanji applies to the open so a gap moves it; a call's strike as a number (LD-07, LD-11, PO, LD-29) |
| L-O2 | Unfilled | A week whose order doesn't fill is skipped: no retry later in the week (LD-08) |

- **Cash:** $25,000 at the start (Sanji starts no book: LD-09), plus every cash flow in Sanji's fills: premiums received, and strike × 100 paid on assignment or received on a call-away.
- **Cost basis:** the assigned put's strike, minus that put's premium and every call premium received since, per share.
- **Expiry and assignment:** Sanji's, at the close (the order page's rules). The algorithm reads the result and doesn't model it.

Every threshold lives in `configs/live.yaml` under its rule ID (the strike band under L-P3 and L-C3, the starting cash under L-P4), and every run-log row carries the ID of the rule that decided it. The picks read the close snapshot directly (PO, LD-26).

## Orders

`open_orders.json` is rewritten on every run, the same file at the repo root and under `mkt/` (PO, LD-04). Each order already in it stays until the week it's for has ended, so a Monday order is there all week; a wheel order for the session planned tonight is replaced by tonight's decision, so a second run the same night can't put on a second option (PO, LD-19). With nothing pending it is `[]`. An order, for example:

```json
[
  {
    "id": "wheel-2026-11-16-P-pct-5",
    "for": "2026-11-16",
    "order_type": "lmt",
    "action": "SHT",
    "qty": 1,
    "underlying": 4815747,
    "contract": "put",
    "expiry": "2026-11-20",
    "strike": "pct:-5",
    "ref": "open",
    "lmt_prc": "mid"
  }
]
```

NVDA's conid is 4815747 (LD-12). The strike above is Monday Nov 16's: the 0.30-delta put at Friday's close was $155, 4.81% below the $162.83 close, sent as a whole 5%, so Sanji takes the open × 0.95 and the nearest listed strike: $155 if NVDA opens where it closed (PO, LD-29). The order is written the night before, so a strike sent as a number would sit at another delta after a gap at the open; a percentage moves with it. Every order is validated against the order language before the file is written; an invalid one fails the run and writes nothing.

## Volatility (PO, LD-33)

A second workflow, `vol`, like the course's `oi-plots.yml` beside its deploy: nightly, 30 minutes after the orders' (cron `47 3 * * *`), and by hand. It asks LSEG for NVDA's volatility and commits two files for the live page's charts; it never touches the orders, and a failed pull commits nothing and fails visibly. The site redeploys after it.

- **IV against RV20, a point a session:** the ATM implied vol of the weekly expiry nearest 30 calendar days out (a tie going later): the mean of the call's and the put's IV at the strike nearest the close, among strikes with both sides quoted at the close (a tie going lower); against RV20, the sample standard deviation of the 20 daily log returns ending at that session's close, × √252. IVs as the picks' (Data › Delta); closes as the last trade in the close bar.
- **The smile:** the coming week's expiry at the last close, the out-of-the-money side (puts below the close, calls above), each strike's IV and delta, and L-P3's pick.
- **History:** backfilled about three months by hand, after the pull's plan is shown; then each run fills the sessions since the last point.
- **Files:** `live/vol.jsonl` (appended, one row a session) and `live/smile.json` (the last session's): numbers derived from LSEG's quotes, never the quotes (LD-34).

## Run log

Each run appends one row to a committed log, `live/runs.jsonl`, failed runs included: the run time; the last resolved session; the next session; the state; cash and the cost basis; the decision (an order, or no order) with its rule ID and reason; the order's `id` and the strike it sent (LD-29), the picked option's strike, expiry and delta at the close, and its bid, ask, mid and spread then (PO, LD-15).

## Site

One new page on the existing site, in its existing look ([UI-SPEC](UI-SPEC.md) §6); the PMCC's and the wheel's pages are unchanged. It shows (PO, LD-10): the algorithm and why it was chosen; tonight's `open_orders.json`, each order beside the strike LSEG gave the run at the close (PO, LD-35); NVDA's implied against realized vol, and the coming week's skew (PO, LD-33, LD-39); Sanji's positions and fills; the nightly run log; and last, the rules with their IDs (PO, LD-35). It doesn't explain the pipeline. It's `#/live/NVDA`, shown as "Wheel forward test" › Overview, first in the nav and on the home page (PO, LD-16, LD-36, LD-38), and it may show LSEG's data: the run log shows each pick's quote at the close (PO, LD-15).

## Invariants

These must hold on every run and fail it if they don't (`LINV-01` … `LINV-09`):

1. Every order written is valid in the order language.
2. At most one short NVDA option is held or ordered at a time: no put order unless in Cash, no call order unless in Shares.
3. A put order's strike, as picked at the close, × 100 × (1 + L-P4's gap allowance) ≤ cash (LD-29).
4. A call order's strike ≥ the cost basis.
5. Every new order's `for` is an NYSE session after the last completed one. (An order kept from earlier in the week keeps its `for`: LD-19.)
6. No new order is written on a stale or unreadable book.
7. Every run-log row carries a rule ID defined in the config.
8. The same inputs (Sanji's files, the LSEG snapshot, the run date) give byte-identical outputs, once the run time is dropped.
9. Credentials are never logged, written or committed.
