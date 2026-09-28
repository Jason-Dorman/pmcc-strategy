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
                 expiries; DEC-33, DEC-84)
  config/        pydantic config models; YAML loader (extends/overrides); hashing; rule-text rendering;
                 calendar.py (configs/calendar.yaml → SessionCalendar, DEC-84)
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
                 (P1-03, DEC-83); unit orchestration and resume (P1-08)
    probe/       the P1-04 probes over the HistoryProvider port, one module per DEC check;
                 one report per symbol (§6.2, DEC-85)
    cache.py     parquet + manifest + sidecar I/O (atomic, never overwrite)
    load.py      polars loaders → SymbolData (no network)
  pricing/       black_scholes.py, iv.py (vectorized), chain.py (per-bar snapshots), measures.py (EM, ATM IV, RV20)
  strategy/      ports.py (MarketView, PositionState), selectors.py, trigger.py, gates.py, exits.py, registry.py
  engine/        market_view.py (as-of gate), loop.py, legs.py (state machines), fills.py, invariants.py
  accounting/    events.py, book.py, marks.py, regt.py, ledger.py
  analytics/     performance.py, cycles.py, attribution.py, bootstrap.py, robustness.py, fillcheck.py, suitability.py
  export/        models.py (pydantic results), manifest.py, canonical.py, schema.py, site.py, verify.py
  log.py         structlog JSON setup: stderr + logs/{command}_{timestamp}.jsonl (DEC-80)
  cli.py         typer: fetch, probe, run, batch, calibrate, export, verify, serve
configs/         _shared.yaml, baseline_pmcc.yaml, quant_pmcc.yaml, ablations/a1…a5.yaml,
                 sensitivity.yaml, universe.yaml, calendar.yaml
