// The thesis page (T4-01; UI-SPEC §6 › Thesis; PO, TD-10, TD-21 to TD-25, TD-28) over a fixture
// `thesis.json`: the assignment's items in order, no insufficient sample shown as a pass, no blank
// shown as zero, and a stale file never shown as fresh.
import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "../app/routes";
import { IndexProvider } from "../data/IndexContext";
import { clearRunCache } from "../data/loader";
import { isStale, signalDetail, signalLabel, volPoints } from "../format/thesis";
import { fakeFetch, FILES, INDEX } from "../test/fixtures";
import { panel, readout } from "../test/page";
import { EPISODES, FIRST_NIGHT, THESIS } from "../test/thesisFixtures";
import type { Thesis } from "../types/generated/thesis";
import { roughReading } from "./thesis/evidence";
import { stateSentence } from "./thesis/prose";

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

function rowsOf(name: string): string[][] {
  return within(screen.getByRole("table", { name })).getAllByRole("row").slice(1)
    .map((row) => [...row.querySelectorAll("td")].map((td) => td.textContent ?? ""));
}

async function shown(thesis: Thesis = THESIS) {
  renderAt("/thesis", thesis);
  await screen.findByRole("table", { name: "Recent sessions" });
}

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

describe("the page", () => {
  it("shows the assignment's items in their order", async () => {
    await shown();
    const names = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(names).toEqual(["The thesis", "Time horizons", "Daily tracker", "Credit spread",
                           "Today's state", "Wrong-if conditions",
                           "Preliminary historical evidence", "Alpha and cost",
                           "Macro environment", "Methodology and sources"]);
    expect(within(await panel("Daily tracker")).getByText("[1]")).toBeDefined();
    expect(within(await panel("Preliminary historical evidence")).getByText("[4]")).toBeDefined();
  });

  it("states the thesis as the spec does", async () => {
    await shown();
    expect((await panel("The thesis")).textContent).toContain(
      "Following equity-volatility spikes, options overprice subsequent market fluctuations when "
      + "corporate credit conditions remain stable and realized volatility begins to normalize, "
      + "creating opportunities to sell protection selectively after costs.");
  });

  it("reads the statuses as words", async () => {
    await shown();
    expect(readout("Thesis status").value).toBe("Provisional");
    expect(readout("Evidence").value).toBe("Insufficient");
    expect(readout("Today's signal").value).toBe("Monitoring a recent volatility spike");
    expect(readout("Data through").value).toBe("Feb 9, 2026");
    expect(readout("VIX minus forecast").value).toBe("+11.5 pts");
    expect(readout("Credit").value).toBe("Unstable");
  });

  it("shows the latest sessions newest first, a pending outcome as pending", async () => {
    await shown();
    const [first] = rowsOf("Recent sessions");
    expect(first?.[0]).toBe("2026-02-09");
    expect(first).toContain("Pending");
    expect(first).not.toContain("0.0%");
  });

  it("shows no file yet as missing, never as zeros", async () => {
    renderAt("/thesis", null);
    expect((await screen.findAllByText("No results for the volatility thesis.")).length)
      .toBeGreaterThan(0);
  });

  it("works on the first night's file, before the rules' values were in it", async () => {
    await shown(FIRST_NIGHT);
    expect(rowsOf("Credit tests").map((r) => r[3])).toEqual(["—", "—", "—"]);
    expect(screen.queryByText(/^Stale/)).toBeNull();
  });
});

describe("credit", () => {
  it("shows the latest level and changes against their limits, outside any tooltip", async () => {
    await shown();
    expect(rowsOf("Credit tests")).toEqual([
      ["Level", "347 bps", "≤ 450 bps", "Within"],
      ["Change over 5 observations", "+17 bps", "≤ +15 bps", "Over"],
      ["Change over 20 observations", "+20 bps", "≤ +40 bps", "Within"],
    ]);
    const text = (await panel("Credit spread")).textContent;
    expect(text).toContain("The observation of Feb 5, 2026, assumed available 2026-02-09 20:30 ET");
    expect(text).toContain("ICE Data Indices, LLC");
  });
});

describe("the wrong-if conditions", () => {
  it("never show too small a sample as a pass", async () => {
    await shown();
    const [k1, k2] = rowsOf("Wrong-if conditions");
    expect(k1?.join(" ")).toContain("Insufficient data");
    expect(k1?.join(" ")).toContain("+0.0019 (provisional)");
    expect(k1?.join(" ")).not.toMatch(/pass/i);
    expect(k2).toEqual(expect.arrayContaining(["Unavailable", "Not yet evaluated",
                                               "Not yet evaluated — requires strategy backtesting"]));
  });
});

