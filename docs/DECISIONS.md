# Decisions — Wheel

Oct 26, 2026 · companion to the [Wheel spec](WHEEL-SPEC.md), the source of truth for the wheel

The user is the product owner (PO). This log tracks what the spec leaves open, the PO's answers, and engineering choices. It starts fresh for the wheel; the PMCC's log, `DEC-nn`, is archived in [archive/pmcc/DECISIONS.md](archive/pmcc/DECISIONS.md) and decides nothing here (WD-01). Wheel entries are `WD-nn`, so they never collide with a `DEC-nn` cited in the PMCC's code.

| Status | Meaning |
| --- | --- |
| `ASK` | Open question, with a recommendation. Asked when the backlog item under **Ask at** starts; nothing that depends on it is built before the answer. |
| `PROVISIONAL` | Answered by the PO, to be confirmed by a stated date. Built on, but nothing hard to undo is done until it's confirmed. |
| `SETTLED` | Decided. **Basis** is a dated PO answer. |
| `ENG` | An engineering choice: how, not what. Recorded so the PO can see it and overrule it. It becomes `ASK` if it turns out to change behaviour, results, scope or the UI. |

**Maintenance:** record each answer under **Outcome** with the date; if it changes the spec, update the spec in the same commit, citing the entry. Never delete an entry; a new one takes the next free number.

## Index

| ID | Decision | Status | Ask at |
| --- | --- | --- | --- |
| WD-01 | PMCC docs archived; styling carried over | SETTLED (PO) | — |
| WD-02 | Option tenor | SETTLED (PO): weekly, confirmed 2026-10-27 | — |
| WD-03 | Benchmarks | SETTLED (PO) | — |
| WD-04 | Backtest window | SETTLED (PO) | — |
| WD-05 | One wheel strategy, fixed rules | SETTLED (PO) | — |
| WD-06 | Put pull now | SETTLED (PO) | — |
| WD-07 | Put strike | SETTLED (PO) | — |
| WD-08 | Covered call strike | SETTLED (PO) | — |
| WD-09 | Management: hold to expiry, no rolls | SETTLED (PO) | — |
| WD-10 | Capital and sizing | SETTLED (PO) | — |
| WD-11 | Put fetch band and a separate cache | ENG | — |
| WD-12 | Wheel ID prefixes | ENG | — |
| WD-13 | Due date | SETTLED (PO): Sun Nov 1 2026, 11:59 pm ET | — |
| WD-14 | Entry trigger | SETTLED (PO): first liquid bar | — |
| WD-15 | Expiry moneyness and early assignment | SETTLED (PO): 16:00 last trade; none early | — |
| WD-16 | Risk-free rate | SETTLED (PO): 3.71% | — |
| WD-17 | S&P 500 source | SETTLED (PO): FRED SP500 | — |
| WD-18 | Dividends and interest on cash | SETTLED (PO): neither | — |
| WD-19 | Fees | SETTLED (PO): $0 | — |
| WD-20 | Metrics | SETTLED (PO): trimmed | — |
| WD-21 | Thesis wording | SETTLED (PO): the draft, unchanged | — |
| WD-22 | Wheel pages | SETTLED (PO): two pages | — |
| WD-23 | Fills at mid | SETTLED (PO) | — |
| WD-24 | The wheel's own book, beside the PMCC's | ENG | — |
| WD-25 | Rule details the spec leaves open (W2-02) | ENG, put to the PO | — |
| WD-26 | The wheel's result: `pmcc wheel`, its file and its checks (W2-03) | ENG | — |
| WD-27 | Delta of a held option under its no-arbitrage floor | SETTLED (PO): ±1 | — |
| WD-28 | The blotter's Trade P&L | SETTLED (PO): per instrument | — |
| WD-29 | Complete cycles, and how each thesis claim is judged | SETTLED (PO) | — |
| WD-30 | The wheel's numbers: where they are computed and checked (W3-01) | ENG | — |
| WD-31 | The fill evidence and the friction runs (W3-02) | ENG | — |
| WD-32 | The wheel's pages: export, index and site code (W4-01) | ENG, the chart's shading put to the PO | — |

## Settled

### WD-01 — PMCC docs archived; styling carried over
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** docs/, CLAUDE.md, README

- **Asked:** which docs are no longer needed, given whether the PMCC stays on the site.
- **Outcome:** the PMCC stays live on the site, but its docs retire, except the UI styling, which the wheel's pages must match. In the PO's words: "I just want to make sure we're meeting the requirements for this assignment and not overdoing it — so I don't want decisions we made for PMCC to leak into the requirements for the wheel." The PO took the recommended split:
  - **Archived to `docs/archive/pmcc/`:** the PMCC spec, PRD, ARCHITECTURE, TEST-STRATEGY, UI-SPEC, BUILD-PLAN and DECISIONS. The PMCC's code and two config tests still cite them there.
  - **Live:** ENGINEERING-PRINCIPLES (how code is written); a new [WHEEL-SPEC](WHEEL-SPEC.md), this log, a wheel [BUILD-PLAN](BUILD-PLAN.md), and a [UI-SPEC](UI-SPEC.md) carrying over only the styling.
  - **CLAUDE.md** keeps the working rules (the PO decides and does all git; credentials; LSEG access; integer money; no styling literals) and points at the new docs.

