# PMCC Backtest — Test Strategy

Sep 25, 2026 · implements Spec › Invariant tests and EP › Testing mindset · see [ARCHITECTURE](ARCHITECTURE.md) and [DECISIONS](DECISIONS.md)

## 1. Rules

- **Tests come first.** A backlog item is done only when its tests exist and pass (EP › Testing mindset).
- **Tests are never cut** (Spec › Build order).
- **Tests never touch the network.**
  - An autouse fixture in `tests/conftest.py` blocks sockets: connect, `create_connection` and `getaddrinfo` raise, localhost included (DEC-77).
  - Another fails any test that changes a file under the repo's `results/` or `configs/`, naming the files: CLI tests run commands that write there by default (DEC-100).
  - LSEG code is tested through `FakeProvider`, which a contract test keeps true to lseg-data 2.1.1 (§6).
  - CI has no cache and no credentials, and it must still prove every invariant (DEC-51).
- **Tests are deterministic.**
  - Fixed seeds everywhere.
  - Hypothesis profiles: `dev` (50 examples) and `ci` (300 examples, derandomized), chosen by `HYPOTHESIS_PROFILE` (default `dev`).
  - No per-example deadline in either profile: a wall-clock limit makes a pass depend on machine load (DEC-77).
- **One behaviour per test.** Name tests `test_<rule-or-inv>_<behaviour>`, e.g. `test_x_s3_fires_within_quarter_em_of_strike`.

## 2. Layers

