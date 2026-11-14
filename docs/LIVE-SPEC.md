# Live Wheel — Spec

Nov 13, 2026 · the source of truth for the live assignment, as amended by PO answers in [DECISIONS](DECISIONS.md) (`LD-nn`). The PMCC's and the wheel's docs are archived in [archive/pmcc/](archive/pmcc/README.md) and [archive/wheel/](archive/wheel/README.md) and are not requirements here (LD-01).

> **Waiting on the PO:** LD-12 (whether the course's price database carries NVDA: test orders placed 2026-11-13), LD-13 (the risk-free rate), LD-14 (a stale or unreadable book), LD-15 (no raw LSEG data on the page), LD-16 (the page's route and name). Each is asked when its backlog item starts ([BUILD-PLAN](BUILD-PLAN.md) › Questions for the PO).

## Assignment

> 1. Set up a GitHub action that runs nightly, modelled on the course's nightly refresh, which runs every evening at 10pm.
> 2. Your nightly refresh should run a Python script that runs a trading algorithm of any kind. It can pull data from anywhere on the internet as well as LSEG, run a model, and do whatever it needs to, but its end effect should be that it **updates an open-order file named `open_orders.json` that lives at your directory's root**, in the course's order language, Sanji.
> 3. Document what you did (your algo, why you chose it, how it works) in a website, as usual, and submit that.
>
> "An algorithm is a function that accepts inputs and outputs a set of open orders."

Each requirement maps to a section below: (1) Nightly job, (2) Trade rules and Orders, (3) Site.

## The course's side

These are the professor's systems; we read their output and never write it. Sources: the order language page (<https://jakevestal.github.io/server-logic-533/order.html>), the course's workflows, and the class of Nov 10.

- **Robin** is the course's price database, on the professor's server. It holds daily equity history and, gathered continuously, option chains for the equities in it. It isn't offered to students: our data comes from LSEG directly, through the PO's headless credentials (LD-11). Whether it carries NVDA is LD-12.
- **Sanji** reads our `open_orders.json` through the repo access the PO gave the professor. After a session closes (from about 16:30 ET), it takes every order whose `for` is that session and whose `id` hasn't filled, fills it against Robin's prices, applies expiries and assignments at the close, and writes the results to our repo: `fills.json` (appended) and `positions.json` (rewritten). It also maintains `price_history.json`, the daily bars of the instruments it tracks, at the repo root. Those files are Sanji's: our code reads them and never edits them.
- **Fills:** a market order fills at the resolved contract's open. A limit sell fills at the open if the open is already through the limit, otherwise at the limit if the day's high reaches it; else it is `unfilled`. Fills are all or nothing. Sanji doesn't check buying power.
- **Order language:** a JSON array of orders with the fields `id`, `for`, `order_type`, `action`, `qty`, `underlying` (an IBKR conid), `contract`, `expiry`, `strike`, `ref` and `lmt_prc`; anything unknown is `rejected`. The page's tokens (`otm:1`, `delta:30`, `5DTE+`, `mid`, …) are resolved by Sanji against Robin.

## Scope

**In:** the wheel (LD-03), live, on NVDA, one contract at a time, with the same states as the backtest; a nightly GitHub Action that reads Sanji's book, pulls NVDA's data from LSEG, picks the week's option and writes `open_orders.json` at the repo root (LD-04, LD-05); a committed log of each night's run; one new page on the existing site (LD-10).

**Out:** other symbols; rolls, early closes and buy-backs; any order type besides a limit sell to open; explaining the pipeline on the site (PO, LD-10); changing the PMCC's or the wheel's code paths, results or pages.

## Why the wheel (LD-03)

