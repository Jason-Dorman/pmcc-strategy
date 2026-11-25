// The thesis page (T4-02; UI-SPEC §6 › Thesis; PO, TD-30) over a fixture `thesis.json`: the reading
// sequence, the raw tables behind their disclosures, no insufficient sample shown as a pass, no
// blank shown as zero, no profit implied, and a stale feed never shown as fresh.
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "../app/routes";
import { IndexProvider } from "../data/IndexContext";
import { clearRunCache } from "../data/loader";
import { isStale, volPoints } from "../format/thesis";
import { fakeFetch, FILES, INDEX } from "../test/fixtures";
import { FIRST_NIGHT, THESIS } from "../test/thesisFixtures";
import type { Thesis, ThesisCohort, ThesisCondition } from "../types/generated/thesis";
import { assessment } from "./thesis/invalidate";
import { gapSentence, leftOut, sampleLimits } from "./thesis/original";

function renderAt(path: string, thesis: Thesis | null) {
  vi.stubGlobal("fetch", vi.fn(fakeFetch({
    ...FILES,
    "data/index.json": { ...INDEX, thesis: thesis === null ? null : "thesis.json" },
    ...(thesis === null ? {} : { "data/thesis.json": thesis }),
  })));
  return render(
    <MemoryRouter initialEntries={[path]}>
      <IndexProvider><AppRoutes /></IndexProvider>
    </MemoryRouter>,
  );
}

async function shown(thesis: Thesis = THESIS) {
  renderAt("/thesis", thesis);
  await screen.findByRole("region", { name: "Latest assessment" });
}

function text(name: string): string {
  return screen.getByRole("region", { name }).textContent ?? "";
}

/** Open a disclosure by its title. */
function open(title: string): void {
  const details = screen.getByText(title).closest("details");
  if (!details) throw new Error(`no disclosure ${title}`);
  details.open = true;
  fireEvent(details, new Event("toggle"));
}

function rowsOf(name: string): string[][] {
  return within(screen.getByRole("table", { name })).getAllByRole("row").slice(1)
    .map((row) => [...row.querySelectorAll("td")].map((td) => td.textContent ?? ""));
}

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

const SEQUENCE = ["Selling expensive protection, selectively", "Latest assessment",
                  "How much volatility was priced in—and what followed?",
                  "Preliminary historical evidence", "What would invalidate the thesis",
                  "Potential return and trading costs", "Macro conditions",
                  "Methodology, sources and detailed data"];

describe("the reading sequence", () => {
  it("runs from the idea to the methodology, each a named section", async () => {
    await shown();
    expect(screen.getAllByRole("region").map((r) => r.getAttribute("aria-labelledby")))
      .toEqual(["idea", "assessment", "tracker", "evidence", "invalidate", "cost", "macro", "method"]
        .map((id) => `${id}-title`));
    for (const name of SEQUENCE) expect(screen.getByRole("region", { name })).toBeDefined();
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent))
      .toEqual([SEQUENCE[0]]);
  });

  it("leads with the thesis as a hypothesis, and its horizons as planning estimates", async () => {
    await shown();
    const idea = text(SEQUENCE[0] ?? "");
    expect(idea).toContain("I believe S&P 500 options with implied volatility substantially above our "
      + "forecast tend to overstate subsequent market swings when corporate credit conditions are "
      + "stable, creating opportunities to sell protection selectively after trading costs.");
    expect(idea).toContain("Version A enters when the pricing gap is wide enough and credit is stable. "
      + "Version B also waits until recent market swings begin to ease.");
    expect(idea).toContain("a hypothesis we are investigating: Investors' demand for downside "
      + "protection may keep option prices elevated.");
    expect(idea).toContain("The research must establish whether the premium is enough");
    expect(idea).toContain("shorter than the 30-calendar-day window");
    expect(idea).not.toMatch(/scare|spike/i);
    expect(idea).toContain("a hypothesis being investigated");
    for (const part of ["12–24 months", "5–10 trading days", "30 calendar days",
                        "planning estimates, not measured results"]) {
      expect(idea).toContain(part);
    }
    expect(idea).not.toMatch(/provisional|insufficient/i);
  });

  it("moves to a section from the contents, with focus", async () => {
    await shown();
    const jumped = vi.fn();
    Element.prototype.scrollIntoView = jumped;
    const nav = screen.getByRole("navigation", { name: "On this page" });
    fireEvent.click(within(nav).getByRole("button", { name: "Evidence" }));
    expect(jumped).toHaveBeenCalled();
    expect(document.activeElement?.id).toBe("evidence");
  });

  it("keeps every raw table behind a disclosure", async () => {
    await shown();
    expect(screen.getAllByRole("table").map((x) => x.getAttribute("aria-label")))
      .toEqual(["Versions A and B, all qualifying stretches"]); // the one compact comparison
    for (const title of ["View credit checks and daily values", "View daily observations",
                         "View the original version's volatility spikes and observations",
                         "Explore the spacing views, medians and observations",
                         "Original spike-based version (reference)",
                         "Cost assumptions and limitations"]) {
      expect(screen.getByText(title)).toBeDefined();
    }
  });

  it("shows the idea and the macro paragraph without a file, and no figure", async () => {
    renderAt("/thesis", null);
    expect(await screen.findByText("The tracker has not published a file yet.")).toBeDefined();
    expect(screen.getAllByRole("region").map((r) => r.id)).toEqual(["idea", "macro"]);
  });
});

