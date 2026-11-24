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
import type { Thesis, ThesisCohort } from "../types/generated/thesis";
import { grossPremium } from "./thesis/cost";
import { gapSentence, leftOut, sampleLimits } from "./thesis/evidence";
import { conditionStatus } from "./thesis/invalidate";

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

const SEQUENCE = ["Selling expensive protection after market scares", "Latest assessment",
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
    expect(idea).toContain("I believe S&P 500 options remain expensive relative to subsequent");
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
    expect(screen.queryAllByRole("table")).toEqual([]);
    for (const title of ["Explore credit conditions", "View daily observations",
                         "View volatility spikes and qualifying observations",
                         "Explore the historical observations",
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
    for (const part of ["Watching a recent volatility spike", "Readings at the Feb 9, 2026 close",
                        "VIX is 11.5 volatility points above the model forecast",
                        "Meets the condition", "Does not meet the condition",
                        "Data through Feb 9, 2026", "Last updated 2026-02-09 23:17 ET",
                        "Next update expected by", "Data feed up to date"]) {
      expect(assessment).toContain(part);
    }
  });

  it("tells a past qualifying session's assessment from the latest readings", async () => {
    const signal = { ...THESIS.signal, status: "ELIGIBLE", candidate_day: "2026-02-06",
                     shock_day: "2026-02-04" };
    await shown({ ...THESIS, signal });
    const assessment = text("Latest assessment");
    expect(assessment).toContain("Research conditions met");
    expect(assessment).toContain("The session of Feb 6, 2026");
    expect(assessment).toContain("Separately, the latest session");
    expect(assessment).toContain("no trade was placed");
  });

  it("explains the failed credit rule, and gives all three checks on request", async () => {
    await shown();
    open("Explore credit conditions");
    expect(rowsOf("Credit checks").map((r) => r.map((c) => c.replace(/^[✓✕?] /, "")))).toEqual([
      ["Level of the spread", "347 bps", "at most 450 bps", "Meets the condition"],
      ["Change over 5 observations", "+17 bps", "at most +15 bps", "Does not meet the condition"],
      ["Change over 20 observations", "+20 bps", "at most +40 bps", "Meets the condition"],
    ]);
    const credit = text("Latest assessment");
    expect(credit).toContain("The latest observation is dated Feb 5, 2026");
    expect(credit).toContain("became usable at 2026-02-09 20:30 ET");
    expect(credit).toContain("ICE Data Indices, LLC");
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
    open("Explore credit conditions");
    for (const row of rowsOf("Credit checks")) expect(row[2]).toBe("Not in this file");
    expect(screen.getByText(/level limit is not in this data file/)).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: /Show signal details/ }));
    expect(screen.getByText(/gap a qualifying observation needs is not in this data file/))
      .toBeDefined();
    open("How the signal and the outcomes are computed");
    expect(screen.getByText(/rules' values are not in this data file/)).toBeDefined();
    expect(text("What would invalidate the thesis")).toContain("Preliminary: 5 observations");
  });
});

describe("the tracker", () => {
  it("opens on a recent period, with its presets and the signal's details on request", async () => {
    await shown();
    const pressed = () => screen.getAllByRole("button", { pressed: true }).map((b) => b.textContent);
    expect(pressed()).toEqual(["1 year"]);
    fireEvent.click(screen.getByRole("button", { name: "All" }));
    expect(pressed()).toEqual(["All"]);
    const toggle = screen.getByRole("button", { name: /Show signal details/ });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("list", { name: "Signal details legend" })).toBeNull();
    fireEvent.click(toggle);
    const legend = screen.getByRole("list", { name: "Signal details legend" });
    for (const glyph of ["●", "■", "▲"]) expect(legend.textContent).toContain(glyph);
    expect(legend.textContent).toContain("needs, 3.0 volatility points");
    expect(screen.getByRole("button", { name: /Hide signal details/ })
      .getAttribute("aria-expanded")).toBe("true");
  });

  it("gives the raw observations newest first, a pending outcome as pending", async () => {
    await shown();
    open("View volatility spikes and qualifying observations");
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

  it("keeps the sample's limits and what is left out beside the comparison", async () => {
    expect(sampleLimits(THESIS)).toContain("a very small sample");
    expect(leftOut(THESIS)).toContain("12 other completed observations are left out");
    await shown();
    const evidence = text("Preliminary historical evidence");
    expect(evidence).toContain("Stable credit: 5 completed observations");
    expect(evidence).toContain("They do not establish trading profitability");
    expect(evidence).toContain("Credit-regime comparison unavailable in this sample.");
    expect(evidence).not.toMatch(/supportive|unsupportive|mispriced|alpha/i);
  });

  it("holds the full statistics behind its disclosure", async () => {
    await shown();
    open("Explore the historical observations");
    expect(rowsOf("Groups")).toHaveLength(5);
    expect(rowsOf("Qualifying observations").map((r) => r[0])).toEqual([
      "2026-02-06", "2026-02-04", "2026-02-02"]);
  });
});

describe("the wrong-if cards", () => {
  it("say what each needs and has, never a pass on too small a sample or a made-up zero", async () => {
    await shown();
    const cards = screen.getAllByRole("article").filter((a) => a.className.includes("th-status-"));
    expect(cards.map((c) => c.querySelector("h3")?.textContent)).toEqual([
      "The apparent pricing advantage disappears", "Trading costs consume the opportunity",
      "The credit filter provides no benefit"]);
    expect(cards[0]?.textContent).toContain(
      "Preliminary: 5 of the required 30 observations available");
    expect(cards[0]?.textContent).toContain("+0.0019 variance units on average");
    for (const card of cards.slice(1)) {
      expect(card.textContent).toContain("Evaluated in the next phase: strategy backtesting.");
      expect(card.textContent).toContain("Not measured yet");
      expect(card.textContent).not.toMatch(/\b0\b/);
    }
    expect(cards[2]?.textContent).not.toContain("disjoint cohort");
  });

  it("read a triggered and an untriggered condition as such", () => {
    const [k1] = THESIS.evidence.conditions;
    if (!k1) throw new Error("no K1");
    expect(conditionStatus({ ...k1, status: "FAIL" })).toContain("Triggered");
    expect(conditionStatus({ ...k1, status: "PASS" })).toContain("Not triggered");
  });
});

describe("return and costs", () => {
  it("keeps the premium, the cost and a net return apart, each with its unit", async () => {
    await shown();
    const cost = text("Potential return and trading costs");
    for (const part of ["19 completed observations", "7.6 volatility points above",
                        "variance units", "gross economic premium, not tradable alpha",
                        "9.8% of a put's price and 19.7% of a call's", "mid-price",
                        "Feb 9, 2026", "Net strategy returns have not yet been estimated",
                        "cannot be subtracted"]) {
      expect(cost).toContain(part);
    }
    expect(cost).not.toContain("29.6%"); // the stressed case is behind its disclosure
    open("Cost assumptions and limitations");
    expect(rowsOf("Cost sample").map((r) => [r[0], r[4], r[5]])).toEqual([
      ["Put", "9.8%", "14.6%"], ["Call", "19.7%", "29.6%"]]);
    expect(text("Potential return and trading costs")).toContain("nothing here validates it");
  });

  it("has a premium sentence for no completed observation", () => {
    const { cohorts } = THESIS.evidence;
    const none = { ...THESIS, evidence: { ...THESIS.evidence,
      cohorts: { ...cohorts, candidates: cohorts.unstable } } };
    expect(grossPremium(none)).toContain("no premium to report yet");
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
                        "Watching a recent volatility spike", "Data through Feb 9, 2026",
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
