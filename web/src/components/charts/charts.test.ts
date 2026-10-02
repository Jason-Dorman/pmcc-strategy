// The chart options (UI-SPEC §4; DEC-04): each series takes its role's colour, references are
// thin and dashed or dotted, holes stay holes, the time axis is trading time, and the tooltip
// lists every series at the point's ET time. The palette here names each colour by its token,
// so an assertion reads as the role it checks.
import { describe, expect, it } from "vitest";

import type { Palette } from "../../theme/echarts";
import { ACCOUNT_LINES } from "../../theme/tokens";
import { LEDGER } from "../../test/fixtures";
import { accountOption } from "./account";
import { barAxis, sessionAxis, shortDate, weekOf, xAxis } from "./axis";
import { legOption } from "./legs";
import { residualOption } from "./residual";

const P = new Proxy({} as Palette, { get: (_t, key) => String(key) });

interface Series {
  name: string;
  data: readonly (number | null)[];
  color?: string;
  lineStyle: { color?: string; width: number; type?: string };
  connectNulls: boolean;
  xAxisIndex?: number;
  yAxisIndex?: number;
  areaStyle?: { color: string; origin: number; opacity?: number };
  markLine?: { lineStyle: { type: string } };
}

function at<T>(items: readonly T[], index: number): T {
  const item = items[index];
  if (item === undefined) throw new Error(`no item ${index}`);
  return item;
}

function series(option: { series: unknown[] }, name: string): Series {
  const found = (option.series as Series[]).find((s) => s.name === name);
  if (!found) throw new Error(`no series ${name}`);
  return found;
}

function tooltip(option: object, index: number): string {
  const { formatter } = (option as { tooltip: { formatter: (p: unknown) => string } }).tooltip;
  return formatter([{ dataIndex: index }]);
}

describe("the trading-time axis", () => {
  it("finds a date's Monday", () => {
    expect(weekOf("2026-04-02")).toBe("2026-03-30");
    expect(weekOf("2026-03-30")).toBe("2026-03-30");
    expect(weekOf("2026-04-05")).toBe("2026-03-30"); // a Sunday ends the week
  });

  it("labels a date as Mon DD", () => {
    expect(shortDate("2026-09-04")).toBe("Sep 4");
  });

  it("ticks each session's first bar and labels each week's", () => {
    const axis = barAxis([
      "2026-04-02T15:00:00-04:00", "2026-04-02T16:00:00-04:00",
      "2026-04-06T10:00:00-04:00", "2026-04-06T11:00:00-04:00",
    ]);
    expect(axis.categories[0]).toBe("2026-04-02 15:00 ET");
    expect(axis.sessionStarts).toEqual([true, false, true, false]);
    expect(axis.weekStarts).toEqual([true, false, true, false]);
  });

  it("reads bar times in New York time", () => {
    expect(barAxis(["2026-04-02T14:00:00Z"]).dates).toEqual(["2026-04-02"]);
    // 22:00 ET on Apr 2 is already Apr 3 in UTC
    expect(barAxis(["2026-04-03T02:00:00Z"]).dates).toEqual(["2026-04-02"]);
  });

  it("is a category axis, its intervals the starts", () => {
    const axis = sessionAxis(["2026-03-30", "2026-03-31", "2026-04-06"]);
    const x = xAxis(P, axis) as unknown as {
      type: string;
      data: string[];
      axisLabel: {
        interval: (i: number) => boolean;
        formatter: (v: string, i: number) => string;
        hideOverlap: boolean;
        showMinLabel: boolean;
      };
    };
    expect(x.type).toBe("category");
    expect(x.data).toEqual(["2026-03-30", "2026-03-31", "2026-04-06"]);
    expect([0, 1, 2].map((i) => x.axisLabel.interval(i))).toEqual([true, false, true]);
    expect(x.axisLabel.formatter("", 2)).toBe("Apr 6");
  });

  it("drops a week label that would overlap the one before it, never the first", () => {
    // a holiday week is narrower than its label on a narrow chart (P7-01 review)
    const x = xAxis(P, sessionAxis(["2026-03-30"])) as unknown as {
      axisLabel: { hideOverlap: boolean; showMinLabel: boolean };
    };
    expect(x.axisLabel.hideOverlap).toBe(true);
    expect(x.axisLabel.showMinLabel).toBe(true);
  });
});

