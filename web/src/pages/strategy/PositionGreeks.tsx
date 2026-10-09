// Strategy [8], position Greeks (UI-SPEC §6.2; PO, DEC-120): each Greek's mean for the long, the
// short and the net over the bars both legs were held, against the textbook PMCC's long delta,
// short gamma, long theta and long vega; then the net at every bar, one pane per Greek, its
// values in a table under it. Each Greek is named in words (PO, DEC-121).
import { useCallback } from "react";

import { Chart } from "../../components/charts/Chart";
import { GREEK_PANES, positionGreeksOption } from "../../components/charts/positionGreeks";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { Details, Empty } from "../../components/Note";
import { count, orDash, pct } from "../../format/number";
import { timeET } from "../../format/time";
import type { Palette } from "../../theme/echarts";
import type {
  GreekPoint,
  PositionGreekRow,
  RunResult,
} from "../../types/generated/run_result";

const LABELS: Record<string, { greek: string; units: string }> = {
  delta: { greek: "Delta", units: "shares" },
  gamma: { greek: "Gamma", units: "shares per $1" },
  theta: { greek: "Theta", units: "$ a day" },
  vega: { greek: "Vega", units: "$ a vol point" },
};

/** A Greek's value in its own units. */
function valueOf(component: string): (v: number) => string {
  return GREEK_PANES.find((p) => p.key === component)?.value ?? String;
}

function mean(pick: (r: PositionGreekRow) => number | null, header: string, id: string):
    TableColumn<PositionGreekRow> {
  return { id, header, num: true, sort: (r) => pick(r) ?? undefined,
           cell: (r) => orDash(pick(r), valueOf(r.component)) };
}

const ROW_COLUMNS: readonly TableColumn<PositionGreekRow>[] = [
  { id: "greek", header: "Greek", sort: (r) => r.component,
    cell: (r) => LABELS[r.component]?.greek ?? r.component },
  { id: "units", header: "Units", sort: (r) => LABELS[r.component]?.units ?? "",
    cell: (r) => LABELS[r.component]?.units ?? "" },
  mean((r) => r.long, "Long", "long"),
  mean((r) => r.short, "Short", "short"),
  mean((r) => r.net, "Net", "net"),
  { id: "sign", header: "Textbook sign", sort: (r) => r.expected_sign,
    cell: (r) => (r.expected_sign > 0 ? "+" : "−") },
  { id: "share", header: "Bars with that sign", num: true,
    sort: (r) => r.share_with_sign ?? undefined, cell: (r) => orDash(r.share_with_sign, pct) },
  { id: "bars", header: "Bars", num: true, sort: (r) => r.bars, cell: (r) => count(r.bars) },
];

const SERIES_COLUMNS: readonly TableColumn<GreekPoint>[] = [
  { id: "time", header: "Time (ET)", sort: (r) => r.time, cell: (r) => timeET(r.time) },
  ...GREEK_PANES.map(({ key, name, value }): TableColumn<GreekPoint> => ({
    id: key, header: name, num: true, sort: (r) => r[key] ?? undefined,
    cell: (r) => orDash(r[key], value),
  })),
  { id: "short", header: "Short call", sort: (r) => (r.short_open ? 1 : 0),
    cell: (r) => (r.short_open ? "open" : "none") },
];

export function PositionGreeks({ run }: { run: RunResult }) {
  const greeks = run.position_greeks;
  const series = greeks?.series;
  const build = useCallback((p: Palette) => positionGreeksOption(p, series ?? []), [series]);
  if (!greeks || !series) return <Empty>This run&apos;s file has no position Greeks.</Empty>;
  return (
    <>
      <DataTable label="Position Greeks by leg" rows={greeks.rows} columns={ROW_COLUMNS}
                 rowId={(r) => r.component} />
      <Chart build={build} hero label="Net delta, gamma, theta and vega at every bar" />
      <Details summary="Values at every bar" table>
        <DataTable label="Position Greeks by bar" rows={series} columns={SERIES_COLUMNS}
                   rowId={(r) => r.time} virtual />
      </Details>
    </>
  );
}
