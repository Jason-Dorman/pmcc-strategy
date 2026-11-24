// The thesis's charts (T4-01; PO, TD-28): the two panes over one zoom, the outcome at its origin
// and blank until it matures, the candidates by shape and colour, the years without credit data,
// and the credit spread's two shadings.
import { describe, expect, it } from "vitest";

import { EPISODES, SERIES } from "../../test/thesisFixtures";
import type { Palette } from "../../theme/echarts";
import {
  CANDIDATES,
  creditOption,
  creditPoints,
  creditSpans,
  CREDIT_SERIES,
  creditStart,
  opening,
  thresholdName,
  trackerOption,
  TRACKER_SERIES,
  windowSpans,
} from "./thesis";

const P = new Proxy({} as Palette, { get: (_t, key) => String(key) });

interface Series {
  name: string;
  type: string;
  data: readonly unknown[];
  symbol?: string;
  color?: string;
  xAxisIndex?: number;
  lineStyle?: { color?: string; type?: string };
  markArea?: { itemStyle: { color: string }; label?: { formatter: string };
               data: [{ xAxis: string }, { xAxis: string }][] };
  markLine?: { data: { yAxis: number; lineStyle?: { type: string } }[] };
}

function series(option: { series: unknown[] }, name: string): Series {
  const found = (option.series as Series[]).find((s) => s.name === name);
  if (!found) throw new Error(`no series ${name}`);
  return found;
}

describe("the tracker", () => {
  const option = trackerOption(P, SERIES, EPISODES, 0.03);
  const { vix, forecast, realized, gap } = TRACKER_SERIES;

  it("draws VIX, the forecast and what followed above, in vol, and the gap below", () => {
    expect(series(option, vix).data).toEqual([0.2, 0.2, 0.2, 0.3, 0.2, 0.275]);
    expect(series(option, vix).lineStyle?.color).toBe("vix-line");
    expect(series(option, forecast).lineStyle?.type).toBe("dashed"); // told by more than hue
    expect(series(option, gap).xAxisIndex).toBe(1);
    expect(series(option, gap).data[1]).toBeNull(); // a hole, never zero
  });

  it("plots the realized vol at the day it is measured from, blank until it matures", () => {
    expect(realized).toBe("Subsequent 30-day realized volatility");
    expect(series(option, realized).data).toEqual([0.14, 0.14, 0.14, 0.14, 0.14, null]);
  });

  it("shares one date axis and one zoom between the panes", () => {
    expect(option.xAxis.map((x) => x.data)).toEqual([SERIES.map((s) => s.day),
                                                     SERIES.map((s) => s.day)]);
    for (const z of option.dataZoom) expect(z.xAxisIndex).toEqual([0, 1]);
    expect(option.axisPointer.link).toEqual([{ xAxisIndex: "all" }]);
  });

  it("opens on about two years", () => {
    expect(opening(3242)).toBe(3242 - 504);
    expect(opening(10)).toBe(0);
  });

  it("marks each candidate at its gap, its credit told by shape and by colour", () => {
    expect(new Set(CANDIDATES.map((c) => c.symbol)).size).toBe(3);
    expect(new Set(CANDIDATES.map((c) => c.role)).size).toBe(3);
    const eligible = series(option, "Eligible");
    expect([eligible.data, eligible.symbol, eligible.color]).toEqual([
      [["2026-02-04", 0.05]], "circle", "eligible-mark"]);
    const filtered = series(option, "Filtered out");
    expect([filtered.data, filtered.symbol, filtered.color]).toEqual([
      [["2026-02-06", 0.05]], "rect", "filtered-mark"]);
    const none = series(option, "Credit data unavailable");
    expect([none.data, none.symbol, none.color]).toEqual([
      [["2026-02-02", 0.05]], "triangle", "unavailable-mark"]);
  });

  it("shades each spike's search window, cut at the last session", () => {
    expect(windowSpans(SERIES, EPISODES)).toEqual([[0, 1], [2, 4], [3, 4], [5, 5]]);
    expect(series(option, vix).markArea?.itemStyle.color).toBe("window-shade");
  });

  it("shades and names the sessions before credit data", () => {
    expect(creditStart(SERIES)).toBe("2026-02-04");
    const area = series(option, gap).markArea;
    expect(area?.label?.formatter).toBe("No credit data before Feb 4, 2026");
    expect(area?.data).toEqual([[{ xAxis: "2026-02-02" }, { xAxis: "2026-02-04" }]]);
  });

  it("draws the candidate's threshold dashed and names it, over a dotted zero", () => {
    expect(series(option, gap).markLine?.data.map((d) => d.yAxis)).toEqual([0, 0.03]);
    expect(thresholdName(0.03)).toBe("Candidate needs 3 points");
    expect(option.legend[1]?.data).toContain("Candidate needs 3 points");
  });

  it("names the outcome's first and last day, and a pending one as pending", () => {
    const tip = (day: string) => option.tooltip.formatter([{ axisValue: day }]);
    expect(tip("2026-02-04")).toContain("Feb 4, 2026");
    expect(tip("2026-02-04")).toContain("Mar 10, 2026");
    expect(tip("2026-02-04")).toContain("Eligible");
    expect(tip("2026-02-09")).toContain("pending");
    expect(tip("2026-02-09")).not.toContain("0.0%");
    expect(tip("2026-02-02")).toContain("no data");
  });

  it("draws without the rules' values, as on the first night's file", () => {
    const bare = trackerOption(P, SERIES, EPISODES, null);
    expect(series(bare, gap).markLine?.data.map((d) => d.yAxis)).toEqual([0]);
  });
});

describe("the credit spread", () => {
  const points = creditPoints(SERIES);
  const option = creditOption(P, points, { level: 450, short: 15, long: 40 });

  it("starts at the first session with a value", () => {
    expect(points.map((p) => p.day)).toEqual(SERIES.slice(2).map((s) => s.day));
    expect(creditPoints([])).toEqual([]);
  });

  it("draws the level limit, dashed", () => {
    expect(series(option, CREDIT_SERIES.spread).markLine?.data).toEqual([{ yAxis: 450 }]);
  });

  it("shades unstable and unavailable sessions apart, one session still having width", () => {
    const spans = creditSpans(points, "UNSTABLE");
    expect(spans).toEqual([[2, 2]]);
    const unstable = series(option, CREDIT_SERIES.spread).markArea;
    expect(unstable?.itemStyle.color).toBe("unstable-shade");
    expect(unstable?.data).toEqual([[{ xAxis: "2026-02-06" }, { xAxis: "2026-02-09" }]]);
    expect(series(option, CREDIT_SERIES.unavailable).markArea?.itemStyle.color)
      .toBe("no-credit-shade");
  });

  it("gives each change against its limit, and the observation's date", () => {
    const tip = option.tooltip.formatter([{ axisValue: "2026-02-04" }]);
    for (const text of ["300 bps (limit 450 bps)", "+5 bps (limit +15 bps)",
                        "−10 bps (limit +40 bps)", "Feb 4, 2026"]) {
      expect(tip).toContain(text);
    }
  });
});
