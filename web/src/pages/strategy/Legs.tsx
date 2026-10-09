// Strategy [4], leg attribution (UI-SPEC §6.2; DEC-63): the net short premium (credits less
// buybacks, and a short still open at the end at its mark), the stock after a missed assignment
// (the rule named, never its ID; DEC-113), and the long leg split
// into its intrinsic and extrinsic change; they add up to the run's P&L. Then the cumulative
// two-line chart, its values in a table under it.
import { useCallback } from "react";

import { Chart } from "../../components/charts/Chart";
import { LEG_SERIES, legOption } from "../../components/charts/legs";
import { KeyValue, RuleLink } from "../../components/cells";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { Details, Empty } from "../../components/Note";
import { moneySigned } from "../../format/money";
import type { Palette } from "../../theme/echarts";
import type { LegAttribution, LegPoint, RunResult } from "../../types/generated/run_result";

/** The rows of the attribution table, each a part of the P&L with its sign as it counts.
 * `assignment` is the missed-assignment rule's name, as the run's config has it. */
export function legRows(leg: LegAttribution, pnl: number, assignment: string) {
  return [
    ["Short credits", moneySigned(leg.short_credits)],
    ["Short buybacks", moneySigned(-leg.short_buybacks)],
    [<b key="n">Net short premium</b>, moneySigned(leg.net_short_premium)],
    ["Short open at the end, at its mark", moneySigned(-leg.short_open)],
    [<>Stock after a <RuleLink id="X-S5" prose>{assignment.toLowerCase()}</RuleLink></>,
     moneySigned(leg.assignment_stock_pnl)],
    ["Long leg, intrinsic change", moneySigned(leg.long_intrinsic)],
    ["Long leg, extrinsic change", moneySigned(leg.long_extrinsic)],
    [<b key="l">Long-leg P&amp;L</b>, moneySigned(leg.long_pnl)],
    [<b key="t">P&amp;L</b>, moneySigned(pnl)],
  ] as const;
}

const [LONG, SHORT] = LEG_SERIES;
const SERIES_COLUMNS: readonly TableColumn<LegPoint>[] = [
  { id: "session", header: "Session", sort: (r) => r.session, cell: (r) => r.session },
  { id: "long", header: LONG, num: true, sort: (r) => r.long_pnl,
    cell: (r) => moneySigned(r.long_pnl) },
  { id: "short", header: SHORT, num: true, sort: (r) => r.net_short_premium,
    cell: (r) => moneySigned(r.net_short_premium) },
];

function assignmentName(run: RunResult): string {
  return run.config.strategy.rules.find((r) => r.id === "X-S5")?.name ?? "Missed assignment";
}

export function Legs({ run }: { run: RunResult }) {
  const leg = run.attribution?.leg;
  const series = leg?.series;
  const build = useCallback((p: Palette) => legOption(p, series ?? []), [series]);
  if (!leg || !series) return <Empty>This run&apos;s file has no leg attribution.</Empty>;
  return (
    <>
      <KeyValue label="Leg attribution"
                rows={legRows(leg, run.summary.metrics?.pnl ?? 0, assignmentName(run))} />
      <Chart build={build} label={`${LONG} and ${SHORT} at each session's close`} />
      <Details summary="Values at each session's close" table>
        <DataTable label="Leg attribution by session" rows={series} columns={SERIES_COLUMNS}
                   rowId={(r) => r.session} />
      </Details>
    </>
  );
}