data_cache/      raw data (gitignored, §6.4)
results/         committed results (§12)
tests/           unit/, property/, scenario/, architecture/, fixtures/synthetic/
typings/lseg/    minimal stubs for pyright strict
web/             frontend (§13)
.github/workflows/ci.yml · justfile · pyproject.toml · uv.lock · .python-version · .pre-commit-config.yaml · .gitattributes
```

The reference files at the repo root (`LSEG-DATA-GUIDE.md`, `DESIGN-GUIDE.md`, `theme.py`, `lseg_client.py`) stay where they are. They are excluded from lint, type-check and tests (DEC-57).

### 3.2 Responsibilities

| Package | One job | Main API | Depends on |
| --- | --- | --- | --- |
| `domain` | Types and time rules everyone shares | `Price`, `Money`, `OptionId`, `RuleId`, `Session`, `SessionCalendar`, `bar_end()` | stdlib |
| `config` | Turn YAML into validated, hashed, rendered config | `load_run_config()` → `RunConfig`; `load_calendar()` → `SessionCalendar` | domain, pydantic, pyyaml |
| `data.lseg` | Talk to LSEG | `lseg_session()` → `LsegProvider` | `data.provider`, lseg.data, pandas, polars |
| `data` (rest) | Know RICs; check the tape against the calendar; probe, plan, fetch, cache, load | `HistoryProvider`, `build_ric()`, `parse_ric()`, `sessions_from_tape()`, `run_probe()`, `plan_symbol()`, `fetch_rics()`, `fetch_contracts()`, `fetch_symbol()`, `load_symbol()` | domain, config, polars, numpy; only `fetch` may use `data.lseg` |
| `pricing` | Turn quotes into IV, Greeks and measures | `implied_vol()`, `greeks()`, `price_chain()`, `expected_move()`, `rv20()` | domain, numpy, scipy |
| `strategy` | Decide what to trade | `build_strategy(cfg)` → `Strategy` | domain, config, pricing, `strategy.ports` |
| `engine` | Run the clock; route decisions to fills and the book | `run_backtest(data, cfg)` → `RunOutput` | domain, config, pricing, strategy, accounting |
| `accounting` | Record and value positions | `Book.apply()`, `value()`, `regt()` | domain |
| `analytics` | Summarize runs | `compute_metrics()`, `bootstrap_ci()`, … | domain, accounting read models |
| `export` | Result models, manifest, canonical JSON, site data, verify | `write_result()`, `export_site()`, `verify()` | domain, config, accounting, analytics |
| `log` | Configure structured logging for one command | `configure_logging()` | structlog |
| `cli` | Wire commands | `pmcc` | everything |

### 3.3 Import rules

These rules are enforced by `tests/architecture/test_imports.py`, an AST scan with no extra dependency.

1. `lseg` and `pandas` are imported only under `pmcc/data/lseg/`.
2. `pmcc.data.lseg` is imported only by `pmcc.data.fetch` and `pmcc.cli`.
3. `pmcc.strategy` never imports `engine`, `data`, `accounting` or `export`.
4. `pmcc.accounting` and `pmcc.pricing` import only `pmcc.domain` from this package.
5. `pmcc.analytics` never imports `engine` or `data`.
6. `pmcc.domain` imports nothing from `pmcc`. Nothing imports `pmcc.cli`.
7. `pmcc.log` is imported only by `pmcc.cli`. Every other module logs through `structlog.get_logger()` (DEC-80).

The test also checks that one planted forbidden import per rule is caught, including relative, function-local and `TYPE_CHECKING` imports.

## 4. Domain: money and time

### 4.1 Money (DEC-44)

| Type | Representation | Notes |
| --- | --- | --- |
| `Price` | frozen dataclass over an `int` of $0.0001 units per share | quotes quantized once at load (round half-even; a float by its shortest repr) |
| `Money` | frozen dataclass over an `int` of $0.0001 units | cash, market values, P&L; `Price.notional(multiplier, qty)` is exact |
| multiplier | 100 per option contract; 1 per share | |
| `float64` | IV, Greeks, ratios, analytics | never cash |

`Price` and `Money` never mix: adding one to the other, or multiplying `Money` by a non-int, raises `TypeError` (DEC-81).

### 4.2 Time (DEC-06, DEC-20, DEC-23, DEC-24, DEC-33)

| Concept | Definition |
| --- | --- |
| Time zone | Every timestamp is tz-aware `America/New_York` after load; never a hardcoded UTC hour (LDG §4.8) |
| `bar_start` | LSEG stamp (tz-naive UTC); kept in the cache for provenance only |
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
    def spot(self) -> Price: ...                              # underlying TRDPRC_1 in the current bar
    def quote(self, opt: OptionId) -> Quote | None: ...       # fresh BID/ASK at now, else None
    def chain(self, expiry: date, right: Right) -> ChainSnapshot: ...   # listed at now (DEC-32), IV/Greeks/eligibility
    def expiries(self, kind: ExpiryKind) -> Sequence[date]: ...          # listed as of now
    def session_closes(self, n: int) -> Sequence[Price]: ...             # completed sessions only
    def calendar(self) -> SessionCalendar: ...                           # reference data (DEC-33)
```

`SessionCalendar` lives in `pmcc.domain` (DEC-84), so `strategy/ports.py` can name it without importing `data`. It is reference data, published in advance, so it answers for future days without the as-of gate (DEC-33).

- The implementation (`engine/market_view.py`) keeps the loaded frames and priced snapshots private.
- Every accessor resolves through a single `_as_of(t)` that raises `LookAheadError` when `t > now`.
- Strategies never receive a frame, so this gate is the structural guarantee the Methodology page cites.
- INV-04 tests call every accessor with future arguments and expect the raise. A hypothesis test asserts that no returned row has `bar_end > now`.

### 5.3 Rule protocols

