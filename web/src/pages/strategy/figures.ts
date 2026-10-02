// The strategy page's figures that come from the ledger's rows rather than the summary (DEC-105):
// the ending account and the lowest available funds, with when. The readouts are built here too.
import type { Readout } from "../../components/Readouts";
import { money, moneySigned } from "../../format/money";
import { orDash, pct } from "../../format/number";
import { timeET } from "../../format/time";
import type { LedgerRowOut, Metrics, RunResult } from "../../types/generated/run_result";

/** The flag a ledger row carries when available funds are below zero (Spec › Reg T). */
export const FUNDS_NEGATIVE = "funds_negative";

/** The lowest available funds over the run, and the first bar it was reached on. */
export function minFunds(ledger: readonly LedgerRowOut[]): LedgerRowOut | undefined {
  return ledger.reduce<LedgerRowOut | undefined>(
    (low, row) => (low === undefined || row.available_funds < low.available_funds ? row : low),
    undefined,
  );
}

/** Bars whose available funds were below zero. */
export function breaches(run: RunResult): number {
  return run.summary.flag_counts[FUNDS_NEGATIVE] ?? 0;
}

export const READOUT_HINTS = [
  ["Ending NAV", "Cash + long call − short call + stock, at the last bar"],
  ["P&L", "Ending NAV − starting cash"],
  ["Return on starting NAV", "P&L ÷ starting cash"],
  ["Return on capital deployed", "P&L ÷ peak long-leg cost"],
  ["Max drawdown", "Largest fall in NAV from a peak"],
  ["Min available funds", "NAV − initial margin, at its lowest"],
  ["Weeks traded / skipped", "Weeks a short was sold / weeks skipped by a rule"],
] as const;

type Shown = readonly [value: string, extra?: string | undefined];

function metricReadouts(m: Metrics | null): Shown[] {
  if (!m) return [["—"], ["—"], ["—"], ["—"]];
  const peak = m.peak_long_cost === null ? undefined : ` (${money(m.peak_long_cost)})`;
  return [
    [moneySigned(m.pnl)],
    [pct(m.return_on_starting_nav)],
    [orDash(m.return_on_capital, pct), peak],
    [money(m.max_drawdown), `: ${pct(m.max_drawdown_pct)}`],
  ];
}

export function readouts(run: RunResult): Readout[] {
  const ledger = run.ledger ?? [];
  const last = ledger.at(-1);
  const low = minFunds(ledger);
  const c = run.summary.cycle_stats;
  const shown: Shown[] = [
    [last ? money(last.nav) : "—"],
    ...metricReadouts(run.summary.metrics),
    low ? [money(low.available_funds), `, ${timeET(low.time)}`] : ["—"],
    c ? [`${c.weeks_traded} / ${c.weeks_skipped}`, `, of ${c.weeks}`] : ["—"],
  ];
  return READOUT_HINTS.map(([label, hint], i) => {
    const [value, extra = ""] = shown[i] ?? ["—"];
    return { label, value, hint: `${hint}${extra}` };
  });
}