### WD-02 — Option tenor
**Status:** SETTLED · **Basis:** PO, 2026-10-26; confirmed 2026-10-27 · **Affects:** Spec › Data, Trade rules

- **Options:** weekly (about 26 cycles in the window, reusing the cached weekly calls); monthly at 30–45 DTE (the textbook wheel, but only 5–6 cycles); both.
- **Outcome:** weekly. Provisional on 2026-10-26 while the PO took it to others; confirmed by the PO on 2026-10-27 (W2-03).

### WD-03 — Benchmarks
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** Spec › Metrics, Thesis

- **Outcome:** two benchmarks.
  - The **baseline PMCC run on NVDA** (`results/NVDA/baseline_pmcc.json`). Clarified by the PO: the PMCC run, not buy-and-hold NVDA. It started with $15,000 and the wheel with $25,000 (WD-10), so they're compared on return on starting cash, Sharpe and drawdown %, not dollars.
  - The **S&P 500's return** over roughly the same period: compared as a return, not charted. A source other than LSEG is fine (WD-17).

### WD-04 — Backtest window
**Status:** SETTLED · **Basis:** PO, 2026-10-26

- **Outcome:** Mon Mar 30 – Fri Sep 25 2026, the PMCC's window. The stock tape and weekly calls are already cached, and the PMCC benchmark covers the same period.

### WD-05 — One wheel strategy, fixed rules
**Status:** SETTLED · **Basis:** PO, 2026-10-26

- **Outcome:** a single fixed-rule wheel, plus the friction runs the fill justification needs. No baseline/quant pair, ablations, parameter grid or universe batch.

### WD-06 — Put pull now
**Status:** SETTLED · **Basis:** PO, 2026-10-26

- **Outcome:** pull the weekly puts as soon as the fetch plan exists, without waiting on WD-02's confirmation. If the group picks monthly, the weekly puts stay cached, unused. The `--plan-only` estimate is still shown to the PO before any pull longer than about 2 minutes.

### WD-07 — Put strike
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** W-P3

- **Options:** OTM put with delta nearest −0.30; nearest −0.20; the highest strike at or below spot minus one weekly expected move.
- **Outcome:** OTM put, delta nearest −0.30.

### WD-08 — Covered call strike
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** W-C3

- **Options:** delta 0.30, never below cost basis; delta 0.30 ignoring basis; always at the assignment strike.
- **Outcome:** among OTM calls with strike at or above cost basis, delta nearest 0.30; none qualifying → no call that week, logged. Cost basis is the assigned put's strike less the premiums collected since (that put's credit and each call's), per share.

### WD-09 — Management: hold to expiry, no rolls
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** Spec › Trade rules

- **Options:** hold to expiry; hold plus a 50% take-profit; hold plus a defensive roll.
- **Outcome:** hold to expiry, no rolls. The assignment lists rolls among the trade types; the blotter will have none, and the site says why: the wheel as specified never rolls.

### WD-10 — Capital and sizing
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** W-P4, Spec › Accounting

- **Options:** $25,000, one contract; $100,000, as many contracts as cash secures; $15,000 like the PMCC (impossible: it can't secure one NVDA put).
- **Evidence:** NVDA's hourly closes in the window run $163.52–$237.87 (the tape's high/low fields reach $306.18 and $141.80 on bad prints), so the highest 0.30-delta put strike is about $237.50, $23,750 secured.
- **Outcome:** $25,000, one contract, a cash account, no margin.

### WD-13 — Due date
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** BUILD-PLAN schedule and cut list

- **Outcome:** Sun Nov 1 2026, 11:59 pm ET (EST: daylight time ends at 2 am that day). Six days from the question; the backlog's schedule and cut list follow from it.

### WD-27 — Delta of a held option under its no-arbitrage floor
**Status:** SETTLED · **Basis:** PO, 2026-10-27 · **Affects:** Spec › Conventions (Greeks); the ledger's leg delta

- **Found by the hand audit (W2-03, WD-26):** on 12 of NVDA's 849 held-leg bars, all on an expiry day and deep in the money, the option's mid sits just under its no-arbitrage floor (S − K·e^(−rT) for a call, K·e^(−rT) − S for a put), so no IV solves. The shared pricing gave a call the PMCC's deep ITM limit (archived DEC-27: delta 1) and a put nothing, since the PMCC never holds one: 5 call bars showed delta 1, 7 put bars a blank. No trade, cash or NAV depends on it, only the ledger's reported delta.
- **Asked:** keep the limit, leave both blank, or keep the code's asymmetry. The PO first chose "keep delta ±1" from a question that wrongly called that the code as it stood; asked again with the asymmetry stated, the PO chose ±1 on both sides.
- **Outcome:** a held option under its floor is shown at the deep in-the-money limit: delta +1 for a call, −1 for a put, gamma and vega 0, theta −r·K·e^(−rT) for a call and +r·K·e^(−rT) for a put. It still has no IV, so it can't be selected; it is in the money anyway, and only out-of-the-money options are picked.
- **Built:** `pmcc/pricing/chain.py` gives a put the mirror of the call's limit. The PMCC holds no puts: a scratch batch of all 24 PMCC runs after the change matches all 31 committed result files. On NVDA's wheel, the 7 put bars now show −1, and the hand audit agrees on every bar.

