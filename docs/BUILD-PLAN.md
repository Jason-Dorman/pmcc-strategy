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
| L2 Algorithm | Sat Nov 14 | `pmcc live` reads the book, picks the week's option and writes a valid `open_orders.json` | Built 2026-11-14: L2-01 and L2-02 done; L2-03 waiting on the PO's dry run against LSEG. Sanji isn't resolving orders yet, so the book is read as cash until its files appear (LD-24) |
| L3 Nightly job | Sun Nov 15 | The scheduled job runs, commits and redeploys; Monday's order is in the file before Sunday's 22:00 run ends | Not started |
| L4 Site | Mon Nov 16 | The live page shows the algorithm, the orders, Sanji's book and the run log | Not started |
| L5 Release | Tue Nov 17 | Monday's order resolved by Sanji and shown; submitted by 18:00 (deadline 23:59 ET) | Not started |

**Critical path:** L2-03's dry run → L3, which must place Monday Nov 16's order before the open, from the nightly run (Sunday's 22:00). It then stays in the file all week (LD-19), so the professor sees it on Tuesday. Sanji isn't resolving orders yet ("Sanji does not resolve these orders yet", the order page), so a fill before the due date isn't expected.

**Cut order if time runs short** (the PO confirms each cut): the page's run-log history (keep tonight's row) → the call side's rules (L-C1 to L-C3; no call can be due before Fri Nov 20's expiry). **Never cut:** the nightly job, a valid `open_orders.json`, the cash-secured and book checks, the page's algorithm write-up and orders.

## Questions for the PO

| When | Asks |
| --- | --- |
| L4-01 | LD-15 (no raw LSEG data on the page), LD-16 (the page's route and name), the "why" text |

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
- [ ] **L2-03 · The live rules and `pmcc live`** — built 2026-11-14 (PO: LD-13, LD-19, LD-23; LD-24): `configs/live.yaml`, `pmcc/live/config.py`, `rules.py`, `run.py`, `pmcc live` (`just live`); 64 tests, after a code review's fixes (PO: LD-25, LD-26): the config, each rule's pick against known Black-Scholes deltas, every way the night declines or fails, the file at both paths and its week-long carry, the log, and the Put, Shares and Call states through the decision. The scripted week through Sanji's files waits on their formats (L5-01). Waiting on the PO's dry run against LSEG
  - Asked first: LD-13 (settled 2026-11-14: DGS3MO 4.32%).
  - `configs/live.yaml` (every `L-` rule with its thresholds and write-up); the pick from an LSEG snapshot with the backtests' pricer; `pmcc live` (`just live`): read the book, decide, write `open_orders.json` and append the run log, checking LINV-01 to LINV-09. `--dry-run` prints the decision and writes nothing.
  - Done when: each rule has tests at its boundaries; a scripted week runs Cash → Put → (assigned) Shares → Call → (called away) Cash on fixtures; a dry run against live LSEG shows Monday's order.
  - Needs: L1-02, L2-01, L2-02

### L3 — Nightly job

- [ ] **L3-01 · The nightly workflow** **[PO]**
  - `.github/workflows/nightly.yml`: cron `0 3 * * *` and a manual run; `uv sync --frozen`; `pmcc live` with the secrets; commit `open_orders.json` and the run log as the bot after a pull (LD-06). `ci.yml` also runs on that workflow's completion and deploys from `main` (LD-06).
  - Done when: a manual run commits Monday's order and the site redeploys; the PO confirms the scheduled run on Sunday night.
  - Needs: L2-03, L1-01

### L4 — Site

- [ ] **L4-01 · The live page** **[PO]**
  - Ask first: LD-15, LD-16; the PO reviews the "why" text.
  - Export publishes the run log and Sanji's files for the page; the page per [UI-SPEC](UI-SPEC.md) §6 › Live; the smoke test covers its route.
  - Done when: the page renders the committed files and the smoke test passes at four widths.
  - Needs: L3-01

### L5 — Release

- [ ] **L5-01 · Sanji's book read** **[PO]** — once Sanji resolves an order (not expected before the due date: "Sanji does not resolve these orders yet")
  - Read the real `positions.json` and `fills.json` into the book (state, cash, cost basis), with tests on the real files, so the run stops failing L-B2 on them; then the scripted week through Sanji's files (L2-03). Until then, confirm Monday night's run keeps Monday's order (LD-19).
  - Needs: L4-01
- [ ] **L5-02 · Submit** **[PO]** — the site's URL, by 18:00 Tue Nov 17. Needs: L5-01

## Risks

- **NVDA not in the course's prices (LD-12).** Closed 2026-11-14: NVDA (4815747) is tracked in `price_history.json`, as the course's setup provides; its bars start with the price job's next run (16:00 ET Monday).
- **Sanji isn't resolving orders.** The order page says so, with no date. The run writes correct orders now; the book stays cash; when Sanji's files appear, the run fails red (L-B2) until L5-01 reads them.
- **Platform entitlement.** Closed 2026-11-14: the headless session returned NVDA's close and a fully quoted weekly chain in Actions (L1-02).
- **Cash may not secure a put.** Closed 2026-11-14: NVDA closed $162.83 on Nov 13, so a 0.30-delta put (a strike near $155) secures about $15,500 of the $25,000.
- **Earnings week.** The Nov 20 weekly's at-the-money straddle cost about $15.75 at Nov 13's close, about 10% of the stock: likely NVDA's earnings that week (not confirmed). The rules have no event filter, as in the backtest, so Monday's put is sold through it; raised with the PO 2026-11-14.
- **Sanji's file formats.** `positions.json` and `fills.json` don't exist yet, and nothing publishes their format; L5-01 reads them once they do.
- **Timing.** Cron runs can start late; Sanji resolves from about 16:30 ET. L-B1 refuses a stale book rather than guess.