describe("the latest assessment", () => {
  it("has one headline, the readings' date, the observations and the feed's dates", async () => {
    await shown();
    const assessment = text("Latest assessment");
    expect(assessment).not.toMatch(/spike|candidate|original/i); // not the original's search
    for (const part of ["A — Pricing gap + stable credit", "No qualifying setup",
                        "B — Also wait for calmer markets",
                        "Cannot assess — required data unavailable",
                        "It is higher than three sessions earlier, 18.5%", "Readings at the Feb 9, 2026 close",
                        "VIX is 11.5 volatility points above our forecast",
                        "To qualify, it must be at least 3.0 volatility points above",
                        "Meets the condition", "Does not meet the condition",
                        "Data through Feb 9, 2026", "Last updated 2026-02-09 23:17 ET",
                        "Next update expected by", "Data feed up to date"]) {
      expect(assessment).toContain(part);
    }
    // The readings alone say why: no summary repeats them.
    expect(assessment).not.toMatch(/The options market is pricing|does not pass its stability/);
    for (const part of [/20-day volatility, 27/g, /rose 17 basis points/g]) {
      expect(assessment.match(part)).toHaveLength(1);
    }
  });

  it("marks no setup neutrally, apart from missing data", async () => {
    await shown();
    const marks = [...document.querySelectorAll(".th-version .th-verdict")];
    expect(marks.map((m) => [m.className, m.textContent?.slice(0, 1)])).toEqual([
      ["th-verdict th-verdict-unmet", "○"], ["th-verdict th-verdict-unknown", "?"]]);
  });

  it("shows the credit chart without opening anything, its legend and source beside it", async () => {
    await shown();
    const chart = screen.getByRole("figure", { name: /high-yield credit spread as known/ });
    expect(chart.closest("details")).toBeNull();
    const legend = screen.getByRole("list", { name: "Credit chart legend" });
    for (const part of ["Level limit, 450 bps", "a check failed", "too little or too old data"]) {
      expect(legend.textContent).toContain(part);
    }
    const assessment = text("Latest assessment");
    expect(assessment).toContain("stable only when three checks all hold");
    expect(assessment).toContain("ICE Data Indices, LLC");
    expect(assessment).not.toContain("The latest observation is dated");
  });

  it("explains the failed credit rule, and gives all three checks on request", async () => {
    await shown();
    open("View credit checks and daily values");
    expect(rowsOf("Credit checks").map((r) => r.map((c) => c.replace(/^[✓✕?] /, "")))).toEqual([
      ["Level of the spread", "347 bps", "at most 450 bps", "Meets the condition"],
      ["Change over 5 observations", "+17 bps", "at most +15 bps", "Does not meet the condition"],
      ["Change over 20 observations", "+20 bps", "at most +40 bps", "Meets the condition"],
    ]);
    const credit = text("Latest assessment");
    expect(credit).toContain("The latest observation is dated Feb 5, 2026");
    expect(credit).toContain("became usable at 2026-02-09 20:30 ET");
  });
});

describe("freshness, apart from the evidence", () => {
  it("marks a feed whose next night is overdue, whatever the file says of itself", async () => {
    const overdue = { ...THESIS, expected_by: "2026-02-11T12:00:00-05:00" };
    expect(isStale(overdue, Date.parse("2026-02-11T11:59:00-05:00"))).toBe(false);
    expect(isStale(overdue, Date.parse("2026-02-11T12:01:00-05:00"))).toBe(true);
    await shown(overdue);
    expect(text("Latest assessment")).toContain("Data feed out of date");
    expect(text("Preliminary historical evidence")).not.toMatch(/out of date/);
  });
});

