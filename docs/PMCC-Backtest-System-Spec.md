# PMCC Backtest System Spec

Sep 25, 2026 · @Jason

## Overview and scope

Build a symbol-agnostic backtester for the Poor Man's Covered Call (PMCC): a deep ITM long-dated call as a stock substitute, with weekly OTM calls sold against it. It runs two strategies through one engine, a fixed-rule baseline PMCC and a quant PMCC, and publishes the results as a static GitHub Pages site. Due Oct 9, 11:59pm.

The deliverable must show accuracy, honest reporting with no look-ahead bias, performance, the purpose of the strategy, and a reproducible process, without unnecessary prose.

**In scope**

- LSEG historical data (hourly bars) for the underlying and options, fetched locally and cached.
- Baseline PMCC and quant PMCC, plus ablation runs of the quant layers.
- Any symbol via CLI; a batch run over a universe baked into the site.
- Blotter, ledger, NAV, and Reg T accounting for every strategy.
- Analytics, a static site, and a rules write-up generated from config.

**Out of scope**

- Dividends: no dividend guard, no ex-div modeling; dividend yield q = 0 in Greeks.
- Buy-and-hold and covered-call benchmarks.
- Pre-registered promotion criteria, out-of-sample holdout, live or paper trading adapters.
- Regime flipping to put diagonals; reverse diagonals.
- Machine learning models.
- Third-party backtesting frameworks (NautilusTrader, backtrader, vectorbt), QuantLib, Docker, database servers, and orchestration tools.

## Architecture

One engine, strategies as config, and look-ahead made structurally impossible.

```
pmcc/
  data/        LSEG adapter (local only), RIC builder, chain discovery, parquet cache
  pricing/     vectorized IV solver, Greeks, expected move
  strategy/    rule modules: long-leg selector, short-leg selector, gates, exits
  engine/      event loop, MarketView, fill simulator
  accounting/  blotter, ledger, Reg T engine, NAV marks
  analytics/   metrics, attribution, bootstrap, friction and timing sensitivity
  export/      results JSON + JSON Schema from pydantic result models, run manifest
  cli.py       typer entry point
configs/       baseline_pmcc.yaml, quant_pmcc.yaml, ablations/, universe.yaml
data_cache/    parquet + manifest (NVDA's committed; DEC-05)
results/       per-symbol, per-strategy JSON (committed)
tests/         pytest + hypothesis invariant tests
web/           Vite + React + TypeScript frontend
  src/types/   TypeScript types generated from the JSON Schema
  public/data/ results JSON copied in by pmcc export
  e2e/         Playwright smoke test
pyproject.toml, uv.lock, justfile, .pre-commit-config.yaml
.github/workflows/  lint, type-check, tests, build, deploy web/dist to Pages
```

**Stack**

| Layer | Choice |
| --- | --- |
| Environment | uv with a committed lockfile; `uv sync` reproduces the exact environment |
| Quality gates | ruff (lint and format), pyright strict, pre-commit hooks mirrored in CI |
| Data | polars with lazy parquet scans, pyarrow |
| Numerics | numpy, scipy; numba only if profiling shows a hotspot |
| Config and results | pydantic models; YAML configs; JSON results plus generated JSON Schema |
| CLI and logging | typer; structlog JSON logs (every soft failure in a fetch is searchable) |
| Tests | pytest, hypothesis (property-based accounting invariants) |
| Frontend | Vite, React, TypeScript, Tailwind, shadcn/ui, TanStack Table, ECharts via `echarts-for-react` |
| Frontend tests | Vitest for transforms and formatting; one Playwright smoke test across all pages |
| Task runner | justfile, including `just reproduce` |
| CI/CD | GitHub Actions: lint, type-check (Python and TS), tests, build, deploy `web/dist` to Pages |

The Action builds only from committed results; it never calls LSEG, and nothing runs server-side.

**Look-ahead guard.** Strategies never see raw dataframes. On each bar the engine passes a `MarketView` that returns only data with a timestamp at or before the current decision time. Any request for later data raises an error. This is the structural guarantee referenced in the write-up.

**Config-driven rules.** Every rule threshold lives in YAML, validated by pydantic. Each rule has a stable rule ID (for example `E-S3`). The engine stamps the firing rule ID on every blotter row and gate-log entry, and the site renders the rules write-up from the same config, so the published rules can never drift from the code.

