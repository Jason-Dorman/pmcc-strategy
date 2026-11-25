// The two exploratory versions' words (PO, TD-33): met, not met with why, or not assessable; the
// original's spike search plays no part; every statistic named by version and counting view.
import { describe, expect, it } from "vitest";

import { COMPARISON, FIRST_NIGHT, THESIS } from "../../test/thesisFixtures";
import type { Thesis, ThesisVersionLatest, ThesisView } from "../../types/generated/thesis";
import { gapPhrase, period, reason, stateLabel, stateVerdict, tileStates, versionGap, versionName }
  from "./versions";

const latest = (state: string, checks: Record<string, boolean | null>,
                stretch: string | null = null): ThesisVersionLatest => ({
  state, stretch_start: stretch,
  checks: Object.entries(checks).map(([key, met]) => ({ key, met })) });

describe("a version's result", () => {
  it("names the two versions as the PO does", () => {
    expect(COMPARISON.versions.map(versionName)).toEqual([
      "A — Pricing gap + stable credit", "B — Also wait for calmer markets"]);
  });

  it("is met, with the stretch it is in, and never a trade", () => {
    const met = latest("MET", { gap: true, credit: true }, "2026-02-06");
    expect([stateLabel(met), stateVerdict(met)]).toEqual(["Conditions met", true]);
    expect(reason(met)).toBe(
      "Every condition holds. The current qualifying stretch began Feb 6, 2026.");
    expect(`${stateLabel(met)} ${reason(met)}`).not.toMatch(/buy|sell|profit|trade/i);
  });

  it("is not met, naming every condition that fails", () => {
    const not = latest("NOT_MET", { gap: false, credit: false, swings_below_long: false,
                                    swings_not_rising: true });
    expect([stateLabel(not), stateVerdict(not)]).toEqual(["Conditions not met", false]);
    expect(reason(not)).toBe("VIX is not far enough above our forecast, credit does not pass its "
      + "stability checks, and five-day volatility is not below 20-day volatility.");
    expect(reason(latest("NOT_MET", { gap: true, credit: false })))
      .toBe("Credit does not pass its stability checks.");
  });

  it("cannot be assessed for missing data, which is never a failed condition", () => {
    const unknown = latest("UNKNOWN", { gap: true, credit: null });
    expect([stateLabel(unknown), stateVerdict(unknown)]).toEqual(["Cannot assess", null]);
    expect(reason(unknown)).toBe("Required data is missing: usable credit data.");
    expect([stateLabel(null), stateVerdict(null)]).toEqual(["Cannot assess", null]);
  });
});

describe("the statistics", () => {
  const having = (over: Partial<ThesisView>): Thesis => ({ ...THESIS, comparison: {
    ...COMPARISON, versions: COMPARISON.versions.map((v) => ({
      ...v, views: v.views.map((w) => (w.key === "all" ? { ...w, ...over } : w)) })) } });

  it("name their version and counting view, and never mix the two", () => {
    expect(versionGap(THESIS, "A", "all")).toBe("Version A, all qualifying stretches: across 64 "
      + "completed observations, market-priced volatility exceeded subsequent actual volatility by "
      + "an average of 3.7 volatility points.");
    expect(versionGap(THESIS, "B", "all")).toContain("across 55 completed observations");
    expect(versionGap(THESIS, "B", "all")).toContain("4.3 volatility points");
    expect(versionGap(THESIS, "A", "thirty_day")).toContain("at least 30 calendar days apart");
    expect(versionGap(THESIS, "A", "thirty_day")).toContain("5.3 volatility points");
  });

  it("handle negative, level, single, empty and absent groups", () => {
    expect(versionGap(having({ mean_gap: -0.02 }), "A", "all")).toContain("fell below");
    expect(versionGap(having({ mean_gap: 0 }), "A", "all")).toContain("matched");
    expect(versionGap(having({ completed: 1 }), "A", "all"))
      .toContain("across 1 completed observation, ");
    expect(versionGap(having({ completed: 0, mean_gap: null }), "A", "all"))
      .toBe("Version A, all qualifying stretches: no observation has completed yet.");
    expect(versionGap(FIRST_NIGHT, "A", "all")).toBe("Version A: not in this data file yet.");
    expect(gapPhrase({ count: 0, mean_vol_gap: 0.1 })).toBeNull();
  });

  it("date the analysis period", () => {
    expect(period(COMPARISON)).toBe("Dec 27, 2023 to Feb 9, 2026");
    expect(period({ ...COMPARISON, analysis_start: null })).toBe("no session yet");
  });

  it("give the home tile each version's state, or say the file lacks them", () => {
    expect(tileStates(COMPARISON)).toBe("A: conditions not met · B: cannot assess");
    expect(tileStates(null)).toBe("Version results not in this file yet");
  });
});
