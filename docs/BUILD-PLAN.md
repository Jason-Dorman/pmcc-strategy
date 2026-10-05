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
| P1 Data layer and open items | Sat Sep 26 – Sun Sep 27 | NVDA's full chain cached; INV-11, INV-12 pass; window, r and identifiers recorded; universe fetch started | Done 2026-09-28 (P1 exit): P1-01 to P1-09 (window Mar 30 – Sep 25 2026, r = 0.0371, universe QQQ, NVDA, TSLA; cache and loader per DEC-46; `pmcc fetch` per DEC-88; NVDA's chain cached, near-money weekly mids 97.7%) |
| P1-10 Universe fetch (background) | Sun Sep 27 – Sat Oct 3 | QQQ and TSLA cached with coverage summaries (NVDA at P1-09) | Estimates shown 2026-09-28 (QQQ 183–547 min, TSLA 98–293 min); the PO scheduled the pull overnight. Seen 2026-09-30: TSLA's pull stopped at 01:14 on Sep 29 with its 53 weekly units cached and none of its 9 monthlies (Oct 2026 – Jun 2027); QQQ not started. Re-running TSLA's fetch resumes at the first missing unit. **Paused 2026-09-30** (PO, DEC-15): QQQ and TSLA set aside, commented out of `configs/universe.yaml` at P5-01; more at the end if time allows. **Resuming means recalibrating first** (the PO asked to be reminded): delete the final starting-cash block, uncomment the symbol, fetch, `just calibrate`, re-run, then repeat P5-05's band-edge check (DEC-15, DEC-48) |
| P2 Pricing | Mon Sep 28 | IV solver matches the reference; EM, ATM IV, RV20 tested | Done 2026-09-28, as one commit (PO, DEC-59): Black-Scholes, T and DTE, the IV solver, measures and the chain pricer (DEC-24 to DEC-27 settled; DEC-89). NVDA prices in 1.4 s; IV failures 8.3%, mostly very deep ITM; DEC-26's missing-close rule is with the PO |
| P3 Engine, accounting, baseline | Mon Sep 28 – Wed Sep 30 | **M1:** baseline blotter, ledger, NAV, Reg T for NVDA; INV-01–10 and 13 pass | Done 2026-09-30 (**M1**): P3-01 done 2026-09-29 (DEC-35, DEC-90); P3-02 to P3-07 as one commit (DEC-91); P3-08 (`pmcc run`, DEC-50, DEC-92); P3-09 (starting cash $10,000, provisional, from NVDA; DEC-30, DEC-93); P3-10 (NVDA's baseline, $10,000 to $13,672.50, 35 trades; hand-audited; NVDA's raw cache committed per DEC-05; DEC-94). Next P4-01 |
| P4 Quant layer and site skeleton | Thu Oct 1 – Fri Oct 2 (done Wed Sep 30) | **M2:** quant + A1–A5 on NVDA; Pages serves the skeleton from the committed results (DEC-74); INV-14, 15 in CI | In progress: P4-01 to P4-03 done 2026-09-30 (quant selectors, gates G-3 to G-5, quant and ablation configs; DEC-95), with the G-5 finding, five rationales and the provisional starting cash ($15,000 with quant built) put to the PO; an adversarial review's 10 confirmed and 1 plausible findings fixed. P4-04 done 2026-09-30: starting cash $15,000, provisional (DEC-30); quant and A1–A5 on NVDA run, reviewed with the PO and committed with the baseline re-run (DEC-95). P4-05 and P4-06 done 2026-09-30 (DEC-96, DEC-97; the PO answered DEC-03: no light theme, and DEC-54's summary: analytics null until P6); NVDA's seven results re-run at schema 2 from `69c01b2` and verified (DEC-59's two commits). P4-07 done 2026-09-30: the site is live at <https://jason-dorman.github.io/pmcc-strategy/>, checked in Chromium (DEC-98). P4-08 done 2026-09-30: the Playwright smoke test (11 tests) passes in CI's web job before every deploy (DEC-99). **M2 reached 2026-09-30.** |
| P5 Universe batch and sensitivity | Sat Oct 3 – Sun Oct 4 | **M3:** all results JSON written and verified | Done 2026-10-01 (**M3**): P5-01 to P5-03 done 2026-09-30, as one commit (PO). The universe is NVDA alone for now, QQQ and TSLA commented out (PO, DEC-15), so the starting cash is final at $15,000 (DEC-30). `configs/sensitivity.yaml` gives 24 runs per symbol (DEC-31 settled: the fixed-bar trigger). `pmcc batch` runs them one process per symbol and writes each symbol's `coverage.json`; the universe files wait for P6 (PO, DEC-100). NVDA's 24 runs take about 18 s. P5-04 done 2026-10-01: the full batch from a clean tree at `bcb6bbe`, 24 runs and `coverage.json` verified (DEC-100). **M3 reached 2026-10-01.** P5-05 done 2026-10-01: no pick on a band edge, nothing refetched or re-run; the guard stays a by-hand review (PO, DEC-48; DEC-08). **P5 done 2026-10-01.** Next P6, after its DEC-60 to DEC-64 and DEC-76 questions |
| P6 Analytics | Mon Oct 5 – Tue Oct 6 (done Thu Oct 1) | **M4:** every table and series in results JSON | Done 2026-10-01: the PO answered the P6 batch on 2026-10-01, every question as recommended (DEC-60 to DEC-65, DEC-76). P6-01, P6-02, P6-05 and P6-06 done 2026-10-01 (DEC-101): every run's summary carries its performance metrics, cycle statistics and weekly-return CI, a full run its cycles; the batch writes each symbol's `robustness.json` and the universe's `headline.json` and `pooled.json`. On NVDA from the uncommitted tree, every P&L matches P5-04's, and premium captured is negative for both strategies (X-S2 stop-losses). The committed results are unchanged until P6-09 re-runs them. An adversarial review (4 reviewers, 2 skeptics per finding): 8 findings confirmed and 1 plausible, all fixed, with the 7 unverified ones; 2,023 tests. P6-03 and P6-04 done 2026-10-01 (DEC-63, DEC-102): a full run's file keeps its leg attribution, and quant's its Greek attribution; the engine now records each bar's spot, each held leg's IV and Greeks, and each option fill's IV. On NVDA the legs add up to each strategy's P&L; quant's long residual is 20.6% of its change. An adversarial review (4 reviewers, 2 skeptics per finding): 7 findings confirmed and 2 plausible, all fixed, none changing a published number; 2,057 tests. P6-07 done 2026-10-01 (DEC-64, DEC-103): each symbol's `fill_check.json` with every print/mid pair and the fits, and the universe's `pooled_fill_check.json`. On NVDA both groups fit with R² above 0.999, but a short's median print is half a spread from the mid, a long's a third, while 21.7% of shorts' prints and 32.2% of longs' lie outside the quote. NVDA's file is 3.9 MB, past the 2 MB results guard, so fill checks get their own 8 MB limit (put to the PO). An adversarial review (4 reviewers, 2 skeptics per finding): 9 findings confirmed and 1 plausible, all fixed, none changing the code's output; 2,084 tests. P6-08 done 2026-10-01 (DEC-66, DEC-104): the PO set the screen's sample, contracts, credit and G-3 count, all as recommended; the batch writes `universe/suitability.json`. On NVDA every measure reads all 26 weeks: the long's extrinsic per delta 3.05% of spot, median spreads 2.48% (long) and 2.07% (short), credit 1.65% of the long a week, IV ÷ RV20 1.12, G-3 2 fires. An adversarial review (4 reviewers, 2 skeptics per finding): 5 findings confirmed and 3 plausible, all fixed, none changing the code's output; 2,108 tests. P6-09 done 2026-10-01 (DEC-105): the batch re-run from a clean tree at `217f676` with every analytic, 24 runs and 8 analytics files in 39 s, all verified; nothing the engine wrote moved but `git_sha` and `run_timestamp`. Every UI-SPEC §6 panel maps to a results field; when timing dispersion is fragile is put to the PO for P7-04 (DEC-67). **M4 reached 2026-10-01** |
| P7 Site pages and write-up | Wed Oct 7 – Thu Oct 8 | **M5:** CI builds and deploys after `pmcc export`; the site passes a full read-through | In progress: P7-01 done 2026-10-01 (the strategy page; DEC-04 answered as recommended; DEC-106), the gate log's Selected column put to the PO. P7-02 done 2026-10-02 (the comparison page, with DEC-109's limit sentence; DEC-110), the sentence's wording for a run that doesn't bear it out put to the PO; return on capital deployed dropped for an annualized Sharpe (DEC-111), the results re-run and verified. P7-03 done 2026-10-03 (the Trade rules page, from `rules.json`, which gains each param as its text shows it and each run's family; DEC-112), the rule tables grow to their rows and no rule ID shows in the copy (PO, DEC-113; the results re-run at `f1d5855` and verified; then the page in plain words, DEC-114, the exits' merged column put to the PO, the results re-run at `882f32f` and verified). P7-04 done 2026-10-04 (the Methodology page, DEC-67 recorded as recommended; DEC-115; then the limits first and three panels dropped, PO, DEC-116), the half-width robustness tables put to the PO. P7-05 done 2026-10-04 (the Universe page; DEC-117). Next P7-06 (DEC-75, asked at P7-05's handover) |
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
| P2 review · Tue Sep 29 | RV20 when one of the 21 closes is missing | DEC-26 |
| P3-01 Config · Tue Sep 29 | Rule rationales and the no-roll paragraph (asked when found) | DEC-35 |
| P3-02 MarketView · Mon Sep 28 | Point-in-time listing (answered at P3-01) | DEC-32 |
| P3-04 Accounting core · Mon Sep 28 | The short stock's margin after X-S5 while the long call is held (found at P1-05) | DEC-10 |
| P3-06 Rule modules · Tue Sep 29 | Tie-breaks | DEC-29 |
| P3-07 Engine loop · Tue Sep 29 | Order of operations, selection freeze, gate log, exits without quotes, rule stamping; asked while building: rules without a delta, when the long is checked, the stock's mark and closing spot | DEC-20, DEC-21, DEC-22, DEC-23, DEC-27, DEC-28, DEC-34 |
| P3-07 handover · Wed Sep 30 | X-S3 without an EM at entry; a short entry blocked by funds; the stock's first mark after X-S5 | DEC-91 |
| P3-08 Results · Wed Sep 30 | Test 13 vs the run timestamp; dirty-tree rule | DEC-50 |
| P3-09 Capital · Wed Sep 30 | Starting-capital calibration | DEC-30 |
| P3-10 Baseline on NVDA · Wed Sep 30 | LSEG terms, before real results go to the public repo | DEC-05 |
| P4-01 to P4-03 handover · Wed Sep 30 | G-5 fires only on a locked quote (E-T1's 10% needs a mid ≥ $0.10); the five quant rationales the spec doesn't give; the provisional starting cash, $15,000 with quant built against the committed $10,000 (found by the review) | DEC-95, DEC-30 |
| P4-05 Export · Wed Sep 30 | Detail levels and report sections (answered at P4-04's handover); the summary's analytics until P6 | DEC-54 |
| P4-06 Web scaffold · Wed Sep 30 | Light theme (answered: none) | DEC-03 |
| P5-01 Final capital · Wed Sep 30 | The universe: NVDA alone, QQQ and TSLA commented out | DEC-15, DEC-30 |
| P5-02 Sensitivity · Wed Sep 30 | Entry-timing variant | DEC-31 |
| P5-03 Batch · Wed Sep 30 | The universe files before P6; `coverage.json` now (asked when found) | DEC-100 |
| P6 start · Mon Oct 5 | Analytics definitions and the Greek display (answered 2026-10-01: all as recommended, with two cycle details and the robustness tables' references, DEC-65) | DEC-60, DEC-61, DEC-62, DEC-63, DEC-64, DEC-65, DEC-76 |
| P6-08 Suitability · Thu Oct 1 | The screen's sample bar, contracts, credit pricing and G-3 count (asked when found; answered 2026-10-01, all as recommended) | DEC-66 |
| P7-01 Strategy page · Wed Oct 7 | Chart colour roles (answered 2026-10-01: as recommended); the gate log's Selected column (asked at the handover) | DEC-04, DEC-106 |
| P7-02 Comparison · Fri Oct 2 | The limit sentence's wording where a run doesn't bear out "the long call riding a rising stock" (asked at the handover) | DEC-110 |
| P7-03 Trade rules · Sat Oct 3 | Whether the rule tables keep UI-SPEC §5's 420 px cap (asked at the handover; answered 2026-10-03: as recommended) | DEC-112 |
| P7-04 Methodology · Sun Oct 4 | When timing dispersion is flagged as fragility (found at P6-09; answered 2026-10-03: as recommended); whether Friction and Entry timing span the full width (asked at the handover) | DEC-67, DEC-115 |
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
- [x] **P1-09 · First symbol: NVDA** **[Workspace]** — done 2026-09-28. The PO saw the estimate (2,263 to 6,789 requests, 52 to 155 min); the pull took 40 min over 63 units, with one connection reset recovered on its retry. Near-the-money weekly mids 97.7%; the other 2.2% are live quotes with a zero bid. The PO spot-checked 5 rows in Workspace (stock, a Good Friday week's call, an Independence Day week's put, and two deep ITM monthlies, one the Juneteenth-shifted Jun 17 2027). INV-11 and INV-12 pass. DEC-08 is measured in full for NVDA: every session bar has an in-band long candidate with a valid mid, and every contract quotes on every bar once listed (median spread 1.52%, none below the no-IV floor). The one gap is listing: Feb and Apr 2027 were listed partway through the window and May 2027 not at all, and its unit is cached empty (evidence for DEC-32). DEC-14's steps were measured on 83 of 86 bands; R-05 is retired
  - Show the PO the `--plan-only` estimate, then fetch NVDA over the window.
  - Review the coverage and spot-check 5 rows against Workspace (LDG §7).
  - Done when:
    - NVDA's full chain is cached
    - near-the-money weekly mid availability is ≥ 90% (or the gap is explained)
    - INV-11 and INV-12 pass
  - **P1 exit.**
  - Needs: P1-05, P1-08
- [ ] **P1-10 · Universe fetch (background)** **[Workspace]** — paused 2026-09-30 (PO, DEC-15): taken up at the end if time allows; TSLA's partial cache stays local, uncommitted
  - Show the PO the estimate, fetch QQQ and TSLA, and re-run any failures.
  - Done when: all 3 (DEC-15) are cached with coverage summaries by **Sat Oct 3**, with any gaps recorded in DEC-08. (Paused: NVDA alone for now, QQQ and TSLA commented out at P5-01. Resuming starts with the recalibration steps in DEC-15.)
  - Needs: P1-09

### P2 — Pricing · Mon Sep 28

- [x] **P2-01 · Black-Scholes and Greeks** — done 2026-09-28; `pmcc/pricing/black_scholes.py` and `expiry.py`. The PO took DEC-24 as recommended: T is ACT/365 to the expiry session's close, and δ, Γ, θ, ν are per $1, per $1², per year and per 1.00 of vol. Reference values (mpmath, 50 digits; Hull 15.6 to 4 dp) match to 1e-8, and parity and the finite-difference Greeks hold. A test across the Nov 1 clock change caught T an hour short (Python subtracts same-zone times by wall clock); T is now measured in UTC. P2 went in as one commit (PO, DEC-59)
  - Ask first: DEC-24.
  - Vectorized call and put price, δ, Γ, θ and ν, with q = 0.
  - Done when: reference values match to 1e-8, and put–call parity and finite-difference Greek checks hold (hypothesis).
  - Needs: P1-01
- [x] **P2-02 · Vectorized IV solver** — done 2026-09-28; `pmcc/pricing/iv.py`. Safeguarded Newton from Manaster and Koehler's start; |Δσ| < 1e-6 against `brentq` where the mid pins the vol down. The price tolerance is 1e-9·max(1, mid), not ARCHITECTURE's 1e-6, which couldn't give that on deep ITM calls. It adds a code, `NO_SPOT`, and checks `NO_QUOTE` first so an IV failure always means a quoted contract (DEC-89)
  - Newton with a bisection fallback, and failure codes per ARCHITECTURE §7.
  - Done when: it matches a scalar `brentq` reference on hypothesis inputs (|Δσ| < 1e-6 where solvable), and each failure code has a test.
  - Needs: P2-01
- [x] **P2-03 · Measures** — done 2026-09-28; `pmcc/pricing/measures.py` and `pmcc/domain/quotes.py` (`Quote`). The PO took DEC-23, DEC-25 and DEC-26 as recommended: the close is the close bar's last trade (R-21's gap goes on Methodology); ATM is the nearest listed strike, the lower on a tie; ATM IV is the call's; EM is call mid + put mid, unavailable without both; RV20 is from the 21 closes before the current session, unavailable if one is missing
  - Ask first: DEC-23, DEC-25, DEC-26.
  - EM, ATM strike and ATM IV, RV20, and extrinsic value.
  - Done when fixture tests pass, including:
    - a missing put quote leaves EM unavailable
    - RV20 uses only completed sessions
  - Needs: P2-02
- [x] **P2-04 · Chain pricer** — done 2026-09-28; `pmcc/pricing/chain.py` (`price_quotes`, `price_symbol` → `PricedSymbol`). The PO took DEC-27 as recommended: a call below its floor gets δ = 1, Γ = ν = 0, θ = −r·K·e^(−rT) and stays ineligible; fresh-quotes-only is P3's. NVDA's full window (400,784 session contract-bars) prices in 1.4 s. The coverage summary counts IV failures (DEC-16): 8.3% on NVDA: 31,966 below the floor (83% at K/S ≤ 0.6, none in the long band) and 437 no convergence (deep ITM calls within a week of expiry). NVDA's empty May 2027 unit crashed the first version; fixed with a test. Left for P3-06/P3-07: what X-S2 and X-L1 do when a held call's IV fails another way, including on its expiry close bar (DEC-27). An adversarial review (4 reviewers, 2 skeptics per finding) confirmed 10 findings (6 test gaps, 2 wrong NVDA figures, ARCHITECTURE §5.2 out of step with the measures, a held short with no delta on its expiry close bar), rated 1 plausible (a naive time keyed by the machine's zone) and refuted 1; all are fixed, with the 6 unverified lows, and DEC-26's missing-close rule went to the PO. 110 new tests, 858 in the suite; the reviewers' 14 surviving mutants are killed (DEC-89)
  - Ask first: DEC-27.
  - Per-bar IV, Greeks and eligibility for a symbol; the held-contract rule; memoized.
  - Done when: NVDA's full window prices in under 10 s, and IV-failure counts appear in the coverage summary.
  - Needs: P2-03, P1-07

### P3 — Engine, accounting, baseline · Mon Sep 28 – Wed Sep 30

- [x] **P3-01 · Config models and baseline config** — done 2026-09-29; `pmcc/config/` (`kinds.py`, `extends.py`, `rule_text.py`, `strategy.py`, `fields.py`), `configs/_shared.yaml` and `configs/baseline_pmcc.yaml`, 286 tests. All 26 kinds are registered, the quant ones too. The rules variants may remove are G-3, G-4, G-5 and X-S1. The fill model sits beside the rules. The config hash covers the strategy, window and r, not the symbol list (DEC-90). The PO settled the rationales: from the spec in the PO's words, with the no-roll paragraph on all five short exits (DEC-35). 28 mutants, all killed after two test fixes and one redundant check removed. An adversarial review found 8 confirmed and 3 plausible findings: ruff errors in the untracked files, a wrong E-S2 rationale, test gaps. All are fixed, with 41 more mutants killed (DEC-90)
  - Pydantic models, the loader (`extends`, `overrides`), registry kinds, the config hash, and rule text (DEC-52, DEC-53).
  - `configs/_shared.yaml` and `configs/baseline_pmcc.yaml`, with every rule's name, condition, action and rationale. The spec's "why" paragraphs go into the X-S3, X-S5 and no-roll rationales.
  - Done when config tests pass: unique IDs, placeholders resolve, params referenced, every spec rule ID present.
  - Needs: P1-01
- [x] **P3-02 · MarketView** — done 2026-09-30, built with P3-03 to P3-07 in one pass and one commit (PO, DEC-59). The PO settled DEC-32 as recommended: listed once it has had a valid quote. `pmcc/strategy/ports.py` (the protocol) and `pmcc/engine/market_view.py` (`MarketData`, `HistoricalView`). Every accessor takes an `at` through one `_as_of` gate. `PricedQuotes` now carries the integer BID and ASK. INV-04's hypothesis test compares every answer against a market cut off at `now` (DEC-91)
  - Ask first: DEC-32.
  - The as-of gate and the accessors (ARCHITECTURE §5.2), with point-in-time listing.
  - Done when the INV-04 tests pass:
    - every accessor raises `LookAheadError` for t > now
    - hypothesis finds no returned row after `now`
    - unlisted strikes stay hidden
  - Needs: P2-04
- [x] **P3-03 · Synthetic market** — done 2026-09-30; `tests/fixtures/synthetic/` (`market.py`, `scenarios.py` with 19 builder functions and 25 `BUILDERS` entries, `store.py` and the session-scoped `synthetic` fixture). The same seed writes byte-identical files, and each builder has a smoke test. Found while tuning: at one IV for both legs, E-S5 fails every week (a 0.80-delta 180-DTE long's extrinsic beats a 0.30-delta weekly's distance plus premium), so the scenario markets price monthlies at 20% and weeklies at 40% (DEC-91)
  - The generator and scenario builders (TEST-STRATEGY §5).
  - Done when: the same seed produces identical files, and each builder has a smoke test.
  - Needs: P1-07
- [x] **P3-04 · Accounting core** — done 2026-09-30. The PO settled DEC-10: while the long is held, X-S5's short stock carries the hedged requirement (no initial beyond the proceeds; maintenance 10% of the long strikes plus their OTM amount, capped), and the spec's NAV and Reg T table is amended. `pmcc/accounting/` (`events`, `book`, `marks`, `valuation`, `regt`, `ledger`) and `pmcc/domain/errors.py`. The property tests for INV-01, 02, 08 and 10 reach every path: 14% of examples assign and cover (DEC-91)
  - Ask first: DEC-10 (the short stock's margin after X-S5 while the long call is held).
  - Events, the book, marks with stale carry-forward, ledger rows, NAV, Reg T and flags (ARCHITECTURE §9).
  - Done when:
    - property tests for INV-01, 02, 08 and 10 pass over random sequences of fills, expiries, assignments and marks
    - an uncovered short raises `EngineError`
  - Needs: P1-01
- [x] **P3-05 · Fill simulator** — done 2026-09-30; `pmcc/engine/fills.py`: exact rationals, rounded half-even once, so capture 0 fills at the Limit; the fee applies per option contract; the audit carries BID, ASK and the capture (DEC-91)
  - ARCHITECTURE §8.3.
  - Done when:
    - the INV-03 tests pass
    - fills at `spread_capture` 0, 0.25 and 0.50 are exact in `Price` units
    - per-contract fees apply
  - Needs: P3-04
- [x] **P3-06 · Baseline rule modules** — done 2026-09-30. The PO settled DEC-29 as recommended; delta distances are rounded to 9 places, since 0.85 and 0.75 aren't equally far from 0.80 in floating point (a unit test caught it). `pmcc/strategy/` (`selectors`, `trigger`, `gates`, `exits`, `registry`); boundary tests for every rule on a stub view (`tests/fakes/view.py`). The quant kinds raise `NotBuiltError` naming P4-01/P4-02. The PO settled DEC-27's open item: a rule missing a delta doesn't fire and is logged (DEC-91)
  - Ask first: DEC-29.
  - E-T1, E-L1–E-L4, E-S1–E-S5, G-1, G-2, X-S1–X-S5, X-L1, X-L2 and X-E1, with the baseline selectors and the registry.
  - Done when: every rule has boundary unit tests (TEST-STRATEGY §4).
  - Needs: P3-01, P3-02
- [x] **P3-07 · Engine loop** — done 2026-09-30. The PO settled DEC-20, 21, 22, 28 and 34 as recommended, plus three questions found while building: the long is checked at the first week-open bar with a fresh long quote and the short waits for it (DEC-28); the stock is marked at its mid, and the closing spot falls back to the session's last trade (DEC-23). `pmcc/engine/` (`legs.py`, `loop.py`, `invariants.py`). 42 scenario runs; the runtime INV-01 to INV-10 hold on every bar. G-3 to G-5's engine scenarios wait for P4-02 (its done-when names them). Three edge cases went to the PO at handover (DEC-91). An adversarial review (4 reviewers, 2 skeptics per finding) confirmed 11 findings and rated 1 plausible, all fixed with the 7 unverified lows: entry notes now carry DEC-34's values, E-T1 is a port again (DEC-31), a listed strike with no row stays in the chain (DEC-32), and new scenarios pin the freezes, the check-once and the reset rows. 259 new tests, 1,403 in the suite
  - Ask first: DEC-20, DEC-21, DEC-22, DEC-28, DEC-34.
  - The bar loop and its order, the leg state machines, the gate log, rule stamping, and runtime invariants (ARCHITECTURE §8).
  - Done when: every TEST-STRATEGY §5 scenario passes, and runtime INV-01–10 hold on all of them.
  - Needs: P3-03, P3-05, P3-06
- [x] **P3-08 · Result models and `pmcc run`** — done 2026-09-30. The PO settled DEC-50 as recommended: canonical JSON, INV-13 without `run_timestamp`, and a dirty tree (tracked or untracked changes outside `results/`) runs but records `git_dirty: true`; `pmcc verify` rejects it at P4-05. The spec's Run manifest and invariant 13 now say so. The PO also answered part of DEC-30: `pmcc run` takes the starting cash only from `configs/universe.yaml` and stops, naming P3-09, until it's set. `pmcc/export/` (`canonical`, `models`, `manifest`, `results`) and `pmcc/runner.py`. The blotter names each contract by the RIC its cache answered with. INV-13 runs `random_walk` in two fresh processes with different hash seeds. A full result is about 0.5 MB, so `results/` gets a 2 MB large-file limit (DEC-92). 78 new tests, 1,481 in the suite. An adversarial review (4 reviewers, 2 skeptics per finding) confirmed 11 findings and refuted 1; all 11 and the 7 unverified lows are fixed. The PO settled three questions it raised: INV-13 also drops `git_sha` (DEC-50), `pmcc run` refuses a window its cache doesn't cover, and dollars in audit and gate values are exact 4-dp strings (DEC-92). 112 new tests in all, 1,515 in the suite
  - Ask first: DEC-50.
  - Provisional result models, canonical JSON, and the run manifest.
  - Done when:
    - INV-13 passes on synthetic data (two runs, byte-identical once `run_timestamp` and `git_sha` are dropped; DEC-50)
    - a dirty tree records `git_dirty: true`
  - Needs: P3-07
- [x] **P3-09 · Provisional capital** — done 2026-09-30. The PO settled DEC-30 as recommended and narrowed it to NVDA for now: 2 × the most expensive first long-leg cost, rounded up to $5,000. The PO noted that the starting cash must cover the entries and a $1,000,000 balance would skew NAV, so $1,000,000 is only the measuring runs' cash; each run is then repeated at the value, and calibration fails if E-L4 blocks any entry. `pmcc calibrate` (`pmcc/calibration.py`, `pmcc/config/capital.py`, DEC-93) wrote **$10,000, provisional**, into `configs/universe.yaml`: NVDA's first entry is the Sep 18 2026 $135 call on Mar 30 at $4,142.50; its later entries ($5,125.00, $5,032.50) are covered. `--check` recomputes the block byte for byte; `pmcc run` notes a provisional value. An adversarial review (4 reviewers, 2 skeptics per finding) confirmed 6 findings and rated 6 plausible, all fixed with the 3 unverified lows; 21 planted mutants killed. The PO settled the three it raised: the 2× and $5,000 are now E-L4's YAML params, stated in E-L4's text; negative available funds are reported, not refused (NVDA: lowest $4,978.50, none below zero); a partial-cache check waits for P5-01 (DEC-30, DEC-93). 76 more tests, 1,591 in the suite
  - Ask first: DEC-30.
  - Run `pmcc calibrate` on the symbols cached so far, and label the value provisional in `universe.yaml`.
  - Done when: calibration is reproducible and records its basis.
  - Needs: P3-08
- [x] **P3-10 · Baseline on NVDA** **[PO]** — done 2026-09-30 (**M1**). The PO settled DEC-05: every derived output is public, the fill-assumption scatter's raw points included, and the raw cache is committed, NVDA's alone for now, with QQQ and TSLA set aside (P1-10 paused, DEC-15). `.gitignore` keeps `data_cache/NVDA/` (7.1 MB, 127 files) and ignores the rest; no hook rewrites the cache, which gets a 2 MB large-file limit. `results/NVDA/baseline_pmcc.json` was run from a clean tree at `de368fd` (`git_dirty: false`): $10,000 to $13,672.50 over 26 weeks, 35 trades (3 long buys, 2 X-L2 rolls, 15 shorts closed by X-S1 9 times and X-S2 6 times), G-2 skipping 11 weeks, lowest available funds $4,978.50. The runtime INV-01–10 held, and INV-13 held on real data (a second run, another hash seed, byte-identical but for the volatile fields). An independent script hand-audited 4 weeks (Mar 30, Apr 6, Apr 20, Jun 22) from the raw parquet: 122 checks, 0 discrepancies (DEC-94). The PO restated that every fill is at the mid and kept P5's friction runs as sensitivity. 13 new tests, 1,604 in the suite
  - Ask first: DEC-05, before real results go to the public repo.
  - Run on real data.
  - Hand-audit 3 weeks: blotter → ledger → raw quotes (TEST-STRATEGY §8).
  - Commit the results from a clean tree.
  - Done when: the baseline blotter, ledger, NAV and Reg T exist for NVDA, and INV-01–10 and 13 pass.
  - **M1: gradable baseline (Wed Sep 30).**
  - Needs: P1-09, P3-09

### P4 — Quant layer and site skeleton · Thu Oct 1 – Fri Oct 2

- [x] **P4-01 · Quant selectors** — done 2026-09-30. `DteRangeExpiry`, `CheapestReplacement` and `ExpectedMoveStrike` in `pmcc/strategy/selectors.py`, with DEC-29's quant ties; extrinsic ÷ delta, and each delta compared with the band's edges, rounded to 9 places; E-S3's threshold exact in units. E-S3 takes the lowest *eligible* strike at or above spot + k × EM (DEC-21). EM, ATM IV and RV20 are read through the MarketView in the new `pmcc/strategy/measures.py`, which the engine's X-S3 EM now shares. NVDA's baseline result is unchanged byte for byte (DEC-95)
  - E-L2 (120–270 DTE), E-L3 (lowest extrinsic ÷ δ, tie-breaks per DEC-29), and E-S3 (lowest listed strike ≥ spot + k·EM).
  - Done when: boundary and tie-break tests pass.
  - Needs: P3-06
- [x] **P4-02 · Gates G-3, G-4, G-5** — done 2026-09-30. `EventRatioGate`, `VrpGate` and `MinPremiumGate`, each `n/a` with its reason when an input is missing. Each fires in a quant run on its market and skips week 1 (`tests/scenario/test_scenario_quant.py`); `next_week_unquoted` (new) shows G-3 `n/a` in a full run. `tiny_premium` was rebuilt around a locked quote: with penny quotes, E-T1's 10% needs a mid of at least $0.10, so G-5 can fire only when BID = ASK, and otherwise G-1 skips the week first. Put to the PO (DEC-95)
  - With gate-log values and `n/a` handling (DEC-22).
  - Done when: boundary tests pass, including missing next-week IV and missing RV20, and each gate fires in a full engine run on its synthetic market (`event_week`, `rv_above_iv`, `tiny_premium`, built at P3-03; TEST-STRATEGY §4, §5), with the gate log recording it (deferred from P3-07, DEC-91).
  - Needs: P4-01
- [x] **P4-03 · Quant and ablation configs** — done 2026-09-30. `configs/quant_pmcc.yaml` and `configs/ablations/a1.yaml` to `a5.yaml`. The config-diff test holds each ablation to its layer, and A1's and A2's rules to the baseline's word for word (`tests/unit/config/test_quant_config.py`). Names, gate conditions and G-3's rationale are the spec's; five rationales the spec doesn't give (E-L2, E-L3, E-S3, G-4, G-5) are with the PO. `NotBuiltError` is gone, and `pmcc calibrate` defaults to both strategies. An adversarial review (4 reviewers, 2 skeptics per finding) confirmed 10 findings and rated 1 plausible, all fixed: the tie order, the score and ratio rounding, EM's neighbour and E-S3's ceiling now pinned by tests; ratios compared at the 6 places results print; two rationales cut back to the spec; the harness runs an ablation with overrides; the starting cash went to the PO. 1,732 tests in the suite (11 from the review) (DEC-95)
  - `configs/quant_pmcc.yaml` and `configs/ablations/a1…a5.yaml`.
  - Done when: a config-diff test shows each ablation differs from quant only in its named layer.
  - Needs: P4-02
- [x] **P4-04 · Quant and A1–A5 on NVDA** **[PO]** — done 2026-09-30. The PO took the three P4-01 to P4-03 handover recommendations (DEC-95): the starting cash recalibrated to $15,000, provisional (DEC-30), committed first so the runs are clean; G-5 kept as specified, its rationale disclosing the locked-quote interaction; the five rationales approved. `results/NVDA/` holds the baseline (re-run at $15,000: the same 35 trades, NAV +$5,000) and quant and A1–A5, all run from a clean tree at `90753bb` (`git_dirty: false`); every run held the runtime INV-01–10, and INV-13 held on quant (a second process, another hash seed). Review notes, end NAV from $15,000 (short-leg net): baseline $18,672.50 (−$490.00), quant $18,303.50 (−$1,651.50), A1 $18,597.50, A2 $18,381.00, A3 $18,426.50, A4 $18,049.00, A5 $18,373.50. **Gates** (first to fire; quant): G-4 11, G-2 5, G-3 2 of 26 weeks, 8 shorts sold; G-4 fires 13 times in all, 4 of them at a ratio of 0.96–0.997; G-1 and G-5 never fire (lowest decision-bar mid $0.315). **Exit mix** (quant): X-S1 4, X-S2 4; A4 (no G-4) sells 19 shorts (X-S1 11, X-S2 7, X-S3 1); A5 lets 4 expire (X-S4). **E-T1 retries:** no short retry in any run (all 26 weeks decide on the first bar); two one-bar long retries (May 26 and Jul 20 10:00, spreads 3.81% and 3.18% against 3%); no cross-session retry, so R-14 didn't occur. **The long rolls as expected:** each quant pick is the shortest monthly at or above 120 DTE (144, 143, 123, 144 DTE), at δ 0.89–0.90, the top of the band, and X-L2 rolls it after 8, 8 and 5 weeks (3 rolls; the baseline 2). Quant's long made about $790 more than the baseline's (A1), and its short lost about $1,160 more; G-2 fires 5 weeks in June–July as the ~$61 long's net debit exceeds the strike gap. Found for P5-05: NVDA's May 2027 monthly returned no data for every strike (270 DTE on Aug 24; not a pick, since extrinsic grows with time) (DEC-95). 1 new test, 1,733 in the suite
  - Run all six, then review gate fire counts, the exit mix and E-T1 retry counts with the PO.
  - Expect the quant long to favour the shortest eligible expiry (extrinsic grows with time), so X-L2 should roll every few weeks. If it doesn't, investigate.
  - Done when: all six runs pass the runtime invariants, and the review notes are in the done line.
  - Needs: P4-03, P3-10
- [x] **P4-05 · Export and verify** — done 2026-09-30. The PO settled DEC-54 as recommended, with the summary's analytics null until P6. Each strategy YAML has a `report` block: baseline and quant keep full detail, the ablations a summary (about 23 KB against 430 KB). Results are at schema version 2. Every output has its model (`pmcc/export/`); the P6 sections are null. `pmcc verify` checks layout, schema, canonical bytes, the manifest, a clean tree, the config hash, the rule text and the recorded invariants, and re-derives INV-01, 02, 03, 05, 06, 07, 08, 09 and 10 from a full run's rows with its own arithmetic. CI runs it after pytest (DEC-79). `pmcc export` writes a schema per model, the results files, `index.json` and `rules.json`; the last two are derived at export, not committed. NVDA's seven results were re-run from `69c01b2` (the code commit, DEC-59): the baseline's and quant's blotter, ledger and gate log are byte-identical to P4-04's, and `pmcc verify results/` passes all 7. `tests/scenario/test_verify.py` fails a hand-corrupted copy on each re-derivable invariant, and on nothing else (DEC-96). 99 new tests, 1,832 in the suite. An adversarial review of P4-05 and P4-06 (4 reviewers, 2 skeptics per finding) confirmed 7 findings and rated 5 plausible; all 12 are fixed, with the clear ones of the 22 left unverified: the worst, export's directory guard, could have deleted any directory holding a `schema/` folder; verify now judges rows by what they do and reconciles the ledger's positions; `report` is no longer inherited (DEC-54, DEC-96). 1,872 tests after the review
  - Ask first: DEC-54.
  - Final result models for every output (P6 sections may stay empty), JSON Schema, `index.json`, `rules.json`, and the `pmcc export` and `pmcc verify` commands (DEC-51). Add the `pmcc verify results/` step to the CI `python` job (DEC-79).
  - Done when: `pmcc verify` passes committed results and fails on hand-corrupted copies, one per re-derivable invariant.
  - Needs: P3-08
- [x] **P4-06 · Web scaffold** *(parallel from Oct 1)* — done 2026-09-30. The PO answered DEC-03: no light theme, the look identical to `DESIGN-GUIDE.md` and `theme.py` (spec amended). The PO approved the packages listed in DEC-97. `web/` holds:
  - `tokens.css` with `theme.py`'s values and `shell.css` porting `PAGE_CSS`, with self-hosted fonts;
  - `gen:types` from the exported schema, the loader with its schema-version check, and HashRouter routes;
  - every page as a placeholder of its UI-SPEC panels, the strategy page choosing its sections from the run's `report`, and the manifest footer.

  `npm run build` builds from NVDA's exported results. Vitest runs 111 tests: token lint, contrast, formatters, the loader and every route. ESLint holds complexity to 10. Screenshots at 1500, 1366 and 390 px (the 390 in an iframe, since headless Edge lays out no narrower than 496) caught the nav overflowing a phone; it now wraps (DEC-97). The review's fixes add the Data page, banner, symbol and footer tests, hold `tokens.css` to `theme.py`, switch Tailwind's own palette off and widen the token lint: 151 Vitest tests
  - Ask first: DEC-03.
  - Vite with React, TypeScript (strict), Tailwind and shadcn/ui (DEC-71); HashRouter and `base: './'` (DEC-73); tokens (DEC-70); self-hosted fonts (DEC-72).
  - Shell components (UI-SPEC §2), the data loader, and `gen:types`.
  - ESLint (complexity ≤ 10) and Vitest (token-lint, contrast).
  - Done when:
    - `npm run build` works from exported sample data
    - every route renders a placeholder
    - the token-lint and contrast tests pass
  - Needs: P4-05
- [x] **P4-07 · Pages deploy** — done 2026-09-30. The CI `web` and `deploy` jobs and the dist guard (`web/scripts/dist-guard.mjs`) (DEC-98); the PO's push of `c040e13` deployed <https://jason-dorman.github.io/pmcc-strategy/>, checked live on 2026-09-30 in Chromium: `#/quant/NVDA` survives a reload, the pages show the committed NVDA results (the gate log's 26 weeks, the footer's commit `69c01b2`, source `lseg`) with no synthetic banner, no console error and no request to another origin, and the Data page says "Data connection required." on github.io. The PO chose the real results over a synthetic sample (DEC-74)
  - The CI `web` and `deploy` jobs, with the dist guard (ARCHITECTURE §14).
  - Done when: the Pages URL serves the skeleton from the committed results (real NVDA, so no synthetic banner; PO, DEC-74), and a deep link survives a refresh. Add the URL to the README.
  - Needs: P4-06, P0-06
- [x] **P4-08 · Smoke test** — done 2026-09-30. `web/e2e/smoke.spec.ts`, 11 tests over the built site (DEC-99); it found the footer wasn't a landmark (fixed). In CI: the PO's push of `2dc3aa2` deployed, and Pages deploys only after the `python` and `web` jobs pass, the `web` job running INV-14's typecheck and INV-15's smoke test before the upload; the live site carries that commit's footer (a `contentinfo` landmark outside `main`, checked in Chromium on 2026-09-30). **M2 reached**
  - Playwright covers every route for one symbol:
    - no console errors
    - no cross-origin requests
    - the footer is present
    - screenshots at 390, 1100, 1366 and 1600 px, uploaded as CI artifacts
  - Done when: INV-14 and INV-15 run and pass in CI.
  - **M2 (Fri Oct 2).**
  - Needs: P4-07

### P5 — Universe batch and sensitivity · Sat Oct 3 – Sun Oct 4

- [x] **P5-01 · Final capital** — done 2026-09-30. The PO kept the universe to NVDA for now: QQQ and TSLA stay in `configs/universe.yaml`, commented out, and bringing either back means recalibrating (DEC-15; Spec › Universe amended). With nothing missing, `just calibrate` wrote the block final: $15,000, from the same first entries (baseline $4,142.50, quant $5,630.00), no entry blocked, lowest available funds $9,978.50 and $8,330.00; `--check` reproduces it (DEC-30). The DEC-93 partial-cache question is set aside with QQQ and TSLA. 1 new test
  - Once the universe is cached (P1-10), run `pmcc calibrate` across the 3 symbols × 2 strategies and commit `starting_cash` with its basis (DEC-30). It replaces the provisional block.
  - First, decide with the PO how calibrate (and `pmcc run`) treat a cache missing option units its fetch plan asks for: today calibrate fails with an engine error, or could pass on a run that never re-entered (DEC-93, deferred by the PO at P3-09).
  - Done when: `universe.yaml` has a non-provisional value.
  - Needs: P1-10, P4-03 (P1-10 waived by the PO's DEC-15 answer: NVDA alone, so no other symbol to cache)
- [x] **P5-02 · Sensitivity variants** — done 2026-09-30. The PO took DEC-31 as recommended. `configs/sensitivity.yaml` holds 17 variants (friction 4, timing 7, grid 6), each extending a strategy and changing only what its check varies; `pmcc/config/matrix.py` adds them after the strategies and ablations, 24 run IDs in §11's order. The kind `fixed_bar_trigger` and `FixedBarTrigger` decide the short on one session bar only; the loop is unchanged (DEC-100). 56 new tests
  - Ask first: DEC-31.
  - `configs/sensitivity.yaml` → run IDs (ARCHITECTURE §11), plus the fixed-bar trigger.
  - Done when: the expanded matrix gives 24 run IDs per symbol, and the timing variants pass their unit tests.
  - Needs: P4-03
- [x] **P5-03 · `pmcc batch`** — done 2026-09-30. `pmcc/batch.py`: one spawned process per symbol, failure isolation per run and per symbol, a printed summary, each symbol's `coverage.json` (PO), and the universe-level stage, which writes nothing until P6 (PO, DEC-100). Two synthetic symbols write 48 runs and two coverage files that pass `pmcc verify`, a batch run matches `pmcc run` byte for byte, and a missing symbol exits 1 with the rest written. On NVDA, 24 runs in about 18 s; the seven committed runs came out identical but for the volatile fields. 11 new tests, and a suite-wide guard against tests writing into the repo (DEC-100). An adversarial review (4 reviewers, 2 skeptics per finding): 12 findings confirmed, all fixed, with the cheap unverified ones (DEC-100)
  - The run matrix in a process pool, with failure isolation, a summary, and the universe-level outputs.
  - Done when: a batch over 2 synthetic symbols writes all 48 run files plus each symbol's `coverage.json`, and exits non-zero when one run fails. The universe files join at P6-01, P6-05 and P6-08 (PO, DEC-100).
  - Needs: P5-02
- [x] **P5-04 · Full batch** — done 2026-10-01. `just batch` from a clean tree at `bcb6bbe`: NVDA's 24 runs and `coverage.json`, all `git_dirty: false`, in 30 s; `just verify` passed all 25 files. The seven committed runs are identical but for `run_timestamp` and `git_sha`, and every run's data hash is the committed cache's, so NVDA's raw cache (DEC-05) goes with them unchanged. Review notes in DEC-100: t1 reproduces the baseline exactly; end NAV from $15,000 runs $17,788.00 (t3) to $19,332.50 (t6). **M3 reached 2026-10-01**
  - Run the whole universe from a clean tree, then `pmcc verify`, then commit the results with each symbol's raw cache (DEC-05).
  - Done when: results JSON exists for every symbol and run.
  - **M3 (Sun Oct 4).**
  - Needs: P5-01, P5-03
- [x] **P5-05 · Data completeness review** — done 2026-10-01. No pick in NVDA's 24 runs is on the top or bottom strike requested: shorts at least 7 strikes inside, longs 10. Every pick quoted on its bar, so nothing is refetched and nothing re-run. The stale-mark rate is 0 (A5's 16 stale shorts are its X-S4 expiry days). No IV failure hides a pickable contract: around the short picks all are below the floor, in the money. No G-1 or G-5 skip; the unanswered contracts are strikes not yet listed. The PO kept the guard a by-hand review, repeated when a symbol is added (DEC-48). Recorded in DEC-08
  - Review band-edge flags (DEC-48), stale-mark rates, IV-failure rates and skip reasons.
  - Refetch wider where flagged, then re-run the affected symbols.
  - Done when: no band-edge flags remain, or each is explained in DEC-08.
  - Needs: P5-04

### P6 — Analytics · Mon Oct 5 – Tue Oct 6

**Ask first (one batch when P6 starts):** DEC-60, DEC-61, DEC-62, DEC-63, DEC-64, DEC-76; answered 2026-10-01, all as recommended, with DEC-65 for the robustness tables. Every item then starts with hand-computed fixture tests.

- [x] **P6-01 · Performance metrics** (DEC-60) — done 2026-10-01. `pmcc/analytics/performance.py`: session closes, daily and weekly returns, P&L, return on starting NAV and on the dearest long, drawdown on every bar, time underwater, unannualized Sharpe and Sortino. The runner gives every run its analytics (`analyze`), whatever its detail; the seed travels beside the starting cash, so no config hash moves. The batch's universe stage writes `universe/headline.json`. Analytics builds export's models, so export never imports analytics (import rule 5). 20 tests worked by hand, plus reconciliation on the synthetic market (DEC-101) — Needs: P5-03
- [x] **P6-02 · Cycle statistics** (DEC-62) — done 2026-10-01. `pmcc/analytics/cycles.py`: one cycle per week with its NAV change, credit and buyback net of fees, the long's cost and exit rule; win rate, payoff, premium captured (credit-weighted, PO) and credit as a share of the long's cost over the weeks they need; the exit mix and skips by rule. A full run's file keeps its cycles. 18 tests (DEC-101) — Needs: P5-03
- [x] **P6-03 · Leg attribution** (DEC-63) — done 2026-10-01. `pmcc/analytics/attribution.py`: credits − buybacks net of fees, X-S5's stock apart, the long's P&L split into its intrinsic change (each long's max(0, S − K) from entry bar to exit bar) and the rest, and both legs at each session's close. The legs must add up to the run's P&L, to the $0.0001, or the run raises. Every full run's file keeps it. 11 tests worked by hand, plus reconciliation on the synthetic market (DEC-63, DEC-102) — Needs: P5-03
- [x] **P6-04 · Greek attribution** (DEC-63, DEC-76) · *cut #3* — done 2026-10-01, not cut. `pmcc/analytics/greek_attribution.py`: each held bar priced by δΔS + ½Γ(ΔS)² + θΔt + νΔσ from the previous bar's Greeks, the residual exact, wholly residual bars counted per leg; the cumulative residual at every bar. The engine now records each bar's spot, each held leg's IV and Greeks, and each option fill's IV (DEC-102). Only quant's file keeps it (`report.sections`). On NVDA's quant run the long's residual is 20.6% of its change, 25 of its 872 bars below the floor (DEC-63). 22 tests (DEC-102) — Needs: P6-03
- [x] **P6-05 · Bootstrap CIs** — per symbol and strategy, plus the pooled week-block bootstrap, seeded (DEC-61) — done 2026-10-01. `pmcc/analytics/bootstrap.py`: one function over a week × symbol table, 10,000 resamples of whole weeks from a fresh PCG64, a 95% percentile CI; `bootstrap: {seed: 535}` in `configs/universe.yaml`. Every run gets its CI; the batch writes `universe/pooled.json`. 8 tests, among them a plain-Python oracle over the same draws (DEC-101) — Needs: P6-01
- [x] **P6-06 · Robustness tables** — ablations; friction; timing dispersion (*cut #2*); the full parameter grid (*cut #1*) — done 2026-10-01. `pmcc/analytics/robustness.py` (DEC-65): each family against the strategy it varies, the reference's row first; timing dispersion over the fixed bars alone. `configs/sensitivity.yaml` is now three lists, which decide each run's table. Each symbol's worker writes `{SYM}/robustness.json` once every run has succeeded. 9 tests, and the file rebuilt from the written results in the batch test (DEC-101) — Needs: P6-01
- [x] **P6-07 · Fill-assumption check** — DEC-64, publishing the raw scatter points (DEC-05) — done 2026-10-01. `pmcc/data/fillcheck.py` pairs every call print in the window with its bar's end-of-bar mid: shorts over each weekly's dates, longs before them, a merged monthly's strikes split by band. `pmcc/analytics/fillcheck.py` fits trade on mid exactly (slope, intercept, R², N, the median gap as a share of the spread, locked quotes). Each symbol's worker writes `{SYM}/fill_check.json` (every pair, as columns of mid, trade and spread), and the universe stage `universe/pooled_fill_check.json`. On NVDA: shorts 46,874 pairs, R² 0.9992, median gap 0.50 of a spread; longs 124,723, R² 0.9997, 0.32. The file is 3.9 MB, so fill checks get their own 8 MB guard (put to the PO). An adversarial review (4 reviewers, 2 skeptics per finding): 9 findings confirmed and 1 plausible, all fixed, among them a wrong figure in DEC-64. 27 tests, 2,084 in the suite (DEC-64, DEC-103) — Needs: P5-03
- [x] **P6-08 · Suitability screen** — the spec's five point-in-time measures — done 2026-10-01. The PO set what the spec left open, all as recommended (DEC-66): one reading a week, at the first bar of each week-open session, from quant's picks (E-L3's long, E-S3's short), the credit as the short's bid ÷ the long's mid, IV ÷ RV20 as G-4's ratio, G-3 checked every week at quant's threshold. `pmcc/analytics/suitability.py` reads each week through the `MarketView` and summarizes the symbol, each measure with its weeks; each symbol's worker hands its row back and the universe stage writes `universe/suitability.json`. On NVDA, all 26 weeks: extrinsic per delta 3.05% of spot, median spreads 2.48% and 2.07%, credit 1.65% of the long a week, IV ÷ RV20 1.12, G-3 fires 2 of 26 (the two weeks quant's gate log has). An adversarial review (4 reviewers, 2 skeptics per finding): 5 findings confirmed and 3 plausible, all fixed, none changing the code's output. 24 tests, 2,108 in the suite (DEC-66, DEC-104) — Needs: P5-03
- [x] **P6-09 · Re-run, verify, export** — done 2026-10-01. `just batch` from a clean tree at `217f676`: NVDA's 24 runs with their analytics, `coverage.json`, `robustness.json`, `fill_check.json` and the universe's four files, in 39 s, every run `git_dirty: false`; `just verify` passed all 31 files and `just export` wrote them with `index.json` and `rules.json`. Against P5-04's runs nothing moved but `git_sha` and `run_timestamp`: the analytics, cycles, attribution and fills' IVs are new, and every NVDA figure P6 quoted from the uncommitted tree is the committed one. Each UI-SPEC §6 panel is mapped to its field (DEC-105); P7-01 reads ending NAV and min available funds from the ledger. The spec's "fragility" has no threshold, so it goes to the PO at P7-04 (DEC-67). **M4 reached 2026-10-01**
  - Re-run the batch with analytics, run `pmcc verify`, and commit.
  - Done when: every table and series the site needs is in results JSON.
  - **M4 (Tue Oct 6).**
  - Needs: P6-01…P6-08

### P7 — Site pages and write-up · Wed Oct 7 – Thu Oct 8

- [x] **P7-01 · Strategy page** — Ask first: DEC-04 (answered 2026-10-01: as recommended, with `@tanstack/react-virtual` approved). UI-SPEC §6.2; one component tree for both strategies — Needs: P6-09 — done 2026-10-01. The baseline and quant pages render every panel from the committed NVDA results: the readouts, the account chart (NAV, IM, MM; available funds below), Reg T with its breach warning, cycle statistics with linked skips and exits, leg attribution with its chart, the blotter, gate log and ledger (sortable, toggle filters, the ledger and blotter virtualized) and, on quant, the Greek attribution with its residual line. ECharts and TanStack Table (v9) and Virtual join the site; DEC-04's roles are tokens. The gate log's Selected column shows the option, not a RIC: put to the PO (DEC-106). An adversarial review (4 reviewers, 2 skeptics per finding): 8 findings confirmed and 4 plausible, all fixed, with the 12 unverified low ones (week labels overlapping at narrow widths, missing values sorting first, test gaps). The PO then had every rule on the page say what it did, not its rule ID: the filter buttons, the blotter's Rule column, the gate log's gate headers and outcomes, and cycle statistics' skips and exits, each still linked to its rule (DEC-107); and the blotter shows each close's round-trip Trade P&L, so a take profit's buyback no longer reads as a loss (DEC-108). 124 new Vitest tests (287); the smoke test checks both pages, the week labels, the ledger's scrolling and an early sort on the built site (15 pass)
- [x] **P7-02 · Comparison page** — UI-SPEC §6.1, including the purpose panel and its sentence on the result's main limit (DEC-109) — Needs: P7-01 — done 2026-10-02. The landing page renders every panel from the committed NVDA results: the readouts (quant +$3,303.50, the baseline +$3,672.50, −$369.00 between them), the purpose with its limit sentence read from both runs' leg attribution (the long +$4,955.00 and +$4,162.50, the shorts −$1,651.50 and −$490.00), the NAV comparison with its values by bar, the headline, the pooled universe (`universe/pooled.json`) and the ablations (`robustness.json`). The loader now caches any results file, and a symbol's or the universe's file is found by its key in the index; `RobustnessTable` is ready for P7-04. The sentence claims the long rode a rising stock only where every run shows it: its wording otherwise is put to the PO (DEC-110). The PO then dropped return on capital deployed for an institutional reader: return on starting NAV is the headline return, beside an annualized Sharpe on excess returns (DEC-111, schema version 3; the results re-run at `9cd5dbf`: Sharpe 1.24 baseline, 1.11 quant). 30 new Vitest tests (317); the smoke test checks the page on the built site (16 pass)
- [x] **P7-03 · Trade rules page and traceability links** — UI-SPEC §6.3, §7 — Needs: P4-05 — done 2026-10-03. The rules page renders from `rules.json` alone: how rules work (the order of operations, how the strategies differ, the rules named and linked), the entry rules, gates and exits with both strategies side by side (Quant reads Same where it runs the baseline's rule; a gate On with its threshold as the rule's text shows it), each rule's rationale under a toggle, the ablations (layer removed → replaced by) and the sensitivity runs (what each changes, filtered by check). `rules.json` gains each param as its text shows it and each run's family, read from the robustness tables (DEC-112). Arriving at `#/rules/<ID>` outlines that row and scrolls to it; the blotter, gate log and cycle statistics already linked there (P7-01). The PO had the three rule tables grow to their rows, the other tables keeping the 420 px cap (DEC-112), and every rule named, never by its ID, in the page's copy and in the rule text and run names in `configs/`, the spec's pinned cells to match (DEC-113); the results re-run from a clean tree at `f1d5855` and verified. The PO then had the page rewritten in plain words: each rule's title and summary as its row and its reasoning under the Why toggle, from new config fields, in the tables as they were; the results' schema goes to 4, re-run from a clean tree at `882f32f` and verified, no figure moved (DEC-114). 28 new Vitest tests and 6 for `DataTable` (352), 62 pytest (2,172; 48 of them DEC-113's guard over the matrix); the smoke test follows a gate-log link to its outlined row and checks the page (18 pass)
- [x] **P7-04 · Methodology page** — Ask first: DEC-67 (answered 2026-10-03: as recommended). UI-SPEC §6.4, with the Reg T citations (DEC-10) and the Limits of this backtest panel, its figures read from the results (DEC-109) — Needs: P6-09 — done 2026-10-04. The page renders every panel from the committed NVDA results: data and RIC scheme (the first long bought as the RIC example), data coverage with the IV failures by reason, bar timing and the look-ahead guard (with R-21's close gap), the fill model, both mid-vs-print scatters drawing every pair (46,874 shorts, 124,723 longs, in ECharts' large mode) with each fit beside the pooled one and every pair's values in a disclosure built when opened, the Reg T treatment quoting 12 CFR 220.12 and FINRA 4210 as re-read on 2026-10-04 (DEC-10), friction, entry timing with its dispersion and DEC-67's verdict (NVDA: not fragile; means 0.8% to 1.1% inside the baseline's −0.9% to 2.8%), the parameter grid, the stated assumptions, and the limits of this backtest, each figure read from the runs, `robustness.json` and `rules.json` and each claim made only where they bear it out (DEC-115). The half-width Friction and Entry timing tables scroll sideways at 1366 and 1600 px: put to the PO. The PO then had the limits lead the page and the grid follow the scatters, and dropped the data and RIC scheme, data coverage and Reg T treatment panels, and the limits' sentence weighing quant's long against A1 (DEC-116). 30 new Vitest tests (17 page, 9 figures, 4 scatter); the smoke test checks the page on the built site (19 pass)
- [x] **P7-05 · Universe page** — UI-SPEC §6.5 — Needs: P6-09 — done 2026-10-04. The page renders every panel from the committed universe files: the suitability screen, a row per symbol with each measure over its own weeks (NVDA: extrinsic per delta 3.0% of spot, spreads 2.5% / 2.1%, credit 1.7% of the long, IV ÷ RV20 1.12, the event-week gate 2 of 26 weeks), its caption naming the quant rules it reads, linked (DEC-66, DEC-113); the headline by symbol, the comparison page's columns after a Symbol column linked to its comparison page, quant first within each symbol (max drawdown in dollars, as `headline.json` has no % of the peak); and the pooled universe, the comparison page's panel. The universe files carry no manifest, so the footer shows the runs the headline came from (`useManifests`; DEC-117). 12 new Vitest tests (401); the smoke test checks the page on the built site (20 pass)
- [ ] **P7-06 · Data page** — Ask first: DEC-75. The github.io banner, plus the local mode if the PO wants it — Needs: P4-06
- [ ] **P7-07 · Responsiveness**
  - Screenshots reviewed at 4 widths. One theme: the PO dropped the light theme (DEC-03, 2026-09-30).
  - Done when: the contrast tests pass and the screenshots show no clipping or overlap.
  - Needs: P7-01…P7-06
- [ ] **P7-08 · Full read-through** **[PO]**
  - Every page at 4 widths: no placeholder text, every number traceable, the fix list closed.
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

### Later, if time allows (PO, DEC-109)

Noted by the PO on 2026-10-02 after reading P7-01's leg attribution: the NVDA result is mostly the long call in a rising market. Neither item is started; each goes to the PO as a proposal first, and neither may delay P7 or P8.

- [ ] **L-01 · Long-only reference run** **[PO]** — the same long rules with no short call, so the difference from each strategy measures what the covered-call overlay added or cost. One config extending the baseline and a re-run; where it shows on the site is part of the proposal.
- [ ] **L-02 · A flat or falling symbol** **[PO]** — run the strategies where the stock didn't rise, so the overlay faces another regime. QQQ and TSLA are set aside (DEC-15; P1-10 paused, TSLA partly cached). First recalibrate the starting cash (DEC-30), then fetch, re-run and repeat P5-05's band-edge check.

## 5. Cut list

The spec sets the order. Cut the next item only when its trigger fires, and mark it `[~]` in §4.

**Never cut:** the blotter, NAV, Reg T, the rules page, or the tests.

| Order | Cut | Trigger | Items affected |
| --- | --- | --- | --- |
| 1 | Parameter grid | M3 not reached by Sun Oct 4, 20:00 | P5-02 grid variants, P6-06 grid table |
| 2 | Entry-timing sensitivity | M4 not reached by Tue Oct 6, 12:00 | P5-02 timing variants, P6-06 timing table |
| 3 | Greek attribution | M4 not reached by Tue Oct 6, 20:00 | P6-04, the quant page's Greek panel |
| 4 | Universe size | — (taken early: the PO cut it from 12 symbols to QQQ, NVDA and TSLA on 2026-09-28, then to NVDA alone for now on 2026-09-30, DEC-15) | P1-10, P5 |
| — | Data page local mode (keep the github.io banner) | P7 behind at Wed Oct 7 end of day | P7-06 |

## 6. Risks

| ID | Risk | Likelihood | Impact | Mitigation | Watch at |
| --- | --- | --- | --- | --- | --- |
| R-01 | Windows (Git Bash) and Ubuntu CI diverge: CRLF line endings, missing time-zone data, shell differences | Med | Med | DEC-58: `.gitattributes` LF, `tzdata`, `newline="\n"`, bash recipes; CI catches what slips through | P0-02, P0-05 |
| R-02 | Hourly option history is shorter than 10 weeks, or uneven across symbols | Med | High | Probe on day 1; window = the intersection; tell the PO at once. **P1-04:** hourly history ends between Sep 26 and Oct 27 2025, the same for every symbol sampled there (DEC-07). **Retired at P1-05:** the PO's window (Mar 30 – Sep 25 2026) and its warm-up sit 3½ months inside that edge | P1-04 |
| R-03 | Deep ITM long-dated quotes are sparse or wide: IV failures, few E-L3 candidates, E-T1 retries | Med | Med | Measure (DEC-08); report on Methodology; leave the rules unchanged. **P1-04 sample:** every bar quoted, but median spreads over E-T1's 3% on 7 symbols. **DEC-15:** the kept three have the tightest (QQQ 1.4%, NVDA 1.4%, TSLA 2.1%). **P1-09, NVDA in full:** an in-band candidate with a valid mid on every session bar; 100% valid mids once listed; median spread 1.52%; none below the no-IV floor. Expiries listed late are the gap (DEC-08, DEC-32) | P1-10 |
| R-04 | Fetch volume and time; possible LSEG request limits | Med | High | Estimate first; resumable units; start Sep 27; run overnight; watch for throttling errors. **P1-05:** the 26-week window scales ARCHITECTURE §6.3's 11-week estimate by about 2.4 ; with the 3 symbols of DEC-15 that's roughly 2–2.5 h, and DEC-48's wider long bands add to it; P1-08's `--plan-only` prints the real figure first. **P1-09:** NVDA estimated at 52–155 min and took 40 min, with no throttling and one connection reset recovered on its retry | P1-10 |
| R-05 | The zero-padded RIC day, settled from the earlier project without a probe, stops resolving | Low | Med | The DEC-01 note: expiries dated the 1st–9th all come back unanswered; the spelling is set in one place, and the parser reads both. **P1-09:** all 15 of NVDA's units dated the 1st–9th answered in the padded form; retired | — |
| R-06 | A strike above $999.99 doesn't fit the 5-digit field | Low | High | Probe the max strike per symbol; ask the PO. **P1-04:** all 12 fit; META is closest ($973.51, DEC-12) | P1-04 |
| R-07 | A split in the window changes the option root | Low | High | Check the tape for discontinuities and corporate actions. **P1-04:** LSEG's history is split-adjusted, so the tape can't show a split; XLE split 2-for-1 on Dec 5 2025 (DEC-12). Confirm the rest against OCC memos and pick the window with it in mind. **Retired at P1-05:** XLE's split is before the window and its warm-up; OCC's series search, issuer filings and news show no other event for the 12, and none announced before Oct 9 2026 (DEC-12) | P1-04, P1-05 |
| R-08 | A wrong bar convention hides look-ahead | Low | High | DEC-06 checks; MarketView keyed on `bar_end`. **P1-04:** start stamps and end-of-bar quotes confirmed on all 12 | P1-04 |
| R-09 | Float nondeterminism breaks INV-13 | Med | Med | Integer money, explicit sorts, seeded RNG, canonical JSON | P3-08 |
| R-10 | The schedule compresses | High | High | Cut list with triggers; parallel web track; M1 gate | status board |
| R-11 | LSEG terms forbid publishing raw-derived series | Med | Med | DEC-05 asked at P3-10; binned scatter as the fallback. **Retired at P3-10:** the PO accepted LSEG's terms for the raw cache and every derived series, raw scatter points included (DEC-05) | P3-10, P6-07 |
| R-12 | pyright strict clashes with untyped libraries (lseg-data, scipy) | Med | Low | Local stubs; typed adapters; narrow ignores, each with a reason | P0-03 |
| R-13 | Results JSON is too heavy for the site | Low | Med | Detail levels (DEC-54); virtualized tables; per-run lazy loading. **P4-05:** a summary run's file is about 23 KB against a full run's 430 KB over NVDA's 26 weeks, and the site loads each run on demand (P4-06) | P4-05 |
| R-14 | Quant E-L3 favours wide-spread contracts, so E-T1 keeps failing | Med | Med | Report retry counts; no tuning after the first run (spec) | P4-04 |
| R-15 | Holiday and half-day edge cases | Med | Med | Calendar tests on known dates. **P1-06:** they pass, and the table matched LSEG's trading days for all 12 from Jan 2025 (DEC-33) | P1-06 |
| R-16 | The Workspace session drops mid-pull | Med | Med | A dead Workspace never changes the session's state (DEC-83), so failing requests are retried 3 times, then abort the unit as an outage; resume | P1-08 |
| R-17 | The Pages base path or routing breaks deep links | Low | Med | `base: './'` with HashRouter; deploy early (P4-07) | P4-07 |
| R-18 | Pulls need the PO's machine on and signed in to Workspace | High | Med | Schedule pulls with the PO; batch them overnight | P1-10 |
| R-19 | A late PO answer stalls the items that depend on it | Med | Med | Batch questions per item and ask one item ahead (§2) | §2 |
| R-20 | A guessed RIC fails with a code that isn't a no-data code, so the fetch stops as an outage | Med | Med | P1-04 records the real codes before any pull; widening the no-data codes is a DEC-83 decision. **Retired by P1-04:** both never-listed codes are no-data codes (DEC-83) | P1-04 |
| R-21 | The close bar's last trade differs from the official close (up to 0.09% in the probes), so a short pinned near its strike can be ITM by one and OTM by the other | Med | Med | DEC-23 (asked at P2-03) decides which close X-S4/X-S5 use; the probe numbers go with the question. **P2-03:** the PO kept the close bar's last trade (the cache has no daily close); the gap is disclosed on Methodology's bar timing (P7-04, done 2026-10-04) | — |
