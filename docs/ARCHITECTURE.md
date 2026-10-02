# PMCC Backtest — Architecture

Sep 25, 2026 · implements the [System Spec](PMCC-Backtest-System-Spec.md) · decisions in [DECISIONS](DECISIONS.md) · UI in [UI-SPEC](UI-SPEC.md)

The spec fixes the stack, the package layout and the trading rules. This document fixes the seams between them:

- module boundaries and interfaces
- the time model and the data plan
- the results contract
- the mechanisms that enforce the spec's guarantees (no look-ahead, reproducibility, invariants)

## 1. Principles and the mechanisms that enforce them

| Principle (Spec / EP) | Mechanism |
| --- | --- |
| One engine; strategies as config | A strategy is a set of rule objects composed from YAML by `kind` through a registry (DEC-53) |
| Look-ahead is structurally impossible | Strategies receive only `MarketView`; every accessor passes through one as-of gate (§5.2) |
| Published rules can't drift from code | Rule text is rendered from the params the engine uses (DEC-52); `rules.json` is exported from config |
| Every number traces to code, config, environment and data | Run manifest in every result; results from a dirty tree are rejected (DEC-50) |
| Fail soft on guesses, fail loud on outages | Failure taxonomy (DEC-49) |
| Reproducible | `uv.lock`, canonical JSON, integer money, seeded RNG (§11) |
| Single responsibility, low coupling | One reason to change per package; import boundaries tested (§3.3) |
| Open/closed | New rule kinds register themselves; the engine loop never changes (§16) |

## 2. System context

```
  One Windows machine (DEC-02): Workspace + this repo, worked from Git Bash                 GitHub
 ┌──────────────────┐ localhost ┌───────────────────────────────────────────────┐  push  ┌──────────────────────────────┐
 │ LSEG Workspace   │◄──:9000──►│ pmcc probe · pmcc fetch   (the only LSEG code)│ ─────► │ Actions on Ubuntu: no data,  │
 │ desktop session  │           │      │                                        │        │ no secrets · lint · types ·  │
 └──────────────────┘           │      ▼                                        │        │ tests · pmcc verify · export │
                                │ data_cache/   parquet + manifests  (ignored)  │        │ · vite build · e2e · deploy  │
                                │      │  load: no network                      │        └───────────────┬──────────────┘
                                │      ▼                                        │                        ▼
                                │ pmcc run · pmcc batch ──► results/ (committed)│              GitHub Pages (static)
                                │ pmcc export ──► web/public/data/ ──► web/dist │
                                └───────────────────────────────────────────────┘
```

Development is on Windows and CI is on Ubuntu, so DEC-58 keeps both identical: LF line endings, `tzdata`, and bash for recipes.

Pipeline, one symbol:

```
LSEG ─fetch─► cache (raw, per chain unit) ─load─► bar_end-keyed polars frames ─price─► per-bar chain snapshots
     ─engine (MarketView → strategy rules → fills → book)─► blotter · ledger · gate log
     ─analytics─► metrics · attribution · CIs · robustness ─export─► results/{SYM}/{run_id}.json
```

## 3. Packages and boundaries

### 3.1 Layout

The spec's tree, plus the `domain/` and `config/` additions from DEC-43.

```
pmcc/
  domain/        money.py (Price, Money), instruments.py (OptionId, Right, Side), rules.py (RuleId),
                 clock.py (ET, bar_end), sessions.py (Session, session bars) (DEC-81),
                 calendar.py (SessionCalendar: sessions, week-open/final, weekly and monthly
                 expiries; DEC-33, DEC-84), quotes.py (Quote: a valid BID/ASK and its mid; DEC-89),
                 errors.py (EngineError, which accounting raises without importing the engine;
                 DEC-91)
  config/        kinds.py (the kind registry: params per kind, SPEC_RULE_IDS), extends.py (extends and
                 overrides), rule_text.py (placeholders, rendering; DEC-52), strategy.py (Rule,
                 StrategyConfig, RunConfig, the config hash), fields.py (dollars, clock times,
                 rule IDs as pydantic fields) (DEC-90);
                 calendar.py (configs/calendar.yaml → SessionCalendar, DEC-84);
                 universe.py (configs/universe.yaml → Universe: window, r, symbols, starting
                 cash, bootstrap seed; DEC-86); matrix.py (configs/sensitivity.yaml's variants,
                 the 24-run matrix and each run's family; DEC-100, DEC-101); capital.py (StartingCash: E-L4's cash rule, the calibrated block and
                 its writer; DEC-93); yaml_file.py (read_yaml, parse_yaml: safe YAML refusing a
                 key given twice; DEC-86)
  data/
    provider.py  HistoryProvider port, RawHistory (long rows), Interval, the DEC-49 failure
                 classes (DEC-83)
    lseg/        the only code importing lseg.data or pandas (DEC-83): api.py (the lseg.data
                 slice called), session.py (lseg_session), shapes.py (any answer shape → long
                 polars rows), provider.py (LsegProvider: one fail-soft get_history call)
    ric.py       build_ric, parse_ric (either day spelling, DEC-01), occ_symbol,
                 forms_to_ask (the DEC-45 form policy) (DEC-82)
    calendar.py  sessions from the tape: its trading days must match the holiday table, or
                 CalendarMismatchError (DEC-33, DEC-84)
    discovery.py strike increments (DEC-14), integer-cent bands, session ranges, and the fetch
                 plan: plan_symbol → FetchPlan of units (DEC-48, DEC-84)
    fetch.py     fetch_rics, fetch_contracts: batching, retries, form fallback, diagnostics
                 (P1-03, DEC-83)
    pull.py      pmcc fetch's unit loop, above fetch and cache (cache imports fetch's result
                 types, DEC-87): prepare (stock tape → plan), pull_units (resumable),
                 measure_step (DEC-14) (DEC-88)
    estimate.py  the estimate printed before any option request: steps from the probe report
    coverage.py  the coverage summary printed after a fetch, from the cache (DEC-16)
    fillcheck.py fill_pairs: each call's prints paired with their bar's mid, shorts and longs,
                 from the loaded cache and its sidecars' bands (P6-07; DEC-64, DEC-103)
    probe/       the P1-04 probes over the HistoryProvider port, one module per DEC check;
                 one report per symbol (§6.2, DEC-85)
    files.py     write_new (whole or not at all, never over a file), replace_file (DEC-87)
    cache.py     UnitPull (chain_pull, stock_pull) → SymbolCache.write_unit: a unit's parquet +
                 sidecar, then the manifest rebuilt from the sidecars; the data-manifest hash
                 (DEC-46, DEC-87)
    load.py      load_symbol → SymbolData (no network): verified units, integer prices,
                 bar_end, session bars, quote validity (DEC-87)
  pricing/       black_scholes.py (price, greeks), expiry.py (T, elapsed years and DTE, DEC-24), iv.py (implied_vol,
                 IvCode), measures.py (close, ATM strike and IV, EM, RV20; DEC-23, DEC-25, DEC-26),
                 chain.py (price_quotes for one bar; price_symbol → PricedSymbol, memoized) (DEC-89)
  strategy/      ports.py (MarketView, LookAheadError, the values rules return), selectors.py
                 (E-L2/E-L3, E-S2/E-S3, baseline and quant), trigger.py (E-T1), gates.py (E-S5,
                 G-1…G-5), exits.py (X-S1…X-S3, X-L1, X-L2, the X-S4/X-S5 resolver), measures.py
                 (ATM strike and IV, EM, RV20 through the MarketView), registry.py (kinds → code,
                 build_strategy) (DEC-91, DEC-95)
  engine/        market_view.py (MarketData, HistoricalView: the as-of gate), loop.py (run_backtest),
                 legs.py (Trader: the leg state machines and the gate log), fills.py, invariants.py,
                 greeks.py (leg_greeks: a contract's IV and Greeks on the bar; DEC-102)
  accounting/    events.py, book.py, marks.py, valuation.py (market values, NAV), regt.py, ledger.py
  analytics/     records.py (what a run's records offer, as protocols the engine's output meets;
                 session closes, weeks, each blotter row's leg, a bar's trades, a leg's value),
                 performance.py (NAV closes, returns, metrics; DEC-60), cycles.py (cycles, their
                 statistics, exit mix, skips; DEC-62), bootstrap.py (mean weekly return CI, per run
                 and pooled; DEC-61), attribution.py (by leg; DEC-63), greek_attribution.py (by
                 Greek, bar by bar; DEC-63, DEC-76), run.py (analyze: one run's analytics;
                 attribute: a full run's attribution), scores.py (RunScore: a finished run's
                 summary), robustness.py (the four tables; DEC-65), universe.py (headline, pooled)
                 (DEC-101, DEC-102), fillcheck.py (the fill-assumption fits, per symbol and pooled;
                 DEC-64, DEC-103), suitability.py (the symbol screen: quant's picks and G-3
                 read each week through the MarketView, and the row; DEC-66, DEC-104)
  export/        canonical.py (canonical JSON, INV-13's timestamp drop), manifest.py (git SHA and
                 dirtiness, lockfile hash, version), results.py (write_result) (P3-08, DEC-92);
                 base.py (the strict model, dollars, schema version), models.py (a run's file),
                 analytics_models.py (P6 sections, per-symbol and universe files), site_models.py
                 (index.json, rules.json), schema.py (JSON Schema), verify.py and rederive.py
                 (pmcc verify), site.py (pmcc export) (P4-05, DEC-96)
  runner.py      run_symbol: load a cache, run the engine and the run's analytics, build the
                 RunResult (DEC-92, DEC-101)
  calibration.py calibrate: measure each run's first long entry, verify the value (DEC-93)
  batch.py       pmcc batch: the run matrix on each symbol in a spawned process, coverage.json,
                 robustness.json and fill_check.json and the suitability-screen row, the
                 universe-level stage: headline.json, pooled.json, pooled_fill_check.json,
                 suitability.json (DEC-100, DEC-101, DEC-103, DEC-104)
  log.py         structlog JSON setup: stderr + logs/{command}_{timestamp}.jsonl (DEC-80)
  cli.py         typer: fetch, probe, run, batch, calibrate, export, verify, serve
configs/         _shared.yaml, baseline_pmcc.yaml, quant_pmcc.yaml, ablations/a1…a5.yaml,
                 sensitivity.yaml, universe.yaml, calendar.yaml
data_cache/      raw data (gitignored, §6.4)
results/         committed results (§12)
tests/           unit/, property/, scenario/, architecture/, fixtures/synthetic/
typings/         minimal stubs for pyright strict: lseg/ (DEC-42), scipy/ (DEC-89)
web/             frontend (§13)
.github/workflows/ci.yml · justfile · pyproject.toml · uv.lock · .python-version · .pre-commit-config.yaml · .gitattributes
```

