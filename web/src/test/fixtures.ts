// A small index, two full runs, NVDA's robustness, coverage and fill check, the pooled universe
// files, and rules.json,
// shaped as `pmcc export` writes them, for the page, route and loader tests. Each is typed against the
// generated schema, so a schema change shows here.
import type { Coverage } from "../types/generated/coverage";
import type { FillCheck } from "../types/generated/fill_check";
import type { Index } from "../types/generated/index";
import type { Pooled } from "../types/generated/pooled";
import type { PooledFillCheck } from "../types/generated/pooled_fill_check";
import type { Robustness, RobustnessRow } from "../types/generated/robustness";
import type { RuleChange, RuleOut, Rules, StrategyRules } from "../types/generated/rules";
import type {
  BlotterRow,
  GateLogRowOut,
  GreekAttribution,
  InstrumentOut,
  LedgerRowOut,
  LegOut,
  Manifest,
  RunResult,
  Section,
} from "../types/generated/run_result";
import { SCHEMA_VERSION } from "../types/generated/version";

export const INDEX: Index = {
  schema_version: SCHEMA_VERSION,
  pmcc_version: "0.1.0",
  window: { start: "2026-03-30", end: "2026-09-25" },
  risk_free_rate: {
    value: 0.0371,
    quoted_pct: 3.73,
    series: "DGS3MO",
    as_of: "2026-03-27",
    source: "FRED",
  },
  starting_cash: 15000,
  universe: { pooled: "universe/pooled.json",
              pooled_fill_check: "universe/pooled_fill_check.json" },
  symbols: [
    {
      symbol: "NVDA",
      files: { robustness: "NVDA/robustness.json", coverage: "NVDA/coverage.json",
               fill_check: "NVDA/fill_check.json" },
      runs: [
        {
          run_id: "baseline_pmcc",
          strategy_id: "baseline_pmcc",
          name: "Baseline PMCC",
          detail: "full",
          sections: [],
          path: "NVDA/baseline_pmcc.json",
          data_source: "lseg",
          config_hash: "c".repeat(64),
          git_sha: "a".repeat(40),
        },
        {
          run_id: "quant_pmcc",
          strategy_id: "quant_pmcc",
          name: "Quant PMCC",
          detail: "full",
          sections: ["gate_log", "greek_attribution"],
          path: "NVDA/quant_pmcc.json",
          data_source: "lseg",
          config_hash: "d".repeat(64),
          git_sha: "a".repeat(40),
        },
      ],
    },
    { symbol: "QQQ", files: {}, runs: [] },
  ],
};

function manifest(runId: string): Manifest {
  return {
    run_id: runId,
    symbol: "NVDA",
    strategy_id: runId,
    git_sha: "a".repeat(40),
    git_dirty: false,
    config_hash: "c".repeat(64),
    data_manifest_hash: "e".repeat(64),
    lock_hash: "f".repeat(64),
    run_timestamp: "2026-09-30T14:42:28-04:00",
    data_source: "lseg",
    pmcc_version: "0.1.0",
  };
}

export const LONG: InstrumentOut = {
  kind: "call",
  ric: "NVDAH212611500.U^H26",
  occ: "NVDA  260821C00115000",
  expiry: "2026-08-21",
  strike: 115,
};

export const SHORT: InstrumentOut = {
  kind: "call",
  ric: "NVDAD022617250.U^D26",
  occ: "NVDA  260402C00172500",
  expiry: "2026-04-02",
  strike: 172.5,
};

function leg(instrument: InstrumentOut, mark: number, delta: number, stale = false): LegOut {
  return { instrument, mark, delta, qty: 1, stale };
}

function bar(time: string, nav: number, funds: number, short: LegOut | null,
             flags: string[] = []): LedgerRowOut {
  return {
    time,
    long: leg(LONG, 56.3, 0.9),
    short,
    stock: null,
    cash: 9439.5,
    nav,
    im: nav - funds,
    mm: nav - funds,
    available_funds: funds,
    excess_equity: funds,
    flags,
  };
}

