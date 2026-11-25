# Build Plan and Backlog — Volatility Thesis and Live Wheel

Two backlogs: the **volatility thesis** (current, from Nov 21) and the **live wheel** (from Nov 13, its nightly runs still going). The wheel's finished plan is archived in [archive/wheel/BUILD-PLAN.md](archive/wheel/BUILD-PLAN.md).

## How to use this plan

- **Order:** take the first unchecked item whose **Needs** are all checked, unless the PO says otherwise.
- **Ask first:** when picking up an item, put its **Ask first** questions to the PO in one message, each with the recommendation from [DECISIONS](DECISIONS.md) (`TD-nn` for the thesis, `LD-nn` for the live wheel), and ask the next item's while finishing the current one. Record every answer in DECISIONS.
- **Done means:** the **Done when** line holds, `just check` is green, every doc the work touched is updated, and the work is handed to the PO with its file list and a proposed commit message (`T1-01: …`, `L1-01: …`). The PO commits.
- **Ticking:** `- [x] **T1-01 · …** — done YYYY-MM-DD; notes`, in the same commit as the work.
- **Tags:** **[PO]** needs a PO answer or review; **[LSEG]** contacts LSEG (the PO runs it locally with the credentials in the environment, or in Actions).
- **Not overdoing it:** each item builds what its spec asks for and no more; the thesis builds only its assignment's scope (TD-03). The wheel's pricer, calendar and site pieces are reused; the PMCC's and the wheel's results and pages must not change.

## Volatility thesis

Nov 21, 2026 · from the [Thesis spec](THESIS-SPEC.md), as scoped for this assignment (TD-03) · **due Tue Nov 24 2026, 11:59 pm ET** (TD-02)

The current work. It builds the thesis, its daily tracker and their page, nothing of the spec's trading test (TD-03). The live wheel's nightly runs keep going beside it, untouched.

### Status board

| Phase | Dates | Exit criteria | Status |
| --- | --- | --- | --- |
| T0 Docs | Sat Nov 21 | Spec scoped, decisions and backlog live | In progress: T0-01 drafted, waiting on the PO's review |
| T1 Data | Sat Nov 21 | A headless probe shows the index's, VIX's and the credit series' coverage, and an SPXW chain | Done 2026-11-22: closes proven (TD-18); credit from FRED, LSEG not entitled (TD-19); SPXW's chain quoted, no spec condor that day (TD-20) |
| T2 Tracker | Sun Nov 22 | The tracker, K1 and R5's note computed from series in memory, tested | Done 2026-11-23: T2-01 (TD-15, TD-16), T2-02 (TD-21 to TD-26) |
| T3 Nightly | Sun Nov 22 | `thesis run` writes `live/thesis/`; the `thesis` workflow commits it and the site redeploys | Done 2026-11-23 (TD-27): the PO's run of the `thesis` workflow committed the file |
| T4 Site | Mon Nov 23 | `#/thesis` shows R1–R7 from the committed files | Done: T4-01 2026-11-23 (TD-28, TD-29), redesigned by T4-02 and polished by T4-03 2026-11-24 (TD-30 to TD-32); versions A and B by T4-04 (TD-33, TD-34); last wording by T4-05 (TD-35, TD-36); the credit chart on the page by T4-06, 2026-11-25 (TD-37) |
| T5 Release | Tue Nov 24 | A scheduled run after Monday's close has updated the page; the URL is submitted | Not started |

**Critical path:** T3-02, live before Monday night, so the scheduled run after Monday's close (04:17 UTC Tue, which GitHub may start hours late, LD-27) updates the page before the deadline: the tracker staying current day to day. A manual run covers a dropped one.

**Cut order if time runs short** (the PO confirms each cut): the home tile → the current-state summary's percentile and RV lines (keep the date and the gap) → R5's measured SPXW cost (keep the stated cost assumption). **Never cut:** R1–R7 visible, the tracker chart on real data, the nightly workflow, K1 computed with its sample gate.

### Questions for the PO

| When | Asks |
| --- | --- |
| T2-02 | Answered 2026-11-23: R5's form (TD-21), the evidence section (TD-23), K1's latch (TD-24), the signal states (TD-25) |
| T4-01 | Answered 2026-11-23: the page's order and copy, the two charts, the home tile (TD-28) |
| T5-01 | The submit target time |

