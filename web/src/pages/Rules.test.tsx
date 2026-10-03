// The Trade rules page (P7-03, UI-SPEC §6.3) over the fixture rules.json: the panels in order;
// the entry, gate and exit tables with both strategies' live values and each rule's rationale;
// the target row of `#/rules/<ID>`; how rules work, its differences read from the rules; the
// ablations and the sensitivity runs in words; and the in-panel state when rules.json is missing.
import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearRunCache } from "../data/loader";
import { FILES } from "../test/fixtures";
import { bodyRows, column, panel, renderRules } from "../test/page";

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

async function table(name: string): Promise<HTMLElement> {
  return screen.findByRole("table", { name });
}

/** A rule table's row by its rule ID (the ID column comes after the toggle). */
function ruleRow(t: HTMLElement, id: string): HTMLElement {
  const row = bodyRows(t).find((r) => r.querySelectorAll("td")[1]?.textContent === id);
  if (!row) throw new Error(`no row ${id}`);
  return row;
}

function cells(row: HTMLElement): string[] {
  return [...row.querySelectorAll("td")].map((td) => td.textContent ?? "");
}

describe("the page", () => {
  it("shows how rules work, then the five tables numbered in order", async () => {
    renderRules();
    await table("Sensitivity");
    const names = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(names).toEqual(["How rules work", "Entry rules", "Skip-week gates", "Exit rules",
                           "Ablations", "Sensitivity"]);
    const numbers = screen.getAllByRole("region")
      .map((r) => r.querySelector(".pm-panel-n")?.textContent ?? null);
    expect(numbers).toEqual([null, "[1]", "[2]", "[3]", "[4]", "[5]"]);
  });

  it("says so in each panel when rules.json is missing, never a blank page", async () => {
    const files = { ...FILES };
    delete files["data/rules.json"];
    renderRules("/rules", files);
    expect(await within(await panel("Entry rules")).findByText(/rules\.json/)).toBeTruthy();
  });
});

describe("entry rules", () => {
  it("lists every entry rule in order with its ID linked to its own row", async () => {
    renderRules();
    const t = await table("Entry rules");
    expect(column(t, 1)).toEqual(["E-T1", "E-L2", "E-L3", "E-S3", "E-S5"]);
    const link = within(ruleRow(t, "E-L2")).getByRole("link", { name: "E-L2" });
    expect(link.getAttribute("href")).toBe("/rules/E-L2");
  });

  it("reads Same where quant runs the baseline's rule, and its own rule where it doesn't", async () => {
    renderRules();
    const t = await table("Entry rules");
    const [, , name, baseline, quant] = cells(ruleRow(t, "E-T1"));
    expect([name, quant]).toEqual(["Entry trigger", "Same"]);
    expect(baseline).toContain("Spread at most 3% of mid");
    expect(baseline).toContain("→ Enter on the first bar");
    const l3 = cells(ruleRow(t, "E-L3"));
    expect(l3[3]).toContain("Choose the strike with delta nearest 0.80");
    expect(l3[4]).toContain("Eligible calls with delta from 0.70 to 0.90");
    expect(l3[4]).toContain("→ Choose the lowest extrinsic ÷ delta");
  });

  it("opens a rule's rationale under its row, each strategy's where they differ", async () => {
    renderRules();
    const t = await table("Entry rules");
    fireEvent.click(within(t).getByRole("button", { name: "Rationale for E-T1" }));
    expect(within(t).getByText("Liquidity decides.")).toBeTruthy();

    fireEvent.click(within(t).getByRole("button", { name: "Rationale for E-S3" }));
    const opened = within(t).getByText("The expected-move short.").closest("td");
    expect(opened?.textContent).toBe(
      "Baseline PMCCThe textbook short.Quant PMCCThe expected-move short.");
  });
});

describe("skip-week gates", () => {
  it("shows each gate on or off per strategy, with the threshold it ran at", async () => {
    renderRules();
    const t = await table("Skip-week gates");
    expect(column(t, 1)).toEqual(["G-1", "G-2", "G-3", "G-4", "G-5"]);
    expect(cells(ruleRow(t, "G-1")).slice(4)).toEqual(["On", "On"]);
    expect(cells(ruleRow(t, "G-3")).slice(4)).toEqual(["Off", "On · 1.20"]);
    expect(cells(ruleRow(t, "G-5")).slice(4)).toEqual(["Off", "On · $0.10"]);
    expect(within(ruleRow(t, "G-3")).getByText("On · 1.20").getAttribute("title"))
      .toBe("max ratio 1.20");
  });

  it("states the condition with its live value and what a firing gate does", async () => {
    renderRules();
    const t = await table("Skip-week gates");
    const [, , gate, condition] = cells(ruleRow(t, "G-4"));
    expect(gate).toBe("Volatility risk premium");
    expect(condition).toBe("Front-week ATM IV ÷ RV20 < 1.00→ Skip the week; keep the long");
  });
});

