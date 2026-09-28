# PMCC Backtest — Product Requirements

Sep 25, 2026 · derived from the [System Spec](PMCC-Backtest-System-Spec.md), which wins any conflict · decisions in [DECISIONS](DECISIONS.md) · schedule in [BUILD-PLAN](BUILD-PLAN.md)

## 1. Summary

This is a symbol-agnostic backtester for the Poor Man's Covered Call. It runs a fixed-rule baseline and a quant variant through one engine on LSEG hourly data and publishes the results as a static GitHub Pages site.

The deliverable is the public site URL, backed by a public repo that reproduces every number on it.

- **Gradable baseline:** Wed Sep 30, 2026.
- **Due:** Fri Oct 9, 2026, 11:59 pm.

## 2. Purpose

A PMCC replaces 100 shares with a deep in-the-money, long-dated call and sells a weekly out-of-the-money call against it. The result is covered-call income for a fraction of the capital.

The quant variant adds three layers:

- a cheapest-replacement long leg
- an expected-move short strike
- volatility-based skip-week gates

The product answers these questions:

| # | Question | Answered on |
| --- | --- | --- |
| Q1 | Does the quant PMCC beat the baseline, per symbol and pooled, after honest costs? | Comparison |
| Q2 | Which quant layers earn their complexity? | Comparison (ablations A1–A5) |
| Q3 | Does the answer survive friction, entry timing and parameter changes? | Methodology |
| Q4 | Which symbols suit a PMCC? | Universe |
| Q5 | Can every trade be traced to its rule and inputs, and every number to its code, config, environment and data? | Strategy pages, Trade rules, manifest footer |

## 3. Users

| User | Needs | Main surface |
| --- | --- | --- |
| Grader | Purpose, accuracy, honest reporting, performance, reproducibility, no unnecessary prose (Spec › Overview) | Comparison, Methodology, Trade rules |
| Auditor | Follow any trade to the rule and values that caused it; test the fill assumption and the look-ahead guard | Strategy pages, Methodology |
| PO and operator (the author) | Answer open questions as they come up; fetch once, run everything, publish reproducibly | DECISIONS, CLI, justfile, CI |
| Maintainer (including the coding agent) | Change a rule without touching the engine; know what must not break | configs, docs, tests |

## 4. Goals and success criteria

| ID | Goal | Measured by |
| --- | --- | --- |
| G1 | Accuracy | INV-01…INV-15 pass for every symbol × run (3 × 24); CI fails otherwise |
| G2 | Honest reporting | Every HR requirement (§7) is visible on the site |
| G3 | Performance reporting | Every metric in Spec › Analytics is present per symbol × strategy and pooled |
| G4 | Purpose | The landing page states it; every rule shows its rationale |
| G5 | Reproducibility | Clean clone + cache → `just reproduce` → byte-identical results; manifest footer on every page |
| G6 | On time | Gradable baseline (M1) by Sep 30; URL submitted by Oct 9, 11:59 pm |

## 5. Scope

In scope and out of scope are exactly as defined in Spec › Overview and scope.

Also out of scope for this build:

- authentication
- server-side code on Pages
- live refresh of results
- internationalization

## 6. Functional requirements

Every row points to its source. "Verified by" names the invariant test (INV-nn), the rule tests, or the backlog check that proves it.

### 6.1 Data (LSEG)

