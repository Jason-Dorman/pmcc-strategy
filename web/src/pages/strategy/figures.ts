// The strategy page's figures that come from the ledger's rows rather than the summary (DEC-105):
// the ending account and the lowest available funds, with when. The readouts are built here too.
import type { Readout } from "../../components/Readouts";
import { money, moneySigned } from "../../format/money";
import { count, orDash, pct, ratio } from "../../format/number";
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

// The headline return and the risk-adjusted one, as every page names them (PO, DEC-111).
export const RETURN_HINT = "P&L ÷ starting cash, not annualized";
export const SHARPE_HINT = "Excess daily return over r ÷ its std, × √252";

type Shown = readonly [value: string, extra?: string | undefined];

/** Return on starting NAV, with the weeks it's over. */
export function returnShown(m: Metrics | null): Shown {
  if (!m) return ["—"];
  const weeks = m.weekly_return ? `; over ${m.weekly_return.weeks} weeks` : undefined;
  return [pct(m.return_on_starting_nav), weeks];
}

/** The annualized Sharpe, with the daily returns it's from. */
export function sharpeShown(m: Metrics | null): Shown {
  if (!m) return ["—"];
  return [orDash(m.sharpe_annualized, ratio), `; from ${count(m.sessions)} daily returns`];
}

export const READOUT_HINTS = [
  ["Ending NAV", "Cash + long call − short call + stock, at the last bar"],
  ["P&L", "Ending NAV − starting cash"],
  ["Return on starting NAV", RETURN_HINT],
  ["Sharpe (annualized)", SHARPE_HINT],
  ["Max drawdown", "Largest fall in NAV from a peak"],
  ["Min available funds", "NAV − initial margin, at its lowest"],
  ["Weeks traded / skipped", "Weeks a short was sold / weeks skipped by a rule"],
] as const;

function metricReadouts(m: Metrics | null): Shown[] {
  if (!m) return [["—"], ["—"], ["—"], ["—"]];
  return [
    [moneySigned(m.pnl)],
    returnShown(m),
    sharpeShown(m),
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
