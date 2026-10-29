// The wheel's NAV chart (UI-SPEC §4, Wheel [1]; WD-22): NAV in the upper grid, the bars holding
// shares shaded behind it; in the lower, on the same bars, the stock's price with the held
// option's strike (dashed) and the shares' cost basis (dotted) as references, each a step that
// changes only when the book does. The bar the portfolio panel shows is a thin amber rule across
// both: a choice, so chrome, not data. One point per ledger bar.
import { money, moneyTick, price } from "../../format/money";
import { orDash } from "../../format/number";
import { holdsShares, stateLabel } from "../../format/wheel";
import {
  baseOption,
  lineSeries,
  LINE,
  PANE_TICKS,
  plotGrid,
  STACKED_GRIDS,
  valueAxis,
  type Palette,
} from "../../theme/echarts";
import { ACCOUNT_LINES } from "../../theme/tokens";
import type { WheelLedgerRowOut } from "../../types/generated/wheel_result";
import { barAxis, xAxis } from "./axis";
import { pointIndex, tipHtml, type TipRow } from "./tooltip";

export const WHEEL_NAV_SERIES = ["NAV", "Stock", "Strike", "Cost basis"] as const;

/** The held option's strike: the put's or the call's, as the wheel never holds both. */
export function heldStrike(row: WheelLedgerRowOut): number | null {
  return (row.put ?? row.call)?.instrument.strike ?? null;
}

/** Each run of consecutive bars holding shares, as its first and last index. */
export function sharesSpans(ledger: readonly WheelLedgerRowOut[]): [number, number][] {
  const spans: [number, number][] = [];
  ledger.forEach((row, i) => {
    if (!holdsShares(row.state)) return;
    const last = spans.at(-1);
    if (last && last[1] === i - 1) last[1] = i;
    else spans.push([i, i]);
  });
  return spans;
}

function tipRows(p: Palette, row: WheelLedgerRowOut): TipRow[] {
  return [
    ["NAV", money(row.nav), p["nav-line"]],
    ["Holding", stateLabel(row.state)],
    ["Stock", orDash(row.spot, price), p["spot-line"]],
    ["Strike", orDash(heldStrike(row), money), p["strike-line"]],
    ["Cost basis", orDash(row.cost_basis, price), p["basis-line"]],
    ["Cash", money(row.cash)],
    ["Flags", row.flags.length > 0 ? row.flags.join(", ") : "none"],
  ];
}

/** The chosen bar's rule, on one grid. */
function chosen(p: Palette, category: string | undefined) {
  if (category === undefined) return {};
  return {
    markLine: {
      silent: true,
      symbol: "none",
      label: { show: false },
      lineStyle: { color: p.accent, width: LINE.ruler, type: "solid" },
      data: [{ xAxis: category }],
    },
  };
}

export function wheelNavOption(p: Palette, ledger: readonly WheelLedgerRowOut[],
                               selected: number | undefined) {
  const base = baseOption(p);
  const axis = barAxis(ledger.map((r) => r.time));
  const at = selected === undefined ? undefined : axis.categories[selected];
  const lower = { xAxisIndex: 1, yAxisIndex: 1 };
  const step = { step: "end" };
  const shading = {
    silent: true,
    itemStyle: { color: p["shares-shade"] },
    data: sharesSpans(ledger).map(([a, b]) => [
      { xAxis: axis.categories[a] }, { xAxis: axis.categories[b] },
    ]),
  };
  return {
    ...base,
    grid: STACKED_GRIDS.map((g) => plotGrid(p, g)),
    xAxis: [xAxis(p, axis, 0, false), xAxis(p, axis, 1)],
    yAxis: [
      valueAxis(p, { gridIndex: 0, axisLabel: { ...valueAxis(p).axisLabel, formatter: moneyTick } }),
      valueAxis(p, { gridIndex: 1, splitNumber: PANE_TICKS,
                     axisLabel: { ...valueAxis(p).axisLabel, formatter: (v: number) => `$${v}` } }),
    ],
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    legend: { ...base.legend, data: [...WHEEL_NAV_SERIES] },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const i = pointIndex(params);
        const row = ledger[i];
        return row ? tipHtml(axis.categories[i] ?? "", tipRows(p, row)) : "";
      },
    },
    series: [
      lineSeries("NAV", ledger.map((r) => r.nav), p["nav-line"], ACCOUNT_LINES.nav.width, "solid",
                 { markArea: shading, ...chosen(p, at) }),
      lineSeries("Stock", ledger.map((r) => r.spot), p["spot-line"], LINE.series, "solid",
                 { ...lower, ...chosen(p, at) }),
      lineSeries("Strike", ledger.map(heldStrike), p["strike-line"], LINE.ruler, "dashed",
                 { ...lower, ...step }),
      lineSeries("Cost basis", ledger.map((r) => r.cost_basis), p["basis-line"], LINE.ruler,
                 "dotted", { ...lower, ...step }),
    ],
  };
}
