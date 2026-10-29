// A small wheel result, shaped as `pmcc wheel` writes it, for the wheel pages' tests (W4-01): three
// weeks, a put sold and assigned, a call sold on the shares and called away (one complete cycle),
// then a week skipped. Every state appears, the call's mark goes stale once, and a friction run
// beside it pays half the spread. Typed against the generated schema, so a schema change shows.
import type {
  InstrumentOut,
  LegOut,
  WheelBlotterRow,
  WheelLedgerRowOut,
  WheelResult,
  WheelRule,
} from "../types/generated/wheel_result";
import { SCHEMA_VERSION } from "../types/generated/version";

export const PUT: InstrumentOut = {
  kind: "put",
  ric: "NVDAP022616250.U^D26",
  occ: "NVDA  260402P00162500",
  expiry: "2026-04-02",
  strike: 162.5,
};

export const CALL: InstrumentOut = {
  kind: "call",
  ric: "NVDAD102616500.U^D26",
  occ: "NVDA  260410C00165000",
  expiry: "2026-04-10",
  strike: 165,
};

const STOCK: InstrumentOut = { kind: "stock", ric: "NVDA.O", occ: null, expiry: null, strike: null };

function leg(instrument: InstrumentOut, mark: number, delta: number, stale = false): LegOut {
  return { instrument, mark, delta, qty: 1, stale };
}

type Bar = Omit<WheelLedgerRowOut, "reserved" | "free_cash" | "put" | "call" | "shares" |
  "stock_mark" | "cost_basis" | "flags"> & Partial<WheelLedgerRowOut>;

function bar(row: Bar): WheelLedgerRowOut {
  const reserved = row.reserved ?? 0;
  return { reserved, free_cash: row.cash - reserved, put: null, call: null, shares: 0,
           stock_mark: null, cost_basis: null, flags: [], ...row };
}

export const WHEEL_LEDGER: WheelLedgerRowOut[] = [
  bar({ time: "2026-03-30T10:00:00-04:00", spot: 166.3, state: "put", cash: 25142.5,
        reserved: 16250, put: leg(PUT, 1.425, -0.29), nav: 25000 }),
  bar({ time: "2026-03-30T16:00:00-04:00", spot: 167, state: "put", cash: 25142.5,
        reserved: 16250, put: leg(PUT, 1.2, -0.25), nav: 25022.5 }),
  bar({ time: "2026-04-02T16:00:00-04:00", spot: 160, state: "shares", cash: 8892.5, shares: 100,
        stock_mark: 160, cost_basis: 161.075, nav: 24892.5 }),
  bar({ time: "2026-04-06T10:00:00-04:00", spot: 162, state: "call", cash: 9002.5, shares: 100,
        stock_mark: 162, call: leg(CALL, 1.1, 0.3), cost_basis: 159.975, nav: 25092.5 }),
  bar({ time: "2026-04-06T16:00:00-04:00", spot: 163, state: "call", cash: 9002.5, shares: 100,
        stock_mark: 163, call: leg(CALL, 1.1, 0.33, true), cost_basis: 159.975, nav: 25192.5,
        flags: ["stale_call"] }),
  bar({ time: "2026-04-10T16:00:00-04:00", spot: 167, state: "cash", cash: 25502.5,
        nav: 25502.5 }),
  bar({ time: "2026-04-13T16:00:00-04:00", spot: 168, state: "cash", cash: 25502.5,
        nav: 25502.5 }),
];

function trade(row: Omit<WheelBlotterRow, "fee" | "audit" | "qty"> & { qty?: number }):
    WheelBlotterRow {
  return { fee: 0, audit: {}, qty: 1, ...row };
}