describe("the first night's file", () => {
  it("says what it lacks where it lacks it, and shows no limit as zero", async () => {
    await shown(FIRST_NIGHT);
    expect(text("Latest assessment")).toContain("Next update time not in this file");
    expect(text("Latest assessment")).toContain("Not assessed");
    open("View credit checks and daily values");
    for (const row of rowsOf("Credit checks")) expect(row[2]).toBe("Not in this file");
    expect(screen.getByText(/level limit is not in this data file/)).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: /Show gap and original-version details/ }));
    expect(screen.getByText(/gap a version needs is not in this data file/))
      .toBeDefined();
    open("How the signal and the outcomes are computed");
    expect(screen.getByText(/rules' values are not in this data file/)).toBeDefined();
    expect(text("What would invalidate the thesis")).toContain(
      "versions' results are not in this data file");
    expect(text("Preliminary historical evidence")).toContain(
      "two versions' results are not in this data file");
    expect(text("Potential return and trading costs")).toContain("not in this data file yet");
  });
});

describe("the tracker", () => {
  it("opens on a recent period, with its presets and the signal's details on request", async () => {
    await shown();
    const pressed = () => screen.getAllByRole("button", { pressed: true }).map((b) => b.textContent);
    expect(pressed()).toEqual(["1 year"]);
    fireEvent.click(screen.getByRole("button", { name: "All" }));
    expect(pressed()).toEqual(["All"]);
    const toggle = screen.getByRole("button", { name: /Show gap and original-version details/ });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("list", { name: "Gap and original-version legend" })).toBeNull();
    fireEvent.click(toggle);
    const legend = screen.getByRole("list", { name: "Gap and original-version legend" });
    for (const glyph of ["●", "■", "▲"]) expect(legend.textContent).toContain(glyph);
    expect(legend.textContent).toContain("Gap every version needs, 3.0 volatility points");
    expect(legend.textContent).toContain("Original version: observation, credit stable");
    expect(screen.getByText(/Versions A and B use neither/)).toBeDefined();
    expect(screen.getByRole("button", { name: /Hide gap and original-version details/ })
      .getAttribute("aria-expanded")).toBe("true");
  });

  it("gives the raw observations newest first, a pending outcome as pending", async () => {
    await shown();
    open("View the original version's volatility spikes and observations");
    expect(rowsOf("Volatility spikes").map((r) => r[0])).toEqual([
      "2026-02-09", "2026-02-05", "2026-02-04", "2026-02-02"]);
    expect(rowsOf("Volatility spikes")[1]).toContain("Pending");
  });
});

