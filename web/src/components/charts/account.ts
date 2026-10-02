// The account chart (UI-SPEC §4, Strategy [1]): NAV with IM and MM in the upper grid; available
// funds in the lower, on the same bars, shaded NEGATIVE below zero against a zero ruler. One
// point per ledger bar.
import { money, moneyTick } from "../../format/money";
import {
  baseOption,
  lineSeries,
  LINE,
  PANE_TICKS,
  plotGrid,
  ruler,
  shadeSeries,
  STACKED_GRIDS,
  valueAxis,
  type Palette,
} from "../../theme/echarts";
import { ACCOUNT_LINES } from "../../theme/tokens";
import type { LedgerRowOut } from "../../types/generated/run_result";
import { barAxis, xAxis } from "./axis";
import { pointIndex, tipHtml, type TipRow } from "./tooltip";

export const ACCOUNT_SERIES = ["NAV", "IM", "MM", "Available funds"] as const;

function tipRows(p: Palette, row: LedgerRowOut): TipRow[] {
  return [
    ["NAV", money(row.nav), p["nav-line"]],
    ["IM", money(row.im), p["margin-im"]],
    ["MM", money(row.mm), p["margin-mm"]],
    ["Available funds", money(row.available_funds), p["available-funds"]],
    ["Excess equity", money(row.excess_equity)],
    ["Flags", row.flags.length > 0 ? row.flags.join(", ") : "none"],
  ];
}

export function accountOption(p: Palette, ledger: readonly LedgerRowOut[]) {
  const base = baseOption(p);
  const axis = barAxis(ledger.map((r) => r.time));
  const funds = ledger.map((r) => r.available_funds);
  const lower = { xAxisIndex: 1, yAxisIndex: 1 };
  const tick = { formatter: moneyTick };
  return {
    ...base,
    grid: STACKED_GRIDS.map((g) => plotGrid(p, g)),
    xAxis: [xAxis(p, axis, 0, false), xAxis(p, axis, 1)],
    yAxis: [
      valueAxis(p, { gridIndex: 0, axisLabel: { ...valueAxis(p).axisLabel, ...tick } }),
      valueAxis(p, { gridIndex: 1, splitNumber: PANE_TICKS,
                     axisLabel: { ...valueAxis(p).axisLabel, ...tick } }),
    ],
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    legend: { ...base.legend, data: [...ACCOUNT_SERIES] },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const i = pointIndex(params);
        const row = ledger[i];
        return row ? tipHtml(axis.categories[i] ?? "", tipRows(p, row)) : "";
      },
    },
    series: [
      lineSeries("NAV", ledger.map((r) => r.nav), p["nav-line"], ACCOUNT_LINES.nav.width),
      lineSeries("IM", ledger.map((r) => r.im), p["margin-im"], ACCOUNT_LINES.im.width,
                 ACCOUNT_LINES.im.dash),
      lineSeries("MM", ledger.map((r) => r.mm), p["margin-mm"], ACCOUNT_LINES.mm.width,
                 ACCOUNT_LINES.mm.dash),
      lineSeries("Available funds", funds, p["available-funds"], LINE.series, "solid",
                 { ...lower, markLine: ruler(p, 0) }),
      shadeSeries("Below zero", funds.map((v) => Math.min(v, 0)), p["negative-shade"], lower),
    ],
  };
}