**CLI:**

```
pmcc fetch  --symbol NVDA --start 2026-07-06 --end 2026-09-18
pmcc run    --symbol NVDA --config configs/quant_pmcc.yaml
pmcc batch  --universe configs/universe.yaml
pmcc export --out web/public/data/
just reproduce   # cached data -> all runs -> export -> built site
```

**Run manifest.** Every result file carries the git commit SHA and whether the working tree was dirty, config hash, data-manifest hash, package lockfile hash, and run timestamp. Results are written as canonical JSON. A run on a dirty tree still runs but records it, and published results must come from a clean tree, so the code is committed before a publishable run (DEC-50). The site shows the manifest in the footer of every page, so any number on the site traces to the exact code, config, environment, and data that produced it.

## Data layer (LSEG)

All LSEG access happens locally through `pmcc fetch`; backtests read only the parquet cache. GitHub Pages never calls LSEG, and any data page on github.io shows "Data connection required."

**Fields and bars**

- Underlying: hourly OHLC plus trade prints.
- Options: hourly `BID`, `ASK`, and when traded `TRDPRC_1`, `OPEN_PRC`, `HIGH_1`, `LOW_1`, `ACVOL_UNS`, `NUM_MOVES`.
- Same bar size for stock and options.

**RIC builder:** `{ROOT}{MONTH}{DAY}{YY}{STRIKE}.U{^MONTHYY if expired}`

- Month letter encodes month and call/put (calls A–L, puts M–X). The caret always uses the call letter, for puts too: a June put's caret is `^F26` (DEC-45).
- Day zero-padded to two digits (DEC-01); strike × 100, five digits, zero-padded.
- Caret suffix only for expired contracts. The long leg (120–270 DTE) is often still live, so the builder must decide expired vs live from the expiry date relative to the fetch date. For a few days after expiry a contract still answers only to the live form, so an expired contract is asked with the caret first, then without it (DEC-45).

**Chain discovery**

- Weekly expiries: take the last trading session of each week from the stock tape, so holiday weeks never get an invented Friday expiry.
- Monthly expiries for the long leg: third Friday, adjusted to the prior session if it's a holiday.
- Strike grid: probe to detect the increment per symbol and expiry ($1, $2.50, $5). Fetch from below the window's low to above its high for shorts, and deep ITM (down to about 0.95 delta) for longs. Fetching ranges from the window's high and low is allowed; selection logic may only use point-in-time data through MarketView.
- Guess-and-check fails soft: a missing RIC returns an empty series and a log entry, never a crash.

**Cache**