```python
class LongSelector(Protocol):                       # E-L2 + E-L3
    def select(self, view: MarketView) -> Selection | None: ...
class ShortSelector(Protocol):                      # E-S2 + E-S3
    def select(self, view: MarketView, long: HeldLeg) -> Selection | None: ...
class EntryTrigger(Protocol):                       # E-T1 (fixed_bar in timing runs, DEC-31)
    def check(self, view: MarketView, sel: Selection, leg: Leg) -> TriggerResult: ...
class Gate(Protocol):                               # G-1…G-5
    rule_id: RuleId
    def evaluate(self, view: MarketView, d: ShortDecision) -> GateResult: ...   # PASS | FIRE | NA + values
class ExitRule(Protocol):                           # X-S1…X-S3, X-L1, X-L2
    rule_id: RuleId
    def check(self, view: MarketView, pos: PositionState) -> ExitSignal | None: ...

@dataclass(frozen=True)
class Strategy:                                     # built by strategy.registry.build_strategy(cfg)
    long_selector: LongSelector
    short_selector: ShortSelector
    trigger: EntryTrigger
    constraint: StructuralConstraint                # E-S5
    sizing: Sizing                                  # E-L4, E-S4
    gates: tuple[Gate, ...]                         # spec order; absent means off
    long_exits: tuple[ExitRule, ...]
    short_exits: tuple[ExitRule, ...]
    expiry: ExpiryResolver                          # X-S4, X-S5
```

A `Selection` carries the contract plus the values that justified it (delta, extrinsic ÷ delta, EM, spread %). Those values become blotter notes and gate-log values.

### 5.4 Accounting

```python
@dataclass(frozen=True)
class Event:                                         # one blotter row
    time: datetime; side: Literal["BUY", "SELL", "EXPIRE", "ASSIGN"]; instrument: Instrument
    qty: int; limit: Price | None; fill: Price | None; cash_delta: Money
    rule_id: RuleId; notes: str; audit: Audit       # bid, ask, spread %, selection values, E-S5 terms, funds after
class Book:                                          # positions + cash; apply() is the only mutator
    def apply(self, e: Event) -> "Book": ...         # new Book; raises EngineError on an uncovered short
def value(book: Book, marks: Marks) -> Valuation     # LongMV, ShortCallMV, StockMV, NAV, stale flags
def regt(book: Book, v: Valuation) -> RegT           # IM, MM, available funds, excess equity, flags
```

## 6. Data layer

### 6.1 Fetch flow (`pmcc fetch --symbol S --start D0 --end D1`)

```
1. Open the session: lseg_session() raises unless open_state == Opened, before any request
   (LDG §4.2). The config is resolved from the repo root, not the caller's CWD.
2. Stock tape [D0 − 30 sessions, D1] → sessions (its trading days must match configs/calendar.yaml,
   DEC-33), weekly expiries, session highs/lows, realized vol.
3. Build the plan (§6.3) and print the estimate: units, RIC requests, minutes. --plan-only stops here.
4. For each unit not already in the manifest:
     - probe increments (DEC-14) → integer-cent strike list (LDG §4.11)
     - fetch in batches of 25; a RIC that doesn't come back with bars is asked again alone;
       a failed request is asked again (3 attempts, 2 s / 4 s backoff), then aborts as an
       outage; live-only or caret→live per DEC-45 (forms_to_ask) (fetch_contracts, DEC-83)
     - check answered + unanswered = requested, per contract (LDG §5)
     - write parquet + sidecar atomically (temp file → rename), then append manifest rows
5. Print the coverage summary: % session bars with a valid mid, unanswered counts, IV-failure counts,
   log file path.
```

- **Resume:** a crash or outage loses at most the unit in flight. Re-running skips units already in the manifest.
- **Never overwrite:** a re-pull means the user renames the old file first (LDG §5).
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
  - **Estimate:** a plan holds bands, not strikes, and a ladder needs its band's increment. The estimate printed before any option request (§6.1) assumes increments from the probe reports' DEC-14 values.
- **Session ranges:** each session's low and high come from its session bars only, and a trade print widens them. The tape's trading days must match the calendar first (DEC-33).
- **Example:** the spec's window (Jul 6 → Sep 18 2026) needs the monthlies Nov 20 2026 through May 21 2027 (7 expiries).
- **Estimate:** requests ≈ Σ strikes × forms asked. LDG measured about 44 RIC requests per minute (~1,100 in ~25 min). An 11-week window is about 700 requests, ~16 min per symbol, or ~3–4 h for all 12.

### 6.4 Cache layout (DEC-46)