| Layer | Covers | Tool | Runs in |
| --- | --- | --- | --- |
| Unit | Domain primitives (half-even quantizing, money arithmetic, `bar_end`, session bars; `tests/unit/domain/`), RIC grammar and OCC symbols (`tests/unit/data/test_ric.py`), the LSEG adapter and batched requests (`tests/unit/data/test_lseg_*.py`, `test_fetch.py`, §6), the calendar (`tests/unit/domain/test_calendar.py`, `tests/unit/config/test_calendar_file.py`, `tests/unit/data/test_tape_calendar.py`), the universe file, with its window planned on the shipped calendar (`tests/unit/config/test_universe_file.py`, DEC-86), the starting-cash rule, block and writer (`tests/unit/config/test_capital.py`, DEC-93), increments, bands and the fetch plan (`tests/unit/data/test_discovery.py`), the probes (`tests/unit/data/test_probe.py`, §6), the cache and loader (`tests/unit/data/test_cache.py`, `test_load.py`, `test_files.py`: atomic writes, never overwriting, counts per contract, the data-manifest hash, a FakeProvider round trip; DEC-46, DEC-87), `pmcc fetch`'s plan, estimate, unit loop, resume and coverage summary (`tests/unit/data/test_pull.py`, `test_estimate.py`, `test_coverage.py`, and the fetch tests in `tests/unit/test_cli.py`; DEC-16, DEC-88), Black-Scholes, T and DTE, the IV solver's codes, measures and the chain pricer (`tests/unit/pricing/`: reference values computed with mpmath at 50 digits; DEC-24 to DEC-27, DEC-89), `Quote` (`tests/unit/domain/test_quotes.py`), MarketView's reads and point-in-time listing (`tests/unit/engine/test_market_view_reads.py`, DEC-32), fills (`tests/unit/engine/test_fills.py`), the runtime invariants and the closing spot (`tests/unit/engine/test_invariants.py`), events, the book, marks, Reg T and the ledger (`tests/unit/accounting/`, DEC-10), every baseline and quant rule at its boundaries, with DEC-29's ties and `n/a` inputs, and the registry building each shipped config (`tests/unit/strategy/`, the quant rules in `test_quant_selectors.py` and `test_quant_gates.py`, on the stub view `tests/fakes/view.py`; DEC-95), the synthetic market's builders (`tests/unit/fixtures/`), canonical JSON and the run's provenance (`tests/unit/export/`: git SHA and dirtiness on a throwaway repository, `tests/fakes/git_repo.py`, with git's global and system config shut out; DEC-50, DEC-92), `pmcc run` and `pmcc calibrate` end to end on a synthetic cache (`tests/unit/test_cli_run.py`, `test_cli_calibrate.py`), the run matrix and `configs/sensitivity.yaml`'s variants against their strategies (`tests/unit/config/test_sensitivity_config.py`), the fixed-bar trigger (`tests/unit/strategy/test_trigger.py`, DEC-31), `pmcc batch` through its real process pool on two synthetic symbols, with failure isolation, the coverage file and the universe stage (`tests/unit/test_cli_batch.py`, DEC-100), the `report` block (`tests/unit/config/test_report.py`, DEC-54), the JSON Schema as written (`tests/unit/export/test_schema.py`: dollars as numbers, the config's dump, every field required, the schema version pinned), `pmcc verify` and `pmcc export` end to end (`tests/unit/test_cli_export.py`) (DEC-96), what git commits and the hooks that guard the cache (`tests/unit/test_repo_policy.py`, DEC-05, DEC-94), metrics | pytest | `just test`, CI |
| Property | Accounting invariants (INV-01, 02, 08, 10) over random fills, expiries, assignments, covers and stale marks (`tests/property/test_accounting_invariants.py`); fills lie between mid and the far side (`test_fills.py`); Black-Scholes put–call parity and each Greek against a central difference; IV vs a scalar `brentq` reference where the mid pins the vol down, a solved vol repricing its mid everywhere else, and each lane solved as if alone (`tests/unit/pricing/`, DEC-89); MarketView's as-of guard (INV-04: every answer at `now` equals a market cut off at `now`, `tests/property/test_market_view.py`); RIC round-trip (INV-11); canonical JSON read and dumped again gives back its bytes (`tests/unit/export/test_canonical.py`); every fetched contract answered or unanswered, never both; the loader's vectorized price quantizing equals `Price.from_dollars` (`test_load.py`); integer strike ladders (`test_discovery.py`); every session sits between its week-open and week-final sessions | hypothesis | CI |
| Scenario | Engine end to end on a synthetic market: one scenario per exit, gate and edge case (§5), `tests/scenario/test_scenario_*.py` over `harness.py`, which runs any shipped config (the baseline, quant or an ablation) with any overrides (`test_scenario_quant.py`: the quant gates, `n/a` in a full run, the quant entries and the ablations; DEC-95); the runtime invariants hold on every bar of each. The result file mirrors the engine's blotter, ledger and gate log, names each contract by the RIC its cache answered with, and records a dirty tree (`tests/scenario/test_run_result.py`, DEC-92) | pytest | CI |
| Determinism | The same synthetic runs in two fresh processes, with different hash seeds, run timestamps and commits, give byte-identical files once `run_timestamp` and `git_sha` are dropped (INV-13, DEC-50) | pytest | CI |
| Architecture | Import boundaries (ARCHITECTURE §3.3), in `tests/architecture/test_imports.py`, with one planted violation per rule | pytest (AST) | CI |
| Config | Rule IDs unique and complete; placeholders resolve; every param referenced; each shipped threshold is the spec's; names, gate conditions and exit actions read against the spec's tables, and the no-roll paragraph against its words, on every short exit (DEC-35); `extends` and `overrides`, kinds and their params, required rules, spec order and the config hash (`tests/unit/config/test_baseline_config.py`, `test_strategy_loader.py`, `test_rule_text.py`, `test_kinds.py`; DEC-90); the quant config against the spec's thresholds, names, gate conditions and G-3 paragraph, and each ablation differing from quant only in its layer, A1 and A2 with the baseline's rules word for word, and G-5's locked-quote sentence held true to E-T1's and G-5's thresholds (`test_quant_config.py`, P4-03, P4-04; DEC-95) | pytest | CI |
| Results | Schema check plus invariants re-derived from committed results (DEC-51). `tests/scenario/test_verify.py` proves each check: results as the pipeline writes them pass (full, summary, a run holding X-S5's stock, and one filled at spread_capture 0.5 with a fee), and a hand-corrupted copy fails on exactly the invariant or file check it targets, one per re-derivable invariant, plus the review's cases (E-S5's recorded terms and strikes, an entry under another rule ID, INV-08 on X-S5's cover bar, the assignment exemption, a row the ledger doesn't hold, a missing strike reported rather than crashing, analytics files off their symbol or not canonical). A sweep of every synthetic scenario under both strategies, with and without X-S1, at capture 0 and 0.5 (208 runs) found no false positive (DEC-96). `tests/scenario/test_export.py` covers the detail levels, the summary (a two-flag bar included), `index.json`, `rules.json` with every change kind, and what export refuses, the directory guard included (DEC-54, DEC-96) | `pmcc verify` | CI |
| Runtime | Invariants checked every bar of every real run; a failure writes nothing | engine | every run |
| Frontend unit | Formatters (`src/format/format.test.ts`), the loader (`src/data/loader.test.ts`), every route with its banners (on and off), footer, render-time numbering, the Data page on github.io, the remembered symbol and the symbol select (`src/app/routes.test.tsx`), token-lint (`src/theme/tokenlint.test.ts`), and contrast with the grid, breakpoints and every token's `theme.py` value (`src/theme/contrast.test.ts`), with `TZ=UTC` as in CI (P4-06, DEC-97) | Vitest | `just check`; CI web job (P4-07) |
| Types | `tsc` against types generated from the current schema (INV-14) | tsc | CI |
| Dist guard | The built site names no LSEG, Refinitiv, `localhost:9000` or Google Fonts host, and isn't empty (`web/scripts/dist-guard.test.mjs` plants each and checks what a correct build carries passes; DEC-98) | Vitest; `npm run guard` | `just web-build`; CI web job |
| Smoke | Every route for NVDA on the built site (`vite preview`), plus `#/`: no console errors or uncaught exceptions, no request to another origin, the footer landmark present, no sideways scroll, and screenshots at 390, 1100, 1366 and 1600 px; a deep link surviving a reload, and no synthetic banner on real results (`web/e2e/smoke.spec.ts`, DEC-99) | Playwright (Node) | `just e2e`; CI web job, screenshots uploaded |
| Data acceptance | answered + unanswered = requested; mid coverage; holiday weeks; spot checks against Workspace | fetch summary + manual | local, per fetch |

## 3. Invariant matrix

Numbering follows Spec › Invariant tests.

| INV | Statement (short) | Enforced by | Where |
| --- | --- | --- | --- |
| 01 | Cash changes only on blotter rows; Σ Cash Δ = Δ cash | runtime · property · verify | `tests/property/test_accounting_invariants.py`; `pmcc verify` |
| 02 | NAV = cash + long MV − short call MV + stock MV, every bar | runtime · property · verify | same |
| 03 | No fill without a valid BID and ASK on the decision bar | runtime · unit · verify | `tests/unit/engine/test_fills.py`; `pmcc verify` (audit bid/ask, fill = mid ± capture·half) |
| 04 | No decision reads data stamped after its decision time; MarketView raises | unit · property | `tests/property/test_market_view.py` |
| 05 | Every short is covered: long strike ≤ short strike, long expiry ≥ short expiry, equal quantities | runtime · scenario · verify | `tests/scenario/`; `pmcc verify` |
| 06 | Every short entry satisfied E-S5 at its decision bar | runtime · unit · verify | `tests/unit/strategy/test_constraint.py`; `pmcc verify` (E-S5 terms in the audit) |
| 07 | No short call is open after its expiry session | runtime · scenario · verify | `tests/scenario/test_scenario_expiry.py`; `tests/unit/engine/test_invariants.py`; `pmcc verify` |
| 08 | Available funds ≥ 0 at every entry decision | runtime · property · verify | property tests; `pmcc verify` (post-trade funds in the audit) |
| 09 | Every blotter and gate-log row carries a valid rule ID from the config | runtime · config · verify | `tests/unit/config/` (`StrategyConfig.rule_ids`: spec IDs only, each once); `pmcc verify` |
| 10 | Short qty = long qty whenever a short is open | runtime · property · verify | property tests; `pmcc verify` |
| 11 | Known examples parse as the right contracts (the spec's unpadded one included); the builder emits the zero-padded day, round-trips its own spelling and puts no caret on live contracts (DEC-01) | unit · property | `tests/unit/data/test_ric.py` |
| 12 | Missing RICs return empty series, never exceptions | unit | `tests/unit/data/test_fetch.py` (FakeProvider) |
| 13 | Re-running a config on cached data gives byte-identical results (ignoring `run_timestamp` and `git_sha`) | determinism test (synthetic, CI) · P8-01 (real, local) | `tests/scenario/test_run_result.py` (`random_walk`, and `friday_unquoted_at_check` without X-S1 for its two-flag ledger rows, run by `inv13_run.py` in two processes with `PYTHONHASHSEED` 2 and 6, which order those two flags oppositely); `just reproduce` |
| 14 | The frontend type-checks against types generated from the current schema | `gen:types` + `tsc` | CI web job |
| 15 | The Playwright smoke test loads every page for one symbol with no console errors | Playwright | `web/e2e/smoke.spec.ts` (CI web job; P4-08) |

INV-01, 02, 08 and 10 also run as hypothesis property tests over random sequences of fills, expiries, assignments and marks (Spec › Invariant tests). The generator must include:

- stale marks
- the X-S5 path (ASSIGN, then a short-stock SELL, then the next session's BUY)
- `spread_capture` values that produce sub-cent fills (these test DEC-44's exactness)

## 4. Rule coverage

Every rule ID needs at least:

- **boundary unit tests:** just inside and just outside each threshold, plus ties (DEC-29) and missing inputs
- **one scenario test** in which it fires during a full run

| Rule | Unit focus | Scenario |
| --- | --- | --- |
| E-T1 | Spread ≤ 3% (long) and ≤ 10% (short) of mid; no quote = fail | first bar fails, a later bar passes |
| E-L1 | Retry the next session after an E-T1 failure | long enters on day 2 |
| E-L2 | Nearest 180 DTE (baseline); 120–270 DTE range, inclusive (quant) | quant entry (`quiet`) |
| E-L3 | δ nearest 0.80; lowest extrinsic ÷ δ in the 0.70–0.90 band, inclusive, with tie-breaks | quant entry (`quiet`) |
| E-L4 | Funds check blocks the entry, and it's logged | underfunded account |
| E-S1 | Week-open only; needs a long and no short; Tuesday after a Monday holiday | Labor Day week |
| E-S2 | Expiry = the week-final session (Thursday when Friday is a holiday) | Jul 3 week |
| E-S3 | 0.30 δ OTM (baseline); lowest eligible strike ≥ spot + k·EM, exact in units, no EM = no pick (quant); listing is point-in-time | quant entry (`quiet`) |
| E-S4 | Short qty = long qty | — |
| E-S5 | Strict inequality at the boundary; uses the long's entry fill, not its mark | expensive long → G-2 |
| G-1 | Frozen contract never passes E-T1 | no valid quote all Monday |
| G-2 | E-S5 fails | as above |
| G-3 | Ratio > threshold fires, on it passes; missing front- or next-week IV = `n/a`; next week after a closed Friday | front-week IV bump; next week unlisted = `n/a` |
| G-4 | IV ÷ RV20 < threshold fires, on it passes; missing RV20 or IV = `n/a`; flat closes pass | RV above IV |
| G-5 | Mid < $0.10 fires, one unit under; on it passes | tiny premium on a locked quote (DEC-95) |
| X-S1 | Mid ≤ 25% of credit, before the Friday check only | premium collapse |
| X-S2 | δ > 0.60 on any bar; δ := 1 when mid is below the floor (DEC-27) | rally through the strike |
| X-S3 | Check bar is the last session bar ending ≤ 15:00 ET; buffer uses EM from entry; delayed fill (DEC-28) | Friday within the buffer |
| X-S4 | OTM at close → EXPIRE at $0 | quiet week |
| X-S5 | ITM at close → ASSIGN + short-stock SELL; cover the next session; Reg T short-stock margin | late-Friday surge |
| X-L1 | δ < 0.50 at week-open → sell, re-enter, then short entry | drop through the long's delta |
| X-L2 | DTE < 90 at week-open → roll | long crossing 90 DTE |
| X-E1 | Final marks; no liquidation | window ends mid-week |

## 5. Synthetic market (`tests/fixtures/synthetic/`)

A deterministic generator (`market.py`, `generate(spec, root)`) writes a dataset in the **cache format**: a parquet and a sidecar per unit, written by `SymbolCache.write_unit`, since `load_symbol` reads the sidecars, never `manifest.json` (DEC-87). So the loader, pricing, MarketView and the engine are tested exactly as they run on real data. The same spec and seed write byte-identical files (P3-03, DEC-91).

**Underlying**

- An hourly tape from a seeded random walk (configurable drift and volatility), or a scripted path of knots (`SpotPath`). The stock quotes a cent either side of spot and trades at it.
- The shipped calendar, so a window can hold a Monday holiday (Labor Day), a Friday holiday (Jul 3) and a half-day (Nov 27 2026).
- A warm-up of 22 sessions before the window, for RV20.

**Option chains**

- Weekly calls (the prior week's open to the expiry), puts around the week-open spot, and monthly calls 90–280 days out, shaped like the fetch plan (ARCHITECTURE §6.3).
- Priced by Black-Scholes from an `IvSurface`: a base, a weekly and a monthly level, and per-expiry overrides (the front-week event bump for G-3).

**Market microstructure**

- Bid/ask spreads as a share of the price (`SpreadModel`, weekly and monthly), rounded out to whole cents. A bid under a cent is a zero bid: no valid quote.
- Random holes (`hole_rate`), and trade prints on a fraction of bars.
- Hooks that rewrite any contract-bar's quote or drop its row (`quote_hook`), and the stock's (`stock_hook`).
- With `extended_hours`, a pre-market bar (ending 09:00) and a post-close bar each session, so tests can check that no read comes from them (DEC-06).

**Scenario builders** (`scenarios.py`, `BUILDERS`)

Each builder scripts the spot path and quotes to force one behaviour, over Mon Aug 31 to Fri Sep 11 2026 unless it says otherwise. Weeklies trade at 40% IV and monthlies at 20%: at one IV for both, a 0.80-delta 180-DTE long carries more extrinsic than a 0.30-delta weekly's distance and premium, and G-2 would skip every week (DEC-91).

- every exit rule: `premium_collapse` (X-S1), `rally_through_strike` (X-S2), `friday_within_buffer` (X-S3, and a delayed fill with `unquoted_at_check`), `quiet` (X-S4), `late_friday_surge` (X-S5 and its cover), `long_delta_drop` (X-L1); X-L2 and X-E1 run `quiet` with a higher `min_dte` (170, above the ~172-DTE long's 164 days at week 2) or an earlier window end;
- gates G-1…G-5: `no_quote_monday`, `expensive_long`, and under the quant PMCC `event_week` (the front week at 60% IV), `rv_above_iv` (a 60%-vol walk under 20% IV), `tiny_premium` and `next_week_unquoted` (G-3 `n/a`: week 2's calls unlisted on Monday; P4-02, DEC-95). `tiny_premium` quotes week 1's calls above $103 locked at $0.08 on Monday: E-T1 passes a short only if its spread is at most 10% of mid, and a one-cent spread is 10% of $0.10, so only a locked quote under $0.10 can reach G-5 (DEC-95). Under the quant PMCC, week 2's next week expires on Fri Sep 18, a third Friday priced at the monthly 20% against the weeklies' 40%, so G-3 fires in week 2 of every default surface; the gate scenarios assert on week 1;
- entry timing: `entry_retry` (E-L1), `first_bar_wide` (E-T1), `long_unquoted_at_open` (DEC-28's long check);
- the freezes and the once-a-week long check: `first_bar_wide` with a rally (`short_frozen_then_rally`, `long_frozen_then_rally`, DEC-21) and `long_falls_after_check` (DEC-28);
- the unfinished reset (`reset_reentry_wide`, DEC-22) and the stock without a quote at assignment (`surge_no_stock_quote`, DEC-91);
- E-L4 underfunding, stale marks (`stale_long_marks`), and negative available funds after X-S5 (`late_friday_surge` with little cash);
- the half-day close (`half_day_week`) and the Jul 3 week (`independence_day_week`);
- a random market (`random_walk`) that must run clean through every invariant, under the baseline and under quant and A1–A5.

X-S3, X-S4 and X-S5 run the baseline without X-S1 (A5's config), since on a flat path X-S1 takes the profit first. The session-scoped `synthetic` fixture (`store.py`) generates each market once per test run. Each builder has a smoke test (`tests/unit/fixtures/test_synthetic_market.py`).

**Other uses**

- The INV-13 determinism test and the result-file tests (P3-08: `random_walk`, and `late_friday_surge` and `friday_unquoted_at_check` without X-S1 for stock rows and two-flag rows).
- The starting-cash calibration (P3-09, DEC-93; `tests/scenario/test_calibration.py`): `quiet` for the measured first entry, the fee in its cost, E-L4's rule from the YAML, the funds report and reproducibility; `long_delta_drop` for the first entry, not the later re-entry; E-L4 blocks from `quiet` underfunded (a first long), `late_friday_surge` without X-S1 at $1,300 (a short skipped as E-L4, and bars below zero reported) and `long_delta_drop` at $1,300 (a re-entry after X-L1); a two-contract run blocked at a value the one-contract run fits (verify checks every run). `pmcc calibrate` runs end to end on `random_walk` (`tests/unit/test_cli_calibrate.py`), with `--check` refusing five byte-level edits that still load.
- The site's tests (`web/src/app/routes.test.tsx`), whose fixtures mark runs `synthetic` to show the banner, and `lseg` to show it absent. The P4-07 deploy serves the real committed results instead of a synthetic sample (PO, DEC-74).

## 6. FakeProvider

The FakeProvider is `fake_provider(FakeLseg(...))` (`tests/fakes/lseg.py`, DEC-83): the real `LsegProvider` over `FakeLseg`.

- The adapter's classification, the frame reader and the fetch logic are all under test, and only the network is fake.
- Tests import it as `tests.fakes` (pytest `pythonpath = ["."]`).

`FakeLseg` answers the way lseg-data 2.1.1 does, not the way a test would like:

- The service answers each RIC on its own: bars, a no-data code (a never-listed RIC: `…Intraday…90001` hourly, `…Interday…70005` daily, as LSEG answered the P1-04 probes), a permission code, or an HTTP status (a failing or signed-out Workspace). A field the RIC doesn't carry is left out of its answer; the request doesn't fail (P1-04, DEC-83).
- A transport failure fails the whole call as an `LDError` holding only its text, and the session still says Opened. The failure can be a timeout, a Workspace that died, or a Pending session.
- If no RIC answered, one `LDError` lists each failure's code, as lseg-data's `validate_responses` does.
- Otherwise a port of lseg-data's `HistoricalBuilder` builds the frame, quirks included:
  - an hourly batch holding a failed RIC raises the `UniverseContainer` TypeError;
  - a daily batch answers without the failed RIC;
  - RICs whose answers carry different fields make the build raise, or file values under the wrong column.
- **Scripted extras:** a closed session, an `open_session` that raises or leaves the session Closed or Pending, and exceptions lseg-data doesn't raise today (an unwrapped transport error, a bug).

It records every request, with whether the session was open. Tests can then assert batch sizes, the order of requests and retries, and that nothing was requested on a closed session.

**The contract test** (`tests/unit/data/test_lseg_contract.py`) keeps the fake honest.

- It feeds the fake's answers to lseg-data's own code: its builder, `validate_responses`, paging, and the flattening in `get_hp_data`.
- The library runs in a separate interpreter with sockets blocked and its config lookup pointed at an empty folder.
- It must give the same frames, messages and raws. An lseg-data upgrade that changes any of them fails there.

The tests are in `tests/unit/data/`:

| File | Covers |
| --- | --- |
| `test_lseg_session.py` | `lseg_session`: the open-state check (Closed and Pending), config path, always closing, a session closed mid-pull, a dead Workspace that still says Opened, importing stays offline |
| `test_lseg_provider.py` | `LsegProvider` and `to_long`: every frame lseg-data builds, UTC bar starts, daily dates, the failure classes, reading the service's codes |
| `test_fetch.py` | INV-12, batches of 25, single-RIC verdicts, retries and backoff, outages at every stage, the form rounds, the log events; a hypothesis property that every contract is answered or unanswered, never both |
| `test_lseg_contract.py` | the fake against lseg-data 2.1.1's own code |
| `test_cache.py`, `test_load.py` | pulls fetched from `FakeLseg` through `fetch_contracts` and `fetch_rics` (`tests/fakes/pulls.py`), cached, then loaded back: the P1-07 round trip (DEC-87) |
| `test_coverage.py` | the coverage summary over a `FakeLseg` cache: valid mids over calendar session bars, near-the-money weekly calls, IV failures per unit over valid quotes (P2-04), the flags (DEC-16) |

**FakeMarket** (`tests/fakes/market.py`, DEC-85) serves code that consumes the port rather than the adapter: the probes (`test_probe.py`), the fetch's plan and unit loop (`test_pull.py`, `test_estimate.py`), and the CLI's `probe` and `fetch` commands (`tests/unit/test_cli.py`).
- It is a `HistoryProvider` over a small synthetic market: one stock, and weekly and monthly calls and puts on a $1 grid near spot and a $5 grid beyond. It has bars from a chosen date, and a contract answers only in the form its expiry calls for.
- It fails the way the port does over lseg-data, as FakeProvider and the contract test pin it:
  - a never-listed RIC gets its real code;
  - a field not carried is left out;
  - an hourly batch holding a failure can't be read, and a daily one answers without it;
  - RICs that each answer one of several fields asked can't be attributed.
- A Workspace that dies (`dies_after`) fails with transient errors, as `LsegProvider` reports a dead or signed-out desktop session (DEC-83); it never raises an outage from the port.
- It has no bars on or after its `today`, and it dates its answers `[start, end)`. LSEG's hourly answers do too; its daily ones don't (DEC-47). The fetch's strike-step asks are daily, so they ask a day wider on each side and keep only bars dated the session; the fake can check that filter (a strike first listed the day after), but not LSEG's own daily edges. P1-09 met those for real: NVDA's fetch measured 83 of its 86 bands, and the 3 unmeasured were on an expiry not yet listed (DEC-14).
- Hooks drive the probe's other branches: several stock suffixes answering, empty fields, never-listed strikes that answer, and a tape that disagrees with the calendar. The fetch adds strikes that aren't listed (to hide a step anchor, DEC-14) and how long before its expiry a contract lists (DEC-88).
- P1-08's done-when names FakeProvider tests. The resume and estimate-order tests run over FakeMarket instead, because a whole symbol's plan asks thousands of dated questions that `FakeLseg`'s fixed bars can't answer; FakeMarket fails as the port does over lseg-data, which FakeProvider and the contract test pin (DEC-88).
- `test_pull.py` runs a whole symbol over a one-week window (9 units) through `prepare` and `pull_units`: the stock tape is the only request before the estimate, a Workspace dying at five points resumes to exactly the missing units, and each band's step follows DEC-14.

Every LDG §4 item, and where it is tested:

| LDG §4 | Behaviour | Tested in |
| --- | --- | --- |
| 1 | Guess RICs; most guesses fail | `test_fetch.py` (INV-12) |
| 2 | `open_session` doesn't raise when it fails | `test_lseg_session.py` |
| 3 | An outage is never recorded as a market fact | `test_fetch.py`, `test_lseg_provider.py`; `test_pull.py` (the unit in flight writes nothing; resume) |
| 4 | Batches of 25; a batch fails whole, or answers partially | `test_fetch.py`, `test_lseg_contract.py` |
| 5 | The response shape varies | `test_lseg_provider.py`, `test_lseg_contract.py` |
| 6 | A field a RIC doesn't carry fails the request. **Not so in the P1-04 probes:** LSEG left `SETTLE` and an unknown field out of the answer, and a batch then came back as flat RIC columns (DEC-83) | `test_lseg_provider.py`, `test_fetch.py` (the field is left out; the batch is split) |
| 7 | No SETTLE; a zero or missing bid means no valid mid | `test_load.py`: `valid_quote` needs BID > 0, ASK > 0 and ASK ≥ BID |
| 8 | Intraday stamps are UTC bar starts | `test_lseg_provider.py`; `bar_end` in `tests/unit/domain/test_clock.py` |
| 9 | The last bar isn't the close; session bars | `tests/unit/domain/test_sessions.py`; `test_load.py`: `session_bar` drops pre-market, the 16:00 stub and a half-day's 13:00 bar |
| 10 | Bogus extended-hours highs and lows | `test_discovery.py`: session ranges use session bars only, and bands err wide |
| 11 | Integer-cent strike ladders | `test_discovery.py` (a hypothesis property) |
| 12 | Band strikes per expiry | `test_discovery.py`: one unit per expiry and right, each with its own bands |
| 13 | A live contract's history is available | `forms_to_ask` in `test_ric.py`; the live-only round in `test_fetch.py` |
| 14 | BID/ASK aren't proven to be the NBBO | wording on the Methodology page (P7); nothing to test in code |
| 15 | Tell the user before a long pull | `test_estimate.py`; `test_cli.py`: the estimate prints before any option request, and `--plan-only` asks only for the stock tape (P1-08) |

## 7. Where tests run

Local commands run in Git Bash on Windows, and CI runs on Ubuntu. The same suite must pass on both (DEC-58).

| Command | Runs |
| --- | --- |
| pre-commit | ruff, ruff-format, pyright, guards (fast; on staged files) |
| `just test` | pytest (dev profile); extra args pass through, e.g. `just test -k ric` |
| `just check` | pre-commit on all files + pytest + `pmcc export --schema-only` + web lint, typecheck and Vitest (DEC-78) |
| CI | everything above (ci profile), plus `pmcc verify`, the web build, the dist guard and the Playwright smoke test |
| `just reproduce` | local, with the cache: batch → verify → INV-13 on real data → export → web build |

## 8. Manual checks

A manual check's result is recorded in the done note of its backlog item.

| Check | When | What |
| --- | --- | --- |
| Data acceptance (LDG §7) | each fetch (P1-09, P1-10) | Spot-check 5 rows per symbol against Workspace. Near-the-money weekly mid availability ≥ 90% (or explained). Holiday weeks look right. Read the diagnostic errors. |
| Trade audit | P3-10, P4-04 | Hand-trace 3 weeks per strategy: blotter row → ledger → raw quotes in the cache, and confirm each rule's triggering values. P3-10's (baseline, NVDA: 4 weeks, 122 checks, no discrepancy) is in DEC-94 |
| Site read-through | P7-08 | Every page at 390, 1100, 1366 and 1600 px (one theme, DEC-03). Every number traceable. No placeholder text. No synthetic banner on real results. |
