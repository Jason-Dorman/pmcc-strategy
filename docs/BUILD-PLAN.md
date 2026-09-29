# PMCC Backtest — Build Plan and Backlog

Sep 25, 2026 · schedule from Spec › Build order · **due Fri Oct 9, 11:59 pm** · gradable baseline Wed Sep 30

## How to use this plan

- **Order.** Work phases in order and items top to bottom. An item starts when everything under **Needs** is checked. Parallel tracks are marked.
- **The PO answers questions just in time.**
  - When you pick up an item, put its **Ask first** questions to the PO in one message, each with the recommendation from [DECISIONS](DECISIONS.md). Build nothing that depends on them until the answers are in.
  - To avoid stalls, ask the next item's questions while you finish the current one.
  - Record every answer in DECISIONS.
  - Anything else that's unclear goes to the PO too; don't assume.
- **Done means:**
  - the **Done when** line is true
  - `just check` is green
  - every doc the work touched is updated in the same commit (lockstep; `CLAUDE.md` maps changes to docs)
  - the work is handed to the PO with a proposed commit message, and the PO commits it (DEC-59)
- **Ticking.** Tick the box in the same commit as the work, and append the date and anything notable, e.g. `- [x] **P3-04 · Accounting core** — done 2026-09-29; 3 scenarios added`.
- **Git and GitHub belong to the PO (DEC-59).** Wherever an item says commit, push, create the repo or change a GitHub setting, the PO does it. The agent prepares the files and the commit message, and may check results with read-only git.
- **Cutting.** Cut only per §5, and mark cut items `- [~] … — CUT <date>: <reason>`.
- **Tags:**
  - **[PO]:** needs a PO answer, review or sign-off.
  - **[Workspace]:** needs LSEG Workspace running and signed in on the PO's machine.

## 1. Status board

| Phase | Dates | Exit criteria (milestone) | Status |
| --- | --- | --- | --- |
| P0 Foundations | Sat Sep 26 | `just check` green in Git Bash and in CI; credentials ignored; LSEG session opens from Git Bash | Done locally 2026-09-25; CI run for P0-07/08 pending the PO's push |
| P1 Data layer and open items | Sat Sep 26 – Sun Sep 27 | NVDA's full chain cached; INV-11, INV-12 pass; window, r and identifiers recorded; universe fetch started | In progress: P1-01 to P1-08 done (window Mar 30 – Sep 25 2026, r = 0.0371, universe QQQ, NVDA, TSLA; cache and loader per DEC-46; `pmcc fetch` per DEC-88); P1-09 (NVDA's fetch, Workspace) next |
| P1-10 Universe fetch (background) | Sun Sep 27 – Sat Oct 3 | QQQ and TSLA cached with coverage summaries (NVDA at P1-09) | Not started |
| P2 Pricing | Mon Sep 28 | IV solver matches the reference; EM, ATM IV, RV20 tested | Not started |
| P3 Engine, accounting, baseline | Mon Sep 28 – Wed Sep 30 | **M1:** baseline blotter, ledger, NAV, Reg T for NVDA; INV-01–10 and 13 pass | Not started |
| P4 Quant layer and site skeleton | Thu Oct 1 – Fri Oct 2 | **M2:** quant + A1–A5 on NVDA; Pages serves the skeleton from sample JSON; INV-14, 15 in CI | Not started |
| P5 Universe batch and sensitivity | Sat Oct 3 – Sun Oct 4 | **M3:** all results JSON written and verified | Not started |
| P6 Analytics | Mon Oct 5 – Tue Oct 6 | **M4:** every table and series in results JSON | Not started |
| P7 Site pages and write-up | Wed Oct 7 – Thu Oct 8 | **M5:** CI builds and deploys after `pmcc export`; the site passes a full read-through | Not started |
| P8 Release | Fri Oct 9 | **M6:** URL submitted (target 18:00; deadline 23:59) | Not started |

## 2. Questions for the PO

Nothing needs answering up front. This is when each open question in [DECISIONS](DECISIONS.md) will come up, so the PO knows what's coming.

| Asked at | About | Questions |
| --- | --- | --- |
| P1-05 Open items · Sat Sep 26 | Probe results (DEC-06–14); confirm the window and r | DEC-07, DEC-11 |
| P1-06 Calendar · Sat Sep 26 | Monthly expiries and holidays | DEC-33 |
| P1-07 Cache · Sun Sep 27 | Cache file layout | DEC-46 |
| P1-08 Fetch · Mon Sep 28 | A strike step with no anchor; the coverage summary (asked when found) | DEC-14, DEC-16 |
| P2-01 Black-Scholes · Mon Sep 28 | Time and Greek units | DEC-24 |
| P2-03 Measures · Mon Sep 28 | Spot and close, ATM IV and EM, RV20 | DEC-23, DEC-25, DEC-26 |
| P2-04 Chain pricer · Mon Sep 28 | Greeks when IV fails; fresh quotes only | DEC-27 |
| P3-02 MarketView · Mon Sep 28 | Point-in-time listing | DEC-32 |
| P3-04 Accounting core · Mon Sep 28 | The short stock's margin after X-S5 while the long call is held (found at P1-05) | DEC-10 |
| P3-06 Rule modules · Tue Sep 29 | Tie-breaks | DEC-29 |
| P3-07 Engine loop · Tue Sep 29 | Order of operations, selection freeze, gate log, exits without quotes, rule stamping | DEC-20, DEC-21, DEC-22, DEC-28, DEC-34 |
| P3-08 Results · Wed Sep 30 | Test 13 vs the run timestamp; dirty-tree rule | DEC-50 |
| P3-09 Capital · Wed Sep 30 | Starting-capital calibration | DEC-30 |
| P3-10 Baseline on NVDA · Wed Sep 30 | LSEG terms, before real results go to the public repo | DEC-05 |
| P4-05 Export · Thu Oct 1 | Detail levels and report sections | DEC-54 |
| P4-06 Web scaffold · Thu Oct 1 | Light theme | DEC-03 |
| P5-02 Sensitivity · Sat Oct 3 | Entry-timing variant | DEC-31 |
| P6 start · Mon Oct 5 | Analytics definitions and the Greek display | DEC-60, DEC-61, DEC-62, DEC-63, DEC-64, DEC-76 |
| P7-01 Strategy page · Wed Oct 7 | Chart colour roles | DEC-04 |
| P7-06 Data page · Wed Oct 7 | What the local Data page shows | DEC-75 |