```
data_cache/                                   gitignored (DEC-05, DEC-56)
  probes/{SYM}_{YYYYMMDD}.json                one report per symbol and day, never overwritten (DEC-85)
  {SYM}/
    manifest.json                             per RIC: ric, unit, form, status, rows, first/last bar,
                                              fetched_at, file, sha256
    stock.parquet            stock.sidecar.json
    chains/{YYYY-MM-DD}_{C|P}.parquet         chains/{YYYY-MM-DD}_{C|P}.sidecar.json
logs/fetch_{timestamp}.jsonl                  gitignored
```

- **Parquet columns** are raw, as returned: `bar_start_utc` (datetime, UTC), `ric`, `expiry`, `strike_cents`, `right`, then one float64 column per field (`BID`, `ASK`, `TRDPRC_1`, `OPEN_PRC`, `HIGH_1`, `LOW_1`, `ACVOL_UNS`, `NUM_MOVES`).
- **Sidecar** (LDG §5):
  - request details: fields requested and fields that came back (LSEG leaves out a field a RIC lacks, DEC-83), dates, interval, tz convention, the strike step per band (DEC-84)
  - results: `ric_form_used`, `unanswered`, `errors`
  - pull date

### 6.5 Loading (`data/load.py`, no network)

`load_symbol()` takes these steps:

1. Polars lazy scans.
2. Quantize prices to `Price`.
3. Add `bar_end` in ET.
4. Tag session bars.
5. Mark quote validity: BID > 0, ASK > 0 and ASK ≥ BID.

It returns `SymbolData`: the stock frame, per-expiry chain frames, the calendar, and the data-manifest hash. Every bar is kept for provenance, but only session bars reach MarketView.

## 7. Pricing

Black-Scholes with q = 0 (Spec › Greeks and pricing), with units per DEC-24:

```
d1 = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)        d2 = d1 − σ·√T
C  = S·N(d1) − K·e^(−rT)·N(d2)                P  = K·e^(−rT)·N(−d2) − S·N(−d1)
δC = N(d1)   δP = N(d1) − 1   Γ = φ(d1) / (S·σ·√T)   ν = S·φ(d1)·√T
θC = −S·φ(d1)·σ/(2√T) − r·K·e^(−rT)·N(d2)     θP = −S·φ(d1)·σ/(2√T) + r·K·e^(−rT)·N(−d2)
```

- **Vectorized IV solver** over a chain snapshot:
  - **Bracket:** σ ∈ [1e-4, 5.0].
  - **Newton step:** taken on each lane.
  - **Bisection fallback:** any lane whose step leaves the bracket, or whose vega < 1e-8, switches to bisection.
  - **Stop:** at |model − mid| < 1e-6·max(1, mid), or after 100 iterations.
  - **Failure codes:** `NO_QUOTE`, `BELOW_FLOOR` (mid < max(0, S − K·e^(−rT))), `ABOVE_CAP` (mid ≥ S), `NO_CONVERGENCE`, `EXPIRED`.
  - **Test:** a scalar `scipy.optimize.brentq` solve serves as the reference.
- **Chain pricing:** `price_chain(snapshot, spot, now, r)` returns IV, δ, Γ, θ, ν, eligibility and spread % for every contract at one bar.
  - It uses only that bar's data.
  - It is memoized per (bar, expiry, right), so all runs for a symbol in a batch share it.
- **Measures:** `expected_move()` and `atm_iv()` (DEC-25), `rv20()` (DEC-26), and `extrinsic = mid − max(0, spot − strike)` (Spec › E-L3).
- **Held contracts** with a failed IV use DEC-27.

## 8. Engine

### 8.1 Bar loop (order per DEC-20)

