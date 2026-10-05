// The methodology page's figures: entry timing's fragility (PO, DEC-67), the fill check's pairs,
// and the limits' facts (DEC-109): each long's round trip and whether two CIs overlap.
import { describe, expect, it } from "vitest";

import { BLOTTER, LONG, run, TIMING } from "../../test/fixtures";
import type { RobustnessRow } from "../../types/generated/robustness";
import type { BlotterRow, RunResult } from "../../types/generated/run_result";
import {
  fillPairs,
  gapOfSpread,
  longTrips,
  overlap,
  timing,
} from "./figures";

function withMean(row: RobustnessRow, mean: number): RobustnessRow {
  const ci = row.weekly_return;
  if (!ci) throw new Error("fixture row has no CI");
  return { ...row, weekly_return: { ...ci, mean } };
}

describe("entry timing (DEC-67)", () => {
  it("counts the fixed bars apart from the E-T1 baseline, and their means' range", () => {
    const t = timing(TIMING);
    expect(t?.reference.run_id).toBe("baseline_pmcc");
    expect(t?.fixed.map((r) => r.run_id)).toEqual(["baseline_pmcc--t1", "baseline_pmcc--t2"]);
    expect(t?.means).toEqual({ low: 0.008, high: 0.01 });
  });

  it("is not fragile while every fixed bar's mean lies inside the baseline's CI", () => {
    expect(timing(TIMING)?.outside).toEqual([]);
  });

  it("is fragile when a fixed bar's mean falls outside the baseline's CI, either side", () => {
    const [reference, t1, t2] = TIMING as [RobustnessRow, RobustnessRow, RobustnessRow];
    // the baseline's CI runs from −1.0% to 3.0%
    const below = timing([reference, withMean(t1, -0.0101), t2]);
    expect(below?.outside.map((r) => r.run_id)).toEqual(["baseline_pmcc--t1"]);
    const above = timing([reference, t1, withMean(t2, 0.0301)]);
    expect(above?.outside.map((r) => r.run_id)).toEqual(["baseline_pmcc--t2"]);
    const edge = timing([reference, withMean(t1, -0.01), withMean(t2, 0.03)]);
    expect(edge?.outside).toEqual([]);
  });

  it("has nothing to judge without the reference row", () => {
    expect(timing(TIMING.slice(1))).toBeUndefined();
  });
});

describe("the fill check's pairs", () => {
  it("zips the three columns into pairs", () => {
    expect(fillPairs({ mid: [1, 2], trade: [1.1, 1.9], spread: [0.2, 0] })).toEqual([
      { i: 0, mid: 1, trade: 1.1, spread: 0.2 },
      { i: 1, mid: 2, trade: 1.9, spread: 0 },
    ]);
  });

  it("takes a pair's gap as a share of its spread, none on a locked quote", () => {
    expect(gapOfSpread({ i: 0, mid: 1, trade: 1.1, spread: 0.2 })).toBeCloseTo(0.5);
    expect(gapOfSpread({ i: 1, mid: 2, trade: 1.9, spread: 0 })).toBeNull();
  });
});

describe("the limits of this backtest", () => {
  const second = { ...LONG, ric: "NVDAL152613000.U", expiry: "2026-12-18" };
  const trips: BlotterRow[] = [
    BLOTTER[0] as BlotterRow, // E-L1 BUY the long, −$5,630.00
    { ...BLOTTER[0] as BlotterRow, time: "2026-05-26T10:00:00-04:00", side: "SELL",
      cash_delta: 6000, rule_id: "X-L2" },
    { ...BLOTTER[0] as BlotterRow, time: "2026-05-26T10:00:00-04:00", instrument: second,
      cash_delta: -4000 },
  ];

  function withLongs(blotter: BlotterRow[], longPnl: number): RunResult {
    const r = run("quant_pmcc", []);
    const attribution = r.attribution;
    if (!attribution?.leg) throw new Error("fixture has no leg attribution");
    return { ...r, blotter,
             attribution: { ...attribution, leg: { ...attribution.leg, long_pnl: longPnl } } };
  }

  it("lists each long's round trip, then the one still held", () => {
    expect(longTrips(withLongs(trips, 500))).toEqual([
      { pnl: 370, closed: { time: "2026-05-26T10:00:00-04:00", ruleId: "X-L2" } },
      { pnl: 130 },
    ]);
  });

  it("has no held long once every long is closed", () => {
    expect(longTrips(withLongs(trips.slice(0, 2), 370))).toEqual([
      { pnl: 370, closed: { time: "2026-05-26T10:00:00-04:00", ruleId: "X-L2" } },
    ]);
  });

  it("tells whether two CIs overlap, touching counting as overlap", () => {
    const ci = (low: number, high: number) => ({ mean: (low + high) / 2, low, high, level: 0.95,
                                                 resamples: 10000, seed: 535, weeks: 26 });
    expect(overlap(ci(-0.01, 0.027), ci(-0.009, 0.028))).toBe(true);
    expect(overlap(ci(-0.01, 0.01), ci(0.01, 0.02))).toBe(true);
    expect(overlap(ci(-0.01, 0.009), ci(0.01, 0.02))).toBe(false);
  });
});