export const WHEEL_BLOTTER: WheelBlotterRow[] = [
  trade({ time: "2026-03-30T10:00:00-04:00", instrument: PUT, side: "SELL", limit: 1.425,
          fill: 1.425, cash_delta: 142.5, trade_pnl: null, rule_id: "W-P1",
          notes: "Sell put: delta -0.29 (target -0.30)" }),
  trade({ time: "2026-04-02T16:00:00-04:00", instrument: PUT, side: "ASSIGN", limit: null,
          fill: 0, cash_delta: 0, trade_pnl: 142.5, rule_id: "W-X2",
          notes: "Assigned: close $160.0000 vs strike $162.5000" }),
  trade({ time: "2026-04-02T16:00:00-04:00", instrument: STOCK, side: "BUY", qty: 100,
          limit: null, fill: 162.5, cash_delta: -16250, trade_pnl: null, rule_id: "W-X2",
          notes: "Buy 100 shares at the strike" }),
  trade({ time: "2026-04-06T10:00:00-04:00", instrument: CALL, side: "SELL", limit: 1.1,
          fill: 1.1, cash_delta: 110, trade_pnl: null, rule_id: "W-C1",
          notes: "Sell call: delta 0.30 (target 0.30)" }),
  trade({ time: "2026-04-10T16:00:00-04:00", instrument: CALL, side: "ASSIGN", limit: null,
          fill: 0, cash_delta: 0, trade_pnl: 110, rule_id: "W-X4",
          notes: "Called away: close $167.0000 vs strike $165.0000" }),
  trade({ time: "2026-04-10T16:00:00-04:00", instrument: STOCK, side: "SELL", qty: 100,
          limit: null, fill: 165, cash_delta: 16500, trade_pnl: 250, rule_id: "W-X4",
          notes: "Sell 100 shares at the strike" }),
];

function rule(id: string, name: string, title: string, summary: string): WheelRule {
  return { id, name, title, summary, params: {}, condition: `${name}: when`,
           action: `${name}: then`, rationale: `Why ${name.toLowerCase()}.` };
}

export const WHEEL_RULES: WheelRule[] = [
  rule("W-T1", "Entry trigger", "When in the session do we sell?",
       "On the first liquid hourly bar of the week."),
  rule("W-P1", "Put timing", "When do we sell a put?", "Every week we hold only cash."),
  rule("W-C1", "Call timing", "When do we sell a covered call?", "Every week we hold shares."),
  rule("W-X2", "Put assigned", "What if the put finishes in the money?",
       "We buy 100 shares at the strike."),
  rule("W-X4", "Called away", "What if the call finishes in the money?",
       "The shares go at the strike."),
];

