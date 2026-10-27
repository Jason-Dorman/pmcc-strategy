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
| WD-02 | Option tenor | PROVISIONAL (PO): weekly, confirm by 2026-10-27 | — |
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
| WD-20 | Metrics | ASK | W3-01 |
| WD-21 | Thesis wording | SETTLED (PO): the draft, unchanged | — |
| WD-22 | Wheel pages | ASK | W4-01 |
| WD-23 | Fills at mid | SETTLED (PO) | — |
| WD-24 | The wheel's own book, beside the PMCC's | ENG | — |
| WD-25 | Rule details the spec leaves open (W2-02) | ENG, put to the PO | — |

## Settled

### WD-01 — PMCC docs archived; styling carried over
**Status:** SETTLED · **Basis:** PO, 2026-10-26 · **Affects:** docs/, CLAUDE.md, README

- **Asked:** which docs are no longer needed, given whether the PMCC stays on the site.
- **Outcome:** the PMCC stays live on the site, but its docs retire, except the UI styling, which the wheel's pages must match. In the PO's words: "I just want to make sure we're meeting the requirements for this assignment and not overdoing it — so I don't want decisions we made for PMCC to leak into the requirements for the wheel." The PO took the recommended split:
  - **Archived to `docs/archive/pmcc/`:** the PMCC spec, PRD, ARCHITECTURE, TEST-STRATEGY, UI-SPEC, BUILD-PLAN and DECISIONS. The PMCC's code and two config tests still cite them there.
  - **Live:** ENGINEERING-PRINCIPLES (how code is written); a new [WHEEL-SPEC](WHEEL-SPEC.md), this log, a wheel [BUILD-PLAN](BUILD-PLAN.md), and a [UI-SPEC](UI-SPEC.md) carrying over only the styling.
  - **CLAUDE.md** keeps the working rules (the PO decides and does all git; credentials; LSEG access; integer money; no styling literals) and points at the new docs.

### WD-02 — Option tenor
**Status:** PROVISIONAL · **Basis:** PO, 2026-10-26; final answer expected 2026-10-27 · **Affects:** Spec › Data, Trade rules

- **Options:** weekly (about 26 cycles in the window, reusing the cached weekly calls); monthly at 30–45 DTE (the textbook wheel, but only 5–6 cycles); both.
- **Outcome:** weekly for now. The PO is taking it to others and expects a final decision by 2026-10-27. If it changes to monthly, the put pull, the call coverage check and W-P2/W-C2 change with it.

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

## Engineering

### WD-11 — Put fetch band and a separate cache
**Status:** ENG · **Affects:** Spec › Data; W1-01

- **Band:** for each weekly expiry, every session from the week's first through expiry, strikes from 80% of the first session's low up to two increments above its high. A 0.30-delta weekly put sits a few percent below spot; 20% below covers it, and the short put's own strike is fetched all week whatever the stock does. The range is two bands that meet at 95% of the low, each measuring its own strike step: one band probed at its centre (~90% of spot) could find a coarser grid there and skip the money's own strikes, where W-P3 picks.
- **Separate cache:** `data_cache/NVDA/wheel/`, with its own manifest: a *part* of the symbol's cache (`SymbolCache(..., part="wheel")`). The PMCC's `_P` units hold one session of near-money puts each, and its planner refuses a cache that isn't its own plan. The PMCC's cache lists only its own `stock` and `chains/`, so the part's units never reach its plan check, loader or data-manifest hash, and the PMCC's results keep their provenance. The folder is already committed with NVDA's (`!data_cache/NVDA/` in `.gitignore`).
- **Command:** `pmcc fetch --wheel` (`just fetch NVDA 2026-03-30 2026-09-25 --wheel [--plan-only]`). It plans from the stock tape the PMCC's fetch cached and asks LSEG nothing to plan, but it opens a Workspace session like every fetch, so even `--plan-only` needs Workspace signed in. It then reuses the PMCC's unit loop, strike-step measurement, RIC builder, estimate and cache format unchanged.
- **Estimate (W1-01, 2026-10-26):** 26 units, 710 strikes on the probe report's $2.50 step, 970 to 2,910 RIC requests, about 23 to 67 min (expect about 2 to 2.5 times the low figure: 45–55 min).
- **Pull (W1-02, 2026-10-26, PO's go):** all 26 units in 14 min, 1.3 MB (`logs/fetch_20261027T023615Z.jsonl`); 0 to 4 strikes a week unanswered, all deep and unlisted. The PMCC's manifest is unchanged.
- **Coverage (W1-02; corrected 2026-10-26):** at each week's first bar (10:00 ET), the put nearest −0.30 delta (IV from the mid, r 3.71%, spot the bar's last trade) had a valid quote (BID > 0, ASK > 0, ASK ≥ BID, as the loader tests it) on 819 of the 875 session bars from then to expiry (93.6%; at least 80% of each week's bars: 28 to 35 a week, 26 to 28 in the five four-session weeks). The other 56 are zero bids late in the week, after the stock moved away from the strike; they mark the put at its last mid, flagged stale, and never need a fill, since the wheel doesn't buy back. (First reported as 100%, which counted any bar with a BID and an ASK present, zero bids included.) Its delta was −0.26 to −0.35; its spread 0.5–2.7% of mid; and at least 9 fetched strikes lay below it, so the 80% floor never bound. Its mid was $1.22–$3.65 a share. This is a data check, not the rules: W-T1 and the delta pick are settled at W2-02, and W2-03 re-checks every strike the run actually picks.

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

## Open

### WD-20 — Metrics
**Status:** ASK · **Ask at:** W3-01

- **Recommendation:** as listed in Spec › Metrics: performance, wheel-cycle statistics, a bootstrap CI on the mean weekly return, and the benchmark table with each thesis claim marked met or not.

### WD-22 — Wheel pages
**Status:** ASK · **Ask at:** W4-01

- **Recommendation:** two pages added to the nav. **Wheel:** readouts, NAV chart, portfolio at a chosen bar, blotter, ledger, cycle statistics, gate log. **Wheel review:** thesis and verdict, benchmark table, fill model and its evidence, friction runs, the rules from the config. The layout is put to the PO as a mockup at W4-01.
- **Also to confirm:** UI-SPEC carries over three copy rules the PMCC's PO set (archived DEC-107, DEC-113, DEC-121): rules named by what they do, never by ID, outside ID columns; rule cells in plain words linking to the rule; Greeks named in words. They're content, not styling, so WD-01 doesn't settle them for the wheel. Recommended: keep them, so the wheel's pages read like the PMCC's.
