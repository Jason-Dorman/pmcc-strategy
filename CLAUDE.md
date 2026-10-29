# CLAUDE.md — Options Backtests (PMCC done, Wheel in progress)

One engine on LSEG hourly data, publishing results as a static GitHub Pages site. The **PMCC** backtest (first assignment) is finished: its code, results and pages stay live and unchanged, and its docs are archived in `docs/archive/pmcc/`. The current work is the **Wheel** backtest (cash-secured puts, then covered calls on assignment) on NVDA.

**Dates:** the wheel is due Sun Nov 1 2026, 11:59 pm ET (WD-13); submit target 18:00.

## The user is the PO: ask, don't assume

The user is the product owner (PO).

- When a question comes up (about what to build, how a rule behaves, what gets reported, or how the site looks), ask the PO and wait for the answer. Don't fill the gap with an assumption, even a reasonable one.
- Known open questions are the `ASK` entries in `docs/DECISIONS.md`, each with a recommendation. They're answered **just in time**, not up front:
  - When you pick up a backlog item, put its **Ask first** questions to the PO in one message, each with its recommendation.
  - Ask the next item's questions while finishing the current one, so the answers are ready.
  - `docs/BUILD-PLAN.md` › Questions for the PO shows when each question comes up.
- Record every answer in DECISIONS (status `SETTLED`, basis "PO" and the date), in the same commit as the work it unblocks.
- Engineering choices that don't change what gets built, run, reported or shown (module layout, integer money, test tooling) are yours to make.
  - Record them as `ENG` entries, so the PO can see them and overrule them.
  - If one turns out to change behaviour, results, scope or the UI, it becomes a question for the PO.
- Never change the spec on your own. When a PO answer changes what the spec says, update the spec in the same commit and cite the WD entry.

## Sources of truth