/** Four bars over two sessions; the third carries a stale short mark. */
export const LEDGER: LedgerRowOut[] = [
  bar("2026-03-30T10:00:00-04:00", 15000, 9370, leg(SHORT, 0.695, 0.19)),
  bar("2026-03-30T16:00:00-04:00", 14850, 9100, leg(SHORT, 0.5, 0.15)),
  bar("2026-03-31T10:00:00-04:00", 15400, 9650, leg(SHORT, 0.5, 0.15, true), ["stale_short"]),
  bar("2026-03-31T16:00:00-04:00", 15712, 9900, null),
];

export const BLOTTER: BlotterRow[] = [
  {
    time: "2026-03-30T10:00:00-04:00", instrument: LONG, side: "BUY", qty: 1, limit: 56.3,
    fill: 56.3, cash_delta: -5630, fee: 0, rule_id: "E-L1", notes: "dte 144, delta 0.897503",
    audit: {},
  },
  {
    time: "2026-03-30T10:00:00-04:00", instrument: SHORT, side: "SELL", qty: 1, limit: 0.695,
    fill: 0.695, cash_delta: 69.5, fee: 0, rule_id: "E-S1", notes: "dte 3, delta 0.190744",
    audit: {},
  },
  {
    time: "2026-03-31T16:00:00-04:00", instrument: SHORT, side: "BUY", qty: 1, limit: 0.3,
    fill: 0.3, cash_delta: -30, fee: 0, rule_id: "X-S1", notes: "take profit", audit: {},
  },
];

function gate(rule_id: string, status: string, values: GateLogRowOut["gates"][number]["values"]) {
  return { rule_id, status, reason: "", values };
}

export const GATE_LOG: GateLogRowOut[] = [
  {
    session: "2026-03-30",
    decision_time: "2026-03-30T10:00:00-04:00",
    selected: { option: "NVDA 2026-04-02 C 172.5000", delta: 0.190744, mid: "0.6950" },
    gates: [
      gate("G-1", "pass", { bars_checked: 1 }),
      gate("G-3", "pass", { ratio: 1.105527, max_ratio: 1.2 }),
      gate("G-4", "pass", { ratio: 1.403563, min_ratio: 1 }),
      gate("G-5", "pass", { mid: "0.6950", min_mid: "0.1000" }),
    ],
    outcome: { kind: "sold", rule_id: "E-S1" },
    notes: "",
  },
  {
    session: "2026-04-06",
    decision_time: "2026-04-06T10:00:00-04:00",
    selected: { option: "NVDA 2026-04-10 C 180.0000", delta: 0.21, mid: "0.9000" },
    gates: [
      gate("G-1", "pass", { bars_checked: 1 }),
      gate("G-3", "n/a", {}),
      gate("G-4", "fire", { ratio: 0.951, min_ratio: 1 }),
      gate("G-5", "not_evaluated", {}),
    ],
    outcome: { kind: "skipped", rule_id: "G-4" },
    notes: "",
  },
];

const GREEK: GreekAttribution = {
  rows: [
    { leg: "long", component: "delta", dollars: 800, share_of_change: 1.12 },
    { leg: "long", component: "residual", dollars: -85, share_of_change: -0.12 },
    { leg: "short", component: "theta", dollars: 30, share_of_change: 0.75 },
    { leg: "short", component: "residual", dollars: 10, share_of_change: null },
  ],
  legs: [
    { leg: "long", change: 715, bars_held: 4, bars_unattributed: 1 },
    { leg: "short", change: 39.5, bars_held: 3, bars_unattributed: 0 },
  ],
  residual: LEDGER.map((r, i) => ({ time: r.time, cumulative: i * -25 })),
};

const NAMES: Readonly<Record<string, string>> = {
  baseline_pmcc: "Baseline PMCC",
  quant_pmcc: "Quant PMCC",
};

