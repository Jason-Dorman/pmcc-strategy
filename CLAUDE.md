# CLAUDE.md — Options Strategies (PMCC and Wheel done; Live Wheel running; Volatility Thesis in progress)

One engine on LSEG data, publishing results as a static GitHub Pages site. Two backtests are finished, and their code, results and pages stay live and unchanged: the **PMCC** (docs archived in `docs/archive/pmcc/`) and the **Wheel** on NVDA (docs archived in `docs/archive/wheel/`). The **Live Wheel** is built and keeps running: a nightly GitHub Action that runs the wheel live on NVDA and writes `open_orders.json`, which the course's order system, Sanji, fills. The current work is the **Volatility Thesis**: a thesis that options overprice the market's moves after a VIX spike while credit stays calm, with a daily tracker of it on the site, kept current by a nightly workflow. This assignment builds only the thesis, its tracker and their page, not the spec's trading test (TD-03).

**Dates:** the thesis is due Tue Nov 24 2026, 11:59 pm ET (TD-02). The live wheel was due Tue Nov 17 (LD-02).

## The user is the PO: ask, don't assume

The user is the product owner (PO).

- When a question comes up (about what to build, how a rule behaves, what gets reported, or how the site looks), ask the PO and wait for the answer. Don't fill the gap with an assumption, even a reasonable one.
- Known open questions are the `ASK` entries in `docs/DECISIONS.md` (`TD-nn` for the thesis, `LD-nn` for the live wheel), each with a recommendation. They're answered **just in time**, not up front:
  - When you pick up a backlog item, put its **Ask first** questions to the PO in one message, each with its recommendation.
  - Ask the next item's questions while finishing the current one, so the answers are ready.
  - `docs/BUILD-PLAN.md` › Questions for the PO shows when each question comes up.
- Record every answer in DECISIONS (status `SETTLED`, basis "PO" and the date), in the same commit as the work it unblocks.
- Engineering choices that don't change what gets built, run, reported or shown (module layout, integer money, test tooling) are yours to make.
  - Record them as `ENG` entries, so the PO can see them and overrule them.
  - If one turns out to change behaviour, results, scope or the UI, it becomes a question for the PO.
- Never change the spec on your own. When a PO answer changes what the spec says, update the spec in the same commit and cite the LD entry.

## Sources of truth

- **`docs/THESIS-SPEC.md` is the source of truth for the volatility thesis**, as amended by PO answers in `docs/DECISIONS.md` (`TD-nn` entries, in its own part). Its "Scope for this assignment" section says which parts are built now (TD-03); the rest waits for the backtesting assignment and isn't built ahead of it.
- **`docs/LIVE-SPEC.md` is the source of truth for the live wheel**, as amended by PO answers in `docs/DECISIONS.md` (`LD-nn` entries). The thesis's `TD` entries decide nothing for it, nor its `LD` entries anything for the thesis.
- `docs/BUILD-PLAN.md` (the thesis's backlog, then the live wheel's) and `docs/UI-SPEC.md` (the site's styling, and the live page) elaborate it. If one disagrees with the spec or a PO answer, fix it.
- `docs/ENGINEERING-PRINCIPLES.md` says how code is written.
- **`docs/archive/pmcc/` and `docs/archive/wheel/` are frozen records, not live requirements** (PO, WD-01, LD-01): don't carry a PMCC or wheel decision into the live work; if one seems to apply, ask. Their code cites them (`DEC-nn`, `ARCHITECTURE §n`, `P3-04`, `WD-nn`, `W2-03`, …); each folder's README maps each citation to a file. Edit an archive only to fix a citation its code depends on.
- **The course's side** (Spec › The course's side): the order language page, <https://jakevestal.github.io/server-logic-533/order.html>, defines `open_orders.json`. Sanji's files (`price_history.json` at the root; `positions.json` and `fills.json` under `mkt/` or at the root) are the professor's: read them, never edit them, except to add a tracked instrument to `price_history.json` in its own format, as the course provides for (LD-12). Sanji isn't resolving orders yet; its book's format is unknown until it does (L5-01).
- Reference material, not authority:
  - **`LSEG-DATA-GUIDE.md` and `lseg_client.py`:** hard-won know-how for getting data out of LSEG, so it isn't relearned. If LSEG's real behaviour contradicts the spec, take it to the PO.
  - **`DESIGN-GUIDE.md` and `theme.py`:** the baseline look (palette, type, terminal layout). The PO may change it, and changes land in `web/src/theme/`.
  - Read these files; never edit or import them (DEC-57).

## Docs move in lockstep with the code

Docs are part of every change. A commit that changes behaviour, structure, config, commands, status or a decision updates every affected doc **in the same commit**.

A doc that disagrees with the code is a bug. Fix it when you find it; don't defer it.

