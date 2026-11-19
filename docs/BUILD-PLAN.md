# Live Wheel — Build Plan and Backlog

Nov 13, 2026 · from the [Live spec](LIVE-SPEC.md) · **due Tue Nov 17 2026, 11:59 pm ET** (LD-02; submit target 18:00) · the wheel's finished plan is archived in [archive/wheel/BUILD-PLAN.md](archive/wheel/BUILD-PLAN.md)

## How to use this plan

- **Order:** take the first unchecked item whose **Needs** are all checked, unless the PO says otherwise.
- **Ask first:** when picking up an item, put its **Ask first** questions to the PO in one message, each with the recommendation from [DECISIONS](DECISIONS.md), and ask the next item's while finishing the current one. Record every answer in DECISIONS.
- **Done means:** the **Done when** line holds, `just check` is green, every doc the work touched is updated, and the work is handed to the PO with its file list and a proposed commit message (`L1-01: …`). The PO commits.
- **Ticking:** `- [x] **L1-01 · …** — done YYYY-MM-DD; notes`, in the same commit as the work.
- **Tags:** **[PO]** needs a PO answer or review; **[LSEG]** contacts LSEG (the PO runs it locally with the credentials in the environment, or in Actions).
- **Not overdoing it:** each item builds what the spec asks for and no more. The wheel's pricer, calendar and site pieces are reused; the PMCC's and the wheel's results and pages must not change.

## Status board

| Phase | Dates | Exit criteria | Status |
| --- | --- | --- | --- |
| L0 Docs | Fri Nov 13 | Spec, decisions and backlog live; the wheel's docs archived | In progress: L0-01 drafted, waiting on the PO's review |
| L1 Foundations | Fri Nov 13 | CI green on Sanji's pushes; a headless LSEG session pulls NVDA's chain | Done 2026-11-14: CI green (L1-01); the headless session pulled NVDA's quoted chain in Actions (L1-02) |
| L2 Algorithm | Sat Nov 14 | `pmcc live` reads the book, picks the week's option and writes a valid `open_orders.json` | Done 2026-11-15: L2-01 to L2-03; the PO's dry run against LSEG planned Monday's $155 put. Sanji isn't resolving orders yet, so the book is read as cash until its files appear (LD-24) |
| L3 Nightly job | Sun Nov 15 | The scheduled job runs, commits and redeploys; Monday's order is in the file before Sunday's 22:00 run ends | Done 2026-11-18 (LD-27): the scheduled run fired at 06:40 ET Wed Nov 18, 8 hours late, committed its row and redeployed. Monday's order was placed by hand on Sunday night (L2-03), as Sunday's 22:00 slot passed before the workflow existed. Monday night's scheduled run hadn't started by 06:51 UTC, so a late run before the open now plans that day, cron 03:17 UTC (PO, LD-31). Sanji's price file stopped at Nov 13 (the course's server last pushed then), so while Sanji has written no book a stale price file is a warning, not a red run (PO, LD-32) |
| L4 Site | Mon Nov 16 | The live page shows the algorithm, the orders, Sanji's book and the run log | L4-01 done 2026-11-16 (PO: LD-15, LD-16, the "why" text; LD-28). L4-02, the volatility workflow and its two charts (PO, LD-33; LD-34), built 2026-11-18, backfilled the same day; the open orders show LSEG's strike (PO, LD-35): waiting on its first nightly run. L4-03, the site's name, home page and menus (PO, LD-36), and L4-04, the home page's redesign (PO, LD-37), done 2026-11-18 |
| L5 Release | Tue Nov 17 | Monday's order resolved by Sanji and shown; submitted by 18:00 (deadline 23:59 ET) | Not started |

**Critical path:** L3, which must place Monday Nov 16's order before the open, from the nightly run (Sunday's 22:00). It then stays in the file all week (LD-19), so the professor sees it on Tuesday. Sanji isn't resolving orders yet ("Sanji does not resolve these orders yet", the order page), so a fill before the due date isn't expected.

**Cut order if time runs short** (the PO confirms each cut): the page's run-log history (keep tonight's row) → the call side's rules (L-C1 to L-C3; no call can be due before Fri Nov 20's expiry). **Never cut:** the nightly job, a valid `open_orders.json`, the cash-secured and book checks, the page's algorithm write-up and orders.

## Questions for the PO

| When | Asks |
| --- | --- |
| — | None open: L4-01's (LD-15, LD-16, the "why" text) were answered 2026-11-15 and 16 |

## Backlog

### L0 — Docs

- [ ] **L0-01 · Archive the wheel's docs; write the live assignment's** **[PO]** — drafted 2026-11-13; LD-01 to LD-10 settled
  - Move the wheel's spec, plan and decisions to `docs/archive/wheel/` (with a copy of the UI spec) and close its last items; write LIVE-SPEC, DECISIONS, this plan, the UI spec's page section; update CLAUDE.md and README.
  - Done when: the PO has reviewed the spec; `just check` is green.

