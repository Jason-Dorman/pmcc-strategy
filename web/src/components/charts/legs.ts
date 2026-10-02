// The leg attribution chart (UI-SPEC §4, Strategy [4]; DEC-63): at each session's close, the
// long leg's P&L so far against the net short premium so far, with a zero ruler.
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
import type { LegPoint } from "../../types/generated/run_result";
import { sessionAxis, xAxis } from "./axis";
import { pointIndex, tipHtml } from "./tooltip";

export const LEG_SERIES = ["Long-leg P&L", "Net short premium"] as const;

export function legOption(p: Palette, series: readonly LegPoint[]) {
  const base = baseOption(p);
  const axis = sessionAxis(series.map((s) => s.session));
  const [longName, shortName] = LEG_SERIES;
  return {
    ...base,
    grid: SINGLE_GRID.map((g) => plotGrid(p, g)),
    xAxis: xAxis(p, axis),
    yAxis: valueAxis(p, { axisLabel: { ...valueAxis(p).axisLabel, formatter: moneyTick } }),
    legend: { ...base.legend, data: [...LEG_SERIES] },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const i = pointIndex(params);
        const point = series[i];
        if (!point) return "";
        return tipHtml(`${point.session} close`, [
          [longName, moneySigned(point.long_pnl), p["long-leg"]],
          [shortName, moneySigned(point.net_short_premium), p["short-leg"]],
        ]);
      },
    },
    series: [
      lineSeries(longName, series.map((s) => s.long_pnl), p["long-leg"], LINE.series, "solid",
                 { markLine: ruler(p, 0) }),
      lineSeries(shortName, series.map((s) => s.net_short_premium), p["short-leg"], LINE.series),
    ],
  };
}
