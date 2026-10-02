// The Greek residual chart (UI-SPEC §4, Strategy [8]; DEC-76): the cumulative residual over both
// legs at every bar, one line in TEXT beside the attribution table, with a zero ruler.
import { moneySigned, moneyTick } from "../../format/money";
import {
  baseOption,
  lineSeries,
  LINE,
  plotGrid,
  ruler,
  SINGLE_GRID,
  valueAxis,
  type Palette,
} from "../../theme/echarts";
import type { ResidualPoint } from "../../types/generated/run_result";
import { barAxis, xAxis } from "./axis";
import { pointIndex, tipHtml } from "./tooltip";

export const RESIDUAL_SERIES = "Cumulative residual";

export function residualOption(p: Palette, points: readonly ResidualPoint[]) {
  const base = baseOption(p);
  const axis = barAxis(points.map((r) => r.time));
  return {
    ...base,
    grid: SINGLE_GRID.map((g) => plotGrid(p, g)),
    xAxis: xAxis(p, axis),
    yAxis: valueAxis(p, { axisLabel: { ...valueAxis(p).axisLabel, formatter: moneyTick } }),
    legend: { ...base.legend, data: [RESIDUAL_SERIES] },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const i = pointIndex(params);
        const point = points[i];
        if (!point) return "";
        return tipHtml(axis.categories[i] ?? "",
                       [[RESIDUAL_SERIES, moneySigned(point.cumulative), p.text]]);
      },
    },
    series: [
      lineSeries(RESIDUAL_SERIES, points.map((r) => r.cumulative), p.text, LINE.series, "solid",
                 { markLine: ruler(p, 0) }),
    ],
  };
}