| ID | Requirement | Source | Verified by |
| --- | --- | --- | --- |
| FR-D1 | `pmcc fetch --symbol S --start --end` pulls hourly bars for the underlying and its options from LSEG through a local Workspace desktop session and writes them to the local cache. Only `fetch` and `probe` contact LSEG. | Spec › Data layer; LDG §1–2 | architecture test; P1-09 |
| FR-D2 | Underlying: hourly OHLC plus trade prints (plus BID/ASK for stock fills). Options: hourly BID, ASK, and when traded TRDPRC_1, OPEN_PRC, HIGH_1, LOW_1, ACVOL_UNS, NUM_MOVES. The same bar size for both. | Spec › Fields and bars; DEC-13 | P1-04 probe reports (`data_cache/probes/`), all 8 fields per leg; `tests/unit/data/test_probe.py` |
| FR-D3 | The RIC builder follows the spec grammar: a zero-padded day, a caret only for expired contracts, the call-month letter in put carets, and a strike field ≤ $999.99. Live vs expired is decided against the fetch date, and an expired contract is asked with the caret first, then without it. | Spec › RIC builder; DEC-01, DEC-45 | INV-11; the form-policy tests in `tests/unit/data/test_ric.py`; the form-round tests in `tests/unit/data/test_fetch.py` (the live fallback) |
| FR-D4 | Chain discovery: weekly expiries are the last session of each week from the stock tape, whose trading days must match the NYSE holiday table (`configs/calendar.yaml`, 2025–2027) or the plan stops; monthly expiries are the third Friday (prior session if a holiday); strike increments are probed per symbol, expiry and region; bands follow the fetch plan. | Spec › Chain discovery; DEC-14, DEC-33, DEC-48, DEC-84 | `tests/unit/domain/test_calendar.py`, `tests/unit/config/test_calendar_file.py`, `tests/unit/data/test_tape_calendar.py`, `tests/unit/data/test_discovery.py` (P1-06) |
| FR-D5 | Guess-and-check fails soft: a missing RIC returns an empty series and a log entry, never an exception. An outage aborts without writing anything. | Spec; LDG §4.3; DEC-49 | INV-12 |
| FR-D6 | Cache: a parquet and a sidecar per fetch unit, plus a manifest (RIC, fetch time, row count, hash) per contract asked. Written whole or not at all, and never overwritten; a re-pull starts with moving the unit's files aside. The data-manifest hash ignores fetch times and the RIC form. Backtests read only the cache, and re-running never re-fetches. | Spec › Cache; DEC-46, DEC-87 | `test_cache.py`, `test_load.py`, `test_files.py` |
| FR-D7 | The raw cache isn't committed unless LSEG terms allow it; derived results are committed. | Spec › Cache; DEC-05, DEC-56 | `.gitignore`; CI check |

### 6.2 Pricing

| ID | Requirement | Source | Verified by |
| --- | --- | --- | --- |
| FR-P1 | Black-Scholes Greeks with IV solved from the bar's mid, vectorized across the chain snapshot (Newton with bisection fallback) | Spec › Greeks and pricing | IV solver vs scalar reference (P2-02) |
| FR-P2 | One constant r for the window, with source and value stated on the site; q = 0. r = 0.0371, from FRED DGS3MO (3.73% on Mar 27 2026), continuously compounded | Spec; DEC-11 | `tests/unit/config/test_universe_file.py`; Methodology page |
| FR-P3 | EM = mid of the weekly ATM straddle | Spec; DEC-25 | P2-03 tests |
| FR-P4 | RV20 = annualized close-to-close vol over the prior 20 sessions, from hourly-derived daily closes | Spec; DEC-26 | P2-03 tests |
| FR-P5 | A failed IV solve makes a contract ineligible on that bar | Spec; DEC-27 | P2-02, P2-04 tests |

### 6.3 Engine and conventions

| ID | Requirement | Source | Verified by |
| --- | --- | --- | --- |
| FR-E1 | Strategies read market data only through `MarketView`; a request past the decision time raises | Spec › Look-ahead guard | INV-04 |
| FR-E2 | Decision time = the bar's end time; fills happen at that bar's mid | Spec › Conventions; DEC-06 | INV-03; DEC-06 probe |
| FR-E3 | Fill model: limit at mid; no BID or no ASK means no fill; `spread_capture` ∈ [0, 1] (default 0); per-contract fee (default $0) | Spec › Fill model | INV-03; P3-05 tests |
| FR-E4 | Order of operations: long exits and resets → short exits → short entry (week-open session) | Spec › Trade rules: entry; DEC-20 | scenario tests |
| FR-E5 | Early assignment is assumed not to happen before expiry; X-S5 handles a short that finishes ITM | Spec › Early assignment | scenario test |
| FR-E6 | Every blotter row and gate-log row carries the firing rule ID, and that ID exists in the config | Spec › Config-driven rules | INV-09 |

### 6.4 Trade rules

| ID | Requirement | Source | Verified by |
| --- | --- | --- | --- |
| FR-R1 | Entry rules E-T1, E-L1–E-L4, E-S1–E-S5 as specified for each strategy | Spec › Trade rules: entry; DEC-21, DEC-29 | rule unit tests; INV-05, 06, 08, 10 |
| FR-R2 | Skip-week gates G-1–G-5, evaluated in order. The first gate to fire is logged with its values; one gate-log row per strategy per week-open session. | Spec › Skip-week gates; DEC-22 | rule and scenario tests |
| FR-R3 | Exits X-S1–X-S5, X-L1, X-L2, X-E1, identical across strategies; the short is never exercised; no rolls | Spec › Trade rules: exits; DEC-28 | scenario tests; INV-07 |
| FR-R4 | When the selected short fails E-T1 or E-S5, the gates decide; the engine never substitutes a different strike | Spec › Trade rules: entry; DEC-21 | scenario test |
| FR-R5 | Every threshold is in YAML, validated by pydantic, with a stable rule ID and `id`, `name`, `condition`, `action`, `rationale` fields | Spec › Config-driven rules; DEC-52 | config tests |

