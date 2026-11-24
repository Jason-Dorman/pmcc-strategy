// The thesis's charts (PO, TD-28, TD-30): the default chart of what was priced in and what followed,
// the signal's details on the same axis and zoom, the outcome at its origin and blank until its
// window completes, and the credit spread's two shadings.
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
  lastSessions,
  priceOption,
  trackerOption,
  TRACKER_SERIES,
  windowSpans,
} from "./thesis";

const P = new Proxy({} as Palette, { get: (_t, key) => String(key) });
const ALL = lastSessions(SERIES.length, SERIES.length);

interface Series {
  name: string;
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

const { vix, forecast, realized, gap } = TRACKER_SERIES;

describe("the default chart", () => {
  const option = priceOption(P, SERIES, ALL);

  it("draws only what was priced in, our forecast and what followed, in the PO's words", () => {
    expect((option.series as Series[]).map((s) => s.name)).toEqual([
      "Market-priced volatility — VIX", "Our volatility forecast",
      "Actual volatility over the following 30 days"]);
    expect(series(option, vix).data).toEqual([0.2, 0.2, 0.2, 0.3, 0.2, 0.275]);
    expect(series(option, forecast).lineStyle?.type).toBe("dashed"); // told by more than hue
    expect(series(option, forecast).data[1]).toBeNull(); // a hole, never zero
    expect(series(option, vix).markArea).toBeUndefined(); // no shading by default
  });

  it("plots what followed at the day it is measured from, blank until it completes", () => {
    expect(series(option, realized).data).toEqual([0.14, 0.14, 0.14, 0.14, 0.14, null]);
  });

  it("opens on the range it is given, and only the slider zooms", () => {
    expect(lastSessions(3242, 252)).toEqual({ start: 2990, end: 3241 });
    expect(lastSessions(10, Number.POSITIVE_INFINITY)).toEqual({ start: 0, end: 9 });
    const narrow = priceOption(P, SERIES, { start: 2, end: 4 });
    expect(narrow.dataZoom.map((z) => [z.type, z.startValue, z.endValue]))
      .toEqual([["slider", 2, 4]]);
  });

  it("names the day an outcome is measured from and when it became known", () => {
    const tip = (day: string) => option.tooltip.formatter([{ axisValue: day }]);
    expect(tip("2026-02-04")).toContain("Feb 4, 2026");
    expect(tip("2026-02-04")).toContain("known only after");
    expect(tip("2026-02-04")).toContain("Mar 10, 2026");
    expect(tip("2026-02-09")).toContain("pending");
    expect(tip("2026-02-03")).toContain("not available");
    expect(tip("2026-02-04")).not.toContain("Credit");
  });
});

describe("the signal details", () => {
  const option = trackerOption(P, SERIES, EPISODES, 0.03, { start: 1, end: 5 });

  it("keep the default's lines, over one date axis and one zoom with the gap's pane", () => {
    expect(series(option, realized).data).toEqual(series(priceOption(P, SERIES, ALL), realized).data);
    expect(option.xAxis.map((x) => x.data)).toEqual([SERIES.map((s) => s.day),
                                                     SERIES.map((s) => s.day)]);
    for (const z of option.dataZoom) {
      expect([z.xAxisIndex, z.startValue, z.endValue]).toEqual([[0, 1], 1, 5]);
    }
    expect(option.axisPointer.link).toEqual([{ xAxisIndex: "all" }]);
    expect(series(option, gap).xAxisIndex).toBe(1);
    expect(series(option, gap).data[1]).toBeNull();
  });

  it("mark each qualifying observation, its credit told by shape and by colour", () => {
    expect(new Set(CANDIDATES.map((c) => c.symbol)).size).toBe(3);
    expect(new Set(CANDIDATES.map((c) => c.role)).size).toBe(3);
    const stable = series(option, "Credit stable");
    expect([stable.data, stable.symbol, stable.color]).toEqual([
      [["2026-02-04", 0.05]], "circle", "eligible-mark"]);
    const not = series(option, "Credit not stable");
    expect([not.data, not.symbol, not.color]).toEqual([
      [["2026-02-06", 0.05]], "rect", "filtered-mark"]);
    const none = series(option, "Credit data unavailable");
    expect([none.data, none.symbol, none.color]).toEqual([
      [["2026-02-02", 0.05]], "triangle", "unavailable-mark"]);
  });

  it("shade each search window, cut at the last session, and the sessions without credit", () => {
    expect(windowSpans(SERIES, EPISODES)).toEqual([[0, 1], [2, 4], [3, 4], [5, 5]]);
    expect(series(option, vix).markArea?.itemStyle.color).toBe("window-shade");
    expect(creditStart(SERIES)).toBe("2026-02-04");
    const area = series(option, gap).markArea;
    expect(area?.label?.formatter).toBe("No credit data before Feb 4, 2026");
    expect(area?.data).toEqual([[{ xAxis: "2026-02-02" }, { xAxis: "2026-02-04" }]]);
  });

  it("draw the threshold dashed over a dotted zero, and none when the file lacks it", () => {
    expect(series(option, gap).markLine?.data.map((d) => d.yAxis)).toEqual([0, 0.03]);
    const bare = trackerOption(P, SERIES, EPISODES, null, ALL);
    expect(series(bare, gap).markLine?.data.map((d) => d.yAxis)).toEqual([0]);
  });

  it("add the gap, the credit and the observation to the tooltip", () => {
    const tip = option.tooltip.formatter([{ axisValue: "2026-02-04" }]);
    for (const text of ["+5.0 pts", "300 bps, stable", "Qualifying observation", "Credit stable"]) {
      expect(tip).toContain(text);
    }
    expect(option.tooltip.formatter([{ axisValue: "2026-02-02" }])).toContain("no data");
  });
});

describe("the credit spread", () => {
  const points = creditPoints(SERIES);
  const option = creditOption(P, points, { level: 450, short: 15, long: 40 });

  it("starts at the first session with a value", () => {
    expect(points.map((p) => p.day)).toEqual(SERIES.slice(2).map((s) => s.day));
    expect(creditPoints([])).toEqual([]);
  });

  it("draws the level limit, dashed, and none when the file lacks it", () => {
    expect(series(option, CREDIT_SERIES.spread).markLine?.data).toEqual([{ yAxis: 450 }]);
    expect(series(creditOption(P, points, null), CREDIT_SERIES.spread).markLine).toBeUndefined();
  });

  it("shades not-stable and unavailable sessions apart, one session still having width", () => {
    expect(creditSpans(points, "UNSTABLE")).toEqual([[2, 2]]);
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