### WD-20 — Metrics
**Status:** SETTLED · **Basis:** PO, 2026-10-27 · **Affects:** Spec › Metrics; W3-01

- **Recommendation:** as listed in Spec › Metrics: performance (with Sortino and the longest time underwater), wheel-cycle statistics, a bootstrap CI on the mean weekly return, and the benchmark table with each thesis claim marked met or not.
- **Outcome:** 2026-10-27, PO: "trim now". The recommended set without the bootstrap CI, Sortino and time underwater, which were first on the cut list: P&L, return on starting cash, max drawdown ($ and %), Sharpe (with its sample length); the cycle statistics; the benchmark table and the verdicts. Asked early, while W2-03 finished; recorded with W3-01, the work it unblocks.

### WD-28 — The blotter's Trade P&L
**Status:** SETTLED · **Basis:** PO, 2026-10-27 · **Affects:** Spec › Accounting (Blotter); W3-01

- **Asked:** the spec names a Trade P&L column but doesn't define it, and assignments make it ambiguous. Offered per instrument (recommended) or per cycle (one figure on the call-away's share sale).
- **Outcome:** 2026-10-27, PO: per instrument. On the row that closes a position, net of fees, blank on opening rows: an option's credit on its `EXPIRE` or `ASSIGN` row, the shares' sale less purchase on the call-away's `SELL`. The rows sum to the realized P&L; cycle totals belong to the cycle statistics. (NVDA's Jun 1 cycle: the put +$208, five calls +$676, the shares −$750.)

### WD-29 — Complete cycles, and how each thesis claim is judged
**Status:** SETTLED · **Basis:** PO, 2026-10-27 · **Affects:** Spec › Metrics; W3-01

- **Asked** at W3-01, before any verdict was computed, so the tests weren't fitted to the result.
- **Complete cycle:** a put assigned and its shares later called away. A put that expires counts as a put expired, not a cycle; a turn still holding shares at the end is reported as open (PO, as recommended; the alternative counted every return to cash).
- **Verdicts:** each claim is met when the wheel's number is higher. (1) Makes money: P&L > $0 over the window, shares still held at the end marked at their mid (W-X5). (2) Improves Sharpe: the wheel's annualized Sharpe > the baseline PMCC's, by the same method. (3) Beats the S&P 500: return on starting cash > the index's price return from Mar 27 to Sep 25 (PO, as recommended; the alternative judged claim 1 on realized P&L only). Judged on the values as published, to 6 places, so `pmcc verify` re-judges them alike; a claim missing a number is not met.

### WD-23 — Fills at mid
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** Spec › Fill model

- **Outcome:** the PO: "we're using the mid for entries/exits". Every option fill in the reported run is at the decision bar's mid (`spread_capture` 0). Under hold-to-expiry (WD-09) that means every put and call sale; options leave the book only by expiring at $0 or by assignment at the strike, which is contractual. The friction runs at 0.25 and 0.50 are sensitivity evidence for the fill assumption, never the reported result.

### WD-21 — Thesis wording
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** Spec › Thesis

- **Asked:** confirm or rewrite the spec's draft thesis, fixed before the first run.
- **Outcome:** the PO: "keep it". Three claims: the wheel makes money; it beats the baseline PMCC's Sharpe; it beats the S&P 500's return over the same period. Fixed as of 2026-10-26, before any wheel run; the site marks each met or not.

### WD-14 — Entry trigger
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** W-T1

- **Recommendation:** sell on the first bar of the week's first session where the selected contract has a valid bid and ask and a spread ≤ 10% of mid; if no bar passes, skip the week (logged). The alternative is a fixed bar (for example 10:00 ET), with no spread check.
- **Outcome:** 2026-10-26, PO: as recommended. Sell on the first bar of the week's first session where the selected contract has a valid bid and ask and a spread ≤ 10% of mid; if none passes, the week is skipped and logged (W-T1).

### WD-15 — Expiry moneyness and early assignment
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** W-X1 to W-X4

- **Recommendation:** ITM is judged by the stock's last trade in the bar ending at the 16:00 close: a put is assigned if that price is below its strike, a call if above; exactly at the strike, neither. No early assignment before expiry (NVDA's dividend is too small to make early call exercise worthwhile).
- **Outcome:** 2026-10-26, PO: as recommended. ITM is judged by the stock's last trade (TRDPRC_1) in the bar ending at the session's close (16:00 ET, 13:00 on a half-day): a put is assigned if it is below the strike, a call if above; at the strike, neither. No early assignment.

### WD-16 — Risk-free rate
**Status:** SETTLED · **Basis:** PO, 2026-10-26

- **Recommendation:** r = 3.71% continuously compounded, from FRED DGS3MO's 3.73% on Fri Mar 27 2026, the last close before the window, for IV, Greeks and the Sharpe's excess return. It's a market fact, and it keeps the wheel's Sharpe comparable with the PMCC's.
- **Outcome:** 2026-10-26, PO: as recommended. r = 0.0371, continuously compounded (FRED DGS3MO 3.73% on Mar 27 2026), for IV, Greeks and the Sharpe's excess return; stated on the site.

### WD-17 — S&P 500 source
**Status:** SETTLED · **Basis:** PO, 2026-10-26