```
for bar in session_bars(window):                           # ascending bar_end
    view = MarketView(data, now=bar.end)
    legs.cover_short_stock(view)                           # X-S5 follow-up
    if bar.session.is_week_open: legs.long_exits(view)     # X-L1, X-L2 (pending until filled)
    if book.long is None: legs.long_entry(view)            # E-L1…E-L4, session-frozen selection
    if book.short: legs.short_exits(view)                  # X-S1, X-S2 any bar; X-S3 on the check bar
    if bar.session.is_week_open: legs.short_entry(view)    # E-S1…E-S5, gates, gate-log row
    if bar.is_close: legs.resolve_expiry(view)             # X-S4 / X-S5 on the expiry session
    ledger.append(book, value(book, marks(view)), regt(...)); invariants.check_bar(...)
# X-E1: the final ledger row marks everything at the last bar; nothing is liquidated
```

### 8.2 Leg state machines (DEC-21, DEC-22, DEC-28, DEC-34)

```
LONG   FLAT ──selector returns c (session s)──────────────► CANDIDATE(c, s)
       CANDIDATE ──E-T1 passes ∧ E-L4 funds ok──────────► HELD                       BUY  E-L1
       CANDIDATE ──E-L4 would go negative────────────────► FLAT (flag; retry next session)
       CANDIDATE ──session ends──────────────────────────► FLAT (retry next session)
       HELD ──week-open ∧ (δ < 0.50 ∨ DTE < 90)──────────► RESETTING (short entry waits)
       RESETTING ──fresh quote───────────────────────────► FLAT → re-entry this session  SELL X-L1|X-L2

SHORT  (week-open session only)
       IDLE ──long held ∧ no short───────────────────────► SELECTING
       SELECTING ──selector returns c────────────────────► FROZEN(c)
       FROZEN ──E-T1 passes──► DECIDE ──G-2…G-5 all pass──► OPEN                     SELL E-S1
                                      └─first gate fires──► SKIPPED(rule)
       SELECTING | FROZEN ──session ends─────────────────► SKIPPED(G-1)
       OPEN ──X-S1 | X-S2 | X-S3─────────────────────────► CLOSED                     BUY  X-S*
       OPEN ──expiry close, OTM──────────────────────────► EXPIRED                    EXPIRE X-S4
       OPEN ──expiry close, ITM──────────────────────────► ASSIGNED                   ASSIGN + stock SELL X-S5
       ASSIGNED ──first valid bar, next session──────────► covered                    stock BUY X-S5
```

Each week-open session writes exactly one gate-log row per strategy (DEC-22).

### 8.3 Fill simulator (Spec › Fill model)

```
fill(quote, side, capture, fee) -> Fill | None
  no fresh BID or no fresh ASK → None                     # no fill, never an invented print (INV-03)
  mid = (BID + ASK)/2 ; half = (ASK − BID)/2
  price = mid + capture·half  (BUY)   |   mid − capture·half  (SELL)   → quantized to Price, round half-even
  cash_delta = −price·multiplier·qty (BUY) | +price·multiplier·qty (SELL)   − fee·contracts
```

The blotter's Limit column is the mid at decision time; its Fill column is `price`.

### 8.4 Runtime invariants

| When checked | Invariants |
| --- | --- |
| After every bar | INV-01, 02, 05, 07, 10 |
| At every event | INV-03, 06, 08, 09 |

A failure raises `InvariantViolation`; the run writes nothing and exits non-zero.

## 9. Accounting and Reg T

- **Cash:** changes only in `Book.apply(event)` (INV-01).
- **Marks:** a fresh mid, or else the last fresh mid flagged `stale`. A stale mark never fills and never triggers a rule (DEC-27).
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
  | Short stock, initial | 50% × \|StockMV\| |
  | Short stock, maintenance | 30% × \|StockMV\| |

  - IM = long + short-stock initial. MM = long + short-stock maintenance.
  - Available funds = NAV − IM. Excess equity = NAV − MM.
- **Entry check:** before a long or short entry, the post-trade available funds are computed and must be ≥ 0. The value is recorded in the event's audit (INV-08).
- **Ledger flags:**
  - `stale_long`, `stale_short`, `stale_stock`
  - `funds_negative` — the site states the position couldn't have been held in a real Reg T account
  - `entry_blocked`, `exit_pending`

## 10. Configuration