function wheel(runId: string, capture: number, pnl: number): WheelResult {
  return {
    schema_version: SCHEMA_VERSION,
    manifest: {
      run_id: runId, symbol: "NVDA", strategy_id: "wheel", git_sha: "a".repeat(40),
      git_dirty: false, config_hash: "9".repeat(64), data_manifest_hash: "e".repeat(64),
      lock_hash: "f".repeat(64), run_timestamp: "2026-10-28T01:05:58-04:00", data_source: "lseg",
      pmcc_version: "0.1.0",
    },
    config: {
      wheel: { id: runId, name: capture === 0 ? "Wheel" : `Friction: the wheel at ${capture}`,
               starting_cash: "25000.0000",
               fill_model: { spread_capture: capture, fee_per_contract: "0.0000" },
               rules: WHEEL_RULES },
      window: { start: "2026-03-30", end: "2026-04-17" },
      risk_free_rate: { value: 0.0371, quoted_pct: 3.73, series: "DGS3MO", as_of: "2026-03-27",
                        source: "FRED" },
    },
    rule_text: Object.fromEntries(WHEEL_RULES.map((r) => [r.id, {
      title: r.title, summary: r.summary, condition: r.condition, action: r.action,
      rationale: r.rationale,
    }])),
    starting_cash: 25000,
    summary: {
      metrics: { pnl, return_on_starting_cash: pnl / 25000, max_drawdown: 107.5,
                 max_drawdown_pct: 0.0043, sharpe_annualized: 1.8, sessions: 4 },
      cycle_stats: {
        puts_sold: 1, puts_expired: 0, puts_assigned: 1, calls_sold: 1, calls_expired: 0,
        calls_called_away: 1, weeks: 3, weeks_sold: 2, weeks_skipped: { "W-T1": 1 },
        premium: 252.5, complete_cycles: 1, open_at_end: false,
        time_in_state: { put: 2 / 7, shares: 1 / 7, call: 2 / 7, cash: 2 / 7 },
      },
      benchmarks: {
        baseline_pmcc: { run_id: "baseline_pmcc", config_hash: "c".repeat(64),
                         starting_cash: 15000, return_on_starting_cash: 0.0475,
                         sharpe_annualized: 1.23, max_drawdown_pct: 0.01 },
        sp500: { series: "SP500", start: "2026-03-27", start_close: 6368.85, end: "2026-04-17",
                 end_close: 6500, price_return: 0.0206, source: "FRED" },
      },
      thesis: [
        { claim: 1, test: "P&L over the window > $0", wheel: pnl, benchmark: 0, met: true },
        { claim: 2, test: "annualized Sharpe > the baseline PMCC's", wheel: 1.8,
          benchmark: 1.23, met: true },
        { claim: 3, test: "return on starting cash > the S&P 500's price return",
          wheel: pnl / 25000, benchmark: 0.0206, met: false },
      ],
      flag_counts: { stale_call: 1 },
      invariants: [{ id: "WINV-01", held: true }],
    },
    blotter: WHEEL_BLOTTER,
    ledger: WHEEL_LEDGER,
    gate_log: [
      { session: "2026-03-30", state: "cash", decision_time: "2026-03-30T10:00:00-04:00",
        selected: { delta: -0.29, target_delta: -0.3, mid: "1.4250", spread_pct: 0.007 },
        outcome: { kind: "sold", rule_id: "W-P1" }, notes: "Sell put" },
      { session: "2026-04-06", state: "shares", decision_time: "2026-04-06T10:00:00-04:00",
        selected: { delta: 0.3, target_delta: 0.3, mid: "1.1000", spread_pct: 0.036 },
        outcome: { kind: "sold", rule_id: "W-C1" }, notes: "Sell call" },
      { session: "2026-04-13", state: "cash", decision_time: null, selected: null,
        outcome: { kind: "skipped", rule_id: "W-T1" }, notes: "No liquid bar" },
    ],
    fill_evidence: {
      contracts: 2,
      groups: [
        { group: "puts", points: { mid: [1.425, 1.2], trade: [1.43, 1.19], spread: [0.01, 0.02] },
          fit: { slope: 1.02, intercept: -0.02, r2: 0.999, n: 2, median_abs_gap_pct_spread: 0.5,
                 locked: 0 },
          within_spread: 1 },
        { group: "calls", points: { mid: [1.1], trade: [1.13], spread: [0.04] }, fit: null,
          within_spread: 0 },
      ],
      fit: { slope: 1.01, intercept: -0.01, r2: 0.998, n: 3, median_abs_gap_pct_spread: 0.5,
             locked: 0 },
      within_spread: 2 / 3,
    },
  };
}

export const WHEEL = wheel("wheel", 0, 502.5);
export const WHEEL_SC050 = wheel("wheel--sc050", 0.5, 497.5);

/** The index's wheel entries for NVDA. */
export const WHEEL_INDEX = [WHEEL, WHEEL_SC050].map((w) => ({
  run_id: w.manifest.run_id,
  name: w.config.wheel.name,
  spread_capture: w.config.wheel.fill_model.spread_capture,
  starting_cash: w.starting_cash,
  path: `NVDA/${w.manifest.run_id}.json`,
  data_source: w.manifest.data_source,
  config_hash: w.manifest.config_hash,
  git_sha: w.manifest.git_sha,
}));