- **Recommendation:** FRED `SP500` (S&P Dow Jones Indices), the closes on Fri Mar 27 and Fri Sep 25 2026, price return, committed as a two-row file with its citation. The alternative is `.SPX` daily closes from LSEG through a small fetch.
- **Outcome:** 2026-10-26, PO: as recommended. FRED `SP500`, closes on Fri Mar 27 and Fri Sep 25 2026, price return, committed as a two-row file with its citation.
- **Built (W1-03):** `configs/benchmarks.yaml`: 6,368.85 (Mar 27) and 7,743.41 (Sep 25), read 2026-10-26; `pmcc/wheel/benchmarks.py` refuses a start that isn't the last close before the window or an end that isn't its last close. Closes are quoted strings, read as exact decimals.

### WD-18 — Dividends and interest on cash
**Status:** SETTLED · **Basis:** PO, 2026-10-26

- **Recommendation:** ignore NVDA's $0.01 quarterly dividend ($1 per 100 shares), and pay no interest on cash, stating both on the site. Paying interest would favour the wheel, which holds the most idle cash.
- **Outcome:** 2026-10-26, PO: as recommended. No dividends, no interest on cash; both stated on the site.

### WD-19 — Fees
**Status:** SETTLED · **Basis:** PO, 2026-10-26

- **Recommendation:** $0 in the base run, matching the PMCC benchmark's assumption; the friction runs at spread capture 0.25 and 0.50 carry the cost sensitivity.
- **Outcome:** 2026-10-26, PO: as recommended. $0 per contract in every run; the friction runs carry the cost sensitivity.

### WD-22 — Wheel pages
**Status:** SETTLED · **Basis:** PO, 2026-10-28 · **Affects:** UI-SPEC §2, §3, §6, §7; Spec › Accounting (portfolio at any point in time), Site; W4-01

- **Asked** at W4-01 with a mockup of both pages; every answer as recommended.
- **Pages:** two, in the existing look. **Wheel** (`#/wheel/:symbol`): readouts; [1] NAV; [2] Portfolio at a bar beside [3] Cycle statistics; [4] Blotter; [5] Gate log; [6] Ledger. **Wheel review** (`#/wheel-review/:symbol/:ruleId?`): readouts; the thesis; [1] Verdicts; [2] Benchmarks; the fill model; [3] and [4] mid vs print for the puts and the calls; [5] Friction runs; [6] Rules, rendered from the config. The layouts are in UI-SPEC §6. (The alternative was one long page.)
- **Portfolio at a bar (requirement 2):** a click on the NAV chart or on a ledger row's time picks the bar; ◀ ▶ step a bar, and a session select and a bar select jump to one. The bar is in the URL (`?bar=`), so a link opens the same portfolio; with none, the last bar. (The alternative was the selects alone.)
- **Nav, landing, wordmark:** the two entries join the nav after Quant. `#/` still opens the PMCC's Compare page and the wordmark stays "PMCC Backtest", so nothing the PMCC's submission links to moves; the wheel is submitted by its deep link, `#/wheel/NVDA`. (The alternative was the wheel first.)
- **Copy rules:** the PMCC PO's three are kept for the wheel: a rule is named by what it did, never by its ID, outside ID columns; rule cells are in plain words and link to the rule (its row on the wheel review page); Greeks are named in words.
- **Claim 1's benchmark (PO, 2026-10-28, at the read-through):** making money has no outside benchmark, only P&L > $0 (WD-29), so its Benchmark cell reads "$0.00 (break-even)" rather than a bare $0.00; the column keeps its name. (The alternative was renaming the column "Must beat".)

## Engineering

### WD-11 — Put fetch band and a separate cache
**Status:** ENG · **Affects:** Spec › Data; W1-01