| File | Holds |
| --- | --- |
| `configs/_shared.yaml` | Rules identical in both strategies (E-T1, E-L1, E-L4, E-S1, E-S2, E-S4, E-S5, G-1, G-2, all exits) |
| `configs/baseline_pmcc.yaml` | `extends: _shared.yaml`; baseline E-L2, E-L3, E-S3; report sections |
| `configs/quant_pmcc.yaml` | `extends: _shared.yaml`; quant E-L2, E-L3, E-S3; G-3, G-4, G-5; report sections |
| `configs/ablations/a1…a5.yaml` | `extends: ../quant_pmcc.yaml` + `overrides` keyed by rule ID |
| `configs/sensitivity.yaml` | friction, timing and grid variants (§11) |
| `configs/universe.yaml` | window, symbols (stock RIC, option root), r with source, starting cash with basis, bootstrap seed |
| `configs/calendar.yaml` | NYSE holidays and early closes 2025–2027, with sources (DEC-33) |

A rule entry (DEC-52):

```yaml
- id: G-3
  name: Event week
  kind: event_ratio_gate
  params: {max_ratio: 1.20}
  condition: "Front-week ATM IV ÷ next-week ATM IV > {max_ratio:.2f}"
  action: "Skip the week; keep the long"
  rationale: "An event priced into the front week lifts its IV above the next week's; a ratio scales across volatility regimes."
```

An ablation (DEC-53):

```yaml
id: quant_pmcc--a3
name: "A3: quant without the event gate"
extends: ../quant_pmcc.yaml
overrides:
  G-3: {remove: true}
```

- **Resolution:** `universe.yaml` + the strategy YAML (with extends and overrides) → frozen `RunConfig` → `config_hash` = sha256 of the resolved config's canonical JSON.
- **Load errors:** an unknown `kind`, an unknown param, a duplicate rule ID, a missing required slot, or an unresolved placeholder all fail at load.

## 11. Runs, batch and determinism

The run matrix per symbol has 24 runs:

| Family | Run IDs | Count | Detail (DEC-54) |
| --- | --- | --- | --- |
| Strategies | `baseline_pmcc`, `quant_pmcc` | 2 | full |
| Ablations | `quant_pmcc--a1` … `--a5` | 5 | summary |
| Friction | `{baseline,quant}_pmcc--sc025`, `--sc050` | 4 | summary |
| Entry timing | `baseline_pmcc--t1` … `--t7` (DEC-31) | 7 | summary |
| Parameter grid | `quant_pmcc--k075`, `--k125`, `--g4r090`, `--g4r110`, `--g3r110`, `--g3r130` | 6 | summary |

`pmcc batch --universe configs/universe.yaml` works as follows:

1. Per symbol: load once, price chains once, then run the matrix.
2. Symbols run in a process pool.
3. A failed symbol is reported without stopping the others, and the batch exits non-zero if any run failed.
4. Universe-level outputs are computed last: pooled, headline, suitability.

Determinism controls (INV-13):

| Source of drift | Control |
| --- | --- |
| Float accumulation in cash/NAV | Integer money (DEC-44) |
| Aggregation and row order | Explicit sorts; polars `maintain_order=True` |
| Randomness (bootstrap) | Seeded PCG64 from `universe.yaml`; seed recorded |
| Parallelism | Runs are independent; one file each; content never depends on completion order |
| Serialization | Canonical JSON (DEC-50) |
| Clock | `run_timestamp` only in the manifest, excluded from INV-13 |
| Environment | `uv.lock`, Python 3.12 pin, `package-lock.json` |
| Operating system | LF line endings (`.gitattributes`; writers pass `newline="\n"`), `tzdata` for time zones, bash for recipes, so Windows and Ubuntu produce the same bytes (DEC-58) |

## 12. Results contract and export

```
results/                            committed
  index.json                        runs per symbol, window, r, starting cash, export manifest
  rules.json                        rendered rules per strategy and variant (Trade rules page)
  universe/pooled.json              pooled metrics + week-block bootstrap CIs
  universe/headline.json            per-symbol headline table
  universe/suitability.json         symbol suitability screen
  {SYM}/{run_id}.json               RunResult, full or summary
  {SYM}/robustness.json             ablation, friction, timing and grid tables
  {SYM}/fill_check.json             scatter points (or bins, DEC-05) + fit
  {SYM}/coverage.json               derived data-coverage counts
```

