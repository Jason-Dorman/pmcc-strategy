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
| P0 Foundations | Sat Sep 26 | `just check` green in Git Bash and in CI; credentials ignored; LSEG session opens from Git Bash | In progress |
| P1 Data layer and open items | Sat Sep 26 – Sun Sep 27 | NVDA's full chain cached; INV-11, INV-12 pass; window, r and identifiers recorded; universe fetch started | Not started |
| P1-10 Universe fetch (background) | Sun Sep 27 – Sat Oct 3 | All 12 symbols cached with coverage summaries | Not started |
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
| P1-04 Probes · Sat Sep 26 | RIC spelling, with the probe result | DEC-01 |
| P1-05 Open items · Sat Sep 26 | Probe results (DEC-06–14); confirm the window and r | DEC-07, DEC-11 |
| P1-06 Calendar · Sat Sep 26 | Monthly expiries and holidays | DEC-33 |
| P1-07 Cache · Sun Sep 27 | Cache file layout | DEC-46 |
| P2-01 Black-Scholes · Mon Sep 28 | Time and Greek units | DEC-24 |
| P2-03 Measures · Mon Sep 28 | Spot and close, ATM IV and EM, RV20 | DEC-23, DEC-25, DEC-26 |
| P2-04 Chain pricer · Mon Sep 28 | Greeks when IV fails; fresh quotes only | DEC-27 |
| P3-02 MarketView · Mon Sep 28 | Point-in-time listing | DEC-32 |
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
- [ ] **P0-06 · CI skeleton**
  - `.github/workflows/ci.yml` `python` job on Ubuntu: setup-uv, `uv sync --frozen`, pre-commit on all files, pytest.
  - Done when: the workflow is green on GitHub.
  - Needs: P0-02, P0-05
- [ ] **P0-07 · Logging and architecture test**
  - structlog JSON config (stderr and `logs/*.jsonl`).
  - `tests/architecture/test_imports.py` enforcing ARCHITECTURE §3.3.
  - Done when: the test passes, and fails on a planted forbidden import.
  - Needs: P0-04
- [ ] **P0-08 · README check**
  - The README was written on Sep 25. Check its requirements, setup and usage sections against the real toolchain, and fix anything that differs.
  - Done when: every README setup step works as written from a fresh clone in Git Bash.
  - Needs: P0-02, P0-05

### P1 — Data layer and open items · Sat Sep 26 – Sun Sep 27

- [ ] **P1-01 · Domain primitives**
  - `pmcc/domain`: `Price`/`Money` (DEC-44), `OptionId`, `Right`, `Side`, `RuleId`, ET time helpers, and the session/bar model (DEC-06).
  - Done when: tests cover half-even quantization, money arithmetic, `bar_end`, and session-bar classification including half-days.
  - Needs: P0-04
- [ ] **P1-02 · RIC builder and parser**
  - `pmcc/data/ric.py`: build and parse both forms, the OCC symbol, the form policy (DEC-45), and day padding per DEC-01.
  - Done when: the INV-11 tests pass:
    - the spec's examples parse
    - the builder emits the verified spelling
    - a put's caret uses the call letter
    - a strike > $999.99 raises
    - live contracts get no caret
    - a hypothesis round-trip over random contracts holds
  - Needs: P1-01 · Refs: Spec › RIC builder; LDG §3
- [ ] **P1-03 · Provider port and LSEG adapter**
  - The `HistoryProvider` protocol.
  - `pmcc/data/lseg/`: a port of `lseg_session`, fail-soft history, the shape normalizer (into polars), 25-RIC batches with per-RIC retry, caret→live fallback, and diagnostics.
  - `FakeProvider` (TEST-STRATEGY §6).
  - Done when:
    - the INV-12 tests pass
    - every LDG §4 behaviour has a FakeProvider test
    - a closed session raises before any request
    - an outage writes nothing
  - Needs: P1-02 · Refs: DEC-49; LDG §4
- [ ] **P1-04 · Probes** **[Workspace]** **[PO]**
  - `pmcc probe` implements the DEC-01, 06, 07, 08, 09, 12, 13 and 14 checks. Run it for all 12 symbols; the requests are small.
  - Then ask: DEC-01, with the probe result.
  - Done when: `data_cache/probes/` has a report per symbol, and each outcome is written into its DEC entry.
  - Needs: P0-01, P1-03
- [ ] **P1-05 · Resolve the spec's open items** **[PO]**
  - Report the probe results (DEC-06–14) to the PO.
  - Ask first: DEC-07 (window) and DEC-11 (r).
  - Start the Reg T citations (DEC-10, due by P7-04).
  - Fill in `configs/universe.yaml` (window, r, symbols with stock RICs and roots) and `configs/calendar.yaml`.
  - Tick the spec's open-item boxes, each with its DEC link.
  - Done when: every open item is resolved or has a dated owner, and both config files validate.
  - Needs: P1-04