describe("the evidence", () => {
  const group = (over: Partial<ThesisCohort>): ThesisCohort => ({
    ...THESIS.evidence.cohorts.stable, ...over });

  it("handles positive, negative, level, single and empty groups", () => {
    expect(gapSentence(group({}))).toBe("Market-priced volatility exceeded subsequent actual "
      + "volatility by an average of 7.6 volatility points.");
    expect(gapSentence(group({ mean_vol_gap: -0.1065, count: 2 }))).toContain(
      "fell below subsequent actual volatility by an average of 10.7 volatility points");
    expect(gapSentence(group({ count: 1 }))).toContain("by 7.6 volatility points");
    expect(gapSentence(group({ mean_vol_gap: 0.0001 }))).toContain("matched");
    expect(gapSentence(THESIS.evidence.cohorts.unstable)).toBe("No completed observation yet.");
  });

  it("compares A and B in one table, with the period and the overlap beside it", async () => {
    await shown();
    expect(rowsOf("Versions A and B, all qualifying stretches")).toEqual([
      ["66", "57"], ["64", "55"], ["+3.7 pts", "+4.3 pts"],
      ["−26.3 pts (Mar 28, 2025)", "−5.2 pts (Feb 14, 2025)"]]);
    const shownText = text("Preliminary historical evidence");
    for (const part of ["Analysis period: Dec 27, 2023 to Feb 9, 2026", "can overlap and are not",
                        "neither version is shown to be better",
                        "justify fewer opportunities?",
                        "A negative gap means the market moved more than options had priced in",
                        "it is not a trading loss or portfolio drawdown",
                        "Counting every qualifying stretch, the average gap is +3.7 points for A"]) {
      expect(shownText).toContain(part);
    }
    expect(shownText).not.toMatch(/winner|5 completed|\+7\.6|mispriced|alpha/i);
  });

  it("holds the spacing views and each version's own observations behind a disclosure", async () => {
    await shown();
    open("Explore the spacing views, medians and observations");
    expect(rowsOf("Counting views").map((r) => r.slice(0, 5))).toEqual([
      ["A", "All qualifying stretches", "66", "64", "2"],
      ["A", "At least 10 sessions apart", "37", "35", "2"],
      ["A", "At least 30 calendar days apart", "23", "21", "2"],
      ["B", "All qualifying stretches", "57", "55", "2"],
      ["B", "At least 10 sessions apart", "32", "30", "2"],
      ["B", "At least 30 calendar days apart", "21", "19", "2"]]);
    expect(rowsOf("Version A observations").map((r) => [r[0], r[3], r[4], r[6]])).toEqual([
      ["2026-01-12", "—", "—", "Pending"], ["2026-01-05", "Kept", "Kept", "14.0%"]]);
    const opened = text("Preliminary historical evidence");
    expect(opened).toContain("held on 393 sessions");
    expect(opened).toContain("held on 145 sessions");
    expect(opened).toContain("still not statistically independent");
  });

  it("keeps the original version apart, whole, and labelled as no evidence for A or B", async () => {
    await shown();
    expect(text("Preliminary historical evidence")).not.toContain("Original, stable credit");
    open("Original spike-based version (reference)");
    const reference = text("Preliminary historical evidence");
    for (const part of ["It is not evidence for versions A or B",
                        "Original, stable credit: 5 completed observations",
                        "Watching a recent volatility spike", "K1.", "K2.", "K3.",
                        "only 5 of the required 30 observations are available"]) {
      expect(reference).toContain(part);
    }
    expect(rowsOf("Original groups")).toHaveLength(5);
    expect(rowsOf("Original qualifying observations").map((r) => r[0])).toEqual([
      "2026-02-06", "2026-02-04", "2026-02-02"]);
    expect(sampleLimits(THESIS)).toContain("a very small sample");
    expect(leftOut(THESIS)).toContain("12 other completed observations are left out");
  });
});

describe("the wrong-if cards", () => {
  const [found] = THESIS.evidence.conditions;
  const k1 = (over: Partial<ThesisCondition>): ThesisCondition => {
    if (!found) throw new Error("no K1");
    return { ...found, ...over };
  };

  it("assess the revised first condition for each version apart, the rest for the backtest",
     async () => {
    await shown();
    const cards = screen.getAllByRole("article").filter((a) => a.className.includes("th-status-"));
    expect(cards.map((c) => c.querySelector("h3")?.textContent)).toEqual([
      "The observed variance premium disappears", "Returns fail to remain positive after costs",
      "Stable-credit selection provides no benefit"]);
    expect([...(cards[0]?.querySelectorAll(".th-status") ?? [])].map((p) => p.textContent)).toEqual([
      "◐ Version A: The average variance premium is currently positive, but only 22 of the required "
      + "30 observations are available.",
      "◐ Version B: The average variance premium is currently positive, but only 20 of the required "
      + "30 observations are available."]);
    expect(cards[0]?.textContent).toContain("at least 30 calendar days apart");
    expect(text("What would invalidate the thesis")).toContain("Three defined conditions for "
      + "reviewing this thesis. Any one of them would count against it and call for reassessment.");
    for (const card of cards.slice(1)) {
      expect(card.querySelector(".th-status")?.textContent)
        .toBe("○ Evaluated in the next phase: strategy backtesting.");
      expect(card.textContent).not.toMatch(/Not measured yet|variance units/);
    }
    const details = cards[0]?.querySelector("details");
    if (!details) throw new Error("no disclosure");
    details.open = true;
    fireEvent(details, new Event("toggle"));
    for (const part of ["K1-A.", "K1-B.", "+0.0012 in variance units, over 22 completed",
                        "over 20 completed", "as of Feb 9, 2026", "wrong if ≤ 0",
                        "a revised observation definition"]) {
      expect(cards[0]?.textContent).toContain(part);
    }
  });

  it("say what too small a sample shows, by its sign, never as a pass", () => {
    const few = "only 5 of the required 30 observations are available.";
    expect(assessment(k1({}))).toContain(`currently positive, but ${few}`);
    expect(assessment(k1({ value: -0.002 }))).toContain(`currently negative, and ${few}`);
    expect(assessment(k1({ value: 0 }))).toContain(`currently zero, and ${few}`);
    expect(assessment(k1({ sample: 1 }))).toContain("only 1 of the required 30 observations is");
    expect(assessment(k1({ value: null, sample: 0 }))).toContain("cannot be assessed yet: 0 of the");
    expect(assessment(k1({ value: null }))).toContain("is unavailable; only 5 of the required 30");
    for (const value of [0.002, -0.002, 0, null]) {
      expect(assessment(k1({ value }))).not.toMatch(/pass|does not hold|needs review/i);
    }
  });

  it("read a large enough sample by the backend's status", () => {
    expect(assessment(k1({ status: "PASS", value: 0.001, sample: 31 }))).toBe(
      "The average variance premium over the latest 30 observations is positive: this condition "
      + "does not hold on the current rolling sample.");
    expect(assessment(k1({ status: "FAIL", value: -0.001, sample: 30 }))).toContain(
      "is negative: this condition holds, so the thesis needs review");
    expect(assessment(k1({ status: "FAIL", value: 0, sample: 30 }))).toContain("is zero");
  });
});