### Backlog

#### T0 — Docs

- [ ] **T0-01 · The thesis assignment's docs** **[PO]** — drafted 2026-11-21; TD-01 to TD-10 settled
  - Rename the spec to `docs/THESIS-SPEC.md` with its scope section; the `TD-nn` part of DECISIONS; this phase; CLAUDE.md and README.
  - Done when: the PO has reviewed the scope section and the entries; `just check` is green.

#### T1 — Data

- [x] **T1-01 · Probe: the index, VIX, the credit spread and an SPXW chain** **[LSEG]** **[PO]** — done 2026-11-22 (TD-18 to TD-20): the index and VIX from 2014, credit from FRED from 2023-11-21, SPXW's Dec 24 chain, no spec condor that day. Built 2026-11-21 (TD-13, TD-14): `thesis probe` (`just thesis-probe`), `pmcc/thesis/probe.py`, `spxw.py`, `fred.py`, `pmcc/data/lseg/discovery.py`, the `thesis-probe` workflow, its thresholds in `configs/thesis.yaml`'s `cost_sample`; 73 tests and the recipe's, after a code review's fixes (FRED's empty cells, outages writing nothing, the history calendar checked against the tape). The contracts' settlement, exercise style and multiplier aren't read from LSEG: the probe settles the RIC spelling, and the profile rests on Cboe's SPXW specification [S5] (TD-14). Waiting on the PO's run
  - First run (Actions, 2026-11-22): FRED's public CSV timed out, so it wrote nothing; FRED moved to its official API with a key (PO, TD-17), with retries (TD-14).
  - First full run (Actions, 2026-11-22 22:37 ET; TD-18): the index's and VIX's closes from 2014, the index's matching the calendar day for day; FRED's spread from 2023-11-21 only; LSEG's search found `.MERH0A0` but didn't read it; no SPXW spelling answered hourly. The probe now reads each search's index RICs first, tries SPXW daily, and searches for SPXW's RICs.
  - Second run (Actions, 2026-11-22 23:18 ET; TD-19): LSEG has ICE's indexes but the account isn't entitled to them, so credit is FRED's, from 2023-11-21 (TD-05's rule). SPXW's spelling and entitlement are proven by LSEG's own RICs; Wed Dec 23 wasn't a listed expiration. The probe now asks every session 28–35 days out and uses the nearest listed.
  - Third run (Actions, 2026-11-22 23:42 ET; TD-20): Dec 24's chain, 76 contracts quoted, 55 inside the spread test, the short legs at −0.201 and 0.204 delta; no wing pair at 35–52 points passes, so §6.2 skips the condor that day. The legs' measured spreads are R5's cost evidence (T2-02).
  - To run: add the `FRED_API_KEY` secret (Settings › Secrets and variables › Actions); then in Actions, "Run workflow" on `thesis-probe`, and download the `thesis-probe-report` artifact into `data_cache/probes/`. Or locally, `just thesis-probe` with the three LSEG variables and `FRED_API_KEY` in the environment.
  - The thesis's own command, `thesis` (TD-13): a second entry point in `pyproject.toml`, its first subcommand `thesis probe` (`just thesis-probe`), over the platform session (TD-04), and FRED's CSV (TD-05): the S&P 500 index's and VIX's daily closes from 2014-01-01 (count, first and last session, sessions missing against each other); whether LSEG has ICE BofA US High Yield OAS, its history and units; FRED's BAMLH0A0HYM2 (first, last, count); for the SPXW expiry nearest 30 days, the contracts' settlement, exercise style and multiplier, and the bid and ask at the close of the strikes nearest ±0.20 delta and their wings. Counts on screen, the report in `data_cache/probes/` (gitignored); runnable by hand in Actions.
  - Done when: the PO's run shows each series' coverage, recorded as a TD entry. If either closes series is missing, or the credit series exists nowhere, take it to the PO before T3.
  - Needs: T0-01

#### T2 — Tracker

