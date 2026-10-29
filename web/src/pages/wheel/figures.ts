// The wheel page's readouts (WD-22), from the result's summary and its last ledger bar; the hints
// define each number as the strategy pages do (PO, DEC-111).
import type { Readout } from "../../components/Readouts";
import { money, moneySigned } from "../../format/money";
import { count, orDash, pct, ratio } from "../../format/number";
import type { WheelResult } from "../../types/generated/wheel_result";
import { RETURN_HINT, SHARPE_HINT } from "../strategy/figures";

export const READOUT_HINTS = [
  ["Ending NAV", "Cash + shares at their mark − the short options' marks, at the last bar"],
  ["P&L", "Ending NAV − starting cash"],
  ["Return on starting cash", RETURN_HINT],
  ["Sharpe (annualized)", SHARPE_HINT],
  ["Max drawdown", "Largest fall in NAV from a peak"],
  ["Complete cycles", "A put assigned, then its shares called away"],
  ["Weeks sold / skipped", "Weeks an option was sold / weeks a rule sold nothing"],
] as const;

type Shown = readonly [value: string, extra?: string];

/** Every skipped week, whatever the rule. */
export function weeksSkipped(run: WheelResult): number {
  return Object.values(run.summary.cycle_stats.weeks_skipped).reduce((a, b) => a + b, 0);
}

export function readouts(run: WheelResult): Readout[] {
  const { metrics: m, cycle_stats: c } = run.summary;
  const last = run.ledger.at(-1);
  const shown: Shown[] = [
    [last ? money(last.nav) : "—"],
    [moneySigned(m.pnl), `, from ${money(run.starting_cash)}`],
    [pct(m.return_on_starting_cash)],
    [orDash(m.sharpe_annualized, ratio), `; from ${count(m.sessions)} daily returns`],
    [money(m.max_drawdown), `: ${pct(m.max_drawdown_pct)}`],
    [count(c.complete_cycles), c.open_at_end ? "; one still open at the end" : ""],
    [`${count(c.weeks_sold)} / ${count(weeksSkipped(run))}`, `, of ${count(c.weeks)}`],
  ];
  return READOUT_HINTS.map(([label, hint], i) => {
    const [value, extra = ""] = shown[i] ?? ["—"];
    return { label, value, hint: `${hint}${extra}` };
  });
}
