// The wheel's NAV chart (Wheel [1]; WD-22, WD-32) and the chart click that picks a bar: NAV above
// with the bars holding shares shaded, the stock with the held strike and the cost basis below as
// references, the chosen bar an amber rule on both grids, and a click mapped to the bar under it.
import { describe, expect, it } from "vitest";

import type { Palette } from "../../theme/echarts";
import { ACCOUNT_LINES } from "../../theme/tokens";
import { WHEEL_LEDGER } from "../../test/wheelFixtures";
import { pickedIndex } from "./Chart";
import { heldStrike, sharesSpans, wheelNavOption } from "./wheelNav";

const P = new Proxy({} as Palette, { get: (_t, key) => String(key) });

interface Series {
  name: string;
  data: readonly (number | null)[];
  lineStyle: { color?: string; width: number; type?: string };
  xAxisIndex?: number;
  step?: string;
  markArea?: { itemStyle: { color: string }; data: { xAxis: string }[][] };
  markLine?: { lineStyle: { color: string }; data: { xAxis: string }[] };
}

function series(option: { series: unknown[] }, name: string): Series {
  const found = (option.series as Series[]).find((s) => s.name === name);
  if (!found) throw new Error(`no series ${name}`);
  return found;
}

describe("the wheel's NAV chart", () => {
  const option = wheelNavOption(P, WHEEL_LEDGER, 1);

  it("draws NAV above as the account's NAV line", () => {
    const nav = series(option, "NAV");
    expect(nav.lineStyle).toEqual({ color: "nav-line", width: ACCOUNT_LINES.nav.width,
                                    type: "solid" });
    expect(nav.data).toEqual(WHEEL_LEDGER.map((r) => r.nav));
    expect(nav.xAxisIndex).toBeUndefined();
  });

  it("shades each run of bars holding shares, alone or under a call", () => {
    expect(sharesSpans(WHEEL_LEDGER)).toEqual([[2, 4]]);
    const area = series(option, "NAV").markArea;
    expect(area?.itemStyle.color).toBe("shares-shade");
    expect(area?.data).toEqual([[{ xAxis: "2026-04-02 16:00 ET" }, { xAxis: "2026-04-06 16:00 ET" }]]);
  });

  it("splits the shading where the shares are sold and bought again", () => {
    const [cash] = WHEEL_LEDGER.slice(-1);
    const twice = [...WHEEL_LEDGER.slice(0, 5), ...(cash ? [cash] : []),
                   ...WHEEL_LEDGER.slice(2, 4).map((r, i) => ({ ...r, time: `2026-04-2${i}T16:00:00-04:00` }))];
    expect(sharesSpans(twice)).toEqual([[2, 4], [6, 7]]);
  });

  it("draws the stock below with the held strike dashed and the cost basis dotted, as steps", () => {
    const stock = series(option, "Stock");
    expect([stock.lineStyle.color, stock.lineStyle.type, stock.xAxisIndex])
      .toEqual(["spot-line", "solid", 1]);
    const strike = series(option, "Strike");
    expect([strike.lineStyle.color, strike.lineStyle.type, strike.step])
      .toEqual(["strike-line", "dashed", "end"]);
    expect(strike.data).toEqual([162.5, 162.5, null, 165, 165, null, null]);
    const basis = series(option, "Cost basis");
    expect([basis.lineStyle.color, basis.lineStyle.type]).toEqual(["basis-line", "dotted"]);
    expect(basis.data).toEqual([null, null, 161.075, 159.975, 159.975, null, null]);
  });

  it("takes the put's strike or the call's, whichever is held", () => {
    expect(WHEEL_LEDGER.map(heldStrike)).toEqual([162.5, 162.5, null, 165, 165, null, null]);
  });

  it("marks the chosen bar in amber on both grids, and none when none is chosen", () => {
    for (const name of ["NAV", "Stock"]) {
      const rule = series(option, name).markLine;
      expect(rule?.lineStyle.color).toBe("accent");
      expect(rule?.data).toEqual([{ xAxis: "2026-03-30 16:00 ET" }]);
    }
    expect(series(wheelNavOption(P, WHEEL_LEDGER, undefined), "NAV").markLine).toBeUndefined();
  });

  it("lists the bar's book in the tooltip at its ET time", () => {
    const { formatter } = (option as unknown as { tooltip: { formatter: (p: unknown) => string } })
      .tooltip;
    const tip = formatter([{ dataIndex: 4 }]);
    expect(tip).toContain("2026-04-06 16:00 ET");
    for (const text of ["$25,192.50", "Covered call", "$163.0000", "$165.00", "$159.9750",
                        "stale_call"]) {
      expect(tip).toContain(text);
    }
  });
});

describe("a click on a chart", () => {
  const chart = (inside: number | undefined, at: number) => ({
    getZr: () => ({ on: () => undefined }),
    getOption: () => ({ grid: [{}, {}] }),
    containPixel: ({ gridIndex }: { gridIndex: number }) => gridIndex === inside,
    convertFromPixel: () => [at, 0],
  });

  it("picks the category under it, on whichever grid it lands", () => {
    expect(pickedIndex(chart(0, 3.4), 10, 10)).toBe(3);
    expect(pickedIndex(chart(1, 5.6), 10, 10)).toBe(6);
  });

  it("picks nothing outside the plots", () => {
    expect(pickedIndex(chart(undefined, 2), 10, 10)).toBeUndefined();
  });
});