describe("the account chart", () => {
  const option = accountOption(P, LEDGER);

  it("draws NAV, IM and MM above, as the account lines", () => {
    expect(series(option, "NAV").lineStyle).toEqual(
      { color: "nav-line", width: ACCOUNT_LINES.nav.width, type: "solid" });
    expect(series(option, "IM").lineStyle).toEqual(
      { color: "margin-im", width: ACCOUNT_LINES.im.width, type: "dashed" });
    expect(series(option, "MM").lineStyle).toEqual(
      { color: "margin-mm", width: ACCOUNT_LINES.mm.width, type: "dotted" });
    expect(series(option, "NAV").data).toEqual(LEDGER.map((r) => r.nav));
  });

  it("draws available funds in its role colour on the lower grid, with a zero ruler", () => {
    const funds = series(option, "Available funds");
    expect(funds.lineStyle.color).toBe("available-funds");
    expect([funds.xAxisIndex, funds.yAxisIndex]).toEqual([1, 1]);
    expect(funds.markLine?.lineStyle.type).toBe("dotted");
    expect(option.xAxis).toHaveLength(2);
  });

  it("shades only the funds below zero, in NEGATIVE", () => {
    const below = accountOption(P, [{ ...at(LEDGER, 0), available_funds: -40 }, at(LEDGER, 1)]);
    const shade = series(below, "Below zero");
    expect(shade.data).toEqual([-40, 0]);
    expect(shade.areaStyle).toEqual({ color: "negative-shade", origin: 0, opacity: 1 });
    expect(shade.lineStyle.width).toBe(0);
    expect([shade.xAxisIndex, shade.yAxisIndex]).toEqual([1, 1]);
  });

  it("shares the pointer between the stacked grids", () => {
    expect(option.axisPointer).toEqual({ link: [{ xAxisIndex: "all" }] });
    expect(series(option, "NAV").xAxisIndex).toBeUndefined();
  });

  it("leaves holes as holes and doesn't animate", () => {
    for (const s of option.series as unknown as Series[]) expect(s.connectNulls).toBe(false);
    expect(option.animation).toBe(false);
  });

  it("puts the legend inside the plot, not in the band above it", () => {
    expect(option.legend.data).toEqual(["NAV", "IM", "MM", "Available funds"]);
    expect(option.legend.top).toBeGreaterThan(0);
  });

  it("lists every series, excess equity and flags at the bar's ET time", () => {
    const tip = tooltip(option, 2);
    expect(tip).toContain("2026-03-31 10:00 ET");
    for (const text of ["NAV", "$15,400.00", "IM", "MM", "Available funds", "$9,650.00",
                        "Excess equity", "stale_short"]) {
      expect(tip).toContain(text);
    }
  });

  it("escapes what it puts in the tooltip's HTML", () => {
    const odd = accountOption(P, [{ ...at(LEDGER, 0), flags: ["<b>"] }]);
    expect(tooltip(odd, 0)).toContain("&lt;b&gt;");
  });
});

describe("the leg chart (DEC-04)", () => {
  const points = [
    { session: "2026-03-30", long_pnl: -150, net_short_premium: 19.5 },
    { session: "2026-03-31", long_pnl: 672.5, net_short_premium: 39.5 },
  ];
  const option = legOption(P, points);

  it("draws the long leg in --long-leg and the short in --short-leg", () => {
    expect(series(option, "Long-leg P&L").lineStyle.color).toBe("long-leg");
    expect(series(option, "Net short premium").lineStyle.color).toBe("short-leg");
    expect(series(option, "Long-leg P&L").data).toEqual([-150, 672.5]);
  });

  it("shows both legs at the session's close, signed", () => {
    const tip = tooltip(option, 0);
    expect(tip).toContain("2026-03-30 close");
    expect(tip).toContain("−$150.00");
    expect(tip).toContain("+$19.50");
  });
});

describe("the residual chart (DEC-76)", () => {
  it("is one line in TEXT over the bars", () => {
    const option = residualOption(P, [
      { time: "2026-03-30T10:00:00-04:00", cumulative: 0 },
      { time: "2026-03-30T11:00:00-04:00", cumulative: 2.31 },
    ]);
    expect(option.series).toHaveLength(1);
    expect(series(option, "Cumulative residual").lineStyle.color).toBe("text");
    expect(tooltip(option, 1)).toContain("+$2.31");
  });
});