`ENG` entries in DECISIONS are engineering choices, recorded for visibility. The PO can overrule any of them at any time.

## 3. Timeline and critical path

```
              Sep26 Sep27 Sep28 Sep29 Sep30 Oct1 Oct2 Oct3 Oct4 Oct5 Oct6 Oct7 Oct8 Oct9
P0 foundations ██
P1 data        ██████
P1-10 fetch          ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    background; done by Oct 3
P2 pricing                 ██
P3 engine                  ████████████ M1
P4 quant + web                          ██████████ M2
P5 batch                                           ██████████ M3
P6 analytics                                                  ██████████ M4
P7 site                                                                  ██████████ M5
P8 release                                                                          ██ M6
```

- **Critical path:** P0-01 toolchain and LSEG access → P1-03 adapter → P1-04 probes → P1-05 window → P1-09 NVDA → P1-10 universe fetch → P5 batch → P6 → P7 → P8.
- **Parallel work:**
  - P2 and P3 build on synthetic data and NVDA while the universe downloads.
  - The web scaffold (P4-06) needs only the P3-08 result models.
  - Analytics (P6) can be written against NVDA results before the full batch lands.

## 4. Backlog

### P0 — Foundations · Sat Sep 26

- [x] **P0-01 · Toolchain and LSEG access from Git Bash** **[Workspace]** — done 2026-09-25; `open_state` prints `Opened` through `uv run`
  - Open the project in Git Bash on Windows, from a Windows path (not `\\wsl.localhost\…`), with `lseg-data.config.json` in the repo root (DEC-58).
  - Confirm git, gh, uv, and Node 22 LTS with npm are installed. Install `just` (`uv tool install rust-just`).
  - Done when: `curl -s http://localhost:9000/api/status` shows `ST_PROXY_READY`, and the LDG §4.2 `open_state` one-liner prints `Opened` (run through `uv run` once P0-03 exists).
  - Needs: P0-03 (for the `open_state` check) · Refs: DEC-02, DEC-58; LDG §4.2
  - Toolchain: git 2.31, gh 2.101, uv 0.12.19, just 1.58.0, Node 22.23.2 / npm 10.9.8 (Node 12 replaced via winget, PO choice).
- [x] **P0-02 · Repository and GitHub** **[PO]** — done 2026-09-25; verified with read-only git (16 files `i/lf`, credentials ignored and untracked, `main` = `origin/main`). Ticked with P0-03, since it could only be checked after the push
  - Agent: add `.gitattributes` (`* text=auto eol=lf`, `*.parquet binary`; DEC-58), review `.gitignore`, and give the PO the first-commit file list and message.
  - PO (DEC-59): `git init`, make the first commit (docs, reference files, `README.md`, `CLAUDE.md`, `.gitignore`, `.gitattributes`, and never the credentials), create the public repo, and push `main`.
  - PO: set the Pages source to GitHub Actions and turn on secret scanning push protection.
  - Agent: check the done-when lines with read-only git.
  - Done when:
    - `git check-ignore lseg-data.config.json` succeeds and `git ls-files` doesn't list it
    - `git ls-files --eol` shows `i/lf` for text files
    - `main` is pushed
  - Refs: LDG §1; DEC-56, DEC-58
- [x] **P0-03 · Python project** — done 2026-09-25; pandas pinned at 2.3.3, Python 3.12.14; checked on a fresh copy; CLI stubs exit 1 naming their backlog item
  - `pyproject.toml`, targeting Python 3.12:
    - Runtime deps: polars, pyarrow, numpy, scipy, pydantic, pyyaml, typer, structlog, tzdata, `lseg-data==2.1.1`, pandas (pinned).
    - Dev deps: pytest, hypothesis, ruff, pyright, pre-commit.
  - Also: `uv.lock`, `.python-version`, the package skeleton per ARCHITECTURE §3.1, the `typings/lseg/` stub, and a typer app with stubbed commands.
  - Done when:
    - a fresh clone runs `uv sync --frozen`
    - `uv run pmcc --help` lists fetch, probe, run, batch, calibrate, export, verify, serve
    - `uv run python -c "import lseg.data"` works
  - Refs: DEC-42, DEC-43
- [x] **P0-04 · Quality gates** — done 2026-09-25; ruff and pyright run through `uv run` (DEC-77); planted C901 and credentials file rejected via `pre-commit run --files`, then removed
  - ruff (lint and format; `C90` with max complexity 10).
  - pyright strict on `pmcc` and `tests`, with the reference files excluded (DEC-57).
  - pytest with hypothesis profiles and the no-network fixture.
  - `.pre-commit-config.yaml`: ruff, ruff-format, pyright, check-yaml, end-of-file-fixer, check-added-large-files, detect-private-key, and a local hook rejecting a staged `lseg-data.config.json`.
  - Done when: `uv run pre-commit run --all-files` passes, and a planted complexity-11 function and a staged fake credentials file are both rejected (then removed).
  - Needs: P0-03 · Refs: Spec › Stack; EP › Cyclomatic Complexity
