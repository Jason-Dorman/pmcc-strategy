// The Trade rules page (P7-03, UI-SPEC §6.3) over the fixture rules.json: the panels in order;
// the entry, gate and exit tables with both strategies' live values and each rule's rationale;
// the target row of `#/rules/<ID>`; how rules work, its differences read from the rules; the
// ablations and the sensitivity runs in words; and the in-panel state when rules.json is missing.
import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearRunCache } from "../data/loader";
import { FILES, RULES } from "../test/fixtures";
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

  it("reads each rule's title and summary, Same where quant runs the baseline's rule (PO, DEC-114)",
     async () => {
    renderRules();
    const t = await table("Entry rules");
    expect(cells(ruleRow(t, "E-T1")).slice(2)).toEqual([
      "When do we enter?", "On the first bar with a spread within 3% (long) or 10% (short).",
      "Same"]);
    expect(cells(ruleRow(t, "E-L3")).slice(2)).toEqual([
      "Which long call do we buy?", "The call with delta closest to 0.80.",
      "Among deltas 0.70 to 0.90, the lowest extrinsic ÷ delta."]);
  });

  it("keeps the rule stated exactly on the summary's hover", async () => {
    renderRules();
    const t = await table("Entry rules");
    const summary = within(ruleRow(t, "E-L3")).getByText("The call with delta closest to 0.80.");
    expect(summary.getAttribute("title")).toBe("E-L3 condition → E-L3 action");
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

  it("states when each gate skips the week, with its live value", async () => {
    renderRules();
    const t = await table("Skip-week gates");
    expect(cells(ruleRow(t, "G-4")).slice(2, 4)).toEqual([
      "Volatility risk premium", "Front-week ATM IV ÷ RV20 is below 1.00."]);
    expect(cells(ruleRow(t, "G-1")).slice(2, 4)).toEqual([
      "No tradable quote", "The selected short never passes the entry trigger on Monday."]);
  });
});

describe("exit rules", () => {
  it("gives each exit and what happens, and its reasoning's paragraphs", async () => {
    renderRules();
    const t = await table("Exit rules");
    expect(column(t, 1)).toEqual(["X-S1", "X-S3", "X-L1", "X-L2", "X-E1"]);
    const headers = within(t).getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["Why", "ID", "Rule", "What happens"]);
    expect(cells(ruleRow(t, "X-S3")).slice(2)).toEqual([
      "Friday risk check",
      "On the last session by 15:00 ET, buy the short back if spot is within 0.25 × EM of it."]);
    fireEvent.click(within(t).getByRole("button", { name: "Rationale for X-S3" }));
    const paragraphs = within(t).getByText("The Friday buffer.").closest("td")
      ?.querySelectorAll("p");
    expect([...(paragraphs ?? [])].map((p) => p.textContent))
      .toEqual(["Why no rolls: next Monday's sale already is the roll.", "The Friday buffer."]);
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
  it("gives the order of operations as numbered steps (PO, DEC-114)", async () => {
    renderRules();
    const how = await panel("How rules work");
    await within(how).findByText(/Every decision is made/);
    const steps = within(how).getAllByRole("listitem").map((li) => li.textContent);
    expect(steps).toEqual([
      "Check whether the long call needs to be exited or replaced.",
      "Check whether the short call needs to be closed.",
      "On the first trading day of the week, sell a new short call if no skip-week gate blocks " +
      "the trade."]);
    expect(how.textContent).toContain("we stop at the first one and log exactly what triggered it");
  });

  it("says how the strategies differ, the count of quant's filters read from the rules", async () => {
    renderRules();
    const how = await panel("How rules work");
    await within(how).findByText(/manage positions the same way/);
    expect(how.textContent).toContain(
      "Baseline PMCC and Quant PMCC manage positions the same way. They differ only in how they " +
      "choose the long and short calls, plus three extra filters used by Quant PMCC. That means " +
      "any performance difference comes from contract selection and trade filtering, not " +
      "different exit rules.");
  });

  it("names each rule that differs where the rules don't bear the sentence out", async () => {
    const quant = RULES.strategies.find((s) => s.id === "quant_pmcc");
    if (!quant) throw new Error("fixture lacks quant");
    const exitsDiffer = { ...quant, rules: quant.rules.map((r) =>
      (r.id === "X-S1" ? { ...r, summary: "Hold to expiry." } : r)) };
    const rules = { ...RULES, strategies: RULES.strategies.map((s) =>
      (s.id === "quant_pmcc" ? exitsDiffer : s)) };
    renderRules("/rules", { ...FILES, "data/rules.json": rules });
    const how = await panel("How rules work");
    await within(how).findByText(/differ in/);
    expect(how.textContent).not.toContain("manage positions the same way");
    expect(within(how).getByRole("link", { name: "Take profit" }).getAttribute("href"))
      .toBe("/rules/X-S1");
  });
});

describe("ablations", () => {
  it("names each layer removed and what replaced it", async () => {
    renderRules();
    const t = await table("Ablations");
    expect(bodyRows(t).map(cells)).toEqual([
      ["A1: quant with the baseline long leg", "Long leg expiry",
       "The monthly expiry closest to 180 days out."],
      ["A1: quant with the baseline long leg", "Long leg strike",
       "The call with delta closest to 0.80."],
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
