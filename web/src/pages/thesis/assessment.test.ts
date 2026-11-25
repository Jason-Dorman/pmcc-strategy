// The latest assessment's words (PO, TD-30): generated from the file, following the backend's state
// and its own checks; what is missing is said to be missing, never failed or zero.
import { describe, expect, it } from "vitest";

import { signalLabel } from "../../format/thesis";
import { FIRST_NIGHT, THESIS } from "../../test/thesisFixtures";
import type { Thesis, ThesisCurrent, ThesisSignal } from "../../types/generated/thesis";
import { creditMet, creditText, lead, moved, observations, swingsMet } from "./assessment";

function current(over: Partial<ThesisCurrent> = {}): ThesisCurrent {
  if (THESIS.current === null) throw new Error("the fixture has a current state");
  return { ...THESIS.current, ...over };
}

function thesis(over: Partial<ThesisCurrent>): Thesis {
  return { ...THESIS, current: current(over) };
}

const CALM: Partial<ThesisCurrent> = {
  swings_below_long: true, swings_not_rising: true, rv_short: 0.1, credit_status: "STABLE",
  credit_change_short_ok: true, credit_change_short_bps: -3,
};
const NO_CREDIT: Partial<ThesisCurrent> = {
  credit_status: "UNAVAILABLE", credit_level_ok: null, credit_change_short_ok: null,
  credit_change_long_ok: null, credit_note: "the latest is 9 business days old; at most 3",
};

const CALMING = "To qualify, five-day volatility must be below 20-day volatility and no higher than "
  + "three sessions earlier.";

describe("the headline", () => {
  it.each([
    ["NO_SHOCK", "No qualifying volatility spike to monitor"],
    ["SEARCHING", "Watching a recent volatility spike"],
    ["NO_CANDIDATE", "No qualifying observation in this search window"],
    ["ELIGIBLE", "Research conditions met"],
    ["FILTERED_OUT", "Candidate did not meet the credit rules"],
    ["CREDIT_UNAVAILABLE", "Credit data needed to assess eligibility"],
    ["INCOMPLETE_CANDIDATE_SEARCH", "Missing observations prevent assessment"],
  ])("%s reads %s", (status, label) => {
    expect(signalLabel(status)).toBe(label);
  });
});

describe("the state in words", () => {
  const signal = (over: Partial<ThesisSignal>): ThesisSignal => ({
    ...THESIS.signal, shock_day: "2026-02-04", candidate_day: "2026-02-06",
    window_end: "2026-02-20", ...over,
  });

  it("dates a qualifying session's assessment, and never implies a trade or a profit", () => {
    const text = lead(signal({ status: "ELIGIBLE" }));
    expect(text).toContain("The session of Feb 6, 2026");
    expect(text).toContain("at its own assessment");
    expect(text).toContain("no trade was placed, and profitability has not been established");
  });

  it("keeps missing data apart from a failed condition, with its reason", () => {
    const credit = lead(signal({ status: "CREDIT_UNAVAILABLE", reason: "too few observations" }));
    expect(credit).toContain("neither eligible nor ruled out");
    expect(credit).toContain("Reason recorded: too few observations.");
    const search = lead(signal({ status: "INCOMPLETE_CANDIDATE_SEARCH", candidate_day: null }));
    expect(search).toContain("not the same as none qualifying");
    for (const text of [credit, search]) expect(text).not.toMatch(/did not meet/);
  });

  it("dates the search window, open and closed", () => {
    expect(lead(signal({ status: "SEARCHING", candidate_day: null })))
      .toContain("through Feb 20, 2026");
    expect(lead(signal({ status: "NO_CANDIDATE", candidate_day: null })))
      .toContain("which ended Feb 20, 2026");
    expect(lead(signal({ status: "FILTERED_OUT" }))).toContain("credit did not meet its rules");
    expect(lead(signal({ status: "NO_SHOCK", shock_day: null, candidate_day: null })))
      .toContain("nothing can qualify today");
  });
});

describe("the readings' verdicts", () => {
  it("never turn a blank into a failed check or a zero", () => {
    const blank = current({ forecast_gap_vol: null, gap_ok: null, swings_below_long: null,
                            swings_not_rising: null, rv_short: null, ...NO_CREDIT });
    expect([swingsMet(blank), creditMet(blank)]).toEqual([null, null]);
    const [pricing, swings, credit] = observations(thesis(blank));
    expect([pricing?.met, swings?.met, credit?.met]).toEqual([null, null, null]);
    expect(pricing?.text).toContain("can't be compared with our forecast");
    expect(swings?.text).toContain("are not both available for this session");
    expect(swings?.text).toContain("over the past three sessions cannot be assessed");
    expect(credit?.text).toContain("Credit data can't be used");
    expect([pricing, swings, credit].map((o) => o?.text).join(" "))
      .not.toMatch(/is higher|is above|rose|0\.0/);
  });
});