describe("exit rules", () => {
  it("gives each exit's trigger and action, and its rationale's paragraphs", async () => {
    renderRules();
    const t = await table("Exit rules");
    expect(column(t, 1)).toEqual(["X-S1", "X-S3", "X-L1", "X-L2", "X-E1"]);
    expect(cells(ruleRow(t, "X-S3")).slice(2)).toEqual([
      "Friday check: Spot ≥ short strike − 0.25 × EM by 15:00 ET", "Buy to close at mid"]);
    fireEvent.click(within(t).getByRole("button", { name: "Rationale for X-S3" }));
    const paragraphs = within(t).getByText("The Friday buffer.").closest("td")
      ?.querySelectorAll("p");
    expect([...(paragraphs ?? [])].map((p) => p.textContent))
      .toEqual(["There are no rolls.", "The Friday buffer."]);
  });
});

describe("arriving for a rule", () => {
  it("outlines that rule's row, and no other", async () => {
    renderRules("/rules/X-S3");
    const t = await table("Exit rules");
    expect(ruleRow(t, "X-S3").classList.contains("pm-target")).toBe(true);
    expect(document.querySelectorAll(".pm-target")).toHaveLength(1);
  });

  it("says so when the results have no such rule", async () => {
    renderRules("/rules/Z-9");
    expect(await within(await panel("How rules work"))
      .findByText("The rule this link names isn't in these results.")).toBeTruthy();
    expect(document.querySelectorAll(".pm-target")).toHaveLength(0);
  });
});

describe("how rules work", () => {
  it("gives the order of operations in words", async () => {
    renderRules();
    const how = await panel("How rules work");
    await within(how).findByText(/Every decision is made/);
    expect(how.textContent).toContain("first the long leg's exits and resets, then the short's " +
      "exits, then, in the week-open session only, the week's new short, sold only if no " +
      "skip-week gate fires");
  });

  it("reads how the strategies differ from the rules", async () => {
    renderRules();
    const how = await panel("How rules work");
    await within(how).findByText(/differ only in/);
    expect(how.textContent).toContain(
      "Baseline PMCC and Quant PMCC differ only in their Long leg expiry, Long leg strike and " +
      "Short leg strike rules, which select the contracts, and in the Event week, Volatility " +
      "risk premium and Minimum premium gates, which only Quant PMCC runs. Every other rule, " +
      "every exit included, is the same in both");
    const link = within(how).getByRole("link", { name: "Minimum premium" });
    expect(link.getAttribute("href")).toBe("/rules/G-5");
  });
});

describe("ablations", () => {
  it("names each layer removed and what replaced it", async () => {
    renderRules();
    const t = await table("Ablations");
    expect(bodyRows(t).map(cells)).toEqual([
      ["A1: quant with the baseline long leg", "Long leg expiry",
       "Choose the monthly expiry nearest 180 days to expiry"],
      ["A1: quant with the baseline long leg", "Long leg strike",
       "Choose the strike with delta nearest 0.80"],
      ["A3: quant without the event gate", "Event week", "nothing"],
    ]);
    const removed = within(t).getByRole("link", { name: "Event week" });
    expect(removed.getAttribute("href")).toBe("/rules/G-3");
  });
});

describe("sensitivity", () => {
  it("says what each run changes against the strategy it varies", async () => {
    renderRules();
    const t = await table("Sensitivity");
    expect(bodyRows(t).map(cells)).toEqual([
      ["Friction", "Friction: baseline at spread capture 0.25", "spread capture 0.00 → 0.25"],
      ["Timing", "Timing: baseline, short decided on bar 1 (10:00)",
       "Entry trigger: replaced by Entry trigger, fixed bar · bar 1"],
      ["Grid", "Grid: quant with k = 0.75", "Short leg strike: k 1.0 → 0.75"],
    ]);
  });

  it("filters by check", async () => {
    renderRules();
    const t = await table("Sensitivity");
    const filter = screen.getByRole("group", { name: "Filter by Check" });
    fireEvent.click(within(filter).getByRole("button", { name: /Grid/ }));
    expect(column(t, 0)).toEqual(["Grid"]);
  });
});

describe("table height (PO, DEC-112)", () => {
  it("lets the three rule tables grow to their rows, and keeps the cap on the others", async () => {
    renderRules();
    await table("Sensitivity");
    const grows = (name: string) => screen.getByRole("table", { name }).closest(".pm-table-scroll")
      ?.classList.contains("pm-table-grow");
    expect(["Entry rules", "Skip-week gates", "Exit rules", "Ablations", "Sensitivity"].map(grows))
      .toEqual([true, true, true, false, false]);
  });
});

describe("the page's copy (PO, DEC-113)", () => {
  const ID = /\b[EGX]-[A-Z]?\d\b/;

  it("names every rule by its name, never its ID, outside the ID columns", async () => {
    renderRules("/rules/Z-9");
    await table("Sensitivity");
    const copy = [
      (await panel("How rules work")).textContent,
      ...[...document.querySelectorAll(".pm-caption, .pm-panel-note")].map((e) => e.textContent),
      ...bodyRows(await table("Ablations")).map((r) => r.textContent),
      ...bodyRows(await table("Sensitivity")).map((r) => r.textContent),
    ];
    expect(copy.filter((text) => ID.test(text ?? ""))).toEqual([]);
  });

  it("keeps the ID in each rule table's ID column", async () => {
    renderRules();
    expect(column(await table("Skip-week gates"), 1)).toEqual(["G-1", "G-2", "G-3", "G-4", "G-5"]);
  });
});