- **Band:** for each weekly expiry, every session from the week's first through expiry, strikes from 80% of the first session's low up to two increments above its high. A 0.30-delta weekly put sits a few percent below spot; 20% below covers it, and the short put's own strike is fetched all week whatever the stock does. The range is two bands that meet at 95% of the low, each measuring its own strike step: one band probed at its centre (~90% of spot) could find a coarser grid there and skip the money's own strikes, where W-P3 picks.
- **Separate cache:** `data_cache/NVDA/wheel/`, with its own manifest: a *part* of the symbol's cache (`SymbolCache(..., part="wheel")`). The PMCC's `_P` units hold one session of near-money puts each, and its planner refuses a cache that isn't its own plan. The PMCC's cache lists only its own `stock` and `chains/`, so the part's units never reach its plan check, loader or data-manifest hash, and the PMCC's results keep their provenance. The folder is already committed with NVDA's (`!data_cache/NVDA/` in `.gitignore`).
- **Command:** `pmcc fetch --wheel` (`just fetch NVDA 2026-03-30 2026-09-25 --wheel [--plan-only]`). It plans from the stock tape the PMCC's fetch cached and asks LSEG nothing to plan, but it opens a Workspace session like every fetch, so even `--plan-only` needs Workspace signed in. It then reuses the PMCC's unit loop, strike-step measurement, RIC builder, estimate and cache format unchanged.
- **Estimate (W1-01, 2026-10-26):** 26 units, 710 strikes on the probe report's $2.50 step, 970 to 2,910 RIC requests, about 23 to 67 min (expect about 2 to 2.5 times the low figure: 45–55 min).
- **Pull (W1-02, 2026-10-26, PO's go):** all 26 units in 14 min, 1.3 MB (`logs/fetch_20261027T023615Z.jsonl`); 0 to 4 strikes a week unanswered, all deep and unlisted. The PMCC's manifest is unchanged.
- **Coverage (W1-02; corrected 2026-10-26):** at each week's first bar (10:00 ET), the put nearest −0.30 delta (IV from the mid, r 3.71%, spot the bar's last trade) had a valid quote (BID > 0, ASK > 0, ASK ≥ BID, as the loader tests it) on 819 of the 875 session bars from then to expiry (93.6%; at least 80% of each week's bars: 28 to 35 a week, 26 to 28 in the five four-session weeks). The other 56 are zero bids late in the week, after the stock moved away from the strike; they mark the put at its last mid, flagged stale, and never need a fill, since the wheel doesn't buy back. (First reported as 100%, which counted any bar with a BID and an ASK present, zero bids included.) Its delta was −0.26 to −0.35; its spread 0.5–2.7% of mid; and at least 9 fetched strikes lay below it, so the 80% floor never bound. Its mid was $1.22–$3.65 a share. This is a data check, not the rules: W-T1 and the delta pick are settled at W2-02, and W2-03 re-checks every strike the run actually picks (done: WD-26).

### WD-12 — Wheel ID prefixes
**Status:** ENG

- Decisions are `WD-nn` and rules `W-…` (W-T1, W-P1, W-C3, W-X2), so nothing collides with the PMCC's `DEC-nn` or its rule IDs, which its code and results still cite. `RuleId` accepts `W-[TPCX]n` beside the PMCC's patterns (W2-01).

### WD-24 — The wheel's own book, beside the PMCC's
**Status:** ENG · **Affects:** W2-01, W2-02

- **Choice:** the wheel gets its own book and valuation (`pmcc/wheel/book.py`): cash, at most one short option, and shares, with WINV-05 to WINV-07 checked after every event and cash never negative (a cash account). It reuses the shared pieces unchanged: blotter `Event`s and their cash check, integer money, `OptionId`/`StockId`, marks and their stale carry, and, from W2-02, `MarketView`, the fill model and pricing.
- **Why not widen the PMCC's book:** its covered-diagonal checks, ledger and Reg T are built around one long call and one short call. Making them general would touch every PMCC path, and the PMCC's results must not move (WD-01). A sibling is less code and leaves the PMCC byte-identical.
- **Not taken from the PMCC:** Reg T (the wheel is a cash account: reserved and free cash replace IM, MM and available funds).
- **The config too (W2-02):** `pmcc/wheel/config.py` has its own rule model (`WheelRule`: the PMCC's fields, params typed by rule ID instead of by kind) and `configs/wheel.yaml`. Adding the wheel's rules to the PMCC's kind registry would break its tests, which pin that registry to the PMCC's spec. The write-up text is checked the same way, with the same renderer.
- **The loop (W2-02):** `pmcc/wheel/engine.py` reuses `MarketView`, the fill simulator, `check_event` (fills and rule IDs), `leg_greeks` and `closing_spot`; its own bar checks (WINV-01, 02, 05 to 08) are `pmcc/wheel/invariants.py`. `pmcc/wheel/market.py` builds the wheel's market from the PMCC cache's stock and calls and the wheel's puts (WD-11), its data-manifest hash over exactly those units, and refuses a cache missing any week's put or call unit: an empty chain would otherwise be logged as a rule's skip when it is a data gap.
- **Import rule:** ARCHITECTURE §3.3's rule 3 (archived; enforced by `tests/architecture/test_imports.py`) now also covers `pmcc.wheel.rules`: the wheel's selectors, like the PMCC's strategies, never import `engine`, `data`, `accounting` or `export`, so they see the market only through `MarketView`.
- **Adversarial review of W0-01 to W2-02 (2026-10-26):** 4 reviewers (correctness, tests by mutating a copy, docs, downstream fit), 2 skeptics per finding on the 12 most severe. 36 raw findings, 26 unique; 8 confirmed, 2 plausible, 2 refuted, 14 low ones unverified. Nothing high: no reviewer found a PMCC behaviour or result change, nor a wrong wheel number on NVDA. Checked after the fixes: a scratch batch of all 24 PMCC runs matches all 31 committed result files, the manifest's commit, dirty flag and timestamp aside. What was found and fixed:
  - **Test gaps (7 confirmed):** no test pinned W-X3, a call week skipped under W-T1, the basis after a second call, the call's OTM filter, the stale_call/stale_stock flags, the stale seed of WD-25 #4, or any runtime invariant firing. Each now has a test; the review's surviving mutants are killed.
  - **The W2-03 line** named `pmcc run`, which rejects the wheel's config (confirmed); it now names `pmcc wheel`.
  - **A data gap read as a rule skip** (plausible): `load_wheel_market` now refuses a cache missing a week's put or call unit, and a W-C3 note names the highest call listed.
  - **WD-25 #4 inflated close-bar NAV** (plausible): assigned shares with no quote were marked at the strike, which the close has just gone through. They're now marked at the closing trade that assigned them (see WD-25).
  - **Unverified lows, fixed anyway:** a tradeless expiry's error named the PMCC's X-S4/X-S5; W-P4 locked the rest of the week after one refusal (now later bars may still sell, as WD-25 #1 implies); fee, two-contract, mid-week-start, week-open-band and later-benchmark-date tests; the import rule above; `pmcc serve`'s stub pointed at the wrong plan; doc counts and wording (W2-01's test count, the risks list, WD-11's per-week coverage, the settled entries filed under Open, README's Workspace note, UI-SPEC's carried-over copy rules, now put to the PO in WD-22).
  - **Refuted:** W-P4 counting the put's own credit (the spec's invariant 5 says the same); the market dropping RICs and option prints (W2-03 and W3-02's job, not a defect now).

### WD-25 — Rule details the spec leaves open (W2-02)
**Status:** ENG, put to the PO 2026-10-26 · **Affects:** W-T1, W-P3, W-C3, W-X1 to W-X4, Accounting

None of these changes NVDA's run: every week sold on its first bar (10:00), deltas are continuous so no exact tie arose, and every close bar had a trade. Each is in the spec now, so the PO can see it and overrule it.

1. **The pick is made afresh on each bar** of the week's first session until one passes W-T1, rather than frozen at the first bar. Simpler, and the strike follows the stock if it moves before the market is liquid.
2. **Ties go further out of the money:** the lower put strike, the higher call strike. The conservative side for a seller.
3. **The closing trade** is the close bar's last trade, or if that bar had none, the session's last trade before it. Only the fallback is new.
4. **A holding with no mid on the bar it was filled** is marked stale until a mid arrives: shares bought on assignment at the closing trade that assigned them (the close has just gone through the strike, so marking at the strike would overstate that bar's NAV; changed after the adversarial review, WD-24), anything else at its fill.
5. **Skip reasons:** a week that sells nothing is logged under W-P4 if cash couldn't secure the put on some bar; under W-C3 if no call at or above the cost basis had a quote on any bar (its note names the highest call listed); otherwise under W-T1. A W-P4 refusal doesn't end the week: a later bar's pick, re-made per #1, may be one cash secures.

### WD-26 — The wheel's result: `pmcc wheel`, its file and its checks (W2-03)
**Status:** ENG · **Affects:** W2-03; `pmcc wheel`, `pmcc verify`, `pmcc export`, `just reproduce`

- **Command:** `pmcc wheel --symbol SYM [--config PATH]` (`just wheel SYM`), from the cache only: `load_wheel_market` (the cache's stock and calls, the wheel part's puts, WD-11), the bar loop, then `results/{SYM}/{run_id}.json`. The window and r come from `configs/universe.yaml`, the starting cash from the wheel's own config (WD-10). A failed run writes nothing. `--config` takes another wheel config under its own run ID, as W3-02's friction runs will (`wheel--sc025`).
- **The file (`pmcc/export/wheel_models.py`):** its own `WheelResult`, beside the PMCC's `RunResult` (WD-24): the PMCC's manifest, blotter row, instrument and leg models unchanged; the wheel's ledger row (state, cash, reserved and free cash, shares and their mark, the put and call legs with RIC, OCC, strike, expiry, mark, stale flag and delta, cost basis per share, NAV, flags) and gate-log row; a summary of the runtime invariants held (WINV-01 to 03, 05 to 09) and the ledger's flag counts. Metrics wait for W3-01. Written by the same canonical writer, so the config in the file hashes to `manifest.config_hash`.
- **`pmcc verify`:** knows a wheel run by its run ID (`wheel.json`, `wheel--*.json`), applies the PMCC's file checks (schema, canonical bytes, its place, a clean tree, the config hash, the rule text, the invariants recorded), and re-derives the invariants from the rows with its own arithmetic (`pmcc/export/wheel_rederive.py`): the positions the rows booked; WINV-01 (each row's Cash Δ, and the cash walk), 02 (NAV), 03 (fills at the quote's mid ± capture; an assignment's shares at its strike), 05 (reserved cash = the put's strike × 100, and cash covers it), 06, 07 (each bar's state is what it holds), 08 and 09. WINV-04 is `MarketView`'s; WINV-10 is a test. A corrupted copy fails on each, one check per corruption.
- **`pmcc export`:** verifies the wheel's results but doesn't publish them, so the site is unchanged until the wheel's pages exist (W4-01; published since, WD-32).
- **`just reproduce`:** the PMCC's batch, then `just wheel NVDA`, then verify, export and the site.
- **The market:** `load_wheel_market` now also refuses a stock tape short of the window, the same data-gap guard as the option units' (WD-24), and names every instrument by the RIC its cache answered with.
- **Shared code, no PMCC change:** the runner's RIC naming (`Names`), blotter row and tape check, and two of the PMCC re-derivation's row checks, are made public for the wheel; the writer's and verify's types widen to either result. After every change here and WD-27's, a scratch batch of all 24 PMCC runs matches all 31 committed result files, the manifest's run time, commit and dirty flag aside.
- **The NVDA run (2026-10-27, from the working tree; re-run from the clean tree at `8abed76` and committed at W3-03, the same figures):** 61 rows over 875 bars and 26 weeks, every week sold on its 10:00 bar: 13 puts (8 expired, 5 assigned) and 13 calls (9 expired, 4 called away), so 4 complete cycles, the fifth ending in shares (100 at a basis of $221.355, marked $225.07). $4,414.50 of premium. NAV $25,000 to $29,171.50, lowest $24,967.00 (May 4, 12:00), highest $29,225.50 (Sep 22, 15:00). 36 bars marked stale (20 call, 16 put), none stale stock. Config hash `0ee09dd0…`, data-manifest hash `5d20c90a…`, 402 KB. It is committed at W3-03, with its metrics.
- **Call coverage (and put):** for each of the 26 options sold, the raw cache on its decision bar had validly quoted strikes on both sides of it (9 to 41 below, 4 to 21 above) on the $2.50 grid, so the nearest-delta search was never cut short by the fetched band; the calls the cost basis pushed far out of the money (down to 0.07 delta) still had 10 or more quoted strikes above them. No week was skipped, so none under W-C3. From sale to expiry, a pick was validly quoted on 63% (the Jun 22 call) to 100% of its bars; the rest are the 36 stale bars.
- **The hand audit (PO, 2026-10-27):** the PO picked the Jun 1 – Jul 10 cycle, with the May 26 week so that W-X1 is in it too, and accepted the audit. A script outside the repo, sharing no code with `pmcc`, re-derived the 7 weeks from the raw parquet with polars, its own Black-Scholes (ACT/365 to the 16:00 close, q = 0, r = 0.0371, spot the bar's TRDPRC_1) and exact decimals, starting from the result's cash at May 22's close: 3,898 checks against the result's 14 blotter rows and 238 ledger bars, 0 discrepancies once WD-27 was settled (before it, 1: WD-27's first case, Jul 10 at 13:00).
  - **May 26:** the $210 put (δ −0.259; next, $212.50 at −0.357 and $207.50 at −0.180) at its mid $1.435 (bid 1.42, ask 1.45, a 2.1% spread); it expires at the $211.15 close.
  - **Jun 1:** the $212.50 put (δ −0.274) at $2.08; assigned at the Jun 5 close of $205.11; 100 shares bought at $212.50; the basis $212.50 − $2.08 = $210.42.
  - **Jun 8 to Jul 6:** calls at $212.50 (δ +0.295), $212.50 (+0.337), $217.50 (+0.328), $205 (+0.088) and $205 (+0.171), each the nearest 0.30 at or above the basis, which fell to $208.485, $206.695, $204.765 and $204.44; the basis set the last two. The first four expire; the Jul 10 close of $210.96 calls the shares away at $205.
  - **The cycle:** the put +$208, the calls +$676, the shares −$750: +$134.
  - **Every bar:** the state, cash, reserved and free cash, shares, the stock's mark, cost basis, NAV, flags, and each leg's RIC, strike, expiry, mark (with the stale carry) and delta.
- **WINV-10:** tested in-process and in two processes with different hash seeds on a synthetic market, and on NVDA: two runs, `PYTHONHASHSEED` 12345 and random, byte-identical once the run time and commit are dropped.
- **Tests:** the result mirrors the engine row by row on a synthetic five-week market where every booking and skip rule fires (`tests/scenario/winv10_run.py`); verify passes it and fails each corruption; export leaves it out (until W4-01, WD-32); the CLI's paths; the market's tape check and names; WD-27's put limit; the justfile.

### WD-30 — The wheel's numbers: where they are computed and checked (W3-01)
**Status:** ENG · **Affects:** W3-01; `pmcc wheel`, `pmcc verify`

- **Where:** `pmcc/wheel/analytics.py` computes the metrics, cycle statistics, each row's Trade P&L and the verdicts from the engine's run, reusing the PMCC's Sharpe and drawdown arithmetic (`pmcc.analytics.performance`), so the wheel and the baseline are measured alike. `pmcc wheel` writes them into the result's summary (`WheelMetrics`, `WheelCycleStats`, `Benchmarks`, `ThesisVerdict`), and each blotter row gains `trade_pnl`; it prints the three verdicts.
- **The baseline's numbers** are read from its committed result, `results/{SYM}/baseline_pmcc.json` (`--out`), which must have run over the same window at the same r: `pmcc wheel` refuses otherwise, or if it's missing ("run pmcc batch first"). `just reproduce` already runs the batch first. Its run ID and config hash are kept beside the numbers, so the table names the run it compares with.
- **The S&P 500** comes from `configs/benchmarks.yaml` (`--benchmarks`), checked against the window as at W1-03.
- **`pmcc verify`** re-derives each row's Trade P&L from the rows, the S&P 500's return from its two closes, and each verdict from the summary's numbers; and checks the baseline PMCC's figures against the `baseline_pmcc.json` beside the wheel's file, so a baseline re-run since is caught.
- **On NVDA** (2026-10-28; committed at W3-03 from the clean tree at `8abed76`, the same figures): P&L $4,171.50, return 16.69% on $25,000, max drawdown $1,943.50 (7.10%), Sharpe 1.574 over 125 sessions; 13 puts (8 expired, 5 assigned), 13 calls (9 expired, 4 called away), 4 complete cycles and one open at the end, no week skipped, $4,414.50 of premium; time in state: put 48.1%, call 48.9%, shares 1.6%, cash 1.4% of bars. The baseline PMCC: 24.48% on $15,000, Sharpe 1.242, max drawdown 20.55%. The S&P 500: 6,368.85 to 7,743.41, 21.58%. Verdicts: (1) met, (2) met, (3) not met.

### WD-31 — The fill evidence and the friction runs (W3-02)
**Status:** ENG · **Affects:** W3-02; Spec › Fill model; `configs/wheel_friction/`, `just wheels`

- **Friction runs:** `configs/wheel_friction/sc025.yaml` and `sc050.yaml`, each a variant that `extends: ../wheel.yaml`, names itself (`wheel--sc025`, `wheel--sc050`) and patches only `fill_model.spread_capture`. The wheel's config loader folds `extends` like the PMCC's (a relative `.yaml` path, cycles refused); a wheel variant can change only its id, name and fill model, since the rules are fixed (WD-05). Each runs as a full wheel result beside `wheel.json`, with its own metrics and verdicts. `just wheels SYM` runs the wheel and every friction file; `just reproduce` uses it after the batch.
- **Fill evidence, which bars:** the spec asks for "each bar with a trade print" of every option the wheel traded. Read here as each session bar from the option's sale through its expiry session's close with a trade print (TRDPRC_1) and a valid quote, the bars the wheel could fill or held it on. The calls' cache also holds their prior week's bars (fetched for the PMCC's band), which this leaves out. Overrule it and the change is one filter.
- **What the evidence holds** (`fill_evidence` in every wheel result): the number of options sold; per right (puts, calls), every pair (mid rounded half-even as a fill at mid is, print, spread), the PMCC's exact OLS fit of print on mid (slope, intercept, R², N, the median |print − mid| ÷ spread, locked quotes counted apart), and the share of prints at or inside the quote (BID ≤ print ≤ ASK); and a fit and share over both. A print can be up to an hour older than the end-of-bar quote it is paired with.
- **`pmcc verify`** checks the evidence's schema and canonical form, like every other block; it doesn't re-fit it, since export may not import the analytics (archived ARCHITECTURE §3.3, rule 5).
- **On NVDA** (2026-10-28; committed at W3-03 from the clean tree at `8abed76`, the same figures): 825 pairs over the 26 options sold (412 put, 413 call bars). Print on mid: slope 0.998, intercept $0.0019, R² 0.9994; 89.1% of prints at or inside the quote (puts 84.7%, calls 93.5%); the median print sits half a spread from the mid, at the bid or the ask. So a fill at mid is optimistic by about half the spread, and the friction runs price that: at 0.25 the P&L is $4,162.87 and at 0.50 $4,154.25, against $4,171.50 at mid, the same 61 trades, Sharpe 1.570 and 1.567 against 1.574, and every claim's verdict unchanged.

### WD-32 — The wheel's pages: export, index and site code (W4-01)
**Status:** ENG; the chart's shading put to the PO at W4-01's read-through · **Affects:** W4-01; `pmcc export`, `index.json`, the site

- **Export** publishes the wheel's results beside the PMCC's (its copy no longer skips them), with their schema, `wheel_result.schema.json`, from which the site generates `WheelResult`. `index.json` lists each symbol's wheel runs in a field of their own, `wheel` (run ID, name, spread capture, starting cash, path, data source, config hash, commit), not among the PMCC's `runs`: their starting cash is the wheel config's own ($25,000, WD-10), which the PMCC runs' shared-cash check would refuse. Export checks that they share the PMCC runs' window and r, as every run must. `rules.json` stays the PMCC's: the wheel pages read their rules from the result, rendered from the config it ran with. On the committed results: 27 runs (the PMCC's 24, the wheel's 3) and 34 files.
- **Rule links:** a wheel rule links to its row on the wheel review page (`#/wheel-review/NVDA/W-X2`), which outlines and scrolls to it as the Rules page does. Plain labels for the wheel's IDs join the PMCC's in `web/src/format/rule.ts`: "Put assigned", "Called away", "Sell put", and for a skip "No liquid bar" (W-T1), "Cash short" (W-P4), "No call at the basis" (W-C3).
- **The NAV chart:** NAV above a pane of the stock, the held option's strike (dashed) and the shares' cost basis (dotted), the two references as steps. The mockup's "shaded by state" is drawn as one shade, over the bars holding shares, alone or under a call; a put shows as no shade with a strike, a call as shade with one, so the four states read without four fills. Three chart roles and a shade join tokens.css, each from an existing colour: `--spot-line` (TEXT), `--strike-line` (MARGIN_IM), `--basis-line` (IDENTITY_LINE), `--shares-shade` (NAV_LINE at 14%). The chosen bar is a thin amber rule on both panes: a reader's choice, so chrome, not data.
- **Shared components, the PMCC pages unchanged:** `Chart` takes an optional `onPick` (a click on a plot gives the bar under it), `DataTable` an optional `selected` row (outlined like a target, not scrolled to), `RuleLink` an optional `to`, and `FitTable` its columns (Methodology still shows the symbol's fit beside the pooled one; the wheel shows its own alone, with the share of prints inside the quote). The ledger's times are buttons, so a keyboard reaches the pick.
- **Tests:** export publishes and indexes the wheel and refuses one over another window (pytest); the chart's option, the click mapping, and both pages over a fixture wheel and its friction run (44 vitest tests); the smoke test's three wheel routes at four widths, with a click on the real NAV chart, the step buttons, a ledger time, a reload of the deep link, and a blotter rule link landing on its outlined rule (Playwright).

## Open

None.