The reference files at the repo root (`LSEG-DATA-GUIDE.md`, `DESIGN-GUIDE.md`, `theme.py`, `lseg_client.py`) stay where they are. They are excluded from lint, type-check and tests (DEC-57).

### 3.2 Responsibilities

| Package | One job | Main API | Depends on |
| --- | --- | --- | --- |
| `domain` | Types and time rules everyone shares | `Price`, `Money`, `Quote`, `OptionId`, `RuleId`, `Session`, `SessionCalendar`, `bar_end()` | stdlib |
| `config` | Turn YAML into validated, hashed, rendered config | `load_strategy()` → `StrategyConfig`; `load_run_config(path, universe)` → `RunConfig` (`config_hash()`, `Rule.text()`); `run_matrix(universe)` → every run's `RunConfig` (DEC-100); `load_calendar()` → `SessionCalendar`; `load_universe()` → `Universe` | domain, pydantic, pyyaml |
| `data.lseg` | Talk to LSEG | `lseg_session()` → `LsegProvider` | `data.provider`, lseg.data, pandas, polars |
| `data` (rest) | Know RICs; check the tape against the calendar; probe, plan, fetch, cache, load | `HistoryProvider`, `build_ric()`, `parse_ric()`, `sessions_from_tape()`, `run_probe()`, `plan_symbol()`, `fetch_rics()`, `fetch_contracts()`, `prepare()`, `pull_units()`, `estimate()`, `coverage()`, `SymbolCache.write_unit()`, `load_symbol()` | domain, config, polars, numpy; `pricing` for the coverage summary's IV failures (DEC-89); only `fetch` may use `data.lseg` |
| `pricing` | Turn quotes into IV, Greeks and measures | `implied_vol()`, `greeks()`, `price_quotes()`, `price_symbol()` → `PricedSymbol.snapshot()`, `atm_iv()`, `expected_move()`, `rv20()` | domain, numpy, scipy, polars (the loader's frames, never `pmcc.data`; DEC-89) |
| `strategy` | Decide what to trade | `build_strategy(cfg)` → `Strategy` | domain, config, pricing, `strategy.ports` |
| `engine` | Run the clock; route decisions to fills and the book | `MarketData.build(stock, chains, calendar, r, root)`; `run_backtest(data, run_config, strategy, starting_cash)` → `RunOutput` (DEC-91) | domain, config, pricing, strategy, accounting; the loader's frames, never `pmcc.data` |
| `accounting` | Record and value positions | `Book.apply()`, `carry()`, `value()`, `regt()`, `funds_after()`, `ledger_row()` | domain |
| `analytics` | Summarize runs into export's result models | `analyze(run, seed, report)` → `RunAnalytics` (metrics, cycle statistics, exit mix, skips, closes, weekly returns, cycles, and a full run's attribution); `leg_attribution(run)`, `greek_attribution(run)`; `mean_ci(table, seed)`; `robustness(symbol, scores, families)`; `headline(scores)`, `pooled(scores, seed)`; `RunScore.of(result)`; `Screen.of(strategy)`, `sample_bars()`, `read_week(view, screen)`, `suitability_row()`, `suitability(rows)` | domain, accounting (its ledger and event types), config (`Family`, `Report`), `pricing.expiry` (elapsed years), strategy (the screen's selectors, G-3, measures and `MarketView`; DEC-104), export's result models, numpy (DEC-101, DEC-102) |
| `export` | Result models, manifest, canonical JSON, JSON Schema, site data, verify | `write_result()`, `write_schemas()`, `export_site()`, `verify()`, `rederive()` | domain, config, accounting; `data.files` for whole-file writes (DEC-92); `engine.invariants` for the names of the runtime invariants a summary records (DEC-96) |
| `runner` | Run configs on one symbol's cache into results | `run_symbol()`, `run_loaded()`; `Market.prepare()` once per symbol, then `run_market(…, seed=)` per config → `RunResult` with its analytics, or `run_output()` → the engine's `RunOutput` | domain, config, accounting, analytics, data, engine, strategy, export, polars (DEC-92, DEC-101) |
| `calibration` | Calibrate the starting cash (E-L4) | `calibrate(markets, configs, universe)` → `Calibration` (the `StartingCash` and each run's `RunFunds`); `cash_rule()`, `measure()`, `first_long_entry()`, `verify()`, `run_funds()`, `blocked_entries()` | domain, config, accounting (the `Event` type), engine, runner (DEC-93) |
| `batch` | Run the matrix on every symbol | `run_batch(jobs, out, seed=)` → `BatchOutcome`; `run_job(SymbolJob)` → `SymbolOutcome` (one symbol, in a worker: its runs, coverage, robustness and fill check, and its suitability row); `coverage_file()`, `stale_mark_rate()`; `UNIVERSE_WRITERS` (`write_headline`, `write_pooled`, `write_pooled_fill_check`, `write_suitability`) over a `UniverseStage`; `write_universe()` | analytics, config, data, domain, export, runner, strategy (`build_strategy`, for the screen) (DEC-100, DEC-101, DEC-104) |
| `log` | Configure structured logging for one command | `configure_logging()` | structlog |
| `cli` | Wire commands | `pmcc` | everything |

### 3.3 Import rules

These rules are enforced by `tests/architecture/test_imports.py`, an AST scan with no extra dependency.

1. `lseg` and `pandas` are imported only under `pmcc/data/lseg/`.
2. `pmcc.data.lseg` is imported only by `pmcc.data.fetch` and `pmcc.cli`.
3. `pmcc.strategy` never imports `engine`, `data`, `accounting` or `export`.
4. `pmcc.accounting` and `pmcc.pricing` import only `pmcc.domain` from this package.
5. `pmcc.analytics` never imports `engine` or `data`, and `pmcc.export` never imports `pmcc.analytics`, which builds export's result models (DEC-101).
6. `pmcc.domain` imports nothing from `pmcc`. Nothing imports `pmcc.cli`.
7. `pmcc.log` is imported only by `pmcc.cli`. Every other module logs through `structlog.get_logger()` (DEC-80).

The test also checks that one planted forbidden import per rule is caught, including relative, function-local and `TYPE_CHECKING` imports.

## 4. Domain: money and time

### 4.1 Money (DEC-44)

| Type | Representation | Notes |
| --- | --- | --- |
| `Price` | frozen dataclass over an `int` of $0.0001 units per share | quotes quantized once at load (round half-even; a float by its shortest repr) |
| `Money` | frozen dataclass over an `int` of $0.0001 units | cash, market values, P&L; `Price.notional(multiplier, qty)` is exact |
| `Quote` | a valid BID and ASK (`Price`s: BID > 0, ASK ≥ BID) | `mid` rounds (BID + ASK) / 2 half-even to $0.0001, as a fill at mid does; EM adds two of them (DEC-25, DEC-89) |
| multiplier | 100 per option contract; 1 per share | |
| `float64` | IV, Greeks, ratios, analytics | never cash |

`Price` and `Money` never mix: adding one to the other, or multiplying `Money` by a non-int, raises `TypeError` (DEC-81).

### 4.2 Time (DEC-06, DEC-20, DEC-23, DEC-24, DEC-33)

| Concept | Definition |
| --- | --- |
| Time zone | Every timestamp is tz-aware `America/New_York` after load; never a hardcoded UTC hour (LDG §4.8) |
| `bar_start` | LSEG stamp, the bar's start in UTC; cached as `bar_start_utc` (tz-aware UTC) for provenance only |
| `bar_end` | `bar_start + 1h`; the only key after load, and the decision time |
| Session bar | A bar whose ET start is 09:00–15:00 on a trading day (ends 10:00–16:00; ends 13:00 on a half-day); `Session.contains()`, `session_of()` |
| Trading days | `SessionCalendar` from `configs/calendar.yaml`: every weekday not listed as closed, with 13:00 early closes (DEC-33). The stock tape's trading days must match it, or loading stops (`CalendarMismatchError`) |
| Week-open session | First session of the calendar week (Monday to Sunday); what the rules call "Monday" |
| Week-final session | Last session of the calendar week; the weekly expiry (E-S2) |
| Monthly expiry | Third Friday, or the session before it when that Friday is closed (DEC-33) |
| Friday-check bar | Last session bar of the week-final session with `bar_end` ≤ 15:00 ET (X-S3) |
| Close bar | Last session bar of a session; its TRDPRC_1 is the session close |
| Expiry instant | The expiry session's close; T is measured to it, ACT/365 |

## 5. Core interfaces

Signatures are indicative. Names and shapes are settled here; details are settled in code review.

### 5.1 Data provider (dependency inversion for LSEG)

```python
class HistoryProvider(Protocol):                              # pmcc/data/provider.py
    def history(self, rics: Sequence[str], fields: Sequence[str], start: date,
                end_exclusive: date, interval: Interval) -> RawHistory: ...
# RawHistory.rows: (bar_start, ric, field, value), one row per non-empty cell; bar_start is
# LSEG's stamp, a UTC datetime (hourly) or a date (daily)
# raises NoDataError (soft) | UnreadableAnswerError (split the batch) | TransientError (ask
# again) | ProviderOutageError (loud)
```

- `LsegProvider` (`pmcc/data/lseg/`) wraps `ld.get_history` (DEC-83):
  - It checks the session before every request; Pending counts as not open.
  - Every frame lseg-data builds is read into long polars rows (LDG §4.5). An answer it can't attribute is rejected, never guessed.
  - Every error becomes one of the four classes, by what lseg-data 2.1.1 actually raises. Only the service's no-data codes (`TS.*.UserRequestError.*`) count as no data. A flattened transport failure, an HTTP status or a permission code is transient, and an error raised once the session has closed is an outage.
- `fetch_rics` and `fetch_contracts` (`pmcc/data/fetch.py`) consume any `HistoryProvider`:
  - 25-RIC batches. A RIC that doesn't come back with bars is asked again alone, and only that single answer can make it unanswered (a no-data code, or no bars in the window).
  - A failed request is asked again, 3 attempts with backoff, and then becomes an outage.
  - The DEC-45 forms are asked in rounds, with `ric_form_used`, per-contract counts, per-RIC misses and errors.
- The FakeProvider (tests) is the real `LsegProvider` over `FakeLseg`, a port of what lseg-data does with the service's answers. A contract test runs the real library offline on the same answers (TEST-STRATEGY §6).

### 5.2 MarketView: the look-ahead guard

```python
class MarketView(Protocol):                                   # pmcc/strategy/ports.py
    @property
    def now(self) -> datetime: ...                            # decision time = bar_end
    @property
    def root(self) -> str: ...                                # the option root, to name contracts
    # `at` defaults to now; a later `at` raises LookAheadError
    def spot(self, at=None) -> Price | None: ...              # underlying TRDPRC_1 on the bar; None if it didn't trade (DEC-23)
    def stock_quote(self, at=None) -> Quote | None: ...       # the underlying's valid BID/ASK (X-S5 cover, stock marks)
    def quote(self, opt: OptionId, at=None) -> Quote | None: ...          # fresh BID/ASK on the bar, else None
    def chain(self, expiry: date, right: Right, at=None) -> ChainSnapshot: ...   # listed contracts only (DEC-32)
    def expiries(self, kind: ExpiryKind, at=None) -> tuple[date, ...]: ...      # with a listed call, not yet expired
    def close_trades(self, at=None) -> Mapping[datetime, Price]: ...            # close-bar TRDPRC_1 of sessions closed by `at` (rv20, DEC-26)
    def calendar(self) -> SessionCalendar: ...                                  # reference data (DEC-33)
```

`SessionCalendar` lives in `pmcc.domain` (DEC-84), so `strategy/ports.py` can name it without importing `data`. It is reference data, published in advance, so it answers for future days without the as-of gate (DEC-33).

- The implementation (`engine/market_view.py`, DEC-91) has two parts. `MarketData.build` takes the loader's frames, prices the symbol once and indexes it. `MarketData.view(now)` gives a `HistoricalView`. Frames and snapshots stay private.
- Every accessor resolves through a single `_as_of(t)` that raises `LookAheadError` (an `EngineError`) when `t > now`, and refuses a naive time.
- Only session bars are read; any other time has no quote, no spot and an empty chain.
- **Listing (PO, DEC-32):** a contract is listed at t once it has had a valid quote on a session bar at or before t, and it stays listed: on a bar where it has no row, the chain still holds it, with no quote (`NO_QUOTE`). An expiry is listed once one of its calls is. A `ChainSnapshot` holds the listed rows of `PricedSymbol.snapshot`, whose `PricedQuotes` carry the integer BID and ASK (DEC-91).
- Strategies never receive a frame, so this gate is the structural guarantee the Methodology page cites.
- **INV-04 tests** (`tests/property/test_market_view.py`) call every accessor with a later time and expect the raise. A hypothesis test asserts that every answer at `now` equals the answer from a market cut off at `now`, so nothing after `now` can leak in.

### 5.3 Rule protocols

```python
class LongExpiryRule(Protocol):                     # E-L2: candidate expiries
    def candidates(self, view: MarketView) -> tuple[date, ...]: ...
class LongStrikeRule(Protocol):                     # E-L3: the pick across them
    def pick(self, view: MarketView, expiries: tuple[date, ...]) -> Selection | None: ...
class ShortExpiryRule(Protocol):                    # E-S2
    def expiry(self, view: MarketView) -> date: ...
class ShortStrikeRule(Protocol):                    # E-S3
    def pick(self, view: MarketView, expiry: date, long: HeldLeg) -> Selection | None: ...
# LongSelector(E-L2, E-L3).select(view); ShortSelector(E-S2, E-S3).select(view, long)
class EntryTrigger(Protocol):                       # E-T1: SpreadTrigger; fixed_bar in timing runs (DEC-31)
    def can_decide(self, view: MarketView, leg: Leg) -> bool: ...     # the loop selects only on such bars
    def check(self, view: MarketView, option: OptionId, leg: Leg) -> TriggerResult: ...
class Gate(Protocol):                               # G-2…G-5; G-1 is decided at the session's end
    rule_id: RuleId
    def evaluate(self, view: MarketView, d: ShortDecision) -> GateResult: ...   # PASS | FIRE | n/a + values
class ExitRule(Protocol):                           # X-S1…X-S3, X-L1, X-L2
    rule_id: RuleId
    def check(self, view: MarketView, pos: PositionState) -> ExitOutcome | None: ...  # None: not its bar

@dataclass(frozen=True)
class Strategy:                                     # built by strategy.registry.build_strategy(cfg)
    config: StrategyConfig                          # rule_ids: the valid stamps (INV-09)
    long_selector: LongSelector
    short_selector: ShortSelector
    trigger: EntryTrigger
    constraint: StructuralConstraint                # E-S5
    long_contracts: int                             # E-L4; E-S4 matches it
    no_quote: NoQuoteGate                           # G-1
    gates: tuple[Gate, ...]                         # G-2…G-5, spec order; absent means off
    long_exits: tuple[ExitRule, ...]
    short_exits: tuple[ExitRule, ...]
    friday_check: FridayCheck                       # X-S3, whose check time X-S1 also reads
    expiry: ExpiryResolver                          # X-S4, X-S5
```

- A `Selection` carries the contract plus the values that justified it (delta, DTE, spread %, spot). Those values become blotter notes and gate-log values.
- An `ExitOutcome` is fire, pass or unevaluated: a rule on a bar with a fresh quote but a missing input doesn't fire, and is logged (PO, DEC-27).
- Every kind in `config.kinds.KINDS` has a factory in `registry.FACTORIES`, and a test holds the two key sets equal. The quant kinds were built at P4-01 and P4-02 (DEC-95).

### 5.4 Accounting

```python
@dataclass(frozen=True)
class Event:                                         # one blotter row (accounting/events.py)
    time: datetime; side: Side; instrument: OptionId | StockId
    qty: int; limit: Price | None; fill: Price | None; cash_delta: Money   # checked against the fill
    rule_id: RuleId; notes: str; fee: Money
    audit: Mapping[str, AuditValue]                  # bid, ask, capture, selection values, E-S5 terms, funds_after
class Book:                                          # cash + signed positions; apply() is the only mutator
    def apply(self, e: Event) -> "Book": ...         # new Book; EngineError on an uncovered or unequal short
def carry(prev: Marks, fresh: Mapping[Instrument, Price | None], now) -> Marks   # stale carry-forward
def value(book: Book, marks: Marks) -> Valuation     # LongMV, ShortCallMV, StockMV, NAV, stale flags
def regt(book: Book, v: Valuation, marks: Marks) -> RegT   # IM, MM, available funds, excess equity
def funds_after(book: Book, marks: Marks, e: Event) -> Money   # E-L4's check before any entry (INV-08)
```

## 6. Data layer

### 6.1 Fetch flow (`pmcc fetch --symbol S --start D0 --end D1`)

```
0. The symbol comes from configs/universe.yaml (stock RIC, option root), and its strike steps for
   the estimate from its newest probe report; with neither, or with a report that stopped early
   or can't be read, stop before asking anything.
1. Open the session: lseg_session() raises unless open_state == Opened, before any request
   (LDG §4.2). The config is resolved from the repo root, not the caller's CWD.
2. D0 and D1 must be sessions, D0 ≤ D1, or stop before asking anything (a band's step is
   measured on its unit's last session, often D1; DEC-88).
   Stock tape [D0 − 30 sessions, D1]: read from the cache when its unit is there (no request),
   else one hourly request → sessions (its trading days must match configs/calendar.yaml,
   DEC-33), session highs/lows, realized vol (prepare, DEC-88).
3. Build the plan (§6.3). Every cached chain unit must be one the plan would write, with its
   dates and bands, or stop and name them; a band whose ladder on a $10 step would pass $999.99
   stops it too (DEC-12, DEC-88). Print the estimate: units, strikes, and a low and a high figure
   for RIC requests and minutes. --plan-only stops here and writes nothing.
4. Write the stock unit if step 2 fetched it. Then for each unit without a sidecar
   (`SymbolCache.has_unit`; manifest.json can lag a unit moved aside) (pull_units):
     - measure each band's strike step on the unit's last session (DEC-14; the neighbour anchors,
       then the probe report's step, flagged) → integer-cent strike ladders (LDG §4.11)
     - fetch the union of the ladders, hourly, in batches of 25; a RIC that doesn't come back
       with bars is asked again alone; a failed request is asked again (3 attempts, 2 s / 4 s
       backoff), then aborts as an outage; live-only or caret→live per DEC-45 (forms_to_ask)
       (fetch_contracts, DEC-83)
     - check answered + unanswered = requested, per contract (LDG §5)
     - write the parquet, then the sidecar, each whole (temp file → hard link, which never
       replaces a file), then rebuild manifest.json from the sidecars (DEC-46, DEC-87)
5. Close the session and print the coverage summary from the cache (DEC-16): per kind, contracts
   requested, answered and unanswered and the % of calendar session bars with a valid mid;
   near-the-money weekly calls, over each weekly's own dates (a merged monthly unit's weekly
   part only); IV failures: of the session contract-bars with a valid quote before the expiry
   close, how many the chain pricer couldn't solve at the universe's r, by reason (P2-04);
   bands whose step wasn't measured, units that answered nothing, fields that never came back;
   the log file path.
```

- **Resume:** a crash or outage loses at most the unit in flight, and the command exits 1. Re-running the same command plans from the cached stock tape and skips units whose sidecar exists. A process killed between a unit's parquet and its sidecar leaves an orphan parquet, which stops that unit's write (and the loader) until the user moves it aside (§6.4).
- **Never overwrite:** a re-pull means the user moves the unit's parquet and sidecar aside first, e.g. into `{SYM}/superseded/` (LDG §5, DEC-46).
- **Tell the user first:** any pull longer than a couple of minutes starts only after its estimate has been shown (LDG §4.15).

### 6.2 Probes (`pmcc probe`, output in `data_cache/probes/`)

Small requests that answer the spec's open items before the full pull, about 100 per symbol (`pmcc/data/probe/`, DEC-85):

- identifiers, splits and max strike (DEC-12), plus the holiday table against LSEG's daily bars (DEC-33)
- error answers: the `LDError` text and codes for a never-listed RIC (hourly and daily, both forms), a live contract asked with a caret, a field the RIC doesn't carry, and batches holding a failure (DEC-83)
- bar convention (DEC-06) and how LSEG reads request dates (DEC-47)
- field availability (DEC-13) and strike increments (DEC-14)
- long-dated coverage (DEC-08) and the live RIC form (DEC-09)
- history depth (DEC-07)

The stock RIC and daily bars come first, since every later check needs them, then the error answers, then the checks that read quotes (increments, bars, edges, fields, coverage, depth). A never-listed RIC must come back with a no-data code. If one answers anyway, the report stops after the error answers and the command exits 1. Any other failure is asked again like any fetch (DEC-49), so a dead or signed-out Workspace, which shows up only as transient failures (DEC-83), ends as an outage. An outage writes nothing. The report is one JSON file per symbol and day, never overwritten. The date edges use the latest complete week, so nothing asked is in the future.

### 6.3 Fetch plan (DEC-48)

| Unit | Contracts | Strikes | Dates | Needed by |
| --- | --- | --- | --- | --- |
| `stock` | underlying RIC | — | window start − 30 sessions → window end | spot, RV20, sessions, bands |
| `chains/{E}_C` | calls, the weekly expiry E of every week with a session in the window (the last one included when the window ends mid-week) **plus the next one after it** | `[low − 4 steps, high + max(2.5·EMest, 6 steps)]` from regular-session highs/lows over the dates | week-open of the **prior** week → E (the next one after the window: → window end) | E-S3, X-S1…X-S5, G-3 next-week IV, ledger marks, fill check |
| `chains/{E}_P` | puts | `[low − 2 steps, high + 2 steps]` of the week-open session | week-open session of E's week | EM (quant E-S3, X-S3) |
| `chains/{M}_C` | calls, every monthly M that is 120–270 DTE on some session of the window, or nearest 180 DTE | union over the unit's weeks of `[weekLow·e^(−2.0·σ̂·√T), weekHigh]` (≈ δ 0.97 → the money), split into 3 bands of equal price ratio, each probed for its own increment; outer edges padded 2 steps, cuts overlapping 1 | first session M is a candidate → M or window end, whichever is first (DEC-48) | E-L2/E-L3, X-L1/X-L2, ledger marks, fill check |

- **Inputs:**
  - `σ̂` = 1.25 × the highest RV20 in the window (the sample standard deviation of 20 daily log returns of session closes × √252).
  - `EMest` = spot · σ̂ · √(5/252), which is at least the ATM straddle. The spot taken is the unit's high.
  - DTE is calendar days, and T is calendar days ÷ 365 from each week's first session in the unit. These only size what is fetched; pricing's T is DEC-24's.
  - Increments follow DEC-14, probed per band: a unit whose expiry is both a weekly and a long candidate keeps every band.
  - The top of the long band is the week's high, not a delta: a strike at δ 0.70 (quant E-L3's edge) is below spot for any σ and T, while a delta-based edge moves deeper as σ̂ grows (DEC-48).
  - **Estimate:** a plan holds bands, not strikes, and a ladder needs its band's increment. The estimate printed before any option request (§6.1) assumes increments from the symbol's newest probe report: per region, the finest step measured where the anchor answered (DEC-88).
- **Session ranges:** each session's low and high come from its session bars only, and a trade print widens them. The tape's trading days must match the calendar first (DEC-33).
- **Examples:**
  - The spec's CLI example window (Jul 6 → Sep 18 2026) needs the monthlies Nov 20 2026 through May 21 2027 (7 expiries).
  - The PO's window (Mar 30 → Sep 25 2026, DEC-07) needs a warm-up from Feb 13 2026 and the monthlies Aug 21 2026 through Jun 17 2027 (11 expiries). `tests/unit/config/test_universe_file.py` plans it on the shipped calendar.
  - The plan follows the calendar, not the listing, so a planned expiry can come back empty. For NVDA (P1-09), May 21 2027 wasn't listed by Sep 25, so its unit is cached with no rows and the coverage summary flags it. Feb and Apr 2027 were listed partway through their units (DEC-08, DEC-32).
- **Estimate:** the low figure is Σ strikes + 5 per band (the step asks), one form per contract. An hourly batch holding an unlisted strike is asked again one RIC at a time, and a recently expired contract can be asked in both forms, so the high figure is three times that; fetches on the fake market asked 2.3 to 2.5 times the low figure (DEC-88). LDG measured about 44 RIC requests per minute (~1,100 in ~25 min).
  - An 11-week window is about 700 requests, ~16 min per symbol, or ~3–4 h for all 12.
  - The PO's 26-week window scales that by about 2.4, roughly 40 min per symbol or 2–2.5 h for the three (DEC-15), and DEC-48's wider long bands add to it. `--plan-only` prints the real figure.
  - **NVDA, measured (P1-09):** 63 units estimated at 2,263 to 6,789 requests and 52 to 155 min. It took 40 min, with one connection reset that recovered on its retry. The printed figure is conservative.

### 6.4 Cache layout (DEC-46)

```
data_cache/                                   NVDA/ committed, the rest gitignored (DEC-05)
  probes/{SYM}_{YYYYMMDD}.json                one report per symbol and day, never overwritten (DEC-85)
  {SYM}/
    manifest.json                             index rebuilt from the sidecars: every entry, the
                                              data-manifest hash, the units
    stock.parquet            stock.sidecar.json
    chains/{YYYY-MM-DD}_{C|P}.parquet         chains/{YYYY-MM-DD}_{C|P}.sidecar.json
    superseded/                               units the user moved aside to re-pull; never read
    …/*.{random}.partial                     temp files a killed write left; never read, never block
logs/fetch_{timestamp}.jsonl                  gitignored
```

- **One parquet and one sidecar per fetch unit** (§6.3), not per RIC (PO, DEC-46).
  - The parquet is written first and the sidecar last, each whole or not at all. A unit exists once its sidecar does.
  - A write that fails before its sidecar is written leaves no file. Once the sidecar is written the unit is cached; if rebuilding manifest.json then fails, the index stays stale until the next write (the loader never reads it). Every sidecar is read before anything is written, so an unreadable one stops the write first.
  - A process killed between the two leaves a parquet with no sidecar. The next write of that unit refuses it, and so does the loader, until it is moved aside (DEC-87).
  - A unit is moved aside out of its folder, into `superseded/`. A sidecar renamed in place (its recorded unit isn't the one its path names) is refused, never read as the unit it records (DEC-87).
- **Parquet columns** are raw, as returned: `bar_start_utc` (datetime, UTC), `ric`, `expiry`, `strike_cents`, `right` (null for the stock), then one float64 column per field requested (`BID`, `ASK`, `TRDPRC_1`, `OPEN_PRC`, `HIGH_1`, `LOW_1`, `ACVOL_UNS`, `NUM_MOVES`). A field that never came back is an all-null column.
- **Sidecar** (LDG §5):
  - request details: fields requested and fields that came back (LSEG leaves out a field a RIC lacks, DEC-83), dates, interval, tz convention, the strike step per band (DEC-84) and how it was found: the session, anchors asked, strikes that answered, and `measured`, `neighbour` or `probe_report` (DEC-14, DEC-88)
  - results: counts (requested = answered + unanswered, per contract), `ric_form_used`, `unanswered` (each contract's RICs asked, with the reason and codes), `errors`
  - the pull date, the parquet's name and sha256, and the unit's manifest entries
- **Manifest entry,** one per contract asked: `instrument` (OCC symbol, or the stock's RIC), `unit`, `status`, `ric` and `form` (the RIC that answered), `rows`, `first_bar`, `last_bar`, `fetched_at`, and `sha256` (of the contract's bars, without the RIC).
- **Data-manifest hash:** the sha256 of every entry's content: identity, unit, status, rows, first and last bar, and the bars' sha256. It leaves out `fetched_at`, `ric` and `form`, so re-pulling identical bars, under either RIC form, never changes it, and another symbol's fetch never does (PO, DEC-46).

### 6.5 Loading (`data/load.py`, no network)

`load_symbol(root, symbol, calendar)` takes these steps:

1. Read the sidecars, never `manifest.json`. Refuse a parquet that is missing or whose sha256 differs, an orphan parquet, or a symbol with no stock unit (`CacheError`).
2. Polars scans, one per unit.
3. Quantize prices to $0.0001 units (Int64), exactly as `Price.from_dollars` (DEC-44, DEC-87).
4. Add `bar_end` in ET.
5. Tag session bars (`session_bar`).
6. Mark quote validity (`valid_quote`): BID > 0, ASK > 0 and ASK ≥ BID.
7. Check the stock tape's trading days against the calendar over the stock unit's dates (`CalendarMismatchError`, DEC-33).

It returns `SymbolData`: the stock frame, chain frames keyed by (expiry, right), the calendar, and the data-manifest hash. Every bar is kept for provenance, but only session bars reach MarketView.

## 7. Pricing

Black-Scholes with q = 0 (Spec › Greeks and pricing), with units per DEC-24:

```
d1 = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)        d2 = d1 − σ·√T
C  = S·N(d1) − K·e^(−rT)·N(d2)                P  = K·e^(−rT)·N(−d2) − S·N(−d1)
δC = N(d1)   δP = N(d1) − 1   Γ = φ(d1) / (S·σ·√T)   ν = S·φ(d1)·√T
θC = −S·φ(d1)·σ/(2√T) − r·K·e^(−rT)·N(d2)     θP = −S·φ(d1)·σ/(2√T) + r·K·e^(−rT)·N(−d2)
```

- **T and DTE (DEC-24):** T is elapsed time from the decision to the expiry session's close, in years, ACT/365, measured in UTC so a clock change counts its hour (`years_to_expiry`, over `years_between`, which the Greek attribution's Δt also uses; DEC-102). DTE is calendar days from the decision's ET date (`days_to_expiry`).
- **Vectorized IV solver** (`implied_vol`) over any number of lanes (DEC-89):
  - **Codes, checked in this order:** `EXPIRED` (T ≤ 0), `NO_QUOTE`, `NO_SPOT` (the underlying didn't trade on the bar), `BELOW_FLOOR` (mid < max(0, S − K·e^(−rT)) for a call, max(0, K·e^(−rT) − S) for a put), `ABOVE_CAP` (mid ≥ S for a call, K·e^(−rT) for a put), then `NO_CONVERGENCE` or `OK`.
  - **Bracket:** σ ∈ [1e-4, 5.0]. A lane no vol in it can price is `NO_CONVERGENCE` before iterating.
  - **Newton step,** safeguarded: each lane keeps a bracket holding its root, and a step that would leave it, or a vega < 1e-8, bisects instead. It starts from Manaster and Koehler's vol.
  - **Stop:** at |model − mid| < 1e-9·max(1, mid), or a bracket narrower than 1e-12, or after 100 iterations (`NO_CONVERGENCE`). It pins σ to 1e-6 wherever vega ≥ 1e-3·max(1, mid); where the price barely moves with vol, σ is looser but still reprices the mid (DEC-89).
  - **Test:** a scalar `scipy.optimize.brentq` solve serves as the reference.
- **Chain pricing** (`chain.py`):
  - `price_quotes` prices one bar's contracts from their quotes. It returns, per contract: the exact mid, spread % of mid, IV, code, δ, Γ, θ, ν, extrinsic (mid − max(0, S − K) for a call, Spec › E-L3; mid − max(0, K − S) for a put), and eligibility, which means the IV solved. It uses only that bar's data.
  - `price_symbol` prices every session bar of every chain unit that `load_symbol` loaded, one vectorized pass per unit. Spot is the stock's TRDPRC_1 on the same `bar_end` (DEC-23), and T comes from `years_to_expiry`.
  - `PricedSymbol.snapshot(bar_end, expiry, right)` is memoized per (bar, expiry, right), so all runs for a symbol in a batch share it. `PricedSymbol.codes(expiry, right)` counts a unit's outcomes for the coverage summary (DEC-16).
  - NVDA's full window, 400,784 session contract-bars, prices in about 1.4 s.
- **Measures** (`measures.py`): `session_close()` and `itm_at_expiry()` (DEC-23); `atm_strike()`, `atm_iv()` and `expected_move()` (DEC-25); `rv20()` (DEC-26). They take what MarketView hands them: listed strikes, fresh quotes, and close-bar trades by `bar_end`.
- **Held contracts** with a failed IV use DEC-27: a call below its floor gets δ = 1, Γ = ν = 0, θ = −r·K·e^(−rT), and stays ineligible. Any other failure leaves its Greeks unknown.

## 8. Engine

### 8.1 Bar loop (order per DEC-20)

```
for bar in session_bars(window):                             # ascending bar_end (engine/loop.py)
    view = data.view(bar.end)
    trader.cover_short_stock(view)                           # X-S5 follow-up
    if week_open: trader.check_long(view)                    # X-L1, X-L2 at the first fresh long quote
    trader.enter_long(view)                                  # if flat: E-L1…E-L4, session-frozen selection
    trader.exit_short(view)                                  # X-S1, X-S2 any bar; X-S3 on the check bar
    if week_open: trader.enter_short(view)                   # E-S1…E-S5, gates, gate-log row
    if week_open and close bar: trader.close_week(view)      # the row for an undecided week
    if the short's expiry close bar: trader.resolve_expiry(view, closing_spot)   # X-S4 / X-S5
    check_event(each new row); marks; value; regt; ledger_row; check_bar(...)
# X-E1: the final ledger row marks everything at the last bar; nothing is liquidated
```

The engine's ledger row also records the bar's spot and each held leg's IV and Greeks from its chain row (`engine/greeks.py`), and every option fill's audit the IV it filled at (`fill_iv`), so the Greek attribution reads what the engine saw (P6-04). The published ledger keeps the delta alone; `fill_iv` is published in the audit (DEC-102).

### 8.2 Leg state machines (DEC-21, DEC-22, DEC-28, DEC-34)

```
LONG   FLAT ──selector returns c (session s)──────────────► CANDIDATE(c, s)
       CANDIDATE ──E-T1 passes ∧ E-L4 funds ok──────────► HELD                       BUY  E-L1
       CANDIDATE ──E-L4 would go negative────────────────► FLAT (flag; retry next session)
       CANDIDATE ──session ends──────────────────────────► FLAT (retry next session)
       HELD ──week-open, first bar with a fresh long quote: checked once (short entry waits for it)
       HELD ──checked ∧ (δ < 0.50 ∨ DTE < 90)────────────► FLAT → re-entry this session  SELL X-L1|X-L2
            (δ unknown: X-L1 unevaluated, logged; no fresh long quote all session: not checked)

SHORT  (week-open session only)
       IDLE ──long held and checked ∧ no short this week─► SELECTING
       SELECTING ──selector returns c (on a bar E-T1 can_decide)► FROZEN(c)
       FROZEN ──E-T1 passes──► DECIDE ──G-2…G-5 all pass──► OPEN                     SELL E-S1
                                      ├─first gate fires──► SKIPPED(rule)
                                      └─funds would go < 0► SKIPPED(E-L4)
       SELECTING | FROZEN ──session ends─────────────────► SKIPPED(G-1)
       no long, or not checked ──session ends────────────► SKIPPED(E-S1) (or X-L1|X-L2: re-entry unfinished)
       OPEN ──X-S1 | X-S2 | X-S3─────────────────────────► CLOSED                     BUY  X-S*
       OPEN ──X-S3 fires without a quote─────────────────► PENDING (fills at the next bar with one)
       OPEN ──expiry close, OTM──────────────────────────► EXPIRED                    EXPIRE X-S4
       OPEN ──expiry close, ITM──────────────────────────► ASSIGNED                   ASSIGN + stock SELL X-S5
       ASSIGNED ──first valid bar, next session──────────► covered                    stock BUY X-S5
```

Each week-open session writes exactly one gate-log row per strategy (DEC-22): the decision bar's gates (G-1 recorded as passed, G-2…G-5 each pass, fire or n/a), or, when the week isn't decided, G-1 fired with the rest `not_evaluated`, or `E-S1`/`X-L1`/`X-L2` with no gates. A short entry that would leave available funds negative is skipped as `E-L4` (DEC-91). The closing spot for X-S4/X-S5 is the close bar's trade, else the session's last trade before it (PO, DEC-23).

### 8.3 Fill simulator (Spec › Fill model)

```
fill(time, side, instrument, qty, quote, model, rule_id, notes, audit) -> Event | None   # engine/fills.py
  no fresh BID or no fresh ASK → None                     # no fill, never an invented print (INV-03)
  mid = (BID + ASK)/2 ; half = (ASK − BID)/2              # exact rationals; capture read as its decimal
  price = mid + capture·half  (BUY)   |   mid − capture·half  (SELL)   → quantized to Price, round half-even
  cash_delta = −price·multiplier·qty (BUY) | +price·multiplier·qty (SELL)   − fee·contracts (options only)
  audit += {bid, ask, spread_capture}                     # so verify can re-derive the fill
```

The blotter's Limit column is the mid at decision time; its Fill column is `price`.

### 8.4 Runtime invariants

| When checked | Invariants |
| --- | --- |
| After every bar | INV-01, 02, 05, 07, 10 |
| At every event | INV-03, 06, 08, 09 |

A failure logs `invariant.failed` and raises `InvariantViolation` (an `EngineError`); the run writes nothing and exits non-zero. INV-03 is re-derived from the event's audit (BID, ASK, capture); the X-S5 stock sale at the strike isn't a quote fill and is exempt (`engine/invariants.py`).

## 9. Accounting and Reg T

- **Cash:** changes only in `Book.apply(event)` (INV-01).
- **Marks:** a fresh mid, or else the last fresh mid flagged `stale`. A stale mark never fills and never triggers a rule (DEC-27). The stock after X-S5 is marked at its BID/ASK mid too (PO, DEC-23); with no valid stock quote on the assignment bar, the closing spot seeds its mark, flagged stale (DEC-91).
- **Market values:**
  - LongMV = mark × 100 × qty.
  - ShortCallMV = mark × 100 × qty.
  - StockMV = shares × mark, with shares < 0 when short.
- **NAV** = cash + LongMV − ShortCallMV + StockMV (INV-02).
- **Reg T**, per the Spec table:

  | Component | Requirement |
  | --- | --- |
  | Long call | LongMV (100%) |
  | Covered short call | $0; an uncovered short is an `EngineError` |
  | Short stock with covering long calls, initial (PO, DEC-10) | $0 beyond the proceeds |
  | Short stock with covering long calls, maintenance (PO, DEC-10) | min(10% × long strikes × shares + the longs' OTM amount, max($5 × shares, 30% × \|StockMV\|)) |
  | Short stock without them, initial | 50% × \|StockMV\| |
  | Short stock without them, maintenance | 30% × \|StockMV\| |

  - IM = long + short-stock initial. MM = long + short-stock maintenance. A requirement that isn't a whole $0.0001 is rounded up (DEC-91).
  - Available funds = NAV − IM. Excess equity = NAV − MM.
- **Entry check:** before a long or short entry, `funds_after` computes the post-trade available funds, with the new leg marked at its limit; they must be ≥ 0. The value is recorded in the event's audit (INV-08).
- **Ledger flags:**
  - `stale_long`, `stale_short`, `stale_stock`
  - `funds_negative` — the site states the position couldn't have been held in a real Reg T account
  - `entry_blocked`, `exit_pending`

## 10. Configuration

| File | Holds |
| --- | --- |
| `configs/_shared.yaml` | Rules identical in both strategies (E-T1, E-L1, E-L4, E-S1, E-S2, E-S4, E-S5, G-1, G-2, all exits) and the fill model (`spread_capture`, `fee_per_contract`). E-L4's params include the starting cash's rule, `cash_multiple` and `cash_round_to`, which `pmcc calibrate` reads (DEC-30, DEC-93). Only ever extended: it has no `id` |
| `configs/baseline_pmcc.yaml` | `extends: _shared.yaml`; baseline E-L2, E-L3, E-S3; `report: {detail: full}` (DEC-54) |
| `configs/quant_pmcc.yaml` | `extends: _shared.yaml`; quant E-L2, E-L3, E-S3; G-3, G-4, G-5 (P4-03, DEC-95); `report: {detail: full, sections: [gate_log, greek_attribution]}` (DEC-54) |
| `configs/ablations/a1…a5.yaml` | `extends: ../quant_pmcc.yaml` + `overrides` keyed by rule ID: A1 and A2 `replace` the quant selectors with the baseline's rules, word for word; A3, A4 and A5 `remove` G-3, G-4 and X-S1 (P4-03, DEC-95); `report: {detail: summary}` (DEC-54) |
| `configs/sensitivity.yaml` | friction, timing and grid variants (§11): three lists, `friction`, `timing` and `grid`, each entry a strategy written inline as an ablation file is (`id`, `name`, `extends` a strategy file, `report: {detail: summary}`, then `fill_model` or `overrides`). A variant's run ID is its strategy's ID, `--`, a suffix; its list is its robustness table (DEC-65). Loaded by `pmcc/config/matrix.py` (P5-02, DEC-100, DEC-101) |
| `configs/universe.yaml` | the window (DEC-07); r with the quote, series, date and source it came from (DEC-11); symbols with stock RIC and option root (DEC-12); last, the `starting_cash` block `pmcc calibrate` writes: the value, whether it's provisional, the calibration cash and each run's first long entry (DEC-30, DEC-93). Above that block, `bootstrap: {seed}`, every CI's seed (P6-05, DEC-61). Loaded by `pmcc/config/universe.py`, which checks the window's sessions against the calendar (DEC-86) |
| `configs/calendar.yaml` | NYSE holidays and early closes 2025–2027, with sources (DEC-33) |

A rule entry (DEC-52):

```yaml
- id: G-3
  name: Event week
  kind: event_ratio_gate
  params: {max_ratio: 1.20}
  condition: Front-week ATM IV ÷ next-week ATM IV > {max_ratio:.2f}
  action: Skip the week; keep the long
  rationale: >-
    G-3 detects events (usually earnings) from the chain itself, with no external calendar: an
    event priced into the front week lifts its IV above the following week's. A ratio is used
    instead of a vol-point difference so the threshold scales across low- and high-volatility
    symbols.
```

An ablation (DEC-53):

```yaml
id: quant_pmcc--a3
name: "A3: quant without the event gate"
extends: ../quant_pmcc.yaml
overrides:
  G-3: {remove: true}
```

- **Kinds (DEC-90):** a `kind` implements exactly one spec rule ID and has a params model (`pmcc/config/kinds.py`): strict, closed to unknown keys, range-checked. Dollars are held as `Price` or `Money` (DEC-44); a clock time is a quoted `"HH:MM"`. `strategy/registry.py` maps each kind to its code (P3-06).
- **Resolution:** the strategy YAML's `extends` chain and `overrides` (`pmcc/config/extends.py`) → frozen `StrategyConfig`, rules in the spec's order → plus `universe.yaml`'s window and r → frozen `RunConfig`.
  - A file extends one parent, by a relative path with forward slashes to a `.yaml` file.
  - A child adds rules the parent lacks and changes the parent's only through `overrides` keyed by rule ID: `params` (a patch), `replace` (a whole rule) or `remove: true`.
  - `fill_model` is patched field by field. `id` and `name` are never inherited.
  - `report` (what the results keep and the page shows, DEC-54) is never inherited, like `id` and `name`: a file without one keeps a summary, so a variant is a summary unless its own file says otherwise. It is part of the config hash.
- **Required rules:** every spec rule but G-3, G-4, G-5 and X-S1, the layers variants switch off (DEC-53).
- **Rule text (DEC-52):** `condition`, `action` and `rationale` are templates with bare-name placeholders (`{max_delta:.2f}`), rendered by `Rule.text()`. Every param must appear in the condition or the action.
- **`config_hash`:** the sha256 of `RunConfig` as JSON with sorted keys, no whitespace and UTF-8. It covers the resolved strategy and the window and r, not the file layout or the symbol list (DEC-90).
- **Load errors:** all of these fail at load:
  - an unknown `kind`, or a kind for another rule ID;
  - an unknown or missing param, or one out of range;
  - a rule defined twice, or an override of a rule no parent defines;
  - a missing required rule;
  - a placeholder with no param, or a param no placeholder in the condition or action uses;
  - an `extends` that is absolute, has a backslash or isn't a `.yaml` file;
  - an `extends` cycle.

## 11. Runs, batch and determinism

The run matrix per symbol has 24 runs:

| Family | Run IDs | Count | Detail (DEC-54) |
| --- | --- | --- | --- |
| Strategies | `baseline_pmcc`, `quant_pmcc` | 2 | full |
| Ablations | `quant_pmcc--a1` … `--a5` | 5 | summary |
| Friction | `{baseline,quant}_pmcc--sc025`, `--sc050` | 4 | summary |
| Entry timing | `baseline_pmcc--t1` … `--t7`: E-T1 replaced by `fixed_bar_trigger`, the short decided on session bar k of the week-open session only (DEC-31) | 7 | summary |
| Parameter grid | `quant_pmcc--k075`, `--k125`, `--g4r090`, `--g4r110`, `--g3r110`, `--g3r130` | 6 | summary |

`run_matrix(universe)` (`pmcc/config/matrix.py`) builds the 24 in this order: the two strategy files, `configs/ablations/*.yaml`, then `configs/sensitivity.yaml`'s friction, timing and grid lists (DEC-100). `run_families()` gives each run ID its family (strategy, ablation, friction, timing or grid) from where its config sits; the robustness tables are the families (DEC-101).

`pmcc batch [--universe configs/universe.yaml] [--cache data_cache] [--out results]` (`pmcc/batch.py`, P5-03, DEC-100) works as follows:

1. Per symbol: load once, price chains once, then run the matrix, writing each result as `pmcc run` would, byte for byte. Then write `{SYM}/coverage.json`, which loads and prices the cache a second time, as the fetch summary does, and `{SYM}/robustness.json` from the runs' summaries, only when every run succeeded (P6-06, DEC-101). Then `{SYM}/fill_check.json` from the cache the runs loaded: `pmcc.data.fillcheck` pairs each print with its mid, and `pmcc.analytics.fillcheck` fits them (P6-07, DEC-64, DEC-103). Last, the suitability screen reads quant's picks and G-3 at each week's first week-open bar on the market the runs priced, and the worker hands the row back in its outcome, unwritten (P6-08, DEC-66, DEC-104).
2. Each symbol runs in its own spawned single-worker process pool, at most one per CPU at once (never forked, so Windows and Linux run alike, DEC-58), so a worker that dies breaks only its own symbol. A job carries everything its worker needs; each worker logs to its own file.
3. A failed run writes nothing and is reported, and the symbol's other runs go on; a symbol whose cache won't load, whose coverage, robustness or fill-check file can't be written, whose screen can't be read, or whose worker raises or dies, is reported without stopping the others, and so is a universe file that fails (DEC-101). The batch exits non-zero if anything failed, and its summary line counts each kind.
4. Universe-level outputs are computed last, in the parent, and only when nothing failed, from each symbol's two strategy runs read back from their files: `universe/headline.json` (P6-01) and `universe/pooled.json` (P6-05, seeded as every run's CI is), then `universe/pooled_fill_check.json` from each symbol's fill check read back (P6-07, DEC-103), and `universe/suitability.json` from each symbol's screen row (P6-08, DEC-104). A writer that fails is reported and fails the batch; the others still write (DEC-101).
5. `--universe` may only name `configs/universe.yaml`, so every run's starting cash comes from there (DEC-30).

Determinism controls (INV-13):

| Source of drift | Control |
| --- | --- |
| Float accumulation in cash/NAV | Integer money (DEC-44) |
| Aggregation and row order | Explicit sorts; polars `maintain_order=True` |
| Randomness (bootstrap) | A fresh PCG64 per CI, seeded from `universe.yaml`'s `bootstrap.seed`; seed recorded in every CI (DEC-61) |
| Float sums (analytics) | the metrics' `statistics.fmean` and `stdev` sum exactly; the bootstrap's numpy means are fixed by the weeks and their order; the Greek attribution sums each float term as an exact `Fraction`, so its totals and residual line don't depend on order; the fill check's OLS sums whole $0.0001 units and its median gap is exact; the screen's spreads and credits are exact fractions and its float means `fmean`s; ratios come from integer money (DEC-101, DEC-102, DEC-103, DEC-104) |
| Parallelism | Runs are independent; one file each; content never depends on completion order |
| Serialization | Canonical JSON (DEC-50) |
| Clock | `run_timestamp` only in the manifest, excluded from INV-13 with `git_sha` (DEC-50) |
| Environment | `uv.lock`, Python 3.12 pin, `package-lock.json` |
| Operating system | LF line endings (`.gitattributes`; writers pass `newline="\n"`), `tzdata` for time zones, bash for recipes, so Windows and Ubuntu produce the same bytes (DEC-58) |

## 12. Results contract and export

```
results/                            committed; every file here is one the pipeline writes (verify)
  universe/pooled.json              pooled metrics + week-block bootstrap CIs
  universe/headline.json            per-symbol headline table
  universe/pooled_fill_check.json   the fill check's fits over every symbol's pairs (DEC-103)
  universe/suitability.json         symbol suitability screen: a row per symbol, each measure
                                    with the weeks it's over (DEC-66, DEC-104)
  {SYM}/{run_id}.json               RunResult, full or summary
  {SYM}/robustness.json             ablation, friction, timing and grid tables
  {SYM}/fill_check.json             shorts and longs: every print/mid pair as columns of mid,
                                    trade and spread (DEC-05), and the fit: slope, intercept,
                                    R², N, median |trade − mid| ÷ spread, locked quotes (DEC-64,
                                    DEC-103); NVDA's is 3.9 MB, under its own 8 MB guard
  {SYM}/coverage.json               derived data-coverage counts: per unit kind, contracts and
                                    valid-mid share; IV failures of iv_priced bars; the strategies'
                                    stale-mark rate; unavailable fields (pmcc batch, DEC-100)
```

`pmcc export` derives two more files from the results into its output, never committed under `results/`, so they can't disagree with the runs (DEC-96): `index.json` (per symbol, its runs with their detail, sections, path, data source, config hash and commit, and the analytics files present; the window, r and starting cash every run shares; the exporter's version) and `rules.json` (per run ID, the rules as it ran them: params, rendered text, and a variant's changes against its strategy).

`RunResult` (pydantic; JSON Schema written by `pmcc export`), schema version 2 (P4-05, DEC-96). The detail is the strategy's `report.detail` (DEC-54): a summary run keeps no rows. Every run's summary holds its analytics (P6-01, P6-02, P6-05; DEC-60 to DEC-62), and a full run keeps its cycles and its attribution: by leg, and by Greek where its `report.sections` lists `greek_attribution` (P6-03, P6-04; DEC-63, DEC-102). A result written before P6 would have null analytics and no fill IV and still validate; the committed results were re-run with both at P6-09 (DEC-101, DEC-102, DEC-105):

```
schema_version  2
manifest    run_id, symbol, strategy_id, git_sha, git_dirty, config_hash, data_manifest_hash,
            lock_hash, run_timestamp, data_source (lseg|synthetic), pmcc_version
config      the resolved RunConfig, dumped exactly as config_hash covers it (dollars as "0.1000");
            its strategy's report {detail, sections} tells the site what to show
rule_text   {rule_id: {condition, action, rationale}}, rendered from the params
starting_cash
summary     metrics{pnl, returns, drawdown, underwater, sharpe, sortino, weekly_return CI},
            cycle_stats, exit_mix {rule: count, all of X-S1…X-L2; the file sorts its keys},
            skips_by_rule, nav_close[], weekly_returns[] (P6),
            flag_counts {flag: ledger rows}, invariants[{id, held}] (P4-05)
blotter[]   time, instrument{…}, side, qty, limit, fill, fee, cash_delta, rule_id, notes, audit{…}     full
            (an option fill's audit holds fill_iv, P6-04)
ledger[]    time, long{instrument{…}, qty, mark, delta, stale}, short{…},
            stock{instrument{…}, shares, mark, stale}, cash, nav, im, mm, available_funds,
            excess_equity, flags[]                                                                   full
gate_log[]  session, decision_time, selected{…}, gates[{rule_id, status, values, reason}],
            outcome{kind, rule_id}, notes                                                          full (every full run; report.sections only decides what the page shows)
cycles[]    week_open, week_final, outcome, rule_id, long_held, credit, buyback, long_cost,
            exit_rule_id, pnl                                                                        full (P6-02)
attribution leg{short_credits, short_buybacks, net_short_premium, short_open, assignment_stock_pnl,
            long_pnl, long_intrinsic, long_extrinsic, series[{session, long_pnl, net_short_premium}]},
            greek{legs[{leg, change, bars_held, bars_unattributed}],
            rows[{leg, component, dollars, share_of_change}], residual[{time, cumulative}]}
            (greek if declared)                                                                     full (P6-03, P6-04)
```

An `instrument` is `{ric, occ, kind, expiry, strike}`: `ric` is the RIC the cache answered with, so a row leads to its raw quotes; the stock has `kind: stock` and null `occ`, `expiry` and `strike`. The audit's `bid`, `ask` and `funds_after` are $0.0001 units, as the engine records them (DEC-91), and dollars inside the audit and the gate-log value maps are exact 4-dp strings (`"82.9900"`; PO, DEC-92); a value in those maps is always a JSON scalar.

- **Canonical JSON** (DEC-50, `export/canonical.py`):
  - one line, sorted keys, no whitespace, UTF-8 with non-ASCII kept, one final newline
  - dollars and prices to 4 dp, as JSON numbers (the config section keeps its hashed dump); IV, Greeks and ratios to 6 dp
  - ISO-8601 times with offset
  - `null` instead of NaN
  - the config section's floats print unrounded, as `config_hash` covers them
  - INV-13 compares whole files after dropping `manifest.run_timestamp` and `manifest.git_sha` (`drop_volatile`; PO, DEC-50)
  - `\n` line endings on every OS
- **`pmcc export --results results/ --out web/public/data/`** (`export/site.py`, DEC-96):
  - refuses results that fail `pmcc verify`, a dirty tree aside (a local preview; CI's verify keeps dirty results off the site), and writes nothing then
  - rebuilds the output directory whole, but only when it's missing, empty, or holds nothing but files an export writes; one foreign file and it touches nothing (`--schema-only` too)
  - writes `schema/*.schema.json`, one per model (`export/schema.py`), in serialization mode: dollars are numbers, a result's config is its dump, and every field is required
  - copies every results file byte for byte, and writes `index.json` and `rules.json`
  - `--schema-only` writes only the schemas, which the site's types need (`just check`)
- **`pmcc verify results/`** (`export/verify.py`, CI, DEC-51, DEC-96):
  - layout: every file is one the pipeline writes, where it writes it
  - schema validation, through the same pydantic models the schema comes from
  - canonical bytes; the manifest's symbol and run ID match the path
  - `git_dirty` must be false; the config hashes to `manifest.config_hash`; the rule text is the config's
  - every run's summary records every runtime invariant as held
  - a full run's rows re-derive INV-01, 02, 03, 05, 06, 07, 08, 09 and 10 (`export/rederive.py`, with its own arithmetic, not the engine's), judging each row by what it does (opens a long or a short), and the ledger's positions must be what the rows booked
  - an analytics file must be canonical and hold its own folder's symbol

## 13. Frontend

```
web/                            P4-06 (DEC-97); Node 22 (.nvmrc, engines)
  scripts/gen-types.mjs         public/data/schema → src/types/generated/ (+ version.ts)
  scripts/dist-guard.mjs        the dist guard (P4-07): no LSEG or Google Fonts host in web/dist
  src/
    main.tsx    the entry: fonts, stylesheet, App
    app/        App (HashRouter + IndexProvider), routes (the table), AppShell (command bar, banners),
                pages (paths), site (repo URL, wordmark)
    data/       loader (index; a per-file cache of runs and a symbol's or the universe's files;
                schema_version check), IndexContext, useRun (useRun, useSymbolFile,
                useUniverseFile; P7-02), state (with both(), two loads as one)
    types/generated/   json-schema-to-typescript output (gitignored; regenerated before typecheck/build)
    theme/      tokens.css (theme.py's values), shell.css (PAGE_CSS, ported), index.css (Tailwind +
                tokens), tokens.ts (with DEC-04's chart roles), fonts.ts; echarts.ts (the modular
                core, the base option and series builders, P7-01)
    components/ CommandBar, Readouts, PanelGrid, Panel, Note (Details, Empty, Loading), PageFrame,
                ManifestFooter, WarningBanner, ui/select; DataTable (sorting, toggle filters,
                virtualization) and cells (RuleLink, Instrument, KeyValue) at P7-01;
                RobustnessTable (a robustness.json table, P7-02);
                charts/: Chart, axis (trading time), tooltip, and one option builder per chart
                (account, legs, residual; navCompare at P7-02) (P7-01, DEC-106, DEC-110)
    pages/      Strategy (P7-01) and strategy/ (its sections, tables and each close's Trade P&L);
                Comparison (P7-02) and compare/ (its figures and panels, DEC-110);
                Rules, Methodology, Universe, Data (placeholders until their P7 item);
                placeholder (the placeholder helpers)
    lib/        cn (shadcn/ui's class joiner)
    format/     money (and chart ticks, signed), number (percent, ratio, IV), time (ET), hash,
                rule (a rule ID's plain label for the filters, DEC-107)
    test/       fixtures (an index, two full runs, NVDA's robustness and the pooled universe,
                typed against the schema); page (the page tests' helpers); setup (Vitest: jsdom's missing canvas, for ECharts)
  e2e/          smoke.spec.ts: the Playwright smoke test (P4-08, DEC-99); playwright.config.ts
                serves web/dist with vite preview; tsconfig.e2e.json type-checks it
  public/data/  written by pmcc export (gitignored)
```

- **Data:**
  - `index.json` loads at startup.
  - Run files, and a symbol's or the universe's files (found by their key in the index), load on demand when the symbol or page changes, and are cached in memory by path.
  - A `schema_version` mismatch shows an error banner.
- **State:**
  - The URL is the state; the symbol comes from the route.
  - Symbol-less routes remember the last symbol for links back.
  - One theme, so no theme state (PO, DEC-03).
- **Types:** `npm run gen:types` runs before `typecheck` and `build`. A schema change the UI doesn't handle fails `tsc` (INV-14).
- **Charts:** modular `echarts/core` via `echarts-for-react`, drawn as SVG. The theme is built from the CSS variables when a chart renders. Animation is off. Each chart's option is a pure function of the palette and the result's rows (`components/charts/`), tested without a DOM.
- **Tables:** TanStack Table (v9, its sorting feature) plus TanStack Virtual for the ledger and blotter, at a fixed row height. Filters run before TanStack sees the rows, so a filter needn't be a column (DEC-106).
- **Tests:**
  - Vitest (jsdom; `css: true`, so a stylesheet read `?raw` has its text): formatters, the loader, every route, the strategy and comparison pages over the fixture runs, the chart options, the data table, token-lint, contrast and DEC-04's roles.
  - Playwright: every route, console errors, cross-origin requests, screenshots, and both strategy pages' and the comparison page's numbers, charts and tables on the built site.
- **Build:** Vite `base: './'` with HashRouter (DEC-73). The static `dist/` makes no cross-origin requests (fonts are bundled, DEC-72).

## 14. Tooling and CI/CD

Recipes run under bash (`set shell := ["bash", "-cu"]`): Git Bash locally, bash on the CI runners (DEC-58). Python tools run through `uv run --frozen` (DEC-77). A recipe whose command isn't built yet fails with exit 1, naming its backlog item (DEC-78).

| just recipe | Does |
| --- | --- |
| `setup` | `uv sync --frozen`, `npm ci` in `web/`, `pre-commit install` |
| `check` | pre-commit on all files, pytest, `pmcc export --schema-only`, web lint/typecheck/vitest |
| `test *ARGS` | pytest (dev profile unless `HYPOTHESIS_PROFILE` is set), extra args passed through |
| `probe SYM` · `fetch SYM START END *ARGS` | LSEG probes / pull (local only); `fetch` passes extra args, e.g. `--plan-only` |
| `run SYM CONFIG` · `batch` · `calibrate *ARGS` | backtests; `batch` runs the 24-run matrix on every universe symbol (DEC-100); `calibrate` passes extra args, e.g. `--check`, or `--symbol NVDA` once a final block is removed (DEC-93) |
| `export` · `verify` | site data / results validation |
| `web-dev` · `web-build` · `e2e` · `serve` | frontend; `web-dev` and `web-build` run `export` first, and `web-build` the dist guard after; `e2e` builds, then runs the Playwright smoke test |
| `reproduce` | cached data → batch → verify → export → web build (Spec › CLI) |

CI (`.github/workflows/ci.yml`, on push and PR; DEC-79):

| Job | Steps |
| --- | --- |
| `python` | credentials guard (`git ls-files`) → setup-uv → `uv sync --frozen` → `pre-commit run --all-files` (ruff, format, pyright, guards) → `pytest` (ci profile) → `pmcc verify results/` (P4-05) |
| `web` | `uv sync --frozen` → `pmcc export --out web/public/data/` (it verifies the results first) → setup-node from `web/.nvmrc` → `npm ci` → `lint` → `typecheck` (runs `gen:types`) → `vitest` → `build` → dist guard (`npm run guard`) → Chromium (`npx playwright install --with-deps chromium`) → Playwright smoke (`npm run e2e`, INV-15) → upload the screenshots (always) → upload the Pages artifact (`main` pushes only), so a failed smoke test blocks the deploy (P4-07, P4-08; DEC-98, DEC-99) |
| `deploy` | `main` pushes only; needs `python` and `web`; the only job with `pages: write` and `id-token: write`; `actions/deploy-pages` to the `github-pages` environment |

- **Dist guard** (`web/scripts/dist-guard.mjs`, DEC-98): fails if any file in `web/dist` references `localhost:9000`, an `lseg`/`refinitiv` URL, or `fonts.googleapis.com`/`fonts.gstatic.com`, or if the build is empty. It matches hosts, not words: the results say `"data_source":"lseg"`, and the footer's github.com links and r's FRED source are expected. The smoke test also fails on any cross-origin request (P4-08, DEC-99).
- **Pre-commit:** ruff, ruff-format, pyright, check-yaml, end-of-file-fixer (never on `data_cache/`, DEC-05), check-added-large-files (500 KB; 2 MB under `results/` and `data_cache/`, DEC-92, DEC-05; 8 MB for `results/*/fill_check.json`, DEC-103), detect-private-key, and a local hook that rejects a staged `lseg-data.config.json`.
  - ruff and pyright run through `uv run --frozen`, at the `uv.lock` versions. The reference files are excluded from every hook (DEC-57, DEC-77).
  - The CI pytest step sets `HYPOTHESIS_PROFILE=ci`.

## 15. Logging, errors and security

- **Logging:** structlog JSON, one event per line, to stderr and to `logs/{command}_{timestamp}.jsonl` (DEC-80).
  - A command calls `pmcc.log.configure_logging(command)` once at startup; every other module calls `structlog.get_logger()`.
  - Each event carries `event`, `level`, `timestamp` (ISO 8601, UTC) and `command`; exceptions are rendered as text in `exception`. Level INFO and up.
  - Every soft fetch failure is one `fetch.ric.unanswered` event, logged once per RIC the service left unanswered, with `symbol`, `unit`, `ric`, `form` (for an option RIC), `reason` (`no_data` or `empty`), `codes` and `message` (Spec › Stack, DEC-83). `fetch.batch.rejected` and `fetch.retry` carry `size` and the error.
  - Event names: `fetch.plan`, `fetch.unit.start|done`, `fetch.increment.unmeasured`, `fetch.ric.unanswered`, `fetch.batch.rejected`, `fetch.retry`, `fetch.abort.outage`, `fetch.coverage`, `fetch.coverage.unit`, `engine.entry.retry`, `engine.gate.fired`, `engine.exit.pending`, `engine.exit.unevaluated` (a rule on a fresh quote missing an input, with `rule`, `option` and `iv_code`; DEC-27), `invariant.failed`, `run.done` (with `trades`, `bars`, `weeks`, `detail` and `git_dirty`), `run.abort` (DEC-92), `export.done` (with `runs`, `symbols`, `files` and `unpublishable`), `export.abort`, `verify.done` (with `runs` and `files`), `verify.failed` (with `files` and `problems`) (DEC-96), `calibrate.measured` (with `symbol`, `run_id`, `time`, `contract` and `cost`), `calibrate.verified` (with `symbol`, `run_id`, `lowest`, `lowest_at` and `negative_bars`), `calibrate.done` (with `value`, `provisional` and `runs`), `calibrate.abort` (DEC-93), `batch.symbol.done` (with `symbol`, `runs` and `failed`), `batch.symbol.abort`, `batch.coverage.abort`, `batch.done` (with `symbols`, `runs`, `ok` and `universe`) (DEC-100), `batch.robustness.abort`, `batch.universe.abort` (with `writer`) (DEC-101), `batch.fill_check.abort` (DEC-103), `batch.suitability.abort` (DEC-104).
  - `pmcc batch`'s workers each configure logging with a suffix, `logs/batch_{timestamp}_worker{pid}.jsonl`, so no two processes append to one file (DEC-100).
- **Errors:** the failure taxonomy is DEC-49.
- **Secrets:**
  - `lseg-data.config.json` is gitignored, blocked by a pre-commit hook, and checked in CI (`git ls-files` must not list it).
  - It is read only by `pmcc/data/lseg/` and never logged.
  - CI holds no secrets and never runs `fetch` or `probe`.

## 16. Extending the system

| Change | Steps; nothing else should need editing |
| --- | --- |
| New rule kind (selector, gate, exit) | Add its params model and `KINDS` entry in `config/kinds.py` (the rule ID it implements); implement the protocol in `strategy/` and map the kind in `strategy/registry.py` (DEC-90); reference it in YAML; add a unit and a scenario test |
| New metric | Function in `analytics/`; field on the result model; regenerate the schema; `tsc` then shows where the UI must change |
| New run variant | Entry in one of `sensitivity.yaml`'s lists or a new ablation file; no code. Its list puts it in that robustness table |
| New page panel | Component on the page; data comes only from results JSON; tokens only for style |

If a change needs edits in several packages, treat it as a design smell (EP › Shotgun Surgery) and raise it before coding.