- [x] **T2-01 · The tracker: features, horizons, outcomes, episodes, candidates, credit** — done 2026-11-21 (TD-15, TD-16): `configs/thesis.yaml`, `configs/calendar_history.yaml` (2014–2024, checked against NYSE's rules; the shipped table unchanged), `pmcc/thesis/` (`run_tracker` and its parts); 79 tests, among them spec §14's 1–4 and 3.52 → 352, and the PO's missing-data rules (TD-16), after a code review's fixes (credit before 2014, a shock at the calendar's end). The history table matches the S&P 500's tape day for day (TD-18)
  - `configs/thesis.yaml` (spec §13's keys that the tracker reads) and `pmcc/thesis/`, pure, on series in memory: log returns, EWMA and RV5/RV20 (§5.1); `N_t`, the forecast and the matured realized variance on one calendar convention (§5.2); shock episodes and their fixed search windows (§5.3); the first candidate, chosen without credit (§5.4); the credit condition, as-of its assumed publication time, in basis points (§4.4, §5.5).
  - Done when: spec §14's tests 1–4 pass on fixtures (future data changing nothing at t; credit available a day late not used; 3.52 → 352; repeated shocks not extending a window; the credit filter not moving a candidate; weekends, holidays, a leap year and a DST change; immature outcomes null), and `just check` is green.
  - Needs: T0-01
- [x] **T2-02 · Evidence: K1–K3, R5's note, the statuses, the current state** **[PO]** — done 2026-11-23 (TD-21 to TD-26): `pmcc/thesis/evidence.py`, `status.py`, `configs/thesis.yaml`'s `r5_cost`; 25 tests, among them spec §14 test 12
  - Ask first: R5's form (TD-07). Answered: TD-21 to TD-25.
  - K1 over the latest 30 matured stable-credit candidates, `INSUFFICIENT_DATA` below 30 (TD-08); K2 and K3 as definitions only; R5's rough note; `run_status`, `data_status`, `signal_status`, `thesis_status`, `evidence_status` (spec §9, as scoped); the dated current-state summary from the tracked series (TD-10).
  - Done when: K1's sample gate is tested (spec §14 test 12: insufficient never passes), R5's numbers are reproduced from a fixture, and `just check` is green.
  - Needs: T2-01

#### T3 — Nightly

- [x] **T3-01 · `thesis run`: pull, compute, write `live/thesis/`** **[LSEG]** — done 2026-11-23; built (TD-27): `thesis run` (`just thesis`), `pmcc/thesis/run.py`, `publish.py`, `pmcc/export/thesis_models.py`, the export's `thesis.json`; 25 tests, among them spec §14 tests 13 and 14. First real run 2026-11-23 00:59 ET, data through Nov 20; corrected at T4-01 to leave out a session before its decision (TD-29)
  - Pulls the closes from LSEG and the credit series (TD-04, TD-05), runs T2's tracker, and writes `live/thesis/*.json`: a schema version, the config's hash, `generated_at`, `data_through`, `data_status` and each series' source (spec §10), nulls explicit, no NaN or Infinity; `--plan-only` first; an outage writes nothing. `pmcc export` publishes it for the page.
  - Done when: spec §14 test 13 (schema, no NaN, no fixture data in the live files) and 14 (a fixture's inputs to its expected episodes, criteria and JSON) pass, a real run writes the files on the PO's machine or in Actions, and `just check` is green.
  - Needs: T1-01, T2-02
- [x] **T3-02 · The `thesis` workflow** **[PO]** — done 2026-11-23, its first manual run committing the file; built (TD-27): `.github/workflows/thesis.yml`, `ci.yml` on its completion; 8 tests. To run: Actions › thesis › "Run workflow" (it needs the `FRED_API_KEY` secret, already set for the probe)
  - `.github/workflows/thesis.yml`: cron `17 4 * * *` and by hand; `thesis run` (`just thesis`), the LSEG secrets in its step alone; commits only `live/thesis/*.json` as the bot after a pull (TD-09); `ci.yml` runs on its completion and redeploys.
  - Done when: a manual run commits the files and the site redeploys.
  - Needs: T3-01

#### T4 — Site

- [x] **T4-01 · The thesis page** **[PO]** — done 2026-11-23 (TD-28, TD-29): `web/src/pages/Thesis.tsx` and `thesis/`, `components/charts/thesis.ts`, `format/thesis.ts`, the home tile and menu; the smoke test at four widths and an end-to-end test of the zoom, the tooltip and the tables
  - Ask first: the panel order and copy, the two charts, the home tile (TD-10).
  - `#/thesis`, a "Volatility thesis" menu and a home tile, per a new UI-SPEC section: the thesis and its statuses; the horizons and mechanism; the tracker chart (VIX, the 30-day forecast vol and the matured realized vol, the candidates marked, pending outcomes shown as gaps); the credit spread with its 450 bps line (TD-06) and the stable/unstable outcomes; the K1–K3 cards; R5's note; the macro paragraph with the current state; methodology and sources. Accessible tables beside the charts.
  - Done when: the page renders the committed files, the smoke test passes at four widths, and `just check` and `just e2e` are green.
  - Needs: T3-01

- [x] **T4-02 · The thesis page, redesigned for a reader** **[PO]** — done 2026-11-24 (TD-30, TD-31)
  - The PO's redesign: a reading sequence from the idea to the methodology, one latest assessment generated from the data, one default chart, plain evidence and wrong-if cards, raw data behind disclosures; the tracker's own checks exported; no calculation changed.
  - Done when: the page reads at 100% zoom on desktop and phone, works on a file without the new fields, the other pages are unchanged, and `just check` and `just e2e` are green.
  - Needs: T4-01

- [x] **T4-03 · The thesis page's polish** **[PO]** — done 2026-11-24 (TD-32)
  - The gap needed stated as above the forecast; stable credit first and the cost as an estimate; shorter wrong-if cards; the volatility definition; pending outcomes noted on the chart and each pane's unit.
  - Needs: T4-02

- [x] **T4-04 · Versions A and B** **[PO]** — done 2026-11-24 (TD-33, TD-34): `pmcc/thesis/versions.py`, `thesis.json`'s `comparison`, the page's A/B results, table and revised first condition; the PO's snapshot figures reproduced exactly; the original version kept as a reference
  - Needs: T3-01, T4-03

- [x] **T4-05 · The thesis page's last wording** **[PO]** — done 2026-11-24 (TD-35, TD-36): the thesis as a belief, the mechanism as a hypothesis, the assessment said once, the gaps explained, the research history and the updates described as they are; no calculation changed
  - Needs: T4-04

- [x] **T4-06 · The credit chart on the page** **[PO]** — done 2026-11-25 (TD-37)
  - Needs: T4-05

#### T5 — Release

- [ ] **T5-01 · Submit** **[PO]** — the site's URL, with a scheduled run after Monday Nov 23's close on the page. Needs: T3-02, T4-01 to T4-05

### Thesis risks

- **Credit history.** FRED supplies three years of BAMLH0A0HYM2, from 2023-11-21 (spec §4.2; confirmed, TD-18), and LSEG's ICE indexes aren't entitled (TD-19). So few episodes carry a credit flag, and K1 and R5's cohorts stay `INSUFFICIENT_DATA` or exploratory: shown as such, never relaxed (TD-08).
- **Entitlement.** The platform session pulled NVDA's chain (LD-21), the index's and VIX's closes (TD-18) and SPXW's quotes (TD-19); not ICE's indexes (TD-19).
- **ICE's terms.** The raw spread is charted (TD-06) and its values committed in public JSON. ICE's copyright notice is shown; if the course or ICE objects, the chart falls back to the flag.
- **Few episodes.** VIX shocks are rare. Even with history from 2015, K1's 30 matured stable-credit candidates may not exist: `INSUFFICIENT_DATA` is the expected, honest state.
- **Timing.** Scheduled runs start late or are dropped (LD-27); Monday night's must land before the deadline.

## Live wheel

Nov 13, 2026 · from the [Live spec](LIVE-SPEC.md) · due Tue Nov 17 2026, 11:59 pm ET (LD-02; submit target 18:00)

### Status board

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

### Questions for the PO

| When | Asks |
| --- | --- |
| — | None open: L4-01's (LD-15, LD-16, the "why" text) were answered 2026-11-15 and 16 |

### Backlog

#### L0 — Docs

- [ ] **L0-01 · Archive the wheel's docs; write the live assignment's** **[PO]** — drafted 2026-11-13; LD-01 to LD-10 settled
  - Move the wheel's spec, plan and decisions to `docs/archive/wheel/` (with a copy of the UI spec) and close its last items; write LIVE-SPEC, DECISIONS, this plan, the UI spec's page section; update CLAUDE.md and README.
  - Done when: the PO has reviewed the spec; `just check` is green.

#### L1 — Foundations

- [x] **L1-01 · CI green on Sanji's pushes** — done 2026-11-13: the hook exempts Sanji's files, two repo-policy tests pin it; CI green on the PO's push
  - Exclude Sanji's files from the file-fixing hooks (LD-17), pinned by the repo-policy test.
  - Done when: `pre-commit run --all-files` passes with `price_history.json` as Sanji wrote it, and the PO's push turns CI green.
  - Needs: L0-01
- [x] **L1-02 · Headless LSEG session and probe** **[LSEG]** **[PO]** — done 2026-11-14 (LD-21): `platform_session`, the close snapshot, `pmcc live-probe` and the `live-probe` workflow; 47 new tests, after a code review's fixes. The PO's run in Actions (green): NVDA closed $162.83 on Nov 13; for the Nov 20 expiry, 28 of the 30 contracts asked ($145–$180) were listed and all 28 quoted at the close, spreads about 1–2% of the mid
  - Settled: LD-11 (the chain from LSEG, PO 2026-11-13).
  - `pmcc/data/lseg/platform.py` opens a platform session from `LSEG_APP_KEY`, `LSEG_USERNAME`, `LSEG_PASSWORD` and checks it really opened (LSEG-DATA-GUIDE's lesson). A probe pulls NVDA's last close, the listed expiries, and the coming week's strikes with their bids and asks at the close, and reports what came back, with no credentials in its output. A fake session, kept true by a contract test, serves the tests.
  - Done when: the probe, run by the PO locally (or by a manual Actions run), shows NVDA's close and a full quoted chain for next week's expiry. If the platform session lacks the entitlement, take it to the PO before L2.
  - Needs: L0-01

#### L2 — Algorithm

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

#### L3 — Nightly job

- [x] **L3-01 · The nightly workflow** **[PO]** — done 2026-11-18 (LD-27, PO: LD-31, LD-32): `nightly.yml` and `ci.yml`'s `workflow_run`; 14 new tests, after a code review's fixes, and the commit step run against a scratch remote (a shallow clone, a push landing mid-run, a failed night). The manual run (Sun Nov 15, 23:25 ET) committed Monday's order and the site redeployed. The first scheduled run that fired, Tuesday night's 03:17 UTC slot, started at 06:40 ET on Wed Nov 18, 8 hours 23 minutes late (GitHub's delay; the course's own runs start 7 to 8 hours late), planned Wednesday from Tuesday's close (LD-31), wrote no order (L-P1) and kept Monday's, committed its run-log row as the bot, and CI redeployed. Sanji's price file had caught up to Nov 17, so no L-B1 warning
  - `.github/workflows/nightly.yml`: cron `17 3 * * *` (PO, LD-31) and a manual run; `uv sync --frozen`; `pmcc live` with the secrets; commit `open_orders.json` and the run log as the bot after a pull (LD-06). `ci.yml` also runs on that workflow's completion and deploys from `main` (LD-06).
  - Done when: a manual run commits Monday's order and the site redeploys; the PO confirms the scheduled run on Sunday night. Sunday's slot (03:00 UTC Nov 16) passed before the workflow existed, so Monday night's run (03:00 UTC Nov 17, planning Tuesday, keeping Monday's order: LD-19) is the first scheduled one. It hadn't started by 06:51 UTC: GitHub starts the cron hours late (the course's started near 10:00 UTC each night), which LD-24 refused before the close. Now a run before the open plans that day, and the cron is 03:17 UTC (PO, LD-31). Its price file also stopped at Nov 13, which L-B1 would refuse every night: while Sanji has written no book that is now a warning (PO, LD-32).
  - Needs: L2-03, L1-01

#### L4 — Site

- [x] **L4-01 · The live page** **[PO]** — done 2026-11-16 (PO: LD-15, LD-16, the "why" text kept as drafted; LD-28): `live.json` from the export (`pmcc/export/live.py`), the run log's pick quote, the page `#/live/NVDA`; 21 new Python tests, 13 page tests, the smoke test's route at four widths, after a code review's fixes
  - Asked first: LD-15 (settled 2026-11-15: not restricted; the pick's quote shown), LD-16 (settled 2026-11-15: `#/live/NVDA`, "Live"); the PO reviews the "why" text (2026-11-16: as drafted, its numbers kept).
  - Export publishes the run log and Sanji's files for the page; the page per [UI-SPEC](UI-SPEC.md) §6 › Live; the smoke test covers its route.
  - Done when: the page renders the committed files and the smoke test passes at four widths.
  - Needs: L3-01
- [ ] **L4-02 · NVDA's volatility: a workflow and two charts** **[PO]** — built 2026-11-18 (PO, LD-33; LD-34): `pmcc vol` (`pmcc/live/vol.py`, `vol_fetch.py`), `.github/workflows/vol.yml`, `live.json`'s `vol` and `smile`, the live page's two panels; 48 new Python tests and 17 page, chart and theme tests. Checked by eye on a build with sample data, at desktop and phone widths. The backfill ran 2026-11-18 (63 sessions, Aug 20 to Nov 17; checked against its own rules: tenors 28–32 days, every ATM strike within $2.50 of the close, RV20 recomputed from the closes). Then (PO, LD-35) the open orders show the strike LSEG gave the run beside the one sent, the smile's caption says "would pick", the rule table is the page's last panel, and the Open orders panel is its table alone. The smile chart is named "This week's skew" (PO, LD-39). The algorithm and the skew's caption are the PO's own copy, checked for accuracy (PO, LD-40). The skew shows the expected move from the ATM straddle, the pull keeping its price in `live/smile.json` (PO, LD-41; 5 Python tests, 6 page, chart and theme tests). The page, the rule texts and the run's reasons say "the course's order system", not "Sanji" (PO, LD-42). The skew marks the open order's strike, not tonight's pick (PO, LD-43). Waiting on the first nightly run
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

#### L5 — Release

- [ ] **L5-01 · Sanji's book read** **[PO]** — once Sanji resolves an order (not expected before the due date: "Sanji does not resolve these orders yet")
  - Read the real `positions.json` and `fills.json` into the book (state, cash, cost basis), with tests on the real files, so the run stops failing L-B2 on them; then the scripted week through Sanji's files (L2-03); and the page's fills as a blotter (PO, LD-30). Until then, confirm Monday night's run keeps Monday's order (LD-19).
  - Needs: L4-01
- [ ] **L5-02 · Submit** **[PO]** — the site's URL, by 18:00 Tue Nov 17. Needs: L5-01

### Live wheel risks

- **NVDA not in the course's prices (LD-12).** Closed 2026-11-14: NVDA (4815747) is tracked in `price_history.json`, as the course's setup provides; its bars start with the price job's next run (16:00 ET Monday).
- **Sanji isn't resolving orders.** The order page says so, with no date. The run writes correct orders now; the book stays cash; when Sanji's files appear, the run fails red (L-B2) until L5-01 reads them.
- **Platform entitlement.** Closed 2026-11-14: the headless session returned NVDA's close and a fully quoted weekly chain in Actions (L1-02).
- **Cash may not secure a put.** Closed 2026-11-14: NVDA closed $162.83 on Nov 13, so a 0.30-delta put (a strike near $155) secures about $15,500 of the $25,000.
- **Earnings week.** The Nov 20 weekly's at-the-money straddle cost about $15.75 at Nov 13's close, about 10% of the stock: likely NVDA's earnings that week (not confirmed). The rules have no event filter, as in the backtest, so Monday's put is sold through it; raised with the PO 2026-11-14.
- **Sanji's file formats.** `positions.json` and `fills.json` don't exist yet, and nothing publishes their format; L5-01 reads them once they do.
- **Timing.** Cron runs can start late or be dropped (LD-27); Sanji resolves from about 16:30 ET. L-B1 refuses a stale book rather than guess.
- **The price job skips days.** It wrote no commit for Nov 12 (Nov 13's carried both days) and has run as late as 10:55 ET the next morning. If Friday's prices haven't landed by Sunday night, every weekend night fails L-B1 and Monday gets no order; a manual run once they land covers it.