describe("the evidence and the alpha/cost note", () => {
  it("carries the file's sentences, the groups and every candidate", async () => {
    await shown();
    const text = (await panel("Preliminary historical evidence")).textContent;
    for (const s of THESIS.evidence.statements) expect(text).toContain(s);
    expect(text).not.toMatch(/supportive|unsupportive/i);
    const groups = rowsOf("Preliminary historical evidence");
    expect(groups.find((r) => r[0] === "Unstable-credit candidates")?.slice(1, 3))
      .toEqual(["0", "—"]);
    expect(rowsOf("Candidates").map((r) => r[0])).toEqual(["2026-02-06", "2026-02-04",
                                                           "2026-02-02"]);
  });

  it("labels the premium gross, sets it beside the cost, and gives no verdict", async () => {
    await shown();
    const text = (await panel("Alpha and cost")).textContent ?? "";
    expect(text).toContain("Gross economic premium, not tradable alpha.");
    expect(text).toContain("skipped on the sample day");
    expect(rowsOf("Cost")).toEqual([["Put", "20", "9.8%", "14.6%"], ["Call", "24", "19.7%", "29.6%"]]);
    expect(roughReading(THESIS)).toContain("VIX overstated the volatility that followed by 22.6%");
    const none = { ...THESIS, evidence: { ...THESIS.evidence, cohorts: {
      ...THESIS.evidence.cohorts,
      candidates: { ...THESIS.evidence.cohorts.unstable } } } };
    expect(roughReading(none)).toContain("there is no edge to set against the cost yet");
  });
});

describe("the macro panel", () => {
  it("gives a dated state from the tracker's values alone", () => {
    expect(stateSentence(THESIS)).toBe(
      "At the Feb 9, 2026 close: VIX at 27.50, against a spike threshold of 19.91; a 30-day "
      + "volatility forecast of 16.0%, so VIX minus the forecast is +11.5 pts; realized volatility "
      + "of 34.2% over 5 sessions and 27.0% over 20; and a high-yield spread of 347 bps (unstable, "
      + "+17 bps over five observations).");
  });
});

describe("freshness", () => {
  it("marks a file whose next night is overdue as stale, whatever it says of itself", async () => {
    const overdue = { ...THESIS, expected_by: "2026-02-11T12:00:00-05:00" };
    expect(isStale(overdue, Date.parse("2026-02-11T11:59:00-05:00"))).toBe(false);
    expect(isStale(overdue, Date.parse("2026-02-11T12:01:00-05:00"))).toBe(true);
    expect(isStale({ ...THESIS, data_status: "STALE" })).toBe(true);
    await shown(overdue);
    expect(screen.getByText(/^Stale: the tracker's last successful update/)).toBeDefined();
  });
});

describe("the blocked signals (TD-25)", () => {
  const blocked = { ...THESIS.signal, assessment: "BLOCKED", shock_day: "2026-02-04",
                    candidate_day: "2026-02-06" };

  it("say why, with the date, and never read as eligible or as no candidate", () => {
    const credit = { ...blocked, status: "CREDIT_UNAVAILABLE", reason: "The latest is too old." };
    expect(signalDetail(credit)).toBe(
      "Credit data unavailable — eligibility cannot be assessed. VIX spiked on Feb 4, 2026. "
      + "The latest is too old.");
    const search = { ...blocked, status: "INCOMPLETE_CANDIDATE_SEARCH", reason: "A close is missing." };
    expect(signalDetail(search)).toContain(
      "Incomplete observation window — candidate assessment unavailable.");
    for (const status of ["CREDIT_UNAVAILABLE", "INCOMPLETE_CANDIDATE_SEARCH"]) {
      expect(signalLabel(status)).not.toMatch(/eligible|no candidate|no qualifying/i);
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
    const text = await tile(THESIS);
    for (const part of ["Daily thesis tracker", "+11.5 volatility points",
                        "Monitoring a recent volatility spike", "Data through Feb 9, 2026",
                        "not an expected trading return"]) {
      expect(text).toContain(part);
    }
    const tiles = screen.getAllByRole("region").map((r) => r.querySelector("h2")?.textContent);
    expect(tiles[0]).toBe("Volatility Thesis");
    const region = screen.getByRole("region", { name: "Volatility Thesis" });
    expect(within(region).getAllByRole("link").map((a) => a.getAttribute("href")))
      .toEqual(["/thesis", "/thesis"]);
  });

  it("says Unavailable, never zero, without a gap or a file", async () => {
    const current = THESIS.current && { ...THESIS.current, forecast_gap_vol: null };
    const text = await tile({ ...THESIS, current });
    expect(text).toContain("Unavailable");
    expect(text).not.toContain("volatility points");
    cleanup();
    clearRunCache();
    expect(await tile(null)).toContain("Unavailable");
  });

  it("shows a negative gap's sign", () => {
    expect(volPoints(-0.0451)).toBe("−4.5");
    expect(volPoints(0.0001)).toBe("0.0");
    expect(EPISODES).toHaveLength(4);
  });
});