- [x] **P0-05 · justfile** — done 2026-09-25; `just check` green in Git Bash (web steps skip until P4-06); added `test` and `fetch … *ARGS` (DEC-78)
  - `set shell := ["bash", "-cu"]` (DEC-58), plus the recipes in ARCHITECTURE §14. A recipe may be a stub until its phase.
  - Done when: `just --list` shows every recipe, and `just check` runs lint, type-check and tests in Git Bash.
  - Needs: P0-01, P0-04
- [x] **P0-06 · CI skeleton** — done 2026-09-25; `python` job plus a credentials guard; `pmcc verify` step deferred to P4-05 (DEC-79); green on GitHub confirmed by the PO on the PR run
  - `.github/workflows/ci.yml` `python` job on Ubuntu: setup-uv, `uv sync --frozen`, pre-commit on all files, pytest.
  - Done when: the workflow is green on GitHub.
  - Needs: P0-02, P0-05
- [x] **P0-07 · Logging and architecture test** — done 2026-09-25; `pmcc/log.py` (DEC-80), not yet wired into the command stubs; added import rule 7 (only `pmcc.cli` imports `pmcc.log`); planted `pandas` import in `pmcc/engine/` rejected, then removed
  - structlog JSON config (stderr and `logs/*.jsonl`).
  - `tests/architecture/test_imports.py` enforcing ARCHITECTURE §3.3.
  - Done when: the test passes, and fails on a planted forbidden import.
  - Needs: P0-04
- [x] **P0-08 · README check** — done 2026-09-25; fresh clone in Git Bash: `just setup` and `just check` green, usage commands match the CLI flags (stubs exit 1 naming their item). Fixed: status note, how to install just, Git Bash and Windows-path notes, Node needed only for `web/`, clone and `just check` steps added to Setup
  - The README was written on Sep 25. Check its requirements, setup and usage sections against the real toolchain, and fix anything that differs.
  - Done when: every README setup step works as written from a fresh clone in Git Bash.
  - Needs: P0-02, P0-05

### P1 — Data layer and open items · Sat Sep 26 – Sun Sep 27

- [x] **P1-01 · Domain primitives** — done 2026-09-25; `money`, `instruments`, `rules`, `clock`, `sessions` (DEC-81); session model follows the DEC-06 recommendation, pending the P1-04 probe
  - `pmcc/domain`: `Price`/`Money` (DEC-44), `OptionId`, `Right`, `Side`, `RuleId`, ET time helpers, and the session/bar model (DEC-06).
  - Done when: tests cover half-even quantization, money arithmetic, `bar_end`, and session-bar classification including half-days.
  - Needs: P0-04
- [x] **P1-02 · RIC builder and parser** — done 2026-09-26; `build_ric`, `parse_ric`, `forms_to_ask`, `occ_symbol` (DEC-82); the builder pads the day and the parser reads both spellings; DEC-01 settled by the PO from the earlier project's measurements, with the spec's RIC line and INV-11 amended; 92 tests, including hypothesis round-trips; an adversarial review's 2 confirmed and 7 plausible findings fixed (DEC-82)
  - `pmcc/data/ric.py`: build and parse both forms, the OCC symbol, the form policy (DEC-45), and day padding per DEC-01.
  - Done when: the INV-11 tests pass:
    - the spec's examples parse
    - the builder emits the verified spelling
    - a put's caret uses the call letter
    - a strike > $999.99 raises
    - live contracts get no caret
    - a hypothesis round-trip over random contracts holds
  - Needs: P1-01 · Refs: Spec › RIC builder; LDG §3