### 6.5 Accounting

| ID | Requirement | Source | Verified by |
| --- | --- | --- | --- |
| FR-A1 | Each strategy has its own blotter with the spec's columns, booked trades only, and the EXPIRE/ASSIGN row conventions | Spec › Blotter; DEC-34 | INV-01, INV-09 |
| FR-A2 | A ledger row per session bar: long, short, stock, cash, NAV, IM, MM, available funds, excess equity. Stale marks are carried and flagged and never fill. | Spec › Ledger | INV-02, INV-03 |
| FR-A3 | NAV = cash + LongMV − ShortCallMV + StockMV | Spec › NAV and Reg T | INV-02 |
| FR-A4 | Reg T as in the spec table. An uncovered short is an engine error. Entries are blocked if they would make available funds negative. Negative available funds are flagged, with the site's Reg T statement. | Spec › NAV and Reg T; DEC-10 | INV-05, INV-08; P3-04 tests |
| FR-A5 | Cash moves only on blotter events | Spec › Accounting | INV-01 |

### 6.6 Runs

| ID | Requirement | Source | Verified by |
| --- | --- | --- | --- |
| FR-B1 | Strategies `baseline_pmcc` and `quant_pmcc`, defined as configs | Spec › Strategies | config tests |
| FR-B2 | Ablations A1–A5: quant with one layer removed | Spec › Ablations | config-diff test (P4-03) |
| FR-B3 | Sensitivity: friction at 0 / 0.25 / 0.50 for both strategies; entry timing (baseline, one run per week-open bar); parameter grid (quant, one parameter at a time). Every result is published. | Spec › Sensitivity checks; DEC-31 | P5-02, P6-06 |
| FR-B4 | A universe batch over `configs/universe.yaml` (QQQ, NVDA, TSLA; DEC-15) on one common window, Mon Mar 30 – Fri Sep 25 2026 (26 weeks; at least 10 required); any symbol can run alone | Spec › Universe; DEC-07, DEC-15 | `tests/unit/config/test_universe_file.py`; P5-04 |
| FR-B5 | One starting cash balance for every symbol and run, fixed before the first run | Spec › E-L4; DEC-30 | P5-01 |
| FR-B6 | `just reproduce`: cached data → all runs → export → built site | Spec › CLI | INV-13; P8-01 |

### 6.7 Analytics

| ID | Requirement | Source | Verified by |
| --- | --- | --- | --- |
| FR-M1 | Performance: dollar P&L; return on starting NAV; return on capital deployed; max drawdown; longest time underwater. Sharpe and Sortino on daily NAV returns, not annualized (any annualized figure is labelled with the sample length). | Spec › Performance; DEC-60 | P6-01 tests |
| FR-M2 | Cycle stats: weeks traded vs skipped (skips by gate); win rate; average win and loss; payoff ratio; premium captured %; weekly credit as % of long cost; exit mix | Spec › Cycle statistics; DEC-62 | P6-02 tests |
| FR-M3 | Attribution by leg (net short premium vs long-leg P&L, split into intrinsic and extrinsic) and by Greek (bar by bar, with the residual) | Spec › Attribution; DEC-63 | P6-03, P6-04 tests |
| FR-M4 | 95% bootstrap CI (10,000 resamples) on mean weekly return per symbol and strategy; the pooled CI uses a week-block bootstrap | Spec › Uncertainty; DEC-61 | P6-05 tests |
| FR-M5 | Robustness tables: ablations, friction, entry-timing dispersion, and the full parameter grid | Spec › Robustness tables | P6-06 |
| FR-M6 | Fill-assumption check: TRDPRC_1 vs mid scatter with fitted line and R², shorts and longs shown separately | Spec › Fill-assumption check; DEC-64 | P6-07 |
| FR-M7 | Symbol suitability screen with the spec's five point-in-time measures | Spec › Symbol suitability screen | P6-08 |
| FR-M8 | Every metric computed per symbol × strategy, and pooled across the universe | Spec › Analytics | `pmcc verify` schema |