### L1 — Foundations

- [x] **L1-01 · CI green on Sanji's pushes** — done 2026-11-13: the hook exempts Sanji's files, two repo-policy tests pin it; CI green on the PO's push
  - Exclude Sanji's files from the file-fixing hooks (LD-17), pinned by the repo-policy test.
  - Done when: `pre-commit run --all-files` passes with `price_history.json` as Sanji wrote it, and the PO's push turns CI green.
  - Needs: L0-01
- [x] **L1-02 · Headless LSEG session and probe** **[LSEG]** **[PO]** — done 2026-11-14 (LD-21): `platform_session`, the close snapshot, `pmcc live-probe` and the `live-probe` workflow; 47 new tests, after a code review's fixes. The PO's run in Actions (green): NVDA closed $162.83 on Nov 13; for the Nov 20 expiry, 28 of the 30 contracts asked ($145–$180) were listed and all 28 quoted at the close, spreads about 1–2% of the mid
  - Settled: LD-11 (the chain from LSEG, PO 2026-11-13).
  - `pmcc/data/lseg/platform.py` opens a platform session from `LSEG_APP_KEY`, `LSEG_USERNAME`, `LSEG_PASSWORD` and checks it really opened (LSEG-DATA-GUIDE's lesson). A probe pulls NVDA's last close, the listed expiries, and the coming week's strikes with their bids and asks at the close, and reports what came back, with no credentials in its output. A fake session, kept true by a contract test, serves the tests.
  - Done when: the probe, run by the PO locally (or by a manual Actions run), shows NVDA's close and a full quoted chain for next week's expiry. If the platform session lacks the entitlement, take it to the PO before L2.
  - Needs: L0-01

### L2 — Algorithm

- [x] **L2-01 · Orders in the order language** — done 2026-11-14 (LD-22): `pmcc/live/orders.py`; 117 tests: the page's examples, each field rule, every token form on the page and its near misses, nulls, an expiry before its session, the file's format, encoding and round trip, and an invalid order failing with the file untouched. A code review's fixes are in; whether a bad order in the file stops the run moved to LD-14
  - A typed order and a writer for `open_orders.json`: the fields and tokens the order page defines, every rejection rule checked before writing (LINV-01), canonical JSON, LF, a final newline; ids per LD-19.
  - Done when: tests cover each field's rule and the page's examples, and an invalid order fails without writing.
  - Needs: L0-01
- [x] **L2-02 · Reading Sanji's book** — done 2026-11-14 (PO: LD-14 stop and fail; LD-04 both paths; LD-24): `pmcc/live/book.py`; 14 tests. Rescoped: Sanji isn't resolving orders, so its `positions.json` and `fills.json` were never seen. With neither, the book is cash at the starting cash; either appearing stops the run (L-B2) until L5-01 reads it. L-B1 reads the price file over every instrument. Cash and the cost basis through a cycle wait on Sanji's formats (L5-01)
  - Asked first: LD-14 (settled 2026-11-14: stop and fail).
  - Readers for `positions.json`, `fills.json` and `price_history.json`: the state, cash (LD-09), the cost basis and the last resolved session. Missing files mean Cash; anything else unknown is unreadable (L-B1, L-B2).
  - Their formats are known only from the order page until Sanji writes our first fill (Mon Nov 16, about 16:30 ET), so the readers are lenient, tested on fixtures built from the page, and re-checked against the real files at L5-01.
  - Done when: tests cover every state, the stale and unreadable cases, and cash and cost basis through a full cycle.
  - Needs: L0-01
- [x] **L2-03 · The live rules and `pmcc live`** — done 2026-11-15 (PO: LD-13, LD-19, LD-23; LD-24): `configs/live.yaml`, `pmcc/live/config.py`, `rules.py`, `run.py`, `pmcc live` (`just live`); 64 tests, after a code review's fixes (PO: LD-25, LD-26): the config, each rule's pick against known Black-Scholes deltas, every way the night declines or fails, the file at both paths and its week-long carry, the log, and the Put, Shares and Call states through the decision. The scripted week through Sanji's files waits on their formats (L5-01). The PO's dry run against LSEG (Sun Nov 15, 22:26 ET): planning Mon Nov 16 from Nov 13's close, holding cash, sell 1 NVDA $155 put expiring Nov 20 at the mid, delta -0.32 at the close; the $147.50 strike isn't listed (as in L1-02's probe), and the first batch's documented `UniverseContainer` rejection fell back to one RIC at a time
  - Asked first: LD-13 (settled 2026-11-14: DGS3MO 4.32%).
  - `configs/live.yaml` (every `L-` rule with its thresholds and write-up); the pick from an LSEG snapshot with the backtests' pricer; `pmcc live` (`just live`): read the book, decide, write `open_orders.json` and append the run log, checking LINV-01 to LINV-09. `--dry-run` prints the decision and writes nothing.
  - Done when: each rule has tests at its boundaries; a scripted week runs Cash → Put → (assigned) Shares → Call → (called away) Cash on fixtures; a dry run against live LSEG shows Monday's order.
  - Needs: L1-02, L2-01, L2-02

- [x] **L2-04 · A put's strike as its percent from the close** **[PO]** — done 2026-11-16 (PO, LD-29, and its code review): `pct_token`, L-O1 sends a put's strike as `pct:X` in whole percents (L-O1's `pct_step`; a call's stays a number), the order language refuses a decimal `pct:`, L-P4 and LINV-03 check the strike picked at the close plus a 10% gap (L-P4's `gap_allowance`), the run log and the page show the strike sent; 21 new tests, among them a property test that an unchanged open lands Sanji on the picked strike and a gap case. Monday Nov 16's order converted to `pct:-5` before the open
  - Asked: the PO, on the gap between the night's close and the open (2026-11-16).
  - Done when: a put order carries `pct:X`, a call order a number, and Monday's order is converted in both files.
  - Needs: L2-03

### L3 — Nightly job

- [x] **L3-01 · The nightly workflow** **[PO]** — done 2026-11-18 (LD-27, PO: LD-31, LD-32): `nightly.yml` and `ci.yml`'s `workflow_run`; 14 new tests, after a code review's fixes, and the commit step run against a scratch remote (a shallow clone, a push landing mid-run, a failed night). The manual run (Sun Nov 15, 23:25 ET) committed Monday's order and the site redeployed. The first scheduled run that fired, Tuesday night's 03:17 UTC slot, started at 06:40 ET on Wed Nov 18, 8 hours 23 minutes late (GitHub's delay; the course's own runs start 7 to 8 hours late), planned Wednesday from Tuesday's close (LD-31), wrote no order (L-P1) and kept Monday's, committed its run-log row as the bot, and CI redeployed. Sanji's price file had caught up to Nov 17, so no L-B1 warning
  - `.github/workflows/nightly.yml`: cron `17 3 * * *` (PO, LD-31) and a manual run; `uv sync --frozen`; `pmcc live` with the secrets; commit `open_orders.json` and the run log as the bot after a pull (LD-06). `ci.yml` also runs on that workflow's completion and deploys from `main` (LD-06).
  - Done when: a manual run commits Monday's order and the site redeploys; the PO confirms the scheduled run on Sunday night. Sunday's slot (03:00 UTC Nov 16) passed before the workflow existed, so Monday night's run (03:00 UTC Nov 17, planning Tuesday, keeping Monday's order: LD-19) is the first scheduled one. It hadn't started by 06:51 UTC: GitHub starts the cron hours late (the course's started near 10:00 UTC each night), which LD-24 refused before the close. Now a run before the open plans that day, and the cron is 03:17 UTC (PO, LD-31). Its price file also stopped at Nov 13, which L-B1 would refuse every night: while Sanji has written no book that is now a warning (PO, LD-32).
  - Needs: L2-03, L1-01

### L4 — Site

- [x] **L4-01 · The live page** **[PO]** — done 2026-11-16 (PO: LD-15, LD-16, the "why" text kept as drafted; LD-28): `live.json` from the export (`pmcc/export/live.py`), the run log's pick quote, the page `#/live/NVDA`; 21 new Python tests, 13 page tests, the smoke test's route at four widths, after a code review's fixes
  - Asked first: LD-15 (settled 2026-11-15: not restricted; the pick's quote shown), LD-16 (settled 2026-11-15: `#/live/NVDA`, "Live"); the PO reviews the "why" text (2026-11-16: as drafted, its numbers kept).
  - Export publishes the run log and Sanji's files for the page; the page per [UI-SPEC](UI-SPEC.md) §6 › Live; the smoke test covers its route.
  - Done when: the page renders the committed files and the smoke test passes at four widths.
  - Needs: L3-01
- [ ] **L4-02 · NVDA's volatility: a workflow and two charts** **[PO]** — built 2026-11-18 (PO, LD-33; LD-34): `pmcc vol` (`pmcc/live/vol.py`, `vol_fetch.py`), `.github/workflows/vol.yml`, `live.json`'s `vol` and `smile`, the live page's two panels; 48 new Python tests and 17 page, chart and theme tests. Checked by eye on a build with sample data, at desktop and phone widths. The backfill ran 2026-11-18 (63 sessions, Aug 20 to Nov 17; checked against its own rules: tenors 28–32 days, every ATM strike within $2.50 of the close, RV20 recomputed from the closes). Then (PO, LD-35) the open orders show the strike LSEG gave the run beside the one sent, the smile's caption says "would pick", the rule table is the page's last panel, and the Open orders panel is its table alone. The smile chart is named "This week's skew" (PO, LD-39). Waiting on the first nightly run
  - Asked first (2026-11-18): the charts, the workflow, the history, how they're drawn; the tenor, ATM IV, RV20's window, the smile's side (LD-33).
  - The backfill: in Actions, "Run workflow" on `vol` with `since` 2026-08-20 and `plan_only` ticked; read the plan; then again unticked. Or on the PO's machine, with the credentials in the environment: `just vol NVDA --since 2026-08-20 --plan-only`, then without `--plan-only`.
  - Done when: the backfill and a scheduled run have committed `live/vol.jsonl` and `live/smile.json` as the bot, and the redeployed page shows both charts.
  - Needs: L4-01, L3-01
- [x] **L4-03 · The site's name, home page and menus** **[PO]** — done 2026-11-18 (PO, LD-36): "Algo Trading Strategies"; `#/` a card per strategy, the live wheel first (`web/src/pages/Home.tsx`); a menu per strategy in the bar (`NavMenu`, the live wheel a plain link); no symbol picker or ident line; Universe and Data off the menus; each page's strategy under the bar. 6 new route and menu tests; the smoke test covers `#/` at four widths. Checked by eye at desktop and phone widths, a menu open
  - Asked first (2026-11-18): the name, the home page, the order, the picker, the ident line, Universe and Data, the label (LD-36).
  - Done when: `#/` shows the four panels, the bar holds the three entries, every page names its strategy, and `just check` and `just e2e` are green.
  - Needs: L4-01
- [x] **L4-04 · The home page, redesigned** **[PO]** — done 2026-11-18 (PO, LD-37): a big headline over three rounded tiles, one big figure each, on a drifting background of the palette's lights (`web/src/pages/Home.tsx`, `web/src/theme/home.css`); still under reduced motion. 3 home tests replace L4-03's two; checked by eye at desktop and phone widths
  - Asked first (2026-11-18): the layout, the motion, the look (LD-37).
  - Then (PO, 2026-11-18): the copy, "Harvesting the volatility risk premium." over "Systematic options strategies" (LD-37); and the site calls the live wheel "Wheel forward test", its page "Overview", its tile telling the week's trade (LD-38).
  - Done when: `#/` shows the headline and the three tiles with their figures and pages, and `just check` and `just e2e` are green.
  - Needs: L4-03

### L5 — Release

- [ ] **L5-01 · Sanji's book read** **[PO]** — once Sanji resolves an order (not expected before the due date: "Sanji does not resolve these orders yet")
  - Read the real `positions.json` and `fills.json` into the book (state, cash, cost basis), with tests on the real files, so the run stops failing L-B2 on them; then the scripted week through Sanji's files (L2-03); and the page's fills as a blotter (PO, LD-30). Until then, confirm Monday night's run keeps Monday's order (LD-19).
  - Needs: L4-01
- [ ] **L5-02 · Submit** **[PO]** — the site's URL, by 18:00 Tue Nov 17. Needs: L5-01

## Risks

- **NVDA not in the course's prices (LD-12).** Closed 2026-11-14: NVDA (4815747) is tracked in `price_history.json`, as the course's setup provides; its bars start with the price job's next run (16:00 ET Monday).
- **Sanji isn't resolving orders.** The order page says so, with no date. The run writes correct orders now; the book stays cash; when Sanji's files appear, the run fails red (L-B2) until L5-01 reads them.
- **Platform entitlement.** Closed 2026-11-14: the headless session returned NVDA's close and a fully quoted weekly chain in Actions (L1-02).
- **Cash may not secure a put.** Closed 2026-11-14: NVDA closed $162.83 on Nov 13, so a 0.30-delta put (a strike near $155) secures about $15,500 of the $25,000.
- **Earnings week.** The Nov 20 weekly's at-the-money straddle cost about $15.75 at Nov 13's close, about 10% of the stock: likely NVDA's earnings that week (not confirmed). The rules have no event filter, as in the backtest, so Monday's put is sold through it; raised with the PO 2026-11-14.
- **Sanji's file formats.** `positions.json` and `fills.json` don't exist yet, and nothing publishes their format; L5-01 reads them once they do.
- **Timing.** Cron runs can start late or be dropped (LD-27); Sanji resolves from about 16:30 ET. L-B1 refuses a stale book rather than guess.
- **The price job skips days.** It wrote no commit for Nov 12 (Nov 13's carried both days) and has run as late as 10:55 ET the next morning. If Friday's prices haven't landed by Sunday night, every weekend night fails L-B1 and Monday gets no order; a manual run once they land covers it.