/** A full run: every section its page shows, for the strategy's `report.sections`. */
export function run(runId: string, sections: Section[]): RunResult {
  return {
    schema_version: SCHEMA_VERSION,
    manifest: manifest(runId),
    starting_cash: 15000,
    config: {
      strategy: {
        id: runId,
        name: NAMES[runId] ?? runId,
        fill_model: { spread_capture: 0, fee_per_contract: "0.00" },
        report: { detail: "full", sections },
        rules: [],
      },
      window: { start: "2026-03-30", end: "2026-09-25" },
      risk_free_rate: INDEX.risk_free_rate,
    },
    rule_text: {},
    blotter: BLOTTER,
    ledger: LEDGER,
    gate_log: GATE_LOG,
    cycles: [],
    summary: {
      flag_counts: { stale_short: 1 },
      invariants: [],
      metrics: {
        pnl: 712, return_on_starting_nav: 0.047467, max_drawdown: 150, max_drawdown_pct: 0.01,
        sessions: 2, longest_underwater_sessions: 1, sharpe_annualized: 1.234, sortino_annualized: null,
        weekly_return: null,
      },
      cycle_stats: {
        weeks: 2, weeks_traded: 1, weeks_skipped: 1, weeks_long_held: 2, win_rate: 0.5,
        average_win: 712, average_loss: -20, payoff_ratio: 35.6, premium_captured_pct: 0.568345,
        credit_pct_of_long_cost: 0.012345,
      },
      exit_mix: { "X-S1": 1, "X-S2": 0 },
      skips_by_rule: { "G-4": 1 },
      nav_close: null,
      weekly_returns: null,
    },
    attribution: {
      leg: {
        short_credits: 69.5, short_buybacks: 30, net_short_premium: 39.5, short_open: 0,
        assignment_stock_pnl: 0, long_intrinsic: 900, long_extrinsic: -227.5, long_pnl: 672.5,
        series: [
          { session: "2026-03-30", long_pnl: -150, net_short_premium: 19.5 },
          { session: "2026-03-31", long_pnl: 672.5, net_short_premium: 39.5 },
        ],
      },
      greek: sections.includes("greek_attribution") ? GREEK : null,
    },
  };
}

function ci(mean: number, low: number, high: number) {
  return { mean, low, high, level: 0.95, resamples: 10000, seed: 535, weeks: 2 };
}

function robustnessRow(run_id: string, label: string, pnl: number, pnl_vs_reference: number,
                       payoff_ratio: number | null): RobustnessRow {
  return { run_id, label, reference: "quant_pmcc", pnl, pnl_vs_reference, max_drawdown: 150,
           payoff_ratio, weekly_return: ci(0.0237, -0.01, 0.0574) };
}

/** A row against `reference`, with its own mean weekly return. */
function against(reference: string, run_id: string, label: string, pnl: number, mean: number,
                 refPnl: number): RobustnessRow {
  return { run_id, label, reference, pnl, pnl_vs_reference: pnl - refPnl, max_drawdown: 150,
           payoff_ratio: 1.2, weekly_return: ci(mean, mean - 0.02, mean + 0.02) };
}

/** The timing table: the E-T1 baseline (CI −1.0% to 3.0%), then two fixed bars inside it. */
export const TIMING: RobustnessRow[] = [
  against("baseline_pmcc", "baseline_pmcc", "Baseline PMCC", 712, 0.01, 712),
  against("baseline_pmcc", "baseline_pmcc--t1", "Timing: baseline, short decided on bar 1 (10:00)",
          712, 0.01, 712),
  against("baseline_pmcc", "baseline_pmcc--t2", "Timing: baseline, short decided on bar 2 (11:00)",
          500, 0.008, 712),
];

/** NVDA's robustness file: quant, then two ablations against it; each strategy's friction; the
 * timing table; one grid run. */
export const ROBUSTNESS: Robustness = {
  schema_version: SCHEMA_VERSION,
  symbol: "NVDA",
  ablations: [
    robustnessRow("quant_pmcc", "Quant PMCC", 712, 0, 35.6),
    robustnessRow("quant_pmcc--a1", "A1: quant with the baseline long leg", 1006, 294, null),
    robustnessRow("quant_pmcc--a4", "A4: quant without the VRP gate", 457.5, -254.5, 2.1),
  ],
  friction: [
    against("baseline_pmcc", "baseline_pmcc", "Baseline PMCC", 712, 0.01, 712),
    against("baseline_pmcc", "baseline_pmcc--sc025", "Friction: baseline at spread capture 0.25",
            690, 0.0095, 712),
    against("quant_pmcc", "quant_pmcc", "Quant PMCC", 712, 0.01, 712),
    against("quant_pmcc", "quant_pmcc--sc025", "Friction: quant at spread capture 0.25", 650,
            0.009, 712),
  ],
  timing: TIMING,
  timing_dispersion: { range: 212, runs: 2, std: 149.906638 },
  grid: [
    against("quant_pmcc", "quant_pmcc", "Quant PMCC", 712, 0.01, 712),
    against("quant_pmcc", "quant_pmcc--k075", "Grid: quant with k = 0.75", 800, 0.011, 712),
  ],
};