describe("return and costs", () => {
  it("estimate a cost in words that claim no trade, and keep it apart from the gap", async () => {
    await shown();
    const cost = text("Potential return and trading costs");
    for (const part of ["Observed volatility gap", "Version A, all qualifying stretches: across 64",
                        "Version B, all qualifying stretches: across 55",
                        "not tradable alpha", "Using the sampled bid–ask quotes and assumed fees, we "
                        + "estimate a round-trip cost of about 9.8% of a put's mid-price and 19.7%",
                        "Feb 9, 2026", "Net strategy returns have not yet been estimated",
                        "cannot be subtracted"]) {
      expect(cost).toContain(part);
    }
    expect(cost).not.toMatch(/opening and closing|29\.6%|The median was|b5 completed|with stable credit/i);
    open("Cost assumptions and limitations");
    expect(rowsOf("Cost sample").map((r) => [r[0], r[4], r[5]])).toEqual([
      ["Put", "9.8%", "14.6%"], ["Call", "19.7%", "29.6%"]]);
    const opened = text("Potential return and trading costs");
    expect(opened).toContain("The table shows the round-trip cost we estimate");
    expect(opened).toContain("nothing here validates it");
  });
});

describe("the research history", () => {
  it("claims neither a design fixed beforehand nor a nightly cost sample", async () => {
    await shown();
    open("Limitations");
    const method = text("Methodology, sources and detailed data");
    expect(method).toContain("The A/B comparison was developed while examining this historical sample, "
      + "and the results have not been tested on unseen data.");
    expect(method).toContain("The trading-cost illustration uses the quote date shown in that section.");
    expect(document.body.textContent).not.toMatch(
      /fixed in advance|before the history was examined|every number here/i);
  });
});

describe("the definitions", () => {
  it("say volatility is annualized, not a return", async () => {
    await shown();
    const assessed = text("Latest assessment");
    expect(assessed).toContain("Volatility measures how strongly prices fluctuate; the figures here "
      + "are expressed on an annualized basis.");
    expect(assessed).not.toContain("percentage per year");
    for (const term of ["VIX is the volatility", "A volatility point is", "a basis point is"]) {
      expect(assessed).toContain(term);
    }
  });
});

describe("the home tile", () => {
  async function tile(thesis: Thesis | null) {
    renderAt("/", thesis);
    const region = await screen.findByRole("region", { name: "Volatility Thesis" });
    await within(region).findByText(/Unavailable|volatility points/);
    return region.textContent ?? "";
  }

  it("comes first and gives the gap, signed, in volatility points, its signal and its date",
     async () => {
    const found = await tile(THESIS);
    for (const part of ["Daily thesis tracker", "+11.5 volatility points",
                        "A: no qualifying setup · B: cannot assess", "Data through Feb 9, 2026",
                        "not an expected trading return"]) {
      expect(found).toContain(part);
    }
    const tiles = screen.getAllByRole("region").map((r) => r.querySelector("h2")?.textContent);
    expect(tiles[0]).toBe("Volatility Thesis");
  });

  it("says Unavailable, never zero, without a gap or a file", async () => {
    const current = THESIS.current && { ...THESIS.current, forecast_gap_vol: null };
    const found = await tile({ ...THESIS, current });
    expect(found).toContain("Unavailable");
    expect(found).not.toContain("volatility points");
    cleanup();
    clearRunCache();
    expect(await tile(null)).toContain("Unavailable");
    expect(volPoints(-0.0451)).toBe("−4.5");
  });
});
