// The comparison page's figures (UI-SPEC §6.1; DEC-105): its readouts and headline rows from each
// strategy's summary, and each strategy's split between the long call and the shorts from its leg
// attribution, which the purpose panel's sentence on the result's main limit reads (DEC-109).
import type { Readout } from "../../components/Readouts";
import { moneySigned } from "../../format/money";
import { orDash } from "../../format/number";
import type { CycleStats, MeanCI, Metrics, RunResult } from "../../types/generated/run_result";
import { RETURN_HINT, returnShown, SHARPE_HINT, sharpeShown } from "../strategy/figures";

export const READOUT_HINTS = [
  ["Quant P&L", "Ending NAV − starting cash"],
  ["Baseline P&L", "Ending NAV − starting cash"],
  ["Quant − Baseline", "The quant layer's P&L over the baseline"],
  ["Return on starting NAV (Q / B)", RETURN_HINT],
  ["Sharpe, annualized (Q / B)", SHARPE_HINT],
  ["Weeks traded (Q / B)", "Weeks a short was sold"],
] as const;

type Shown = readonly [value: string, extra?: string | undefined];

function pnlShown(q: Metrics | null, b: Metrics | null): Shown[] {
  if (!q || !b) return [[orDash(q?.pnl, moneySigned)], [orDash(b?.pnl, moneySigned)], ["—"]];
  return [[moneySigned(q.pnl)], [moneySigned(b.pnl)], [moneySigned(q.pnl - b.pnl)]];
}

/** Quant's figure / the baseline's, as Weeks traded shows them; the hint's detail is quant's
 * (both runs share the window, so the weeks and daily returns are the same). */
function paired(q: Shown, b: Shown): Shown {
  return [`${q[0]} / ${b[0]}`, q[1] ?? b[1]];
}

function weeksShown(q: CycleStats | null, b: CycleStats | null): Shown {
  return q && b ? [`${q.weeks_traded} / ${b.weeks_traded}`, `, of ${q.weeks}`] : ["—"];
}

export function readouts(quant: RunResult, baseline: RunResult): Readout[] {
  const q = quant.summary.metrics;
  const b = baseline.summary.metrics;
  const shown: Shown[] = [
    ...pnlShown(q, b),
    paired(returnShown(q), returnShown(b)),
    paired(sharpeShown(q), sharpeShown(b)),
    weeksShown(quant.summary.cycle_stats, baseline.summary.cycle_stats),
  ];
  return READOUT_HINTS.map(([label, hint], i) => {
    const [value, extra = ""] = shown[i] ?? ["—"];
    return { label, value, hint: `${hint}${extra}` };
  });
}

/** One strategy's P&L split between the long call and the shorts (DEC-63). */
export interface LegSplit {
  name: string;
  pnl: number;
  /** The long leg's P&L. */
  long: number;
  /** Everything else: the net short premium, less a short open at the end, plus X-S5's stock. */
  shorts: number;
  /** The long's intrinsic change: above zero, the stock rose under it. */
  intrinsic: number;
}

export function legSplit(run: RunResult): LegSplit | undefined {
  const leg = run.attribution?.leg;
  const pnl = run.summary.metrics?.pnl;
  if (!leg || pnl === undefined) return undefined;
  return {
    name: run.config.strategy.name,
    pnl,
    long: leg.long_pnl,
    shorts: leg.net_short_premium - leg.short_open + leg.assignment_stock_pnl,
    intrinsic: leg.long_intrinsic,
  };
}

/** The long call riding a rising stock made the result: the stock rose under the long, and the
 * shorts lost, so the long made more than the whole P&L. */
export function longRode(split: LegSplit): boolean {
  return split.intrinsic > 0 && split.shorts < 0;
}

/** A headline row (Comparison [2]): one strategy's result. */
export interface HeadlineRow {
  id: string;
  name: string;
  pnl: number | null;
  returnOnNav: number | null;
  maxDrawdown: number | null;
  maxDrawdownPct: number | null;
  sharpe: number | null;
  payoff: number | null;
  weekly: MeanCI | null;
}

const NO_METRICS = {
  pnl: null, returnOnNav: null, maxDrawdown: null, maxDrawdownPct: null, sharpe: null,
  weekly: null,
} as const;

function metricCells(m: Metrics | null) {
  if (!m) return NO_METRICS;
  return {
    pnl: m.pnl,
    returnOnNav: m.return_on_starting_nav,
    maxDrawdown: m.max_drawdown,
    maxDrawdownPct: m.max_drawdown_pct,
    sharpe: m.sharpe_annualized,
    weekly: m.weekly_return,
  };
}

export function headlineRow(run: RunResult): HeadlineRow {
  return {
    id: run.manifest.run_id,
    name: run.config.strategy.name,
    ...metricCells(run.summary.metrics),
    payoff: run.summary.cycle_stats?.payoff_ratio ?? null,
  };
}