| When the change touches… | Update |
| --- | --- |
| what the thesis's tracker computes, its scope, data, criteria or workflow (a PO-approved change) | `docs/THESIS-SPEC.md`, plus its TD entry |
| what the live wheel does, its scope, data, orders or nightly job (a PO-approved change) | `docs/LIVE-SPEC.md`, plus its LD entry |
| a decision, a PO answer, an engineering choice, or a probe result | `docs/DECISIONS.md` |
| pages, panels, tokens, charts, tables | `docs/UI-SPEC.md` |
| progress | `docs/BUILD-PLAN.md`: tick the item, update the status board |
| setup, commands, status, reproduction steps | `README.md` and the command table below |
| agent rules or conventions | this file |

## Working the backlog

- `docs/BUILD-PLAN.md` is the backlog. Take the first unchecked item whose **Needs** are all checked, unless the PO says otherwise.
- Ask its **Ask first** questions before building on them.
- Write tests first. An item is done when its **Done when** line holds and `just check` is green.
- One commit per backlog item, prefixed with its ID (`T2-01: the tracker`, `L2-01: orders in the order language`). It includes the item's doc updates and its tick (`- [x] … — done YYYY-MM-DD`). **The PO makes the commit** (DEC-59): leave the work in the tree and hand over the file list and a proposed message.

## Environment

- The project runs from **Git Bash on Windows**, on the same machine as LSEG Workspace (DEC-02). CI runs on Ubuntu, and both must behave the same (DEC-58):
  - LF line endings everywhere (`.gitattributes`); code that writes files passes `newline="\n"`.
  - `pathlib` for paths; the `tzdata` package for time zones; just recipes under bash.
- Keep the project on a Windows path, never `\\wsl.localhost\…`.

## Hard rules

These are working rules, kept for the wheel (WD-01), the live wheel (LD-01) and the thesis (TD-01); a `DEC-nn` beside one is its origin in the archived PMCC log.

- **Git and GitHub (DEC-59):** the PO does all of it: repo setup, init, staging, commits, pushes, branches, tags, GitHub settings, secrets. You may run read-only git (`status`, `diff`, `log`, `show`, `ls-files`, `check-ignore`); never a git or gh command that changes the repo or GitHub.
  - Automated writers exist, by design: Sanji (the professor's server, with the PO's token) pushes its files; the nightly workflow's Actions bot commits only `open_orders.json` and the run log (LD-06); the `vol` workflow's only `live/vol.jsonl` and `live/smile.json` (LD-34); and the `thesis` workflow's only `live/thesis/*.json` (TD-09).