It's the strategy already built and tested here: its backtest on NVDA over Mar 30 – Sep 25 2026 made +$4,171.50 (16.69%) on $25,000, with a Sharpe of 1.574 against the baseline PMCC's 1.242 (the wheel's archived spec, WD-29). It also suits Sanji: Sanji settles expiries and assignments itself, so the algorithm only has to sell one option at the start of each week.

## Nightly job

- **Schedule:** cron `0 3 * * *` (03:00 UTC: 22:00 EST, 23:00 EDT), as the course's is, plus a manual run (`workflow_dispatch`). It runs after Sanji has resolved the day's session.
- **Steps:** check out `main`; install from `uv.lock`; run the algorithm with the LSEG credentials from the repo's GitHub secrets `LSEG_APP_KEY`, `LSEG_USERNAME` and `LSEG_PASSWORD` (a platform session: no Workspace, LD-05); commit `open_orders.json` and the run log as the Actions bot, after pulling, because Sanji pushes to the same branch (LD-06).
- **Deploy:** the site redeploys after every successful nightly run through CI's existing deploy (LD-06). Sanji's own pushes already trigger CI.
- **Failure:** if LSEG fails or Sanji's files can't be read, the run writes no new order, logs why, and fails visibly (LD-14). A failed request is never treated as "no data".

## Data

- **From Sanji (the repo root):** `positions.json` (the book), `fills.json` (every fill), `price_history.json` (the latest resolved session). Until our first order resolves, neither `positions.json` nor `fills.json` exists, which means the Cash state.
- **From LSEG, nightly, on the night before a week's first session only:** NVDA's last close; the listed expiry on that week's last session; its strikes; each one's bid and ask at the close. One platform session per run.
- **Delta:** Black-Scholes, implied vol solved from the close's mid, dividend yield 0, the risk-free rate in the config (LD-13), the time from the close to the expiry session's 16:00. The pricer is the one the backtests use.
- **Calendar:** NYSE sessions from the repo's session calendar (2025–2027).

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
| L-B1 | Book is current | The latest session in `price_history.json` is the last completed NYSE session; otherwise no new order, logged (LD-14) |
| L-B2 | Book is readable | `positions.json` maps to one of the four states; otherwise no new order, logged (LD-14) |
| L-S1 | Next session | The order is for the first NYSE session after the run's date (ET) |
| L-P1 | Put timing | Only when the next session is its week's first, in the Cash state |
| L-P2 | Put expiry | The listed expiry on that week's last session; none listed → no order that week, logged |
| L-P3 | Put strike | The OTM put whose delta at the close is nearest −0.30; a tie goes further out of the money (LD-11) |
| L-P4 | Cash-secured | One contract, only if cash ≥ strike × 100; otherwise no order, logged (LD-09) |
| L-C1 | Call timing | Only when the next session is its week's first, in the Shares state |
| L-C2 | Call expiry | As L-P2 |
| L-C3 | Call strike | Among OTM calls with strike ≥ cost basis, the one whose delta at the close is nearest 0.30; a tie goes further out of the money. None → no order that week, logged |
| L-T1 | Liquidity | The picked contract has a bid > 0 and an ask ≥ the bid at the close, and its spread is ≤ 10% of its mid; otherwise no order that week, logged |
| L-O1 | Order | `SHT` 1 contract, limit at `mid`, `ref` `open`, the expiry as a date, the strike as a number (LD-07, LD-11) |
| L-O2 | Unfilled | A week whose order doesn't fill is skipped: no retry later in the week (LD-08) |

- **Cash:** $25,000 at the start (Sanji starts no book: LD-09), plus every cash flow in Sanji's fills: premiums received, and strike × 100 paid on assignment or received on a call-away.
- **Cost basis:** the assigned put's strike, minus that put's premium and every call premium received since, per share.
- **Expiry and assignment:** Sanji's, at the close (the order page's rules). The algorithm reads the result and doesn't model it.

Every threshold lives in `configs/live.yaml` under its rule ID, and every run-log row carries the ID of the rule that decided it.

## Orders

`open_orders.json` at the repo root (LD-04) is rewritten on every run. It keeps every order already in it whose `for` session Sanji hasn't resolved yet and adds the night's new order, so it is `[]` on nights with nothing pending (LD-19). An order, for example:

```json
[
  {
    "id": "wheel-2026-11-16-P-200",
    "for": "2026-11-16",
    "order_type": "lmt",
    "action": "SHT",
    "qty": 1,
    "underlying": 4815747,
    "contract": "put",
    "expiry": "2026-11-20",
    "strike": "200",
    "ref": "open",
    "lmt_prc": "mid"
  }
]
```

NVDA's conid is 4815747 (LD-12); the strike above is a placeholder until the first pick. Every order is validated against the order language before the file is written; an invalid one fails the run and writes nothing.

## Run log

Each run appends one row to a committed log: the run time; the last resolved session; the next session; the state; cash and the cost basis; the decision (an order, or no order) with its rule ID and reason; the order's `id`, strike, expiry and delta at the close. LSEG's quotes themselves are not logged for publication (LD-15).

## Site

One new page on the existing site, in its existing look ([UI-SPEC](UI-SPEC.md) §6); the PMCC's and the wheel's pages are unchanged. It shows (PO, LD-10): the algorithm and why it was chosen; tonight's `open_orders.json`; Sanji's positions and fills; the nightly run log. It doesn't explain the pipeline. Its route and nav name: LD-16.

## Invariants

These must hold on every run and fail it if they don't (`LINV-01` … `LINV-09`):

1. Every order written is valid in the order language.
2. At most one short NVDA option is held or ordered at a time: no put order unless in Cash, no call order unless in Shares.
3. A put order's strike × 100 ≤ cash.
4. A call order's strike ≥ the cost basis.
5. Every order's `for` is an NYSE session after the last one Sanji resolved.
6. No new order is written on a stale or unreadable book.
7. Every run-log row carries a rule ID defined in the config.
8. The same inputs (Sanji's files, the LSEG snapshot, the run date) give byte-identical outputs, once the run time is dropped.
9. Credentials are never logged, written or committed.