/** NVDA's fetch coverage. */
export const COVERAGE: Coverage = {
  schema_version: SCHEMA_VERSION,
  symbol: "NVDA",
  rows: [
    { kind: "stock", requested: 1, answered: 1, unanswered: 0, mid_availability: 1 },
    { kind: "weekly calls", requested: 993, answered: 881, unanswered: 112,
      mid_availability: 0.829144 },
  ],
  iv_priced: 1000,
  iv_failures: { below_floor: 80, no_convergence: 3 },
  stale_mark_rate: 0.0125,
  unavailable_fields: [],
};

/** NVDA's fill check: three short pairs (one on a locked quote), two long ones. */
export const FILL_CHECK: FillCheck = {
  schema_version: SCHEMA_VERSION,
  symbol: "NVDA",
  groups: [
    { group: "shorts",
      fit: { slope: 0.999837, intercept: 0.002265, r2: 0.999227, n: 3, locked: 1,
             median_abs_gap_pct_spread: 0.5 },
      points: { mid: [0.5, 1.25, 2], trade: [0.55, 1.2, 2], spread: [0.1, 0.1, 0] } },
    { group: "longs",
      fit: { slope: 1.000335, intercept: -0.003417, r2: 0.99969, n: 2, locked: 0,
             median_abs_gap_pct_spread: 0.318182 },
      points: { mid: [50, 60], trade: [50.2, 59.9], spread: [0.6, 0.6] } },
  ],
};

/** The fill check pooled over NVDA alone. */
export const POOLED_FILL_CHECK: PooledFillCheck = {
  schema_version: SCHEMA_VERSION,
  symbols: ["NVDA"],
  groups: [
    { group: "shorts", fit: { slope: 0.99, intercept: 0.01, r2: 0.98, n: 3, locked: 1,
                              median_abs_gap_pct_spread: 0.5 } },
    { group: "longs", fit: null },
  ],
};

/** The universe pooled over NVDA alone. */
export const POOLED: Pooled = {
  schema_version: SCHEMA_VERSION,
  symbols: ["NVDA"],
  quant_beat_baseline: [],
  strategies: [
    { strategy_id: "baseline_pmcc", total_pnl: 712, weekly_return: ci(0.009547, -0.008884, 0.027615) },
    { strategy_id: "quant_pmcc", total_pnl: 712, weekly_return: ci(0.008852, -0.010061, 0.027401) },
  ],
};

// ---- rules.json --------------------------------------------------------------------------------

interface RuleFixture {
  name: string;
  title: string;
  summary: string;
  rationale: string;
  shown?: Record<string, string>;
}

/** A rule as rules.json writes it. The condition and action, the rule stated exactly, are only
 * hovers on this page, so they're the summary's stand-ins. */
function rule(id: string, { name, title, summary, rationale, shown = {} }: RuleFixture): RuleOut {
  return { id, name, kind: id.toLowerCase(), params: {}, shown, title, summary,
           condition: `${id} condition`, action: `${id} action`, rationale };
}

const NO_ROLLS = "Why no rolls: next Monday's sale already is the roll.";