- **Credentials:** never print, read out, copy or commit `lseg-data.config.json` (it's gitignored), the platform credentials (`LSEG_APP_KEY`, `LSEG_USERNAME`, `LSEG_PASSWORD`: GitHub secrets, or environment variables locally; LD-05) or FRED's key (`FRED_API_KEY`, the same way; TD-17). Only `pmcc/data/lseg/` reads LSEG's, and only `pmcc/thesis/fred.py` FRED's.
- **LSEG access:**
  - Only `pmcc fetch`, `pmcc probe`, `pmcc live-probe`, the live wheel's run (`pmcc live`) and its volatility pull (`pmcc vol`, LD-34), and the thesis's probe and run (`thesis probe`, `thesis run`: the thesis's own command, TD-04, TD-13), from the workflows or the PO's machine (LD-05), contact LSEG. Tests, the CI checks, builds and the site never do.
  - `lseg.data` and `pandas` are imported only under `pmcc/data/lseg/`.
  - Before any pull longer than about 2 minutes, show the PO the `--plan-only` estimate. A Workspace (desktop) session needs Workspace signed in throughout; the live wheel's platform session doesn't.
  - Never overwrite cached data. Never record a failed request as "no data": an outage aborts and writes nothing.
- **FRED (TD-05, TD-17):** only the thesis's probe and run contact it, for the high-yield spread if LSEG lacks its history, through its official API with the `FRED_API_KEY` key and the standard library, sending nothing else about the user or the project. Same rules as LSEG: never from tests, CI checks, builds or the site; an outage writes nothing.
- **Strategies:**
  - Strategies see market data only through `MarketView`. No rule touches a dataframe. The live wheel's picks read the close snapshot instead, which holds only the past (PO, LD-26).
  - Every threshold lives in YAML under a rule ID, and every blotter and gate-log row carries one.
  - A strategy variant is rule composition (`extends` and `overrides`), never a boolean flag passed into rule logic.
- **Money and results:**
  - Money is an integer count of $0.0001 units in accounting and fills (DEC-44). Cash is never a float.
  - Results are generated, never hand-edited. Regenerate them from a clean tree and commit them with the code that produced them.
- **Style:** no hex colour, font name or px literal outside `web/src/theme/`.
- **Dependencies:**
  - Never install the Python `playwright` package in the uv env; it breaks `lseg-data`. End-to-end tests use Node Playwright in `web/`.
  - Add no dependency outside the spec's stack without asking the PO.
  - Never add a backtesting framework, QuantLib, Docker, a database server, an orchestration tool, or ML.
- **Complexity:** ruff `C901` ≤ 10 per function; aim for 5 (EP › Cyclomatic Complexity).

## Commands

These exist once P0 is done.

| Command | Does |
| --- | --- |
| `just setup` | install the Python and web environments and the git hooks |
| `just check` | lint, format check, pyright, pytest, and web lint/typecheck/tests |
| `just test [ARGS]` | pytest only |
| `just probe SYM` / `just fetch SYM START END [--plan-only] [--wheel]` | LSEG spikes / pull (local, Workspace signed in); `--wheel` pulls the wheel's weekly puts into `data_cache/SYM/wheel/` (WD-11) |
| `just live-probe SYM` | the live wheel's close snapshot over the headless platform session (credentials in the environment) → `data_cache/probes/live_SYM_*.json`, counts only on screen (L1-02); the `live-probe` workflow runs it in Actions by hand |
| `just run SYM CONFIG` / `just batch` / `just calibrate [ARGS]` | backtests; `calibrate` sets each symbol's own starting cash, skipping final ones; `calibrate --check` recomputes it without writing |
| `just wheel SYM [--config PATH]` | the wheel on one symbol, from the cache only → `results/SYM/wheel.json` (W2-03), with its metrics, benchmarks and verdicts (W3-01); reads the symbol's `baseline_pmcc.json`, so run `just batch` first; `pmcc verify` checks it, `pmcc export` publishes it for the wheel's pages (W4-01) |
| `just wheels SYM` | the wheel and each friction run in `configs/wheel_friction/` (W3-02) |
| `just export` / `just verify` | site data / results validation |
| `just web-dev` / `just web-build` / `just e2e` / `just serve` | frontend (`web-dev` and `web-build` export first) |
| `just reproduce` | cached data → all runs (the PMCC's batch, the wheel and its friction runs on NVDA) → verify → export → built site |
| `just live SYM [--dry-run] [--root DIR]` | one night of the live wheel, after the close or before the next open (LD-31): check Sanji's book (L-B1, L-B2), decide, and write `open_orders.json` at the root and under `mkt/` and a row of `live/runs.jsonl`; asks LSEG (platform credentials in the environment) only on nights that plan a week's first session (Friday to Sunday for a Monday, LD-25); `--dry-run` writes nothing (L2-03); the `nightly` workflow runs it at 03:17 UTC and commits its files (L3-01) |
| `just thesis-probe` | the thesis's data probe (`thesis probe`, T1-01; TD-04, TD-05): the S&P 500's and VIX's daily closes since 2014, the high-yield OAS on LSEG (search, then each RIC found) and FRED, and an SPXW chain ~30 days out with a rough 0.20-delta condor → `data_cache/probes/thesis_*.json`, counts and dates only on screen; platform credentials and `FRED_API_KEY` in the environment (TD-17); the `thesis-probe` workflow runs it by hand in Actions |
| `just vol SYM [--since DAY] [--plan-only]` | NVDA's volatility for the live page's charts (L4-02): ATM IV ~30 days out and RV20, a point a session, into `live/vol.jsonl`, and the coming week's smile into `live/smile.json`; platform credentials in the environment; asks LSEG nothing when both are current; `--since` backfills, after `--plan-only`; the `vol` workflow runs it at 03:47 UTC and commits the two files (LD-34) |

## Conventions

- **Time:**
  - Timestamps are tz-aware America/New_York. Bars are keyed by their end time (`bar_end`), and every decision happens at a bar's end (DEC-06).
  - In the PMCC's rules, "Monday" means the week-open session (DEC-20); the wheel's and the live wheel's specs say "the week's first session".
  - The live wheel decides once a night, from the last close, for the next NYSE session; an order's `for` is that session's date.
- **Logging:** log through `structlog.get_logger()` with dotted event names (ARCHITECTURE §15). Only `pmcc.cli` imports `pmcc.log` to configure it (DEC-80).
- **IDs:**
  - The thesis keeps the spec's IDs exactly: `R1`–`R7`, `K1`–`K3`, its config keys (§13); decisions `TD-nn`, backlog `T0-01`… (TD-11).
  - Live wheel rule IDs match `docs/LIVE-SPEC.md` exactly (`L-B1`, `L-P3`, `L-O1`, …); its invariants are `LINV-01`…`LINV-09` in the spec's order (LD-18). The wheel keeps its own (`W-T1`, `WINV-01`…, archived spec) and the PMCC its own (`E-T1`, `G-3`, `INV-01`…).
- **Test names:** `test_<rule-or-inv>_<behaviour>`, e.g. `test_l_c3_never_sells_below_cost_basis`.
