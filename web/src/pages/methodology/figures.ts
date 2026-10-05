// The methodology page's figures (UI-SPEC §6.4), each read from the results as the page renders:
// the entry-timing dispersion and when it is fragile (PO, DEC-67), the fill check's pairs, and
// the facts the Limits of this backtest panel states (DEC-109).
import type { FillPoints } from "../../types/generated/fill_check";
import type { RobustnessRow } from "../../types/generated/robustness";
import type { MeanCI, RunResult } from "../../types/generated/run_result";
import { tradeResults } from "../strategy/tradePnl";

// ---- entry timing ------------------------------------------------------------------------------

/** The timing table's spread over its fixed-bar runs, and whether it is fragile. */
export interface Timing {
  /** The E-T1 baseline: shown beside the fixed bars, not counted. */
  reference: RobustnessRow;
  fixed: readonly RobustnessRow[];
  /** The lowest and highest mean weekly return over the fixed bars. */
  means: { low: number; high: number } | null;
  /** The fixed bars whose mean weekly return falls outside the reference's 95% CI. */
  outside: readonly RobustnessRow[];
}

/** Fragile when any fixed bar's mean weekly return falls outside the E-T1 baseline's 95% CI (PO,
 * DEC-67): timing moved the result more than the sample's own noise. No new threshold. */
export function timing(rows: readonly RobustnessRow[]): Timing | undefined {
  const reference = rows.find((r) => r.run_id === r.reference);
  if (!reference) return undefined;
  const fixed = rows.filter((r) => r !== reference);
  const means = fixed.flatMap((r) => (r.weekly_return ? [r.weekly_return.mean] : []));
  const ci = reference.weekly_return;
  const outside = ci
    ? fixed.filter((r) => r.weekly_return
        && (r.weekly_return.mean < ci.low || r.weekly_return.mean > ci.high))
    : [];
  return {
    reference,
    fixed,
    means: means.length > 0 ? { low: Math.min(...means), high: Math.max(...means) } : null,
    outside,
  };
}

// ---- the fill check ----------------------------------------------------------------------------

/** One pair of the fill check: a session bar's mid and its last trade. */
export interface FillPair {
  i: number;
  mid: number;
  trade: number;
  spread: number;
}

export function fillPairs(points: FillPoints): FillPair[] {
  return points.mid.map((mid, i) => ({ i, mid, trade: points.trade[i] ?? 0,
                                       spread: points.spread[i] ?? 0 }));
}

/** |trade − mid| ÷ spread, as the fit's median takes it: none for a locked quote. */
export function gapOfSpread(pair: FillPair): number | null {
  return pair.spread > 0 ? Math.abs(pair.trade - pair.mid) / pair.spread : null;
}

// ---- the limits of this backtest ---------------------------------------------------------------

/** A long call's round trip, or the long still held at the end. */
export interface LongTrip {
  pnl: number;
  /** When it was closed, and the rule that closed it; none for the long still held. */
  closed?: { time: string; ruleId: string };
}

/** Each long a run held, in order: the closed ones from the blotter's round trips (DEC-108), and
 * the one still held, the long leg's P&L less theirs. */
export function longTrips(run: RunResult): LongTrip[] {
  const blotter = run.blotter ?? [];
  const longs = new Set(blotter.filter((b) => b.rule_id === "E-L1").map((b) => b.instrument.ric));
  const results = tradeResults(blotter);
  const closed: LongTrip[] = blotter.flatMap((b) => {
    const result = results.get(b);
    return result && longs.has(b.instrument.ric)
      ? [{ pnl: result.pnl, closed: { time: b.time, ruleId: b.rule_id } }]
      : [];
  });
  const total = run.attribution?.leg?.long_pnl;
  if (total === undefined) return closed;
  const booked = closed.reduce((s, t) => s + Math.round(t.pnl * 100), 0) / 100;
  const held = blotter.length > 0 && openLong(blotter, longs);
  return held ? [...closed, { pnl: Math.round((total - booked) * 100) / 100 }] : closed;
}

function openLong(blotter: NonNullable<RunResult["blotter"]>, longs: Set<string>): boolean {
  const qty = new Map<string, number>();
  for (const b of blotter) {
    if (!longs.has(b.instrument.ric)) continue;
    const signed = b.side === "BUY" ? b.qty : -b.qty;
    qty.set(b.instrument.ric, (qty.get(b.instrument.ric) ?? 0) + signed);
  }
  return [...qty.values()].some((q) => q !== 0);
}

/** Whether two weekly-return CIs overlap: if they do, the sample can't tell the means apart. */
export function overlap(a: MeanCI, b: MeanCI): boolean {
  return Math.max(a.low, b.low) <= Math.min(a.high, b.high);
}
