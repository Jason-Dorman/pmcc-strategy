// The mid-vs-print scatter (UI-SPEC §4, Methodology [2], [3]; DEC-64): every pair a cyan circle,
// x the mid and y the print, with the OLS fit and y = x as references, thin and never a series
// hue. Every pair is drawn (PO, DEC-05): ECharts' large mode draws them as one path, so tens of
// thousands of points don't become tens of thousands of nodes.
import { price } from "../../format/money";
import {
  baseOption,
  LINE,
  plotGrid,
  SINGLE_GRID,
  valueAxis,
  type Palette,
} from "../../theme/echarts";
import { SIZE_MARK } from "../../theme/tokens";
import type { Fit, FillPoints } from "../../types/generated/fill_check";
import { tipHtml } from "./tooltip";

export const SCATTER_SERIES = ["Print vs mid", "OLS fit", "y = x"] as const;

// Above this many points ECharts draws them in large mode, one path for all.
const LARGE_FROM = 2000;

function bounds(mid: readonly number[]): [number, number] {
  let low = Infinity;
  let high = -Infinity;
  for (const m of mid) {
    if (m < low) low = m;
    if (m > high) high = m;
  }
  return [low, high];
}

function reference(name: string, from: [number, number], to: [number, number], stroke: string,
                   dash: "solid" | "dashed") {
  return {
    name,
    type: "line",
    data: [from, to],
    showSymbol: false,
    symbol: "none",
    color: stroke,
    lineStyle: { color: stroke, width: LINE.ruler, type: dash },
    emphasis: { disabled: true },
    tooltip: { show: false },
    silent: true,
  };
}

export function scatterOption(p: Palette, points: FillPoints, fit: Fit | null) {
  const base = baseOption(p);
  const [low, high] = bounds(points.mid);
  const data = points.mid.map((m, i) => [m, points.trade[i] ?? null]);
  const axisLabel = { ...valueAxis(p).axisLabel, formatter: (v: number) => `$${v}` };
  const [pairs, fitName, identity] = SCATTER_SERIES;
  const series: object[] = [
    {
      name: pairs,
      type: "scatter",
      data,
      symbol: "circle",
      symbolSize: SIZE_MARK,
      color: p.mark,
      itemStyle: { color: p.mark },
      large: true,
      largeThreshold: LARGE_FROM,
      emphasis: { disabled: true },
    },
  ];
  if (points.mid.length > 0) {
    if (fit) {
      const line = (x: number): [number, number] => [x, fit.slope * x + fit.intercept];
      series.push(reference(fitName, line(low), line(high), p["fit-line"], "solid"));
    }
    series.push(reference(identity, [low, low], [high, high], p["identity-line"], "dashed"));
  }
  return {
    ...base,
    grid: SINGLE_GRID.map((g) => plotGrid(p, g)),
    xAxis: valueAxis(p, { axisLabel }),
    yAxis: valueAxis(p, { axisLabel }),
    legend: { ...base.legend, data: series.map((s) => (s as { name: string }).name) },
    tooltip: {
      ...base.tooltip,
      trigger: "item",
      axisPointer: { type: "none" },
      formatter: (params: unknown) => {
        const value = (params as { value?: [number, number | null] }).value;
        if (!value) return "";
        const [mid, trade] = value;
        return tipHtml(`Mid ${price(mid)}`, [["Print", trade === null ? "—" : price(trade),
                                             p.mark]]);
      },
    },
    series,
  };
}
