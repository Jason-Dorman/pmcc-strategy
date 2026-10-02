// The NAV comparison (UI-SPEC §4, Comparison [1]): quant's NAV and the baseline's on the same
// bars, each in its strategy's role colour (DEC-04); the tooltip shows both and the difference.
import { money, moneySigned, moneyTick } from "../../format/money";
import { orDash } from "../../format/number";
import {
  baseOption,
  lineSeries,
  LINE,
  plotGrid,
  SINGLE_GRID,
  valueAxis,
  type Palette,
} from "../../theme/echarts";
import type { LedgerRowOut } from "../../types/generated/run_result";
import { barAxis, xAxis } from "./axis";
import { pointIndex, tipHtml } from "./tooltip";

/** One bar: each strategy's NAV, or null where its run has no such bar (a hole, rule 6). */
export interface NavRow {
  time: string;
  quant: number | null;
  baseline: number | null;
}

/** Both runs' NAV on every bar either has, in time order. */
export function navRows(quant: readonly LedgerRowOut[], baseline: readonly LedgerRowOut[]):
    NavRow[] {
  const rows = new Map<string, NavRow>();
  const at = (time: string) => {
    const row = rows.get(time) ?? { time, quant: null, baseline: null };
    rows.set(time, row);
    return row;
  };
  for (const r of quant) at(r.time).quant = r.nav;
  for (const r of baseline) at(r.time).baseline = r.nav;
  return [...rows.values()].sort((a, b) => Date.parse(a.time) - Date.parse(b.time));
}

/** Quant's NAV less the baseline's, where both have the bar. */
export function navGap(row: NavRow): number | null {
  return row.quant === null || row.baseline === null ? null : row.quant - row.baseline;
}

export interface NavNames {
  quant: string;
  baseline: string;
}

export function navCompareOption(p: Palette, rows: readonly NavRow[], names: NavNames) {
  const base = baseOption(p);
  const axis = barAxis(rows.map((r) => r.time));
  return {
    ...base,
    grid: SINGLE_GRID.map((g) => plotGrid(p, g)),
    xAxis: xAxis(p, axis),
    yAxis: valueAxis(p, { axisLabel: { ...valueAxis(p).axisLabel, formatter: moneyTick } }),
    legend: { ...base.legend, data: [names.quant, names.baseline] },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const i = pointIndex(params);
        const row = rows[i];
        if (!row) return "";
        return tipHtml(axis.categories[i] ?? "", [
          [names.quant, orDash(row.quant, money), p["strategy-quant"]],
          [names.baseline, orDash(row.baseline, money), p["strategy-baseline"]],
          [`${names.quant} − ${names.baseline}`, orDash(navGap(row), moneySigned)],
        ]);
      },
    },
    series: [
      lineSeries(names.quant, rows.map((r) => r.quant), p["strategy-quant"], LINE.series),
      lineSeries(names.baseline, rows.map((r) => r.baseline), p["strategy-baseline"],
                 LINE.series),
    ],
  };
}