- Parquet per fetch unit (the stock tape, and each expiry's calls or puts), each with a sidecar, plus a manifest with RIC, fetch time, row count, and hash. The data-manifest hash ignores fetch times and which RIC form answered, and a unit is re-pulled only after its files are moved aside (DEC-46).
- Re-running a backtest never re-fetches. Commit derived results, and commit the raw cache of each symbol in the published results, so anyone can re-run them (DEC-05; NVDA's for now).

## Conventions

Every decision uses only data available at the bar's end time, and every fill is at that bar's mid.

**Bar timing**

- Decision time = the bar's end time. If LSEG stamps a bar at its start but reports BID/ASK as of its end, acting on those quotes at the start time is look-ahead. Verify the convention before building (see Open items).
- No fixed entry time. Entry is triggered by liquidity (rule E-T1).
- The Friday check (X-S3) uses the last bar whose end time is at or before 15:00 ET on the week's final trading session.

**Greeks and pricing**

- Black-Scholes, with implied vol solved from the bar's mid, vectorized across the whole chain snapshot (Newton's method with a bisection fallback).
- Risk-free rate r: one constant for the window, stated on the site: the 3-month Treasury yield at the last close before the window, continuously compounded (DEC-11).
- Dividend yield q = 0 (dividends out of scope).
- Weekly expected move EM = mid of the weekly ATM straddle (nearest-strike call mid + put mid). This needs put quotes for the ATM strike only.
- Realized vol RV20: annualized close-to-close vol over the prior 20 sessions, using daily closes derived from the hourly tape.
- If the IV solve fails (price below intrinsic, or no bid/ask), the contract is ineligible on that bar.

**Fill model**

- Default: limit at mid = (BID + ASK) / 2, filled at mid on the decision bar.
- No BID or no ASK on that bar means no fill. Never invent a print.
- Friction parameter `spread_capture` in \[0, 1\]: buys fill at mid + capture × half-spread, sells at mid − capture × half-spread. Default 0; sensitivity runs at 0.25 and 0.50.
- No commissions by default; a per-contract fee parameter exists, default $0.

**Early assignment:** Assumed not to occur before expiry. The defensive close (X-S2) keeps shorts from sitting deep ITM, where early exercise becomes likely. The Friday check handles expiry; a missed-assignment fallback (X-S5) covers shorts that still finish ITM.

## Trade rules: entry

Both strategies share entry timing, sizing, and the structural constraint; they differ only in how the long and short contracts are selected. All values are starting parameters, fixed before the first run.

**Order of operations each session:** evaluate long-leg exits and resets first, then short-leg exits, then short-leg entry (Mondays only).

| ID | Rule | Baseline PMCC | Quant PMCC |
| --- | --- | --- | --- |
| E-T1 | Entry trigger | Enter on the first bar of the session where the selected contract has a valid bid/ask and passes its spread threshold (long ≤ 3% of mid, short ≤ 10% of mid) | Same |
| E-L1 | Long leg timing | First session of the window; retry each following session until E-T1 passes | Same |
| E-L2 | Long leg expiry | Monthly expiry nearest 180 DTE | Any monthly expiry 120–270 DTE |
| E-L3 | Long leg strike | Strike with delta nearest 0.80 | Among eligible strikes with delta 0.70–0.90 across E-L2 expiries: lowest extrinsic ÷ delta, where extrinsic = mid − max(0, spot − strike). Tiebreak: lower spread % of mid |
| E-L4 | Sizing | Fixed 1 contract. Every symbol's account starts with the same cash balance, used for NAV and Reg T tracking: 2× the most expensive first long-leg cost in the universe, rounded up to the nearest $5,000 and fixed before the first run. If available funds would go negative, no entry (logged) | Same |
| E-S1 | Short leg timing | Each Monday (first session of the week if Monday is a holiday), once a long leg is held and no short is open; E-T1 governs which bar | Same |
| E-S2 | Short leg expiry | That week's final trading session | Same |
| E-S3 | Short leg strike | OTM strike with delta nearest 0.30 | Lowest listed strike ≥ spot + 1.0 × EM |
| E-S4 | Short leg quantity | Equal to long contracts | Same |
| E-S5 | Structural constraint | Short strike − long strike > long entry fill − short mid (per share) | Same |

The structural constraint uses the long leg's entry fill rather than its current mark. That keeps it conservative and ensures a short that finishes deep ITM can't turn the structure into a net loss, since the long leg's intrinsic gain covers the short's loss plus the net debit.

If the short leg's selected contract fails E-T1 or E-S5, the skip gates below decide the outcome; the engine never substitutes a different strike.

## Trade rules: skip-week gates

When any gate fires, the long leg stays on and no short call is sold that week. Gates are evaluated in the order below at the Monday decision bar; the first to fire is logged with its rule ID and the values that triggered it.

| ID | Gate | Condition that skips the week | Baseline PMCC | Quant PMCC |
| --- | --- | --- | --- | --- |
| G-1 | No quote / liquidity | Selected short never passes E-T1 on any Monday bar | On | On |
| G-2 | Structural constraint | Selected short fails E-S5 | On | On |
| G-3 | Event week | Front-week ATM IV ÷ next-week ATM IV > 1.20 | Off | On |
| G-4 | Volatility risk premium | Front-week ATM IV ÷ RV20 < 1.00 | Off | On |
| G-5 | Minimum premium | Selected short mid < $0.10 per share | Off | On |

G-3 detects events (usually earnings) from the chain itself, with no external calendar: an event priced into the front week lifts its IV above the following week's. A ratio is used instead of a vol-point difference so the threshold scales across low- and high-volatility symbols.

G-1 replaces the separate short-leg spread gate discussed earlier; the E-T1 spread threshold already covers it.

**Gate log.** Every Monday produces one gate-log row per strategy: date, symbol, gate results (pass or fire with values), and the outcome (short sold, or skipped with rule ID). The site shows this log on the quant PMCC page.

## Trade rules: exits

Both strategies use identical exit rules, so any difference in results comes from entry selection and gates, not management. The short is never allowed to be exercised, and there are no discretionary rolls.

| ID | Trigger | Action |
| --- | --- | --- |
| X-S1 | Take profit: short mid ≤ 25% of credit received, any bar before the Friday check | Buy to close at mid. No new short until next Monday |
| X-S2 | Defensive: short delta > 0.60, any bar | Buy to close at mid. No new short until next Monday |
| X-S3 | Friday check (bar ending at or before 15:00 ET): spot ≥ short strike − 0.25 × EM, with EM measured at short entry | Buy to close at mid |
| X-S4 | Short still open at expiry and OTM at the close | `EXPIRE` at $0 |
| X-S5 | Missed assignment: short still open and ITM at the close | `ASSIGN` the call; open short stock at the strike (Reg T short-stock margin applies); buy to cover at the first valid bar of the next session |
| X-L1 | Long reset: long delta < 0.50 at the Monday decision bar | Sell long at mid, then re-enter per E-L1 to E-L4 in the same session if E-T1 passes; then apply short-leg entry rules |
| X-L2 | Long roll: long DTE < 90 at the Monday decision bar | Same as X-L1 |
| X-E1 | End of backtest | Mark all positions to the final bar's mid; no forced liquidation |

**Why the short is never exercised.** Buying back an ITM short at expiry costs its intrinsic value plus almost no extrinsic, which is economically equal to assignment and covering. Assignment only adds weekend gap risk on short stock, short-stock margin that can push available funds negative, or the loss of the long leg's extrinsic if it's exercised to deliver.

**Why there are no rolls.** With weekly shorts, the Monday entry already is the roll. A same-bar roll would let a new short bypass the skip gates, and rolling to defer a loss turns a defined loss into an open-ended one. The loss is realized and the next week starts fresh.

**Why the Friday buffer.** The stock can move ITM in the final hour after the check. Treating "within 0.25 × EM of the strike" as ITM reduces missed assignments; X-S5 handles any that still occur, honestly recorded rather than assumed away.

## Accounting: blotter, ledger, NAV, Reg T

Cash moves only on blotter events, and every strategy gets its own blotter, ledger, NAV path, and Reg T panel.

**Blotter** (booked trades only; no working orders, no signals)

| Column | Contents |
| --- | --- |
| Time | Decision bar end time |
| Instrument | RIC, with OCC symbol as a subtitle |
| Side | `BUY` / `SELL` / `EXPIRE` / `ASSIGN` |
| Qty | Contracts or shares |
| Limit | Mid at decision time |
| Fill | Simulated fill (mid, adjusted by `spread_capture`) |
| Cash Δ | Signed; options × 100 × qty |
| Rule | Rule ID that fired (for example `X-S3`) |
| Notes | Short human-readable reason with triggering values |

An OTM expiry is one `EXPIRE` row at $0. A missed assignment (X-S5) is an `ASSIGN` row on the call plus a `SELL` row opening short stock at the strike, then a `BUY` cover row next session.

**Ledger** (one row per bar)

- Long call: RIC, strike, expiry, qty, mark, delta.
- Short call: RIC, strike, expiry, qty, mark, delta.
- Stock position (only after X-S5), cash, NAV, IM, MM, available funds, excess equity.
- Option marks at mid. If a bar has no bid/ask, carry the last valid mid for marking only and flag it as stale; stale marks never produce fills.

**NAV and Reg T**

```latex
\text{NAV} = \text{cash} + \text{LongMV} - \text{ShortCallMV} + \text{StockMV}
```

| Quantity | Definition |
| --- | --- |
| Long call requirement | 100% of long call market value. Listed options with 9 months or less to expiry have no loan value; E-L2 caps DTE at 270, so the long is always fully paid |
| Covered short call | $0, when long strike ≤ short strike and long expiry ≥ short expiry. E-S5 and the X-L1 ordering guarantee this; an uncovered short is an engine error, not a margin case |
| Short stock (X-S5 only), while long calls covering the shares are held | Initial: none beyond the sale proceeds. Maintenance: 10% of the long calls' aggregate exercise price plus their out-of-the-money amount, capped at the greater of $5 a share and 30% of the short stock's value (12 CFR 220.12(c)(2); FINRA 4210(f)(2)(H)(v)a; DEC-10) |
| Short stock (X-S5 only), without such long calls | Initial: additional 50% of short value (150% total with proceeds). Maintenance: 30% |
| Initial margin (IM) | Long call requirement + short stock initial |
| Maintenance margin (MM) | Long call requirement + short stock maintenance |
| Available funds | NAV − IM |
| Excess equity | NAV − MM |

With only the diagonal open, available funds reduce to cash − short call MV. No entry is allowed if it would make available funds negative. If available funds go negative on any bar anyway (for example after X-S5), the ledger flags it and the site states that the position could not have been held in a real Reg T account.

## Strategies, ablations, and universe

Two strategies, five ablations, and three sensitivity checks, run independently on each symbol with the same starting capital for every symbol and run (see E-L4).

**Strategies**

| Config | Description |
| --- | --- |
| `baseline_pmcc` | Fixed selection (E-L2/E-L3 baseline, E-S3 at 0.30 delta), gates G-1 and G-2 only, shared exits |
| `quant_pmcc` | Cheapest-replacement long leg, expected-move short strike, gates G-1 to G-5, shared exits |

**Ablations** (quant PMCC with one layer switched off; answers which layers earn their complexity)

| ID | Layer removed | Replaced by |
| --- | --- | --- |
| A1 | Cheapest-replacement long leg | Baseline long selection |
| A2 | Expected-move short strike | 0.30 delta short |
| A3 | G-3 event gate | Off |
| A4 | G-4 VRP gate | Off |
| A5 | X-S1 take profit | Hold to Friday check |

**Sensitivity checks** (robustness reporting, not optimization; the full results are published, never a best-cell pick)

- **Friction:** both strategies at `spread_capture` 0, 0.25, 0.50.
- **Entry timing:** baseline with E-T1 replaced by a fixed Monday bar, run once per Monday bar. Large dispersion is reported as fragility.
- **Parameter grid (quant):** k in {0.75, 1.00, 1.25}; G-4 threshold in {0.90, 1.00, 1.10}; G-3 threshold in {1.10, 1.20, 1.30}. One parameter varied at a time from the defaults.

**Universe** (`configs/universe.yaml`)

QQQ, NVDA, TSLA (DEC-15). An equity index ETF and two single names across a wide volatility range (roughly 20%, 40% and 55% realized), chosen from the probed twelve for the tightest long-leg spreads. The first plan's twelve (SPY, QQQ, IWM, AAPL, NVDA, AMD, META, TSLA, COIN, JPM, TLT, XLE) added financials, long-duration Treasuries and energy; the PO cut it for time (DEC-15). The probes had also found most of the dropped symbols' long legs wider than E-T1's 3%. All symbols use the same window: Mon Mar 30 2026 to Fri Sep 25 2026, 26 weeks of hourly bars, set by the PO from the probed history (DEC-07). A window must lie within LSEG's hourly option history and be at least 10 weeks. Any symbol can also be run alone via `pmcc run --symbol`.

## Analytics and metrics

Every metric is computed per symbol and strategy, plus pooled across the universe. Small-sample statistics are reported with their uncertainty, never as standalone headline claims.

**Performance**

- Dollar P\&L; return on starting NAV; return on capital deployed (P&L ÷ peak long-leg cost).
- Max drawdown on NAV and longest time underwater.
- Sharpe and Sortino on daily NAV returns, not annualized. If an annualized figure is shown, it's labeled with the sample length.

**Cycle statistics** (one cycle = one week)

- Weeks traded vs skipped, with skips counted by gate ID.
- Win rate, average win, average loss, payoff ratio (average win ÷ average loss).
- Premium captured as % of credit received; weekly credit as % of long-leg cost.
- Exit mix: counts of X-S1 through X-S5, X-L1, X-L2.

**Attribution**

- By leg: net short premium (credits − buybacks) vs long-leg P&L, split into intrinsic and extrinsic change.
- By Greek, bar by bar, with the residual reported:

```latex
\Delta V \approx \delta\,\Delta S + \tfrac{1}{2}\,\Gamma\,(\Delta S)^2 + \theta\,\Delta t + \nu\,\Delta\sigma + \text{residual}
```

**Uncertainty**

- Bootstrap (10,000 resamples) 95% CI on mean weekly return per symbol and strategy.
- Pooled universe CI uses a week-block bootstrap: resample whole weeks with all symbols together, so cross-symbol correlation isn't mistaken for independent evidence.

**Robustness tables**

- Ablation table: each A1–A5 run vs the full quant PMCC on P&L, drawdown, payoff ratio, and CI.
- Friction table at `spread_capture` 0 / 0.25 / 0.50.
- Entry-timing dispersion: range and spread of baseline P&L across fixed Monday bars.
- Parameter grid results, published in full.

**Fill-assumption check**

- Scatter of `TRDPRC_1` (y) vs mid (x) on bars with a trade print, with fitted line and R², shown separately for weekly shorts and long-dated longs. The long leg is expected to fit worse; that's reported, not hidden.

**Symbol suitability screen**

- Per symbol, from point-in-time data: long-leg extrinsic per delta (% of spot), median spread % for long and short candidates, average weekly credit after half-spread (% of long cost), average IV ÷ RV20, and G-3 fire count.

## Site and UI

A static React app on GitHub Pages with a global symbol selector; the comparison page is the landing page, and every strategy page is the same component tree fed different results.

| Page | Contents |
| --- | --- |
| Comparison (landing) | Overlaid NAV curves for baseline and quant PMCC; headline table (P&L, return on capital, max drawdown, payoff ratio, weekly-return CI); ablation table; pooled-universe summary |
| Baseline PMCC | Blotter; NAV chart with IM, MM, and available funds on mouseover; ledger; Reg T panel; cycle statistics; leg attribution |
| Quant PMCC | Everything on the baseline page, plus the gate log and Greek attribution |
| Trade rules | Entry, skip-gate, and exit tables rendered from the YAML configs, with rule IDs and live parameter values, plus the short rationale text for each rule |
| Methodology | Data and RIC scheme; bar-timing convention; fill model; mid-vs-trade scatters with R²; Reg T treatment; look-ahead guard; friction, timing, and parameter sensitivity; stated assumptions (r, q = 0, no early assignment) |
| Universe | Symbol suitability screen and per-symbol headline table |
| Data | Shows "Data connection required" on github.io; only works via the local server |

**Traceability.** Every blotter row's rule ID links to that rule on the Trade rules page, and every gate-log entry links to its gate. A reader can go from any trade to the exact rule and values that caused it.

**Rule write-up source.** Each rule in the YAML carries `id`, `name`, `condition`, `action`, and `rationale` fields. The Trade rules page and the write-up text are generated from these, so the published rules always match the code that ran.

**Frontend constraints**

- **Static output only.** `vite build` produces static files; the app loads results JSON from its own origin and never calls LSEG or any external API.
- **Hash routing.** GitHub Pages has no SPA fallback, so routes use HashRouter (for example `#/quant/NVDA`); deep links survive a refresh.
- **Typed results.** `pmcc export` writes JSON Schema from the pydantic result models; the build generates TypeScript types from it, so a schema change the frontend doesn't handle fails type-checking.
- **Per-run data files.** One JSON file per symbol per strategy or ablation, fetched on demand when the symbol or page changes, plus a small index file listing what exists.
- **Global state.** Selected symbol lives in app state and the URL, so every page and chart follows it.
- **Tables.** Blotter, ledger, and gate log use TanStack Table: sortable, filterable by rule ID and side, virtualized for long hourly ledgers.
- **Styling.** Tailwind with shadcn/ui components; light and dark themes.
- **Run manifest footer** on every page.

**Charts.** ECharts with mouseover on all time series; NAV charts show IM, MM, and available funds on a shared time axis. Theme-aware and readable on mobile.

## Invariant tests

These tests prove logical consistency and must pass on every run, for every symbol and config; the CI build fails if any do.

1. Cash changes only on blotter rows, and the sum of Cash Δ equals the change in cash.
2. NAV reconciles every bar: cash + long MV − short call MV + stock MV.
3. No fill without a valid bid and ask on the decision bar.
4. No decision reads data stamped after its decision time; MarketView raises on any attempt.
5. Every short call is covered: long strike ≤ short strike, long expiry ≥ short expiry, quantities match.
6. Every short entry satisfied E-S5 at its decision bar.
7. No short call is open after its expiry session.
8. Available funds ≥ 0 at every entry decision.
9. Every blotter row and gate-log row carries a valid rule ID defined in the config.
10. Short and long quantities stay equal whenever a short is open.
11. RIC parser reads known examples as the right contracts (including `UUUUH212601450.U^H26` and the unpadded `AAPLF52619000.U^F26`); the builder emits the zero-padded day, round-trips its own spelling, and emits no caret for live contracts (DEC-01).
12. Missing RICs return empty series, never exceptions.
13. Re-running a config on cached data produces byte-identical results, once the run timestamp and the git commit SHA are dropped: the time changes on every run, and the commit moves on once results are committed (DEC-50).
14. The frontend type-checks against TypeScript types generated from the current result schema.
15. The Playwright smoke test loads every page for one symbol with no console errors.

Tests 1, 2, 8, and 10 run as hypothesis property tests: generate random sequences of fills, expiries, and marks, and assert the invariants hold for all of them, in addition to running on every real backtest. The vectorized IV solver is tested against a reference scalar solve on random inputs.

## Build order

A gradable baseline exists by Sep 30; everything after that adds depth, and Oct 9 is buffer only.

| Dates | Work | Done when |
| --- | --- | --- |
| Sep 26–27 | Repo tooling (uv, ruff, pyright, pre-commit, justfile, CI skeleton); resolve open items; RIC builder, chain discovery, parquet cache; fetch one symbol | One symbol's full chain cached; tests 11–12 pass |
| Sep 27 onward | Start universe fetches in the background as soon as the fetcher works | All 3 symbols cached by Oct 3 |
| Sep 28–30 | Pricing (IV, Greeks, EM, RV20); engine and MarketView; fill simulator; accounting; baseline PMCC | Baseline blotter, ledger, NAV, Reg T for one symbol; tests 1–10 and 13 pass |
| Oct 1–2 | Quant long and short selectors; gates G-3 to G-5; gate log; ablation configs; scaffold the Vite app and Pages deploy Action with sample JSON | Quant PMCC and A1–A5 run on one symbol |
| Oct 3–4 | Batch runs across the universe; friction, timing, and parameter sensitivity | All results JSON written |
| Oct 5–6 | Analytics: metrics, attribution, bootstrap, scatters, suitability screen | All tables and series in results JSON |
| Oct 7–8 | React pages (comparison, strategy, rules from YAML, methodology, universe) and write-up | CI builds and deploys the site after `pmcc export`, and the site passes a full read-through |
| Oct 9 | Buffer; publish to GitHub Pages; check no live LSEG on Pages | URL submitted by 11:59pm |

If time runs short, cut in this order: parameter grid, entry-timing sensitivity, Greek attribution, universe size (already cut to three symbols, DEC-15). Never cut the blotter, NAV, Reg T, rules page, or tests.

## Open items to verify before building

Resolve these by Sep 27; each one affects every fill or the backtest window.

- [x] **Bar timestamp convention.** Pull one known contract and confirm whether LSEG hourly bars are stamped at start or end, and whether BID/ASK are end-of-bar values. Set the decision-time rule accordingly. *Resolved in DEC-06: stamped at the start, end-of-bar quotes; decisions at the bar's end.*
- [x] **History depth.** How far back LSEG hourly BID/ASK goes for expired weeklies and for long-dated contracts. This sets the backtest window for all symbols. *Resolved in DEC-07: back to late Oct 2025; the window is Mar 30 – Sep 25 2026.*
- [ ] **Long-dated coverage.** Whether hourly BID/ASK exists for deep ITM, 120–270 DTE strikes on each universe symbol, and how sparse it is. Sparse data will limit E-L3's candidate set. *DEC-08: sampled at P1-04; measured in full at P1-09 and P1-10 (by Sat Oct 3).*
- [x] **Live-contract RICs.** Confirm that long legs still listed at fetch time resolve without the caret suffix. *Resolved in DEC-09: confirmed on all 12 symbols.*
- [ ] **Reg T text.** Confirm the long-option loan value (≤ 9 months: none) and the covered-diagonal treatment against the Reg T and FINRA 4210 text, and cite it on the Methodology page. *DEC-10: both confirmed and cited. The PO settled the short stock after X-S5 on Sep 29 (the hedged requirement, now in the NAV and Reg T table); the quotes go on Methodology at P7-04 (Wed Oct 7).*
- [x] **Risk-free rate.** Choose the source and value of r, and state it on the site. *Resolved in DEC-11: FRED DGS3MO, 3.73% on Mar 27 2026, so r = 0.0371.*
- [x] **LSEG terms.** Confirm whether raw cached data may be committed to a public repo; default to committing derived results only. *Resolved in DEC-05 (PO, Sep 30): the raw cache is committed (NVDA's for now), and every derived output is public, the fill-assumption scatter's raw points included.*
