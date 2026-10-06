// The position Greeks chart (UI-SPEC §4, Strategy [8]; DEC-120): the position's net δ, Γ, θ and
// ν at every bar, one pane each on a shared time axis, each against a zero ruler, since the sign
// is the point. A bar holding nothing, or a Greek unknown on it, is a hole.
import { moneySigned, moneyTick } from "../../format/money";
import { count, ratio, shares } from "../../format/number";
import {
  baseOption,
  FOUR_PANES,
  lineSeries,
  LINE,
  PANE_NAME_GAP,
  PANE_TICKS,
  plotGrid,
  ruler,
  valueAxis,
  type Palette,
} from "../../theme/echarts";
import type { GreekPoint } from "../../types/generated/run_result";
import { barAxis, xAxis } from "./axis";
import { pointIndex, tipHtml, type TipRow } from "./tooltip";

type Component = "delta" | "gamma" | "theta" | "vega";

interface Pane {
  key: Component;
  /** The series name, also the tooltip's label. */
  name: string;
  /** The pane's axis name: the Greek and its units. */
  axis: string;
  value: (v: number) => string;
  tick: (v: number) => string;
}

export const GREEK_PANES: readonly Pane[] = [
  { key: "delta", name: "Net δ", axis: "Net δ · shares", value: shares, tick: count },
  { key: "gamma", name: "Net Γ", axis: "Net Γ · shares per $1", value: ratio, tick: ratio },
  { key: "theta", name: "Net θ", axis: "Net θ · $ a day", value: moneySigned, tick: moneyTick },
  { key: "vega", name: "Net ν", axis: "Net ν · $ a vol point", value: moneySigned,
    tick: moneyTick },
];

function tipRows(p: Palette, point: GreekPoint): TipRow[] {
  return [
    ...GREEK_PANES.map(({ key, name, value }): TipRow => {
      const v = point[key];
      return [name, v === null ? "—" : value(v), p.text];
    }),
    ["Short call", point.short_open ? "open" : "none"],
  ];
}

export function positionGreeksOption(p: Palette, points: readonly GreekPoint[]) {
  const base = baseOption(p);
  const axis = barAxis(points.map((r) => r.time));
  const last = GREEK_PANES.length - 1;
  return {
    ...base,
    grid: FOUR_PANES.map((g) => plotGrid(p, g)),
    xAxis: GREEK_PANES.map((_, i) => xAxis(p, axis, i, i === last)),
    yAxis: GREEK_PANES.map((pane, i) => valueAxis(p, {
      gridIndex: i,
      splitNumber: PANE_TICKS,
      name: pane.axis,
      nameLocation: "end",
      nameGap: PANE_NAME_GAP,
      nameTextStyle: { color: p["text-muted"], fontFamily: p.fontBody, align: "left" },
      axisLabel: { ...valueAxis(p).axisLabel, formatter: pane.tick },
    })),
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    legend: { ...base.legend, show: false },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const i = pointIndex(params);
        const point = points[i];
        return point ? tipHtml(axis.categories[i] ?? "", tipRows(p, point)) : "";
      },
    },
    series: GREEK_PANES.map((pane, i) => lineSeries(
      pane.name, points.map((r) => r[pane.key]), p.text, LINE.series, "solid",
      { xAxisIndex: i, yAxisIndex: i, markLine: ruler(p, 0) },
    )),
  };
}
