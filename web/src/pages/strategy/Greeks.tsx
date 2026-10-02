// Strategy [8], Greek attribution (UI-SPEC §6.2; DEC-63, DEC-76): a row per leg × component
// (δ, Γ, θ, ν, residual) with its dollars and its share of the leg's change; each leg's change,
// with the bars wholly residual out of its bars held; and the cumulative residual line.
import { useCallback } from "react";

import { Chart } from "../../components/charts/Chart";
import { RESIDUAL_SERIES, residualOption } from "../../components/charts/residual";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { Details, Empty } from "../../components/Note";
import { moneySigned } from "../../format/money";
import { count, orDash, pct } from "../../format/number";
import { timeET } from "../../format/time";
import type { Palette } from "../../theme/echarts";
import type {
  GreekLeg,
  GreekRow,
  ResidualPoint,
  RunResult,
} from "../../types/generated/run_result";

const COMPONENTS: Record<string, string> = {
  delta: "δ delta",
  gamma: "Γ gamma",
  theta: "θ theta",
  vega: "ν vega",
  residual: "residual",
};

const ROW_COLUMNS: readonly TableColumn<GreekRow>[] = [
  { id: "leg", header: "Leg", sort: (r) => r.leg, cell: (r) => r.leg },
  { id: "component", header: "Component", sort: (r) => r.component,
    cell: (r) => COMPONENTS[r.component] ?? r.component },
  { id: "dollars", header: "Cumulative $", num: true, sort: (r) => r.dollars,
    cell: (r) => moneySigned(r.dollars) },
  { id: "share", header: "% of leg's change", num: true,
    sort: (r) => r.share_of_change ?? undefined, cell: (r) => orDash(r.share_of_change, pct) },
];

const LEG_COLUMNS: readonly TableColumn<GreekLeg>[] = [
  { id: "leg", header: "Leg", sort: (r) => r.leg, cell: (r) => r.leg },
  { id: "change", header: "Change", num: true, sort: (r) => r.change,
    cell: (r) => moneySigned(r.change) },
  { id: "held", header: "Bars held", num: true, sort: (r) => r.bars_held,
    cell: (r) => count(r.bars_held) },
  { id: "residual", header: "Wholly residual", num: true, sort: (r) => r.bars_unattributed,
    cell: (r) => `${count(r.bars_unattributed)} of ${count(r.bars_held)}` },
];

const RESIDUAL_COLUMNS: readonly TableColumn<ResidualPoint>[] = [
  { id: "time", header: "Time (ET)", sort: (r) => r.time, cell: (r) => timeET(r.time) },
  { id: "cumulative", header: RESIDUAL_SERIES, num: true, sort: (r) => r.cumulative,
    cell: (r) => moneySigned(r.cumulative) },
];

export function Greeks({ run }: { run: RunResult }) {
  const greek = run.attribution?.greek;
  const residual = greek?.residual;
  const build = useCallback((p: Palette) => residualOption(p, residual ?? []), [residual]);
  if (!greek || !residual) return <Empty>This run&apos;s file has no Greek attribution.</Empty>;
  return (
    <>
      <div className="pm-stack">
        <DataTable label="Greek attribution by leg and component" rows={greek.rows}
                   columns={ROW_COLUMNS} rowId={(r) => `${r.leg}/${r.component}`} />
        <DataTable label="Bars each leg was held" rows={greek.legs} columns={LEG_COLUMNS}
                   rowId={(r) => r.leg} />
      </div>
      <Chart build={build} label={`${RESIDUAL_SERIES} over both legs at every bar`} />
      <Details summary="Values at every bar" table>
        <DataTable label="Cumulative residual by bar" rows={residual}
                   columns={RESIDUAL_COLUMNS} rowId={(r) => r.time} virtual />
      </Details>
    </>
  );
}
