// A robustness table (DEC-65; `robustness.json`): its reference's row first, then each run
// against it: P&L, the difference from the reference, max drawdown, payoff and the mean weekly
// return with its CI. Every row is published; none is picked as best (HR-6). The Comparison's
// ablations use it (P7-02); Methodology's friction, timing and grid tables are the same shape.
import { useMemo } from "react";

import { money, moneySigned } from "../format/money";
import { meanCI, orDash, ratio } from "../format/number";
import type { RobustnessRow } from "../types/generated/robustness";
import { DataTable, type TableColumn } from "./DataTable";

/** The table's columns; `against` names the reference in the difference column's header. */
export function robustnessColumns(against: string): TableColumn<RobustnessRow>[] {
  return [
    { id: "run", header: "Run", sort: (r) => r.label,
      cell: (r) => <span className="pm-label" title={r.run_id}>{r.label}</span> },
    { id: "pnl", header: "P&L", num: true, sort: (r) => r.pnl, cell: (r) => moneySigned(r.pnl) },
    { id: "delta", header: `Δ vs ${against}`, num: true, sort: (r) => r.pnl_vs_reference,
      cell: (r) => (r.run_id === r.reference ? "reference" : moneySigned(r.pnl_vs_reference)) },
    { id: "drawdown", header: "Max drawdown", num: true, sort: (r) => r.max_drawdown,
      cell: (r) => money(r.max_drawdown) },
    { id: "payoff", header: "Payoff", num: true, sort: (r) => r.payoff_ratio ?? undefined,
      cell: (r) => orDash(r.payoff_ratio, ratio) },
    { id: "weekly", header: "Mean weekly return (95% CI)", num: true,
      sort: (r) => r.weekly_return?.mean, cell: (r) => orDash(r.weekly_return, meanCI) },
  ];
}

export function RobustnessTable({ label, rows, against }: {
  label: string;
  rows: readonly RobustnessRow[];
  against: string;
}) {
  const columns = useMemo(() => robustnessColumns(against), [against]);
  return <DataTable label={label} rows={rows} columns={columns} rowId={(r) => r.run_id} />;
}