### 6.8 Export

| ID | Requirement | Source | Verified by |
| --- | --- | --- | --- |
| FR-X1 | One results JSON per symbol per run (committed), plus JSON Schema generated from the pydantic result models | Spec › Architecture | P4-05 |
| FR-X2 | Every result carries a run manifest: git SHA, config hash, data-manifest hash, lockfile hash, run timestamp | Spec › Run manifest; DEC-50 | `pmcc verify` |
| FR-X3 | `pmcc export --out web/public/data/` writes the per-run files, the index, the rules and the schema | Spec › Frontend constraints | P4-05 |
| FR-X4 | Re-running a config on cached data gives byte-identical results (excluding the run timestamp) | Spec › Invariant tests; DEC-50 | INV-13 |

### 6.9 Site

| ID | Requirement | Source | Verified by |
| --- | --- | --- | --- |
| FR-S1 | Pages: Comparison (landing), Baseline PMCC, Quant PMCC, Trade rules, Methodology, Universe, Data, with the contents in the spec's page table | Spec › Site and UI; UI-SPEC §6 | INV-15; P7-08 |
| FR-S2 | A global symbol selector held in app state and the URL; every page and chart follows it | Spec › Frontend constraints | smoke test |
| FR-S3 | Traceability: each blotter rule ID links to its rule, each gate-log entry to its gate | Spec › Traceability | smoke test |
| FR-S4 | The Trade rules page and write-up are generated from config: live parameter values plus each rule's rationale | Spec › Rule write-up source; DEC-52 | config tests; P7-03 |
| FR-S5 | Static output only: results load from the site's own origin; no calls to LSEG or any external API; hash routes survive a refresh | Spec › Frontend constraints; DEC-72, DEC-73 | dist guard; smoke test |
| FR-S6 | TypeScript types generated from the result schema; a mismatch fails type-checking | Spec › Typed results | INV-14 |
| FR-S7 | Per-run files fetched on demand, plus a small index file | Spec › Per-run data files | P4-06 |
| FR-S8 | Blotter, ledger and gate log use TanStack Table: sortable, filterable by rule ID and side, virtualized ledger | Spec › Tables | P7-01 |
| FR-S9 | ECharts with mouseover on every time series; NAV charts show IM, MM and available funds on a shared time axis; theme-aware; readable on mobile | Spec › Charts; DEC-04 | P7-01, P7-07 |
| FR-S10 | Light and dark themes | Spec › Frontend constraints; DEC-03 | contrast test; P7-07 |
| FR-S11 | The run manifest in the footer of every page | Spec › Run manifest | smoke test |
| FR-S12 | The Data page shows "Data connection required" on github.io | Spec › Site and UI; DEC-75 | smoke test |
| FR-S13 | Pages built from synthetic data show a warning banner | DEC-74 | smoke test |

### 6.10 CLI and delivery

| ID | Requirement | Source | Verified by |
| --- | --- | --- | --- |
| FR-C1 | CLI commands `fetch`, `run`, `batch`, `export` (spec), plus `probe`, `calibrate`, `verify`, `serve` | Spec › CLI; ARCHITECTURE §14 | `pmcc --help` |
| FR-C2 | GitHub Actions runs lint, type-check (Python and TS), tests, build, and deploys `web/dist` to Pages. It builds only from committed results and never calls LSEG. | Spec › Stack | CI |

## 7. Honest-reporting requirements

| ID | Requirement | Verified by |
| --- | --- | --- |
| HR-1 | No decision uses data after its decision time. This is structural (MarketView) and stated on the Methodology page. | INV-04 |
| HR-2 | Fills happen only on a valid BID and ASK at the decision bar. No invented prints. Stale marks are flagged and never fill. | INV-03; ledger flags |
| HR-3 | Missed assignments are recorded (X-S5 rows), never assumed away | scenario test |
| HR-4 | Negative available funds are flagged per bar, with the statement that the position couldn't have been held in a real Reg T account | ledger flags; UI state |
| HR-5 | Small-sample statistics are shown with bootstrap CIs, never as standalone headlines. Sharpe and Sortino are unannualized, or labelled. | P6-05 |
| HR-6 | Every sensitivity result is published in full; no best-cell picks | P6-06 |
| HR-7 | The fill-assumption fit is published even where it's weak (the long leg) | P6-07 |
| HR-8 | Data coverage is disclosed: unanswered contracts, IV failures, stale-mark rates, unavailable fields | `coverage.json`; Methodology |
| HR-9 | Stated assumptions: r (value and source); q = 0; no early assignment; dividends out of scope; Black-Scholes on American calls; the bar's final quotes aren't proven to be the NBBO (LDG §4.14) | Methodology |
| HR-10 | Synthetic data can never pass for real | banner (DEC-74) |