- [ ] **P1-06 · Calendar and chain discovery**
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
- [ ] **P1-07 · Cache and loader**
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
- [ ] **P1-08 · `pmcc fetch`**
  - Plan → estimate (units, RIC requests, minutes) → resumable unit loop → coverage summary; `--plan-only`.
  - Done when FakeProvider tests show:
    - a resume after a mid-run outage refetches only the missing units
    - the estimate prints before any request
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
  - Show the PO the estimate, fetch the other 11 symbols (overnight is fine), and re-run any failures.
  - Done when: all 12 are cached with coverage summaries by **Sat Oct 3**, with any gaps recorded in DEC-08.
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
  - Final result models for every output (P6 sections may stay empty), JSON Schema, `index.json`, `rules.json`, and the `pmcc export` and `pmcc verify` commands (DEC-51).
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
  - Once the universe is cached (P1-10), run `pmcc calibrate` across 12 symbols × 2 strategies and commit `starting_cash` with its basis (DEC-30).
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
| 4 | Universe down to 5 symbols (best data coverage, spanning the volatility range) | fewer than 12 cached by Sat Oct 3, 20:00, or M3 at risk | P1-10, P5 |
| — | Data page local mode (keep the github.io banner) | P7 behind at Wed Oct 7 end of day | P7-06 |

## 6. Risks

| ID | Risk | Likelihood | Impact | Mitigation | Watch at |
| --- | --- | --- | --- | --- | --- |
| R-01 | Windows (Git Bash) and Ubuntu CI diverge: CRLF line endings, missing time-zone data, shell differences | Med | Med | DEC-58: `.gitattributes` LF, `tzdata`, `newline="\n"`, bash recipes; CI catches what slips through | P0-02, P0-05 |
| R-02 | Hourly option history is shorter than 10 weeks, or uneven across symbols | Med | High | Probe on day 1; window = the intersection; tell the PO at once | P1-04 |
| R-03 | Deep ITM long-dated quotes are sparse or wide: IV failures, few E-L3 candidates, E-T1 retries | Med | Med | Measure (DEC-08); report on Methodology; leave the rules unchanged | P1-09 |
| R-04 | Fetch volume and time; possible LSEG request limits | Med | High | Estimate first; resumable units; start Sep 27; run overnight; watch for throttling errors | P1-08, P1-10 |
| R-05 | The RIC day-padding conflict breaks INV-11 as written | High | Med | Probe both spellings; DEC-01 to the PO | P1-04 |
| R-06 | A strike above $999.99 doesn't fit the 5-digit field | Low | High | Probe the max strike per symbol; ask the PO | P1-04 |
| R-07 | A split in the window changes the option root | Low | High | Check the tape for discontinuities and corporate actions | P1-04 |
| R-08 | A wrong bar convention hides look-ahead | Low | High | DEC-06 checks; MarketView keyed on `bar_end` | P1-04 |
| R-09 | Float nondeterminism breaks INV-13 | Med | Med | Integer money, explicit sorts, seeded RNG, canonical JSON | P3-08 |
| R-10 | The schedule compresses | High | High | Cut list with triggers; parallel web track; M1 gate | status board |
| R-11 | LSEG terms forbid publishing raw-derived series | Med | Med | DEC-05 asked at P3-10; binned scatter as the fallback | P3-10, P6-07 |
| R-12 | pyright strict clashes with untyped libraries (lseg-data, scipy) | Med | Low | Local stubs; typed adapters; narrow ignores, each with a reason | P0-03 |
| R-13 | Results JSON is too heavy for the site | Low | Med | Detail levels (DEC-54); virtualized tables; per-run lazy loading | P4-05 |
| R-14 | Quant E-L3 favours wide-spread contracts, so E-T1 keeps failing | Med | Med | Report retry counts; no tuning after the first run (spec) | P4-04 |
| R-15 | Holiday and half-day edge cases | Med | Med | Calendar tests on known dates | P1-06 |
| R-16 | The Workspace session drops mid-pull | Med | Med | Per-unit session check; outages abort cleanly; resume | P1-08 |
| R-17 | The Pages base path or routing breaks deep links | Low | Med | `base: './'` with HashRouter; deploy early (P4-07) | P4-07 |
| R-18 | Pulls need the PO's machine on and signed in to Workspace | High | Med | Schedule pulls with the PO; batch them overnight | P1-10 |
| R-19 | A late PO answer stalls the items that depend on it | Med | Med | Batch questions per item and ask one item ahead (§2) | §2 |