/** The rules both strategies share, as the shared YAML writes them. */
const SHARED: Record<string, RuleOut> = {
  "E-T1": rule("E-T1", { name: "Entry trigger", title: "When do we enter?",
                         summary: "On the first bar with a spread within 3% (long) or 10% (short).",
                         rationale: "Liquidity decides.",
                         shown: { long_max_spread: "3%", short_max_spread: "10%" } }),
  "E-S5": rule("E-S5", { name: "Structural constraint", title: "Structural safety check",
                         summary: "Sell only if the strikes cover the debit.",
                         rationale: "The strikes cover the debit.\nIt uses the long's entry fill." }),
  "G-1": rule("G-1", { name: "No quote / liquidity", title: "No tradable quote",
                       summary: "The selected short never passes the entry trigger on Monday.",
                       rationale: "No quote, no trade." }),
  "G-2": rule("G-2", { name: "Structural constraint", title: "Structural constraint",
                       summary: "The selected short fails the structural safety check.",
                       rationale: "No losing structure." }),
  "X-L1": rule("X-L1", { name: "Long reset", title: "Replace the long when its delta gets too low",
                         summary: "On Monday, if the long's delta is below 0.50, replace it.",
                         rationale: "Keep the stock substitute.", shown: { min_delta: "0.50" } }),
  "X-L2": rule("X-L2", { name: "Long roll", title: "Replace the long when expiry gets close",
                         summary: "On Monday, if the long has under 90 days left, replace it.",
                         rationale: "Stay long-dated.", shown: { min_dte: "90" } }),
  "X-S1": rule("X-S1", { name: "Take profit", title: "Take profit",
                         summary: "If the short falls to 25% of the premium, before the Friday check, buy it back.",
                         rationale: `${NO_ROLLS}\nBuy the short back once it is cheap.`,
                         shown: { max_credit_fraction: "25%" } }),
  "X-S3": rule("X-S3", { name: "Friday check", title: "Friday risk check",
                         summary: "On the last session by 15:00 ET, buy the short back if spot is within 0.25 × EM of it.",
                         rationale: `${NO_ROLLS}\nThe Friday buffer.`,
                         shown: { check_by: "15:00", em_buffer: "0.25" } }),
  "X-E1": rule("X-E1", { name: "End of backtest", title: "End of the backtest",
                         summary: "Mark everything to its mid.", rationale: "Nothing is force-closed." }),
};

const BASELINE_PICKS: Record<string, RuleOut> = {
  "E-L2": rule("E-L2", { name: "Long leg expiry", title: "Which expiry do we use for the long call?",
                         summary: "The monthly expiry closest to 180 days out.",
                         rationale: "The textbook long.", shown: { target_dte: "180" } }),
  "E-L3": rule("E-L3", { name: "Long leg strike", title: "Which long call do we buy?",
                         summary: "The call with delta closest to 0.80.", rationale: "A deep ITM long.",
                         shown: { target_delta: "0.80" } }),
  "E-S3": rule("E-S3", { name: "Short leg strike", title: "Which short strike do we sell?",
                         summary: "The OTM call with delta closest to 0.30.",
                         rationale: "The textbook short.", shown: { target_delta: "0.30" } }),
};

const QUANT_PICKS: Record<string, RuleOut> = {
  "E-L2": rule("E-L2", { name: "Long leg expiry", title: "Which expiry do we use for the long call?",
                         summary: "Any monthly expiry 120 to 270 days out.",
                         rationale: "A range of longs.", shown: { max_dte: "270", min_dte: "120" } }),
  "E-L3": rule("E-L3", { name: "Long leg strike", title: "Which long call do we buy?",
                         summary: "Among deltas 0.70 to 0.90, the lowest extrinsic ÷ delta.",
                         rationale: "The cheapest replacement.",
                         shown: { max_delta: "0.90", min_delta: "0.70" } }),
  "E-S3": rule("E-S3", { name: "Short leg strike", title: "Which short strike do we sell?",
                         summary: "The lowest strike at or above spot + 1.0 × the expected move.",
                         rationale: "The expected-move short.", shown: { k: "1.0" } }),
};

const QUANT_GATES: Record<string, RuleOut> = {
  "G-3": rule("G-3", { name: "Event week", title: "Event week",
                       summary: "Front-week ATM IV ÷ next-week ATM IV is above 1.20.",
                       rationale: "Events from the chain.", shown: { max_ratio: "1.20" } }),
  "G-4": rule("G-4", { name: "Volatility risk premium", title: "Volatility risk premium",
                       summary: "Front-week ATM IV ÷ RV20 is below 1.00.",
                       rationale: "The VRP gate.", shown: { min_ratio: "1.00" } }),
  "G-5": rule("G-5", { name: "Minimum premium", title: "Minimum premium",
                       summary: "The selected short's mid is below $0.10 a share.",
                       rationale: "Too small a premium.", shown: { min_mid: "$0.10" } }),
};

