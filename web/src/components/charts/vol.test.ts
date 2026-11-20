// The live page's volatility charts (L4-02; PO, LD-33): ATM IV about 30 days out against RV20 by
// session, the gap between them shaded, and the coming week's smile with the close and the pick.
import { describe, expect, it } from "vitest";

import { SMILE, VOL } from "../../test/liveFixtures";
import type { Palette } from "../../theme/echarts";
import { expectedMove, gapBand, ivRvOption, smileOption, VOL_SERIES, withHeadroom } from "./vol";

const P = new Proxy({} as Palette, { get: (_t, key) => String(key) });

interface Series {
  name: string;
  data: readonly unknown[];
  stack?: string;
  lineStyle: { color?: string; width: number; type?: string };
  areaStyle?: { color: string };
  markLine?: { data: { xAxis: number; lineStyle: { color: string; type: string } }[] };
  markArea?: { itemStyle: { color: string }; data: [{ xAxis: number }, { xAxis: number }][] };
}

function series(option: { series: unknown[] }, name: string): Series {
  const found = (option.series as Series[]).find((s) => s.name === name);
  if (!found) throw new Error(`no series ${name}`);
  return found;
}

function tip(option: { tooltip: { formatter: (params: unknown) => string } }, params: unknown) {
  return option.tooltip.formatter(params);
}

describe("IV against RV20", () => {
  const option = ivRvOption(P, VOL);
  const [ivName, rvName] = VOL_SERIES;

  it("draws ATM IV and RV20 by session in their roles' colours", () => {
    expect(series(option, ivName).data).toEqual([0.52, null, 0.48]);
    expect(series(option, ivName).lineStyle.color).toBe("iv-line");
    expect(series(option, rvName).data).toEqual([0.47, 0.49, 0.52]);
    expect(series(option, rvName).lineStyle.color).toBe("rv-line");
    expect(option.xAxis.data).toEqual(["2026-11-13", "2026-11-16", "2026-11-17"]);
  });

  it("shades the gap between them, a hole where either is missing", () => {
    expect(gapBand(VOL)).toEqual({ floor: [0.47, null, 0.48], height: [0.05, null, 0.04].map(
      (h) => (h === null ? null : expect.closeTo(h, 10))) });
    const band = series(option, "IV − RV20 gap");
    expect(band.stack).toBe(series(option, "IV − RV20 floor").stack);
    expect(band.areaStyle?.color).toBe("vol-gap-shade");
  });

  it("names only the two lines in its legend", () => {
    expect(option.legend.data).toEqual([...VOL_SERIES]);
  });

  it("tells the session's numbers and the gap in points", () => {
    const html = tip(option, [{ dataIndex: 0 }]);
    expect(html).toContain("2026-11-13 close");
    expect(html).toContain("52.0%");
    expect(html).toContain("47.0%");
    expect(html).toContain("+5.0 pts");
    expect(html).toContain("Dec 11 expiry, $162.50 strike");
    expect(tip(option, [{ dataIndex: 1 }])).toContain("no strike had both sides quoted");
  });
});

describe("the smile", () => {
  const option = smileOption(P, SMILE);
  const curve = series(option, "IV at the close");

  it("draws each out-of-the-money strike's IV in the IV line's colour", () => {
    expect(curve.data).toEqual([[145, 0.62], [147.5, 0.58], [160, 0.49]]);
    expect(curve.lineStyle.color).toBe("iv-line");
  });

  it("marks the close as a line and the pick as a dashed strike", () => {
    expect(curve.markLine?.data.map((d) => [d.xAxis, d.lineStyle.color, d.lineStyle.type]))
      .toEqual([[155.46, "spot-line", "solid"], [147.5, "strike-line", "dashed"]]);
  });

  it("leaves the pick out when there is none", () => {
    const none = series(smileOption(P, { ...SMILE, pick: null }), "IV at the close");
    expect(none.markLine?.data).toHaveLength(1);
  });

  it("tells a strike's right, IV and delta", () => {
    const html = tip(option, { dataIndex: 1 });
    expect(html).toContain("Put $147.50");
    expect(html).toContain("58.0%");
    expect(html).toContain("−0.30");
  });
});

describe("the expected move (PO, LD-41)", () => {
  function moveOf(smile: typeof SMILE) {
    const move = expectedMove(smile);
    if (move === null) throw new Error("no expected move");
    return move;
  }

  it("is the ATM straddle's price either side of the close", () => {
    const move = moveOf(SMILE); // $155.46 close, an $8.45 straddle
    expect(move.move).toBe(8.45);
    expect(move.share).toBeCloseTo(8.45 / 155.46, 10);
    expect(move.low).toBeCloseTo(147.01, 10);
    expect(move.high).toBeCloseTo(163.91, 10);
  });

  it("places the pick inside or outside it", () => {
    expect(moveOf(SMILE).pick).toEqual({ strike: 147.5, below: (155.46 - 147.5) / 155.46,
                                         inside: true });
    expect(moveOf({ ...SMILE, pick: 145 }).pick).toMatchObject({ inside: false });
    expect(moveOf({ ...SMILE, pick: null }).pick).toBeNull();
  });

  it("is a neutral band across the strikes it spans, and none without a straddle", () => {
    const band = series(smileOption(P, SMILE), "IV at the close").markArea;
    if (!band) throw new Error("no band");
    expect(band.itemStyle.color).toBe("move-shade");
    expect(band.data.flat().map((d) => d.xAxis)).toEqual([155.46 - 8.45, 155.46 + 8.45]);
    expect(expectedMove({ ...SMILE, straddle: null })).toBeNull();
    const none = series(smileOption(P, { ...SMILE, straddle: null }), "IV at the close");
    expect(none.markArea).toBeUndefined();
  });
});

describe("the vol axes", () => {
  it("leave the legend room above the data, the top a whole 5%", () => {
    expect(withHeadroom({ min: 0.42, max: 0.62 })).toBeCloseTo(0.7, 10); // 0.67 up to 70%
    expect(withHeadroom({ min: 0.3, max: 0.46 })).toBeCloseTo(0.5, 10);
  });
});