- **`docs/WHEEL-SPEC.md` is the source of truth for the wheel**, as amended by PO answers in `docs/DECISIONS.md` (`WD-nn` entries).
- `docs/BUILD-PLAN.md` (the wheel's backlog) and `docs/UI-SPEC.md` (the site's styling, and the wheel's pages) elaborate it. If one disagrees with the spec or a PO answer, fix it.
- `docs/ENGINEERING-PRINCIPLES.md` says how code is written.
- **`docs/archive/pmcc/` is the PMCC's frozen record, not wheel requirements** (PO, WD-01): don't carry a PMCC decision into the wheel; if one seems to apply, ask. The PMCC's code cites it (`DEC-nn`, `ARCHITECTURE §n`, `P3-04`, …); its README maps each citation to a file. Edit the archive only to fix a citation the PMCC's code depends on.
- Reference material, not authority:
  - **`LSEG-DATA-GUIDE.md` and `lseg_client.py`:** hard-won know-how for getting data out of LSEG, so it isn't relearned. If LSEG's real behaviour contradicts the spec, take it to the PO.
  - **`DESIGN-GUIDE.md` and `theme.py`:** the baseline look (palette, type, terminal layout). The PO may change it, and changes land in `web/src/theme/`.
  - Read these files; never edit or import them (DEC-57).

## Docs move in lockstep with the code

Docs are part of every change. A commit that changes behaviour, structure, config, commands, status or a decision updates every affected doc **in the same commit**.

A doc that disagrees with the code is a bug. Fix it when you find it; don't defer it.

| When the change touches… | Update |
| --- | --- |
| what the wheel does, its scope, data, cache or results (a PO-approved change) | `docs/WHEEL-SPEC.md`, plus its WD entry |
| a decision, a PO answer, an engineering choice, or a probe result | `docs/DECISIONS.md` |
| pages, panels, tokens, charts, tables | `docs/UI-SPEC.md` |
| progress | `docs/BUILD-PLAN.md`: tick the item, update the status board |
| setup, commands, status, reproduction steps | `README.md` and the command table below |
| agent rules or conventions | this file |

## Working the backlog

- `docs/BUILD-PLAN.md` is the backlog. Take the first unchecked item whose **Needs** are all checked, unless the PO says otherwise.
- Ask its **Ask first** questions before building on them.
- Write tests first. An item is done when its **Done when** line holds and `just check` is green.
- One commit per backlog item, prefixed with its ID (`W2-01: accounting for puts and shares`). It includes the item's doc updates and its tick (`- [x] … — done YYYY-MM-DD`). **The PO makes the commit** (DEC-59): leave the work in the tree and hand over the file list and a proposed message.

## Environment

- The project runs from **Git Bash on Windows**, on the same machine as LSEG Workspace (DEC-02). CI runs on Ubuntu, and both must behave the same (DEC-58):
  - LF line endings everywhere (`.gitattributes`); code that writes files passes `newline="\n"`.
  - `pathlib` for paths; the `tzdata` package for time zones; just recipes under bash.
- Keep the project on a Windows path, never `\\wsl.localhost\…`.

## Hard rules

These are working rules, kept for the wheel (WD-01); a `DEC-nn` beside one is its origin in the archived PMCC log.

- **Git and GitHub (DEC-59):** the PO does all of it: repo setup, init, staging, commits, pushes, branches, tags, GitHub settings. You may run read-only git (`status`, `diff`, `log`, `show`, `ls-files`, `check-ignore`); never a git or gh command that changes the repo or GitHub.
- **Credentials:** never print, read out, copy or commit `lseg-data.config.json` (it's gitignored). Only `pmcc/data/lseg/` reads it.
- **LSEG access:**
  - Only `pmcc fetch` and `pmcc probe` contact LSEG. Tests, CI, builds and the site never do.
  - `lseg.data` and `pandas` are imported only under `pmcc/data/lseg/`.
  - Before any pull longer than about 2 minutes, show the PO the `--plan-only` estimate. Workspace must stay signed in throughout.
  - Never overwrite cached data. Never record a failed request as "no data": an outage aborts and writes nothing.
- **Strategies:**
  - Strategies see market data only through `MarketView`. No rule touches a dataframe.
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
| `just run SYM CONFIG` / `just batch` / `just calibrate [ARGS]` | backtests; `calibrate` sets each symbol's own starting cash, skipping final ones; `calibrate --check` recomputes it without writing |
| `just wheel SYM [--config PATH]` | the wheel on one symbol, from the cache only → `results/SYM/wheel.json` (W2-03), with its metrics, benchmarks and verdicts (W3-01); reads the symbol's `baseline_pmcc.json`, so run `just batch` first; `pmcc verify` checks it, `pmcc export` publishes it for the wheel's pages (W4-01) |
| `just wheels SYM` | the wheel and each friction run in `configs/wheel_friction/` (W3-02) |
| `just export` / `just verify` | site data / results validation |
| `just web-dev` / `just web-build` / `just e2e` / `just serve` | frontend (`web-dev` and `web-build` export first) |
| `just reproduce` | cached data → all runs (the PMCC's batch, the wheel and its friction runs on NVDA) → verify → export → built site |

## Conventions

- **Time:**
  - Timestamps are tz-aware America/New_York. Bars are keyed by their end time (`bar_end`), and every decision happens at a bar's end (DEC-06).
  - In the PMCC's rules, "Monday" means the week-open session (DEC-20); the wheel's spec says "the week's first session".
- **Logging:** log through `structlog.get_logger()` with dotted event names (ARCHITECTURE §15). Only `pmcc.cli` imports `pmcc.log` to configure it (DEC-80).
- **IDs:**
  - Wheel rule IDs match `docs/WHEEL-SPEC.md` exactly (`W-T1`, `W-P3`, `W-X2`, …); its invariants are `WINV-01`…`WINV-10` in the spec's order (WD-12). The PMCC keeps its own (`E-T1`, `G-3`, `INV-01`…).
- **Test names:** `test_<rule-or-inv>_<behaviour>`, e.g. `test_w_c3_never_sells_below_cost_basis`.