const ORDER = ["E-T1", "E-L2", "E-L3", "E-S3", "E-S5", "G-1", "G-2", "G-3", "G-4", "G-5", "X-S1",
               "X-S3", "X-L1", "X-L2", "X-E1"];

function rulesOf(...sets: Record<string, RuleOut>[]): RuleOut[] {
  const all: Record<string, RuleOut> = Object.assign({}, ...sets);
  return ORDER.flatMap((id) => all[id] ?? []);
}

function strategy(id: string, name: string, rules: RuleOut[], family: StrategyRules["family"],
                  changes: RuleChange[] = [], spread_capture = 0): StrategyRules {
  const strategy_id = id.split("--")[0] ?? id;
  return { id, name, strategy_id, family, detail: family === "strategy" ? "full" : "summary",
           spread_capture, fee_per_contract: 0, rules, changes };
}

const QUANT_RULES = rulesOf(SHARED, QUANT_PICKS, QUANT_GATES);

/** rules.json: the two strategies, two ablations and one run of each sensitivity check. */
export const RULES: Rules = {
  schema_version: SCHEMA_VERSION,
  strategies: [
    strategy("baseline_pmcc", "Baseline PMCC", rulesOf(SHARED, BASELINE_PICKS), "strategy"),
    strategy("baseline_pmcc--sc025", "Friction: baseline at spread capture 0.25",
             rulesOf(SHARED, BASELINE_PICKS), "friction", [], 0.25),
    strategy("baseline_pmcc--t1", "Timing: baseline, short decided on bar 1 (10:00)",
             rulesOf(SHARED, BASELINE_PICKS, {
               "E-T1": rule("E-T1", { name: "Entry trigger, fixed bar", title: "When do we enter?",
                                      summary: "The short is decided only on bar 1.",
                                      rationale: "The timing check.",
                                      shown: { bar: "1", long_max_spread: "3%",
                                               short_max_spread: "10%" } }),
             }), "timing", [{ rule_id: "E-T1", change: "replaced" }]),
    strategy("quant_pmcc", "Quant PMCC", QUANT_RULES, "strategy"),
    strategy("quant_pmcc--a1", "A1: quant with the baseline long leg",
             rulesOf(SHARED, QUANT_PICKS, QUANT_GATES, BASELINE_PICKS,
                     { "E-S3": QUANT_PICKS["E-S3"] as RuleOut }),
             "ablation",
             [{ rule_id: "E-L2", change: "replaced" }, { rule_id: "E-L3", change: "replaced" }]),
    strategy("quant_pmcc--a3", "A3: quant without the event gate",
             QUANT_RULES.filter((r) => r.id !== "G-3"), "ablation",
             [{ rule_id: "G-3", change: "removed" }]),
    strategy("quant_pmcc--k075", "Grid: quant with k = 0.75",
             rulesOf(SHARED, QUANT_PICKS, QUANT_GATES, {
               "E-S3": rule("E-S3", { name: "Short leg strike", title: "Which short strike do we sell?",
                                      summary: "The lowest strike at or above spot + 0.75 × the expected move.",
                                      rationale: "The expected-move short.", shown: { k: "0.75" } }),
             }), "grid", [{ rule_id: "E-S3", change: "params" }]),
  ],
};

export const FILES: Record<string, unknown> = {
  "data/index.json": INDEX,
  "data/NVDA/baseline_pmcc.json": run("baseline_pmcc", []),
  "data/NVDA/quant_pmcc.json": run("quant_pmcc", ["gate_log", "greek_attribution"]),
  "data/NVDA/robustness.json": ROBUSTNESS,
  "data/NVDA/coverage.json": COVERAGE,
  "data/NVDA/fill_check.json": FILL_CHECK,
  "data/universe/pooled_fill_check.json": POOLED_FILL_CHECK,
  "data/universe/pooled.json": POOLED,
  "data/rules.json": RULES,
};

/** A fetch over `files`, answering 404 for anything else. */
export function fakeFetch(files: Record<string, unknown> = FILES) {
  return (url: string): Promise<Response> => {
    const body = files[url];
    return Promise.resolve(
      body === undefined
        ? new Response("not found", { status: 404 })
        : new Response(JSON.stringify(body), { status: 200 }),
    );
  };
}