`RunResult` (pydantic; JSON Schema generated by `pmcc export`):

```
schema_version
manifest    run_id, symbol, strategy_id, git_sha, git_dirty, config_hash, data_manifest_hash,
            lock_hash, run_timestamp, data_source (lseg|synthetic), pmcc_version
config      resolved config, rule text rendered
summary     metrics, cycle_stats, exit_mix, skips_by_rule, weekly_returns, nav_close[], flag counts, invariants[]
blotter[]   time, instrument{ric, occ, kind}, side, qty, limit, fill, cash_delta, rule_id, notes, audit{…}   full
ledger[]    time, long{ric, strike, expiry, qty, mark, delta, stale}, short{…}, stock{…}, cash, nav,
            im, mm, available_funds, excess_equity, flags[]                                          full
gate_log[]  session, decision_time, selected{…}, gates[{rule_id, status, values}], outcome{kind, rule_id}   full, if declared
cycles[]    full
attribution leg{…}, greek{…} (if declared)                                                          full
```

- **Canonical JSON** (DEC-50):
  - sorted keys
  - dollars and prices to 4 dp; IV, Greeks and ratios to 6 dp
  - ISO-8601 times with offset
  - `null` instead of NaN
  - `\n` line endings on every OS
- **`pmcc export --out web/public/data/`:**
  - validates and copies `results/`
  - writes `schema/*.schema.json` from the result models
  - writes the files the frontend reads
- **`pmcc verify results/`** (CI, DEC-51):
  - schema validation
  - `git_dirty` must be false
  - re-derives INV-01, 02, 03, 05, 06, 07, 08, 09 and 10 from the blotter, ledger and gate log
  - every summary run's recorded invariants must pass

## 13. Frontend

```
web/
  src/
    app/        HashRouter, AppShell, providers (symbol, theme)
    data/       index loader, per-run loader with cache, schema_version check
    types/generated/   json-schema-to-typescript output (gitignored; regenerated before typecheck/build)
    theme/      tokens.css, tokens.ts, echarts.ts
    components/ CommandBar, Readouts, PanelGrid, Panel, Caption, DataTable, charts/*, ManifestFooter, WarningBanner
    pages/      Comparison, Strategy, Rules, Methodology, Universe, Data
    format/     money, percent, time (ET), ric/occ
  e2e/          Playwright smoke test
  public/data/  written by pmcc export (gitignored)
```

- **Data:**
  - `index.json` loads at startup.
  - Run files load on demand when the symbol or page changes, and are cached in memory by path.
  - A `schema_version` mismatch shows an error banner.
- **State:**
  - The URL is the state; the symbol comes from the route.
  - Symbol-less routes remember the last symbol for links back.
  - The theme preference is kept in `localStorage`, wrapped in try/catch.
- **Types:** `npm run gen:types` runs before `typecheck` and `build`. A schema change the UI doesn't handle fails `tsc` (INV-14).
- **Charts:** modular `echarts/core` via `echarts-for-react`. The theme is built from the CSS variables. Animation is off.
- **Tables:** TanStack Table plus TanStack Virtual for the ledger and blotter.
- **Tests:**
  - Vitest: formatters, transforms, token-lint, contrast.
  - Playwright: every route, console errors, cross-origin requests, screenshots.
- **Build:** Vite `base: './'` with HashRouter (DEC-73). The static `dist/` makes no cross-origin requests (fonts are bundled, DEC-72).

## 14. Tooling and CI/CD

Recipes run under bash (`set shell := ["bash", "-cu"]`): Git Bash locally, bash on the CI runners (DEC-58). Python tools run through `uv run --frozen` (DEC-77). A recipe whose command isn't built yet fails with exit 1, naming its backlog item; until `web/` exists (P4-06), `setup` and `check` skip their web steps with a note, and the web recipes fail (DEC-78).