## 8. Non-functional requirements

| ID | Requirement | Target or check |
| --- | --- | --- |
| NFR-01 | Reproducible environments | `uv sync --frozen`; `npm ci` |
| NFR-02 | Deterministic results | INV-13 (synthetic data in CI; real data in P8-01) |
| NFR-03 | Code quality gates | ruff, pyright strict, ESLint, tsc strict. Complexity ≤ 10 (target 5). Pre-commit hooks mirrored in CI. |
| NFR-04 | Engineering principles | Import-boundary test. A new rule kind needs no engine edit (EP; DEC-53). |
| NFR-05 | Runtime | One run ≤ 10 s; full universe batch ≤ 20 min on the dev machine |
| NFR-06 | Site weight | First load ≤ 2 s on broadband; a full run file ≤ 2 MB; tables stay responsive at 5,000 ledger rows |
| NFR-07 | Observability | structlog JSON. Every soft fetch failure is a searchable event with symbol, unit, RIC, form, reason and the service's codes (DEC-83). |
| NFR-08 | Security | Credentials never committed or printed; CI holds no secrets; the site makes no cross-origin requests |
| NFR-09 | Accessibility | WCAG AA text contrast in both themes; keyboard-reachable controls; a caption explains each chart |
| NFR-10 | Responsive | Usable at 390 px wide; tables and charts scroll rather than squash |
| NFR-11 | Static hosting | Static files only; HashRouter; relative base path |
| NFR-12 | Platform parity | Git Bash on Windows (development) and Ubuntu (CI) behave identically: LF line endings, `tzdata`, bash recipes (DEC-58) |

## 9. Constraints and assumptions

**Constraints**

- **Dates:** a gradable baseline by Sep 30; submission by Oct 9, 11:59 pm.
- **LSEG access:**
  - It requires the Workspace desktop app, running and signed in on the PO's Windows machine, and it is local only.
  - The project therefore runs from Git Bash on that machine (DEC-02); CI runs on Ubuntu.
  - The data is hourly bars.
  - Expired contracts can't be found through the chain endpoint, so RICs are guessed and checked (LDG §4.1).
- **Stack:** fixed by the spec, including its excluded technologies (backtesting frameworks, QuantLib, Docker, database servers, orchestration tools, ML).
- **Data licensing:** the raw cache stays private by default (DEC-05).
- **Team:** one developer plus a coding agent, over 14 days.

**Modelling assumptions** (per the spec, published on Methodology)

- No early assignment before expiry.
- q = 0, and one constant r.
- Black-Scholes values American calls exactly under q = 0.
- Fills at the mid of the bar's final BID/ASK, which isn't proven to be the NBBO.
- The exchange calendar is known in advance.

## 10. Deliverables

1. A public GitHub repo: code, configs, committed results, lockfiles, and these governance docs.
2. The GitHub Pages site: seven pages, static.
3. A reproduction path: `uv sync --frozen` and `just reproduce`, given a local cache.
4. A README with the reproduction steps and the data-licensing note.

## 11. Release criteria

- [ ] CI is green on `main`: lint, type-check (Python and TS), tests, `pmcc verify`, build, smoke test.
- [ ] Results are committed from a clean tree for every symbol × run in the universe (after any cuts per BUILD-PLAN §5).
- [ ] Every spec open item is resolved in DECISIONS.
- [ ] The site passes the full read-through (P7-08) in both themes at 390, 1100, 1366 and 1600 px.
- [ ] The footer manifest matches the committed results, the site makes no cross-origin requests, and the Data page shows "Data connection required".
- [ ] A clean clone plus the cache reproduces byte-identical results (P8-01).
- [ ] The URL is submitted.

## 12. Milestones and open questions

- **Milestones M1–M6** and their dates: [BUILD-PLAN §1](BUILD-PLAN.md#1-status-board).
- **Open questions** go to the PO just in time, when the backlog item that needs the answer starts. [BUILD-PLAN §2](BUILD-PLAN.md#2-questions-for-the-po) lists when each comes up, and the answers are recorded in [DECISIONS](DECISIONS.md).