describe("the supporting observations", () => {
  it("read the reviewed snapshot, each with the tracker's own verdict", () => {
    const [pricing, swings, credit] = observations(THESIS);
    expect(pricing).toEqual({ name: "Pricing gap (both versions)", met: true, text:
      "VIX is 11.5 volatility points above our forecast. To qualify, it must be at least 3.0 "
      + "volatility points above the forecast." });
    expect(swings).toEqual({ name: "Market swings (version B only)", met: false, text:
      "Five-day volatility, 34.2%, is above 20-day volatility, 27.0%. It is higher than three "
      + `sessions earlier, 18.5%. ${CALMING}` });
    expect(credit?.met).toBe(false);
    expect(credit?.text).toContain(
      "The spread rose 17 basis points over five observations; the stability limit is 15.");
    expect(credit?.text).toContain("347 basis points, is within the 450 limit");
  });

  it("say where VIX stands, and that the gap needed is above the forecast", () => {
    const gap = (over: Partial<ThesisCurrent>) => observations(thesis(over))[0];
    const needs = " To qualify, it must be at least 3.0 volatility points above the forecast.";
    expect(gap({ forecast_gap_vol: -0.038334, gap_ok: false })).toEqual({ name: "Pricing gap (both versions)",
      met: false, text: `VIX is 3.8 volatility points below our forecast.${needs}` });
    expect(gap({ forecast_gap_vol: 0.031, gap_ok: true })?.text)
      .toBe(`VIX is 3.1 volatility points above our forecast.${needs}`);
    for (const level of [0, 0.0002, -0.0002]) {
      expect(gap({ forecast_gap_vol: level, gap_ok: false })?.text)
        .toBe(`VIX matches our forecast.${needs}`);
    }
    const missing = gap({ forecast_gap_vol: null, gap_ok: null });
    expect(missing?.met).toBeNull();
    expect(missing?.text).toContain("can't be compared with our forecast");
    expect(missing?.text).not.toMatch(/0\.0|matches|below/);
  });

  it("follow the file's verdicts, not a comparison of their own", () => {
    // 34.2% is above 27.0%, but the verdict shown is the tracker's.
    expect(observations(thesis({ swings_below_long: true, swings_not_rising: true }))[1]?.met)
      .toBe(true);
    expect(observations(thesis({ gap_ok: false }))[0]?.met).toBe(false);
  });

  it("explain each calming condition on its own, whichever fails", () => {
    const swings = (over: Partial<ThesisCurrent>) => observations(thesis(over))[1];
    expect(swings({ rv_short: 0.2, swings_below_long: true })).toMatchObject({ met: false,
      text: "Five-day volatility, 20.0%, is below 20-day volatility, 27.0%. It is higher than three "
        + `sessions earlier, 18.5%. ${CALMING}` });
    expect(swings({ rv_short_earlier: 0.4, swings_not_rising: true })).toMatchObject({ met: false,
      text: "Five-day volatility, 34.2%, is above 20-day volatility, 27.0%. It is no higher than "
        + `three sessions earlier, 40.0%. ${CALMING}` });
    const calm = swings({ rv_short: 0.15, swings_below_long: true, swings_not_rising: true });
    expect(calm?.met).toBe(true);
    expect(calm?.text).toContain("is below 20-day volatility, 27.0%. It is no higher than");
    const unknown = swings({ rv_short: 0.2, swings_below_long: true, swings_not_rising: null,
                             rv_short_earlier: null });
    expect(unknown?.met).toBeNull();
    expect(unknown?.text).toContain("cannot be assessed");
    expect(swings({ rv_short: 0.27, rv_long: 0.27 })?.text).toContain("equals 20-day volatility");
  });

  it("name the rule a spread breaks", () => {
    const p = THESIS.parameters;
    expect(creditText(current({ credit_bps: 463, credit_level_ok: false,
                                credit_change_short_ok: true }), p))
      .toBe("The spread is 463 basis points; the stability limit is 450.");
    expect(creditText(current({ credit_change_short_ok: true, credit_change_long_ok: false,
                                credit_change_long_bps: 55 }), p))
      .toContain("rose 55 basis points over twenty observations; the stability limit is 40");
    const all = creditText(current({ credit_bps: 463, credit_level_ok: false,
      credit_change_long_ok: false, credit_change_long_bps: 55 }), p);
    for (const rule of ["463 basis points; the stability limit is 450", "rose 17 basis points over "
                        + "five observations; the stability limit is 15", "rose 55 basis points over "
                        + "twenty observations; the stability limit is 40"]) {
      expect(all).toContain(rule); // every rule it breaks, not only the first
    }
    expect(all).not.toContain("within");
    expect(creditText(current(CALM), p)).toContain("fell 3 basis points over five observations");
    expect(creditText(current(CALM), p)).toContain("within all three limits");
    expect(creditText(current(NO_CREDIT), p)).toContain("The latest is 9 business days old");
  });

  it("say what the first night's file lacks, without a verdict it can't support", () => {
    const [pricing, swings, credit] = observations(FIRST_NIGHT);
    expect([pricing?.met, swings?.met]).toEqual([null, null]);
    expect(pricing?.text).toBe("VIX is 11.5 volatility points above our forecast. The gap needed to "
      + "qualify is not in this data file.");
    expect(credit?.text).toContain("The limits it was checked against are not in this file");
    expect(credit?.met).toBe(false); // the file's own credit status
  });

  it("count basis points in words", () => {
    expect([moved(17), moved(-1), moved(0.2)]).toEqual([
      "rose 17 basis points", "fell 1 basis point", "did not change"]);
  });
});