- [x] **P1-03 · Provider port and LSEG adapter** — done 2026-09-26; `HistoryProvider` and four failure classes in `pmcc/data/provider.py`; `lseg_session` and `LsegProvider` in `pmcc/data/lseg/`; batches, single-RIC verdicts and form rounds in `pmcc/data/fetch.py` (DEC-83). An adversarial review confirmed 9 findings (2 high: a dead or signed-out Workspace was filed as no data, and flat RIC columns could file one field's values under another) and rated 2 plausible; all are fixed, and errors are now classified by what lseg-data 2.1.1 really raises. The FakeProvider ports lseg-data's behaviour, and a contract test runs the real library offline to keep it true. 110 tests; 31 planted mutants killed across both rounds. LDG §4's adapter items (1–6, 8, 13) have FakeProvider tests, and TEST-STRATEGY §6 maps the rest to the items that build them. P1-04 checks the assumed error codes (DEC-83)
  - The `HistoryProvider` protocol and its failure classes (`pmcc/data/provider.py`).
  - `pmcc/data/lseg/`: a port of `lseg_session`, fail-soft history and the frame reader (into polars).
  - `pmcc/data/fetch.py`: 25-RIC batches, single-RIC verdicts, retries, caret→live fallback, and diagnostics. None of it depends on LSEG, so it sits outside the adapter (DEC-83).
  - `FakeProvider` (TEST-STRATEGY §6), kept true to lseg-data by a contract test.
  - Done when:
    - the INV-12 tests pass
    - every LDG §4 behaviour has a FakeProvider test
    - a closed session raises before any request
    - an outage writes nothing
  - Needs: P1-02 · Refs: DEC-49; LDG §4
- [x] **P1-04 · Probes** **[Workspace]** — done 2026-09-27; `pmcc probe` (`pmcc/data/probe/`, DEC-85) wrote one report per symbol to `data_cache/probes/` for all 12, about 100 requests and 100 s each, with no retries; outcomes are in DEC-06 to DEC-09, DEC-12 to DEC-14, DEC-47 and DEC-83. For P1-05: hourly history ends between Sep 26 and Oct 27 2025 (a rolling year?); start stamps and end-of-bar quotes are confirmed, but the official close isn't the close bar's last trade (R-21, DEC-23); XLE split 2-for-1 on Dec 5 2025 and LSEG's history is split-adjusted; long-leg median spreads exceed E-T1's 3% on 7 symbols. Both never-listed codes are no-data codes, and a field a RIC lacks isn't an error at all, so both fakes were corrected (DEC-83). An adversarial review (4 reviewers, 2 skeptics per finding) confirmed a high: a Workspace dying during the DEC-83 asks got a report written; now an outage (DEC-85). 68 tests, over a new port-level `FakeMarket`
  - `pmcc probe` implements the DEC-06, 07, 08, 09, 12, 13 and 14 checks. Run it for all 12 symbols; the requests are small. (DEC-01 was settled without a probe.)
  - It also records the real error answers for DEC-83: the `LDError` text and codes for a never-listed RIC (hourly and daily, both forms), a field the RIC doesn't carry, and an hourly batch holding one of each. The fake's assumed codes are then checked against them.
  - Done when: `data_cache/probes/` has a report per symbol, and each outcome is written into its DEC entry.
  - Needs: P0-01, P1-03
- [x] **P1-05 · Resolve the spec's open items** **[PO]** — done 2026-09-28. The PO confirmed the bar convention (DEC-06). They set the window to Mon Mar 30 – Fri Sep 25 2026, 26 weeks, the shortest of the three offered, and the spec's Universe line now names it (DEC-07). They took FRED DGS3MO for r, 3.73% on Mar 27, so r = 0.0371 (DEC-11), and the primary-listing stock RICs (DEC-12). `configs/universe.yaml` and its loader (`pmcc/config/universe.py`, DEC-86) come with 54 tests. An adversarial review (4 reviewers, 2 skeptics per finding) found 11 unique findings: 1 confirmed and 6 plausible, all fixed (six test gaps, plus DEC-13 back to VERIFY until the `.P` primaries' fields are seen), and 4 refuted. Then the PO cut the universe to QQQ, NVDA and TSLA for time (DEC-15), which dropped the `.P` RICs and settled DEC-13. Both config files are now read by a strict YAML reader that refuses a key given twice, and 30 planted mutants were all killed. A test runs the real fetch planner over the window, and `configs/calendar.yaml` covers every date it asks for, from the Feb 13 warm-up to the Jun 17 2027 monthly. Splits were checked against OCC: XLE's (Dec 5 2025) is the only one, before the window. The Reg T citations are found, and one finding contradicts the spec: X-S5's short stock, hedged by the long call, needs less margin than the spec's 150%/30%, so DEC-10 is asked at P3-04. The spec's open items: 4 resolved, and 3 with dated owners (DEC-05 at P3-10, DEC-08 at P1-10, DEC-10 at P3-04 and P7-04)
  - Report the probe results (DEC-06–14) to the PO.
  - Ask first: DEC-07 (window) and DEC-11 (r).
  - Start the Reg T citations (DEC-10, due by P7-04).
  - Fill in `configs/universe.yaml` (window, r, symbols with stock RICs and roots). `configs/calendar.yaml` came with P1-06 (2025–2027); check that it covers the window and the long legs' expiries.
  - Tick the spec's open-item boxes, each with its DEC link.
  - Done when: every open item is resolved or has a dated owner, and both config files validate.
  - Needs: P1-04
- [x] **P1-06 · Calendar and chain discovery** — done 2026-09-27; DEC-33 settled by the PO, taking all four recommendations, with the table widened to 2025–2027. Built: `SessionCalendar` (`pmcc/domain/calendar.py`, placed in `domain` because MarketView returns it, DEC-84); `configs/calendar.yaml` with its loader; the tape check, which stops on any mismatch; and `pmcc/data/discovery.py` (increments, integer-cent bands, `plan_symbol`). 97 tests, including a hypothesis ladder property. Changes to ARCHITECTURE §6.3 (DEC-48): a monthly counts as a candidate on every session and its unit ends at its expiry; after the adversarial review (DEC-84), the long band reaches the money in 3 separately probed bands (it had stopped near δ 0.75), and a window ending mid-week keeps its last week. The P1-04 probes then checked the table against LSEG's daily bars for all 12 symbols (DEC-33)
  - Ask first: DEC-33.
  - Sessions from the tape, week-open and week-final sessions, weekly and monthly expiries, increments (DEC-14), and the bands and fetch plan (DEC-48).
  - Done when tests pass for:
    - Thu Jul 2 2026 expiry (Jul 3 closed)
    - Tue Sep 8 2026 week-open (Labor Day)
    - Thu Jun 18 2026 weekly
    - the June 2027 monthly (Thu Jun 17)
    - integer-cent ladders and band formulas
    - tape holidays matching the table
  - Needs: P1-01
- [x] **P1-07 · Cache and loader** — done 2026-09-28. The PO settled DEC-46, taking all three recommendations: one parquet and sidecar per fetch unit (the spec's Cache line amended); a data-manifest hash that ignores fetch times and the RIC form; a re-pull by moving the unit's two files aside, with `manifest.json` rebuilt from the sidecars. Built: `pmcc/data/files.py` (never-overwrite writes, now also behind the probe report), `pmcc/data/cache.py` and `pmcc/data/load.py` (DEC-87). The loader checks each parquet's sha256 and the stock tape against the calendar, and quantizes prices exactly as `Price.from_dollars` does, vectorized. An adversarial review (4 reviewers, 2 skeptics per finding) confirmed 10 findings and rated 1 plausible, all fixed with 9 unverified lows: a unit renamed in place was read as the unit its sidecar records, a stale `.partial` blocked the next write, and test and doc gaps (DEC-87). 90 tests over FakeProvider pulls; 44 planted mutants killed. P1-08's unit loop sits above `fetch` and `cache`, since `cache` imports `fetch`'s result types (DEC-87)
  - Ask first: DEC-46.
  - Atomic writes, never overwriting, the manifest and sidecars, and the per-symbol content hash.
  - `load_symbol()`: polars, `bar_end`, session bars, quote validity.
  - Done when tests show:
    - an interrupted write leaves no file
    - an existing unit is skipped, never overwritten
    - answered + unanswered = requested, per contract
    - the hash ignores fetch times
    - the loader round-trips FakeProvider data
  - Needs: P1-03, P1-06
- [x] **P1-08 · `pmcc fetch`** — done 2026-09-28; `pmcc/data/pull.py` (`prepare`, `pull_units`, `measure_step`), `estimate.py`, `coverage.py` and the command (DEC-88). The PO answered three questions that came up: a band whose anchor doesn't answer tries the anchors $10 either side, then takes the probe report's step, flagged (DEC-14); the coverage summary leaves IV failures out until P2-04 and counts valid mids over every calendar session bar, and a merged monthly unit's near-money strikes over its weekly part only (DEC-16). The plan comes from the cached stock tape when there is one, cached units must match the plan, and the window's ends must be sessions. The done-when's resume and estimate-order tests run over `FakeMarket`, the port-level fake, not FakeProvider (TEST-STRATEGY §6): a Workspace dying at five points resumes to exactly the missing units, and the estimate (a low and a high figure) prints before the first option request. An adversarial review (4 reviewers, 2 skeptics per finding) confirmed 10 findings (a window ending on a weekend or holiday cached unmeasured steps; a stopped probe report crashed the command; a stale README note; 7 test gaps), rated 1 plausible (put to the PO) and refuted 1; all are fixed, with the 16 unverified lows. 77 new tests, 748 in the suite; 51 planted mutants killed (DEC-88)
  - Plan → estimate (units, RIC requests, minutes) → resumable unit loop → coverage summary; `--plan-only`.
  - Done when FakeProvider tests show:
    - a resume after a mid-run outage refetches only the missing units
    - the estimate prints before any option request (only the stock tape, which the plan is built from, comes first: ARCHITECTURE §6.1)
  - Needs: P1-07 · Refs: ARCHITECTURE §6.1
- [ ] **P1-09 · First symbol: NVDA** **[Workspace]**
  - Show the PO the `--plan-only` estimate, then fetch NVDA over the window.
  - Review the coverage and spot-check 5 rows against Workspace (LDG §7).
  - Done when:
    - NVDA's full chain is cached
    - near-the-money weekly mid availability is ≥ 90% (or the gap is explained)
    - INV-11 and INV-12 pass
  - **P1 exit.**
  - Needs: P1-05, P1-08
- [ ] **P1-10 · Universe fetch (background)** **[Workspace]**
  - Show the PO the estimate, fetch QQQ and TSLA, and re-run any failures.
  - Done when: all 3 (DEC-15) are cached with coverage summaries by **Sat Oct 3**, with any gaps recorded in DEC-08.
  - Needs: P1-09

### P2 — Pricing · Mon Sep 28

- [ ] **P2-01 · Black-Scholes and Greeks**
  - Ask first: DEC-24.
  - Vectorized call and put price, δ, Γ, θ and ν, with q = 0.
  - Done when: reference values match to 1e-8, and put–call parity and finite-difference Greek checks hold (hypothesis).
  - Needs: P1-01
- [ ] **P2-02 · Vectorized IV solver**
  - Newton with a bisection fallback, and failure codes per ARCHITECTURE §7.
  - Done when: it matches a scalar `brentq` reference on hypothesis inputs (|Δσ| < 1e-6 where solvable), and each failure code has a test.
  - Needs: P2-01
- [ ] **P2-03 · Measures**
  - Ask first: DEC-23, DEC-25, DEC-26.
  - EM, ATM strike and ATM IV, RV20, and extrinsic value.
  - Done when fixture tests pass, including:
    - a missing put quote leaves EM unavailable
    - RV20 uses only completed sessions
  - Needs: P2-02
- [ ] **P2-04 · Chain pricer**
  - Ask first: DEC-27.
  - Per-bar IV, Greeks and eligibility for a symbol; the held-contract rule; memoized.
  - Done when: NVDA's full window prices in under 10 s, and IV-failure counts appear in the coverage summary.
  - Needs: P2-03, P1-07

### P3 — Engine, accounting, baseline · Mon Sep 28 – Wed Sep 30

- [ ] **P3-01 · Config models and baseline config**
  - Pydantic models, the loader (`extends`, `overrides`), registry kinds, the config hash, and rule text (DEC-52, DEC-53).
  - `configs/_shared.yaml` and `configs/baseline_pmcc.yaml`, with every rule's name, condition, action and rationale. The spec's "why" paragraphs go into the X-S3, X-S5 and no-roll rationales.
  - Done when config tests pass: unique IDs, placeholders resolve, params referenced, every spec rule ID present.
  - Needs: P1-01
- [ ] **P3-02 · MarketView**
  - Ask first: DEC-32.
  - The as-of gate and the accessors (ARCHITECTURE §5.2), with point-in-time listing.
  - Done when the INV-04 tests pass:
    - every accessor raises `LookAheadError` for t > now
    - hypothesis finds no returned row after `now`
    - unlisted strikes stay hidden
  - Needs: P2-04
- [ ] **P3-03 · Synthetic market**
  - The generator and scenario builders (TEST-STRATEGY §5).
  - Done when: the same seed produces identical files, and each builder has a smoke test.
  - Needs: P1-07
- [ ] **P3-04 · Accounting core**
  - Ask first: DEC-10 (the short stock's margin after X-S5 while the long call is held).
  - Events, the book, marks with stale carry-forward, ledger rows, NAV, Reg T and flags (ARCHITECTURE §9).
  - Done when:
    - property tests for INV-01, 02, 08 and 10 pass over random sequences of fills, expiries, assignments and marks
    - an uncovered short raises `EngineError`
  - Needs: P1-01
- [ ] **P3-05 · Fill simulator**
  - ARCHITECTURE §8.3.
  - Done when:
    - the INV-03 tests pass
    - fills at `spread_capture` 0, 0.25 and 0.50 are exact in `Price` units
    - per-contract fees apply
  - Needs: P3-04
- [ ] **P3-06 · Baseline rule modules**
  - Ask first: DEC-29.
  - E-T1, E-L1–E-L4, E-S1–E-S5, G-1, G-2, X-S1–X-S5, X-L1, X-L2 and X-E1, with the baseline selectors and the registry.
  - Done when: every rule has boundary unit tests (TEST-STRATEGY §4).
  - Needs: P3-01, P3-02
- [ ] **P3-07 · Engine loop**
  - Ask first: DEC-20, DEC-21, DEC-22, DEC-28, DEC-34.
  - The bar loop and its order, the leg state machines, the gate log, rule stamping, and runtime invariants (ARCHITECTURE §8).
  - Done when: every TEST-STRATEGY §5 scenario passes, and runtime INV-01–10 hold on all of them.
  - Needs: P3-03, P3-05, P3-06
- [ ] **P3-08 · Result models and `pmcc run`**
  - Ask first: DEC-50.
  - Provisional result models, canonical JSON, and the run manifest.
  - Done when:
    - INV-13 passes on synthetic data (two runs, byte-identical once `run_timestamp` is dropped)
    - a dirty tree records `git_dirty: true`
  - Needs: P3-07
- [ ] **P3-09 · Provisional capital**
  - Ask first: DEC-30.
  - Run `pmcc calibrate` on the symbols cached so far, and label the value provisional in `universe.yaml`.
  - Done when: calibration is reproducible and records its basis.
  - Needs: P3-08
- [ ] **P3-10 · Baseline on NVDA** **[PO]**
  - Ask first: DEC-05, before real results go to the public repo.
  - Run on real data.
  - Hand-audit 3 weeks: blotter → ledger → raw quotes (TEST-STRATEGY §8).
  - Commit the results from a clean tree.
  - Done when: the baseline blotter, ledger, NAV and Reg T exist for NVDA, and INV-01–10 and 13 pass.
  - **M1: gradable baseline (Wed Sep 30).**
  - Needs: P1-09, P3-09

### P4 — Quant layer and site skeleton · Thu Oct 1 – Fri Oct 2

- [ ] **P4-01 · Quant selectors**
  - E-L2 (120–270 DTE), E-L3 (lowest extrinsic ÷ δ, tie-breaks per DEC-29), and E-S3 (lowest listed strike ≥ spot + k·EM).
  - Done when: boundary and tie-break tests pass.
  - Needs: P3-06
- [ ] **P4-02 · Gates G-3, G-4, G-5**
  - With gate-log values and `n/a` handling (DEC-22).
  - Done when: boundary tests pass, including missing next-week IV and missing RV20.
  - Needs: P4-01
- [ ] **P4-03 · Quant and ablation configs**
  - `configs/quant_pmcc.yaml` and `configs/ablations/a1…a5.yaml`.
  - Done when: a config-diff test shows each ablation differs from quant only in its named layer.
  - Needs: P4-02
- [ ] **P4-04 · Quant and A1–A5 on NVDA** **[PO]**
  - Run all six, then review gate fire counts, the exit mix and E-T1 retry counts with the PO.
  - Expect the quant long to favour the shortest eligible expiry (extrinsic grows with time), so X-L2 should roll every few weeks. If it doesn't, investigate.
  - Done when: all six runs pass the runtime invariants, and the review notes are in the done line.
  - Needs: P4-03, P3-10
- [ ] **P4-05 · Export and verify**
  - Ask first: DEC-54.
  - Final result models for every output (P6 sections may stay empty), JSON Schema, `index.json`, `rules.json`, and the `pmcc export` and `pmcc verify` commands (DEC-51). Add the `pmcc verify results/` step to the CI `python` job (DEC-79).
  - Done when: `pmcc verify` passes committed results and fails on hand-corrupted copies, one per re-derivable invariant.
  - Needs: P3-08
- [ ] **P4-06 · Web scaffold** *(parallel from Oct 1)*
  - Ask first: DEC-03.
  - Vite with React, TypeScript (strict), Tailwind and shadcn/ui (DEC-71); HashRouter and `base: './'` (DEC-73); tokens (DEC-70); self-hosted fonts (DEC-72).
  - Shell components (UI-SPEC §2), the data loader, and `gen:types`.
  - ESLint (complexity ≤ 10) and Vitest (token-lint, contrast).
  - Done when:
    - `npm run build` works from exported sample data
    - every route renders a placeholder
    - the token-lint and contrast tests pass
  - Needs: P4-05
- [ ] **P4-07 · Pages deploy**
  - The CI `web` and `deploy` jobs, with the dist guard (ARCHITECTURE §14).
  - Done when: the Pages URL serves the skeleton from synthetic sample results with the synthetic banner, and a deep link survives a refresh. Add the URL to the README.
  - Needs: P4-06, P0-06
- [ ] **P4-08 · Smoke test**
  - Playwright covers every route for one symbol:
    - no console errors
    - no cross-origin requests
    - the footer is present
    - screenshots at 390, 1100, 1366 and 1600 px, uploaded as CI artifacts
  - Done when: INV-14 and INV-15 run and pass in CI.
  - **M2 (Fri Oct 2).**
  - Needs: P4-07

### P5 — Universe batch and sensitivity · Sat Oct 3 – Sun Oct 4

- [ ] **P5-01 · Final capital**
  - Once the universe is cached (P1-10), run `pmcc calibrate` across the 3 symbols × 2 strategies and commit `starting_cash` with its basis (DEC-30).
  - Done when: `universe.yaml` has a non-provisional value.
  - Needs: P1-10, P4-03
- [ ] **P5-02 · Sensitivity variants**
  - Ask first: DEC-31.
  - `configs/sensitivity.yaml` → run IDs (ARCHITECTURE §11), plus the fixed-bar trigger.
  - Done when: the expanded matrix gives 24 run IDs per symbol, and the timing variants pass their unit tests.
  - Needs: P4-03
- [ ] **P5-03 · `pmcc batch`**
  - The run matrix in a process pool, with failure isolation, a summary, and the universe-level outputs.
  - Done when: a batch over 2 synthetic symbols writes all 48 run files plus the universe files, and exits non-zero when one run fails.
  - Needs: P5-02
- [ ] **P5-04 · Full batch**
  - Run the whole universe from a clean tree, then `pmcc verify`, then commit the results within the limits of DEC-05.
  - Done when: results JSON exists for every symbol and run.
  - **M3 (Sun Oct 4).**
  - Needs: P5-01, P5-03
- [ ] **P5-05 · Data completeness review**
  - Review band-edge flags (DEC-48), stale-mark rates, IV-failure rates and skip reasons.
  - Refetch wider where flagged, then re-run the affected symbols.
  - Done when: no band-edge flags remain, or each is explained in DEC-08.
  - Needs: P5-04

### P6 — Analytics · Mon Oct 5 – Tue Oct 6

**Ask first (one batch when P6 starts):** DEC-60, DEC-61, DEC-62, DEC-63, DEC-64, DEC-76. Every item then starts with hand-computed fixture tests.

- [ ] **P6-01 · Performance metrics** (DEC-60) — Needs: P5-03
- [ ] **P6-02 · Cycle statistics** (DEC-62) — Needs: P5-03
- [ ] **P6-03 · Leg attribution** (DEC-63) — Needs: P5-03
- [ ] **P6-04 · Greek attribution** (DEC-63, DEC-76) · *cut #3* — Needs: P6-03
- [ ] **P6-05 · Bootstrap CIs** — per symbol and strategy, plus the pooled week-block bootstrap, seeded (DEC-61) — Needs: P6-01
- [ ] **P6-06 · Robustness tables** — ablations; friction; timing dispersion (*cut #2*); the full parameter grid (*cut #1*) — Needs: P6-01
- [ ] **P6-07 · Fill-assumption check** — DEC-64, published in the form DEC-05 allows — Needs: P5-03
- [ ] **P6-08 · Suitability screen** — the spec's five point-in-time measures — Needs: P5-03
- [ ] **P6-09 · Re-run, verify, export**
  - Re-run the batch with analytics, run `pmcc verify`, and commit.
  - Done when: every table and series the site needs is in results JSON.
  - **M4 (Tue Oct 6).**
  - Needs: P6-01…P6-08

### P7 — Site pages and write-up · Wed Oct 7 – Thu Oct 8

- [ ] **P7-01 · Strategy page** — Ask first: DEC-04. UI-SPEC §6.2; one component tree for both strategies — Needs: P6-09
- [ ] **P7-02 · Comparison page** — UI-SPEC §6.1, including the purpose panel — Needs: P7-01
- [ ] **P7-03 · Trade rules page and traceability links** — UI-SPEC §6.3, §7 — Needs: P4-05
- [ ] **P7-04 · Methodology page** — UI-SPEC §6.4, with the Reg T citations (DEC-10) — Needs: P6-09
- [ ] **P7-05 · Universe page** — UI-SPEC §6.5 — Needs: P6-09
- [ ] **P7-06 · Data page** — Ask first: DEC-75. The github.io banner, plus the local mode if the PO wants it — Needs: P4-06
- [ ] **P7-07 · Themes and responsiveness**
  - The light theme (DEC-03) and the contrast test in both themes, with screenshots reviewed at 4 widths.
  - Done when: the contrast tests pass in both themes and the screenshots show no clipping or overlap.
  - Needs: P7-01…P7-06
- [ ] **P7-08 · Full read-through** **[PO]**
  - Every page, in both themes, at 4 widths: no placeholder text, every number traceable, the fix list closed.
  - Done when: CI builds and deploys after `pmcc export`, and the read-through passes.
  - **M5 (Thu Oct 8).**
  - Needs: P7-07

### P8 — Release · Fri Oct 9

- [ ] **P8-01 · Reproduce from a clean clone**
  - Clone, copy in the cache, run `just reproduce`.
  - Done when: the results are byte-identical to the committed ones (INV-13 on real data).
  - Needs: P7-08
- [ ] **P8-02 · Final deploy and live checks**
  - Done when:
    - `main` is green
    - the footer SHA matches the committed results
    - the site makes no cross-origin requests
    - the Data page shows "Data connection required" on github.io
  - Needs: P8-01
- [ ] **P8-03 · README final and tag**
  - Final README pass (status, site URL, reproduction steps), then tag `v1.0`.
  - Needs: P8-02
- [ ] **P8-04 · Submit** **[PO]**
  - Submit the URL: target 18:00, deadline 23:59.
  - **M6.**
  - Needs: P8-03

## 5. Cut list

The spec sets the order. Cut the next item only when its trigger fires, and mark it `[~]` in §4.

**Never cut:** the blotter, NAV, Reg T, the rules page, or the tests.

| Order | Cut | Trigger | Items affected |
| --- | --- | --- | --- |
| 1 | Parameter grid | M3 not reached by Sun Oct 4, 20:00 | P5-02 grid variants, P6-06 grid table |
| 2 | Entry-timing sensitivity | M4 not reached by Tue Oct 6, 12:00 | P5-02 timing variants, P6-06 timing table |
| 3 | Greek attribution | M4 not reached by Tue Oct 6, 20:00 | P6-04, the quant page's Greek panel |
| 4 | Universe size | — (taken early: the PO cut it from 12 symbols to QQQ, NVDA and TSLA on 2026-09-28, DEC-15) | P1-10, P5 |
| — | Data page local mode (keep the github.io banner) | P7 behind at Wed Oct 7 end of day | P7-06 |

## 6. Risks

| ID | Risk | Likelihood | Impact | Mitigation | Watch at |
| --- | --- | --- | --- | --- | --- |
| R-01 | Windows (Git Bash) and Ubuntu CI diverge: CRLF line endings, missing time-zone data, shell differences | Med | Med | DEC-58: `.gitattributes` LF, `tzdata`, `newline="\n"`, bash recipes; CI catches what slips through | P0-02, P0-05 |
| R-02 | Hourly option history is shorter than 10 weeks, or uneven across symbols | Med | High | Probe on day 1; window = the intersection; tell the PO at once. **P1-04:** hourly history ends between Sep 26 and Oct 27 2025, the same for every symbol sampled there (DEC-07). **Retired at P1-05:** the PO's window (Mar 30 – Sep 25 2026) and its warm-up sit 3½ months inside that edge | P1-04 |
| R-03 | Deep ITM long-dated quotes are sparse or wide: IV failures, few E-L3 candidates, E-T1 retries | Med | Med | Measure (DEC-08); report on Methodology; leave the rules unchanged. **P1-04 sample:** every bar quoted, but median spreads over E-T1's 3% on 7 symbols. **DEC-15:** the kept three have the tightest (QQQ 1.4%, NVDA 1.4%, TSLA 2.1%) | P1-09 |
| R-04 | Fetch volume and time; possible LSEG request limits | Med | High | Estimate first; resumable units; start Sep 27; run overnight; watch for throttling errors. **P1-05:** the 26-week window scales ARCHITECTURE §6.3's 11-week estimate by about 2.4 ; with the 3 symbols of DEC-15 that's roughly 2–2.5 h, and DEC-48's wider long bands add to it; P1-08's `--plan-only` prints the real figure first | P1-08, P1-10 |
| R-05 | The zero-padded RIC day, settled from the earlier project without a probe, stops resolving | Low | Med | The DEC-01 note: expiries dated the 1st–9th all come back unanswered; the spelling is set in one place, and the parser reads both | P1-04, P1-09 |
| R-06 | A strike above $999.99 doesn't fit the 5-digit field | Low | High | Probe the max strike per symbol; ask the PO. **P1-04:** all 12 fit; META is closest ($973.51, DEC-12) | P1-04 |
| R-07 | A split in the window changes the option root | Low | High | Check the tape for discontinuities and corporate actions. **P1-04:** LSEG's history is split-adjusted, so the tape can't show a split; XLE split 2-for-1 on Dec 5 2025 (DEC-12). Confirm the rest against OCC memos and pick the window with it in mind. **Retired at P1-05:** XLE's split is before the window and its warm-up; OCC's series search, issuer filings and news show no other event for the 12, and none announced before Oct 9 2026 (DEC-12) | P1-04, P1-05 |
| R-08 | A wrong bar convention hides look-ahead | Low | High | DEC-06 checks; MarketView keyed on `bar_end`. **P1-04:** start stamps and end-of-bar quotes confirmed on all 12 | P1-04 |
| R-09 | Float nondeterminism breaks INV-13 | Med | Med | Integer money, explicit sorts, seeded RNG, canonical JSON | P3-08 |
| R-10 | The schedule compresses | High | High | Cut list with triggers; parallel web track; M1 gate | status board |
| R-11 | LSEG terms forbid publishing raw-derived series | Med | Med | DEC-05 asked at P3-10; binned scatter as the fallback | P3-10, P6-07 |
| R-12 | pyright strict clashes with untyped libraries (lseg-data, scipy) | Med | Low | Local stubs; typed adapters; narrow ignores, each with a reason | P0-03 |
| R-13 | Results JSON is too heavy for the site | Low | Med | Detail levels (DEC-54); virtualized tables; per-run lazy loading | P4-05 |
| R-14 | Quant E-L3 favours wide-spread contracts, so E-T1 keeps failing | Med | Med | Report retry counts; no tuning after the first run (spec) | P4-04 |
| R-15 | Holiday and half-day edge cases | Med | Med | Calendar tests on known dates. **P1-06:** they pass, and the table matched LSEG's trading days for all 12 from Jan 2025 (DEC-33) | P1-06 |
| R-16 | The Workspace session drops mid-pull | Med | Med | A dead Workspace never changes the session's state (DEC-83), so failing requests are retried 3 times, then abort the unit as an outage; resume | P1-08 |
| R-17 | The Pages base path or routing breaks deep links | Low | Med | `base: './'` with HashRouter; deploy early (P4-07) | P4-07 |
| R-18 | Pulls need the PO's machine on and signed in to Workspace | High | Med | Schedule pulls with the PO; batch them overnight | P1-10 |
| R-19 | A late PO answer stalls the items that depend on it | Med | Med | Batch questions per item and ask one item ahead (§2) | §2 |
| R-20 | A guessed RIC fails with a code that isn't a no-data code, so the fetch stops as an outage | Med | Med | P1-04 records the real codes before any pull; widening the no-data codes is a DEC-83 decision. **Retired by P1-04:** both never-listed codes are no-data codes (DEC-83) | P1-04 |
| R-21 | The close bar's last trade differs from the official close (up to 0.09% in the probes), so a short pinned near its strike can be ITM by one and OTM by the other | Med | Med | DEC-23 (asked at P2-03) decides which close X-S4/X-S5 use; the probe numbers go with the question | P2-03 |