| just recipe | Does |
| --- | --- |
| `setup` | `uv sync --frozen`, `npm ci` in `web/`, `pre-commit install` |
| `check` | pre-commit on all files, pytest, web lint/typecheck/vitest |
| `test *ARGS` | pytest (dev profile unless `HYPOTHESIS_PROFILE` is set), extra args passed through |
| `probe SYM` · `fetch SYM START END *ARGS` | LSEG probes / pull (local only); `fetch` passes extra args, e.g. `--plan-only` |
| `run SYM CONFIG` · `batch` · `calibrate` | backtests |
| `export` · `verify` | site data / results validation |
| `web-dev` · `web-build` · `e2e` · `serve` | frontend |
| `reproduce` | cached data → batch → verify → export → web build (Spec › CLI) |

CI (`.github/workflows/ci.yml`, on push and PR; DEC-79):

| Job | Steps |
| --- | --- |
| `python` | credentials guard (`git ls-files`) → setup-uv → `uv sync --frozen` → `pre-commit run --all-files` (ruff, format, pyright, guards) → `pytest` (ci profile) → `pmcc verify results/` (added with P4-05) |
| `web` | `uv sync --frozen` → `pmcc export --out web/public/data/` → `npm ci` → `gen:types` → `lint` → `typecheck` → `vitest` → `build` → dist guard → Playwright smoke → upload the Pages artifact |
| `deploy` | `main` only; needs `python` and `web`; `actions/deploy-pages` |

- **Dist guard:** fails if `web/dist` references `localhost:9000`, an `lseg`/`refinitiv` URL, or `fonts.googleapis.com`. The smoke test also fails on any cross-origin request.
- **Pre-commit:** ruff, ruff-format, pyright, check-yaml, end-of-file-fixer, check-added-large-files, detect-private-key, and a local hook that rejects a staged `lseg-data.config.json`.
  - ruff and pyright run through `uv run --frozen`, at the `uv.lock` versions. The reference files are excluded from every hook (DEC-57, DEC-77).
  - The CI pytest step sets `HYPOTHESIS_PROFILE=ci`.

## 15. Logging, errors and security

- **Logging:** structlog JSON, one event per line, to stderr and to `logs/{command}_{timestamp}.jsonl` (DEC-80).
  - A command calls `pmcc.log.configure_logging(command)` once at startup; every other module calls `structlog.get_logger()`.
  - Each event carries `event`, `level`, `timestamp` (ISO 8601, UTC) and `command`; exceptions are rendered as text in `exception`. Level INFO and up.
  - Every soft fetch failure is one `fetch.ric.unanswered` event, logged once per RIC the service left unanswered, with `symbol`, `unit`, `ric`, `form` (for an option RIC), `reason` (`no_data` or `empty`), `codes` and `message` (Spec › Stack, DEC-83). `fetch.batch.rejected` and `fetch.retry` carry `size` and the error.
  - Event names: `fetch.unit.start|done`, `fetch.ric.unanswered`, `fetch.batch.rejected`, `fetch.retry`, `fetch.abort.outage`, `engine.entry.retry`, `engine.gate.fired`, `engine.exit.pending`, `invariant.failed`.
- **Errors:** the failure taxonomy is DEC-49.
- **Secrets:**
  - `lseg-data.config.json` is gitignored, blocked by a pre-commit hook, and checked in CI (`git ls-files` must not list it).
  - It is read only by `pmcc/data/lseg/` and never logged.
  - CI holds no secrets and never runs `fetch` or `probe`.

## 16. Extending the system

| Change | Steps; nothing else should need editing |
| --- | --- |
| New rule kind (selector, gate, exit) | Implement the protocol in `strategy/`; add a params model; register the `kind`; reference it in YAML; add a unit and a scenario test |
| New metric | Function in `analytics/`; field on the result model; regenerate the schema; `tsc` then shows where the UI must change |
| New run variant | Entry in `sensitivity.yaml` or a new ablation file; no code |
| New page panel | Component on the page; data comes only from results JSON; tokens only for style |

If a change needs edits in several packages, treat it as a design smell (EP › Shotgun Surgery) and raise it before coding.
