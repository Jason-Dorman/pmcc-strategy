// The wheel page (W4-01; PO, WD-22) over the fixture wheel: its readouts, the six panels in order,
// the portfolio at a chosen bar (from the URL, the step buttons and a ledger time), the cycle
// statistics, and the record tables' cells and links, rules in plain words (the copy rules the PO
// kept, WD-22).
import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearRunCache } from "../data/loader";
import { bodyRows, kv, panel, readout, renderWheel, rowAt, where } from "../test/page";

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

const BAR_2 = "2026-03-30T16:00:00-04:00";

async function portfolio(): Promise<Record<string, string>> {
  return kv(await screen.findByRole("table", { name: "Portfolio" }));
}

function bar(): string {
  return new URLSearchParams(where().split("?")[1] ?? "").get("bar") ?? "";
}

describe("readouts", () => {
  it("shows the run's NAV, P&L, return, Sharpe, drawdown, cycles and weeks", async () => {
    renderWheel();
    await screen.findByRole("table", { name: "Ledger" });
    expect(readout("Ending NAV").value).toBe("$25,502.50");
    expect(readout("P&L").value).toBe("+$502.50");
    expect(readout("P&L").hint).toContain("from $25,000.00");
    expect(readout("Return on starting cash").value).toBe("2.0%");
    expect(readout("Sharpe (annualized)").value).toBe("1.80");
    expect(readout("Sharpe (annualized)").hint).toContain("from 4 daily returns");
    expect(readout("Max drawdown").value).toBe("$107.50");
    expect(readout("Max drawdown").hint).toContain("0.4%");
    expect(readout("Complete cycles").value).toBe("1");
    expect(readout("Weeks sold / skipped").value).toBe("2 / 1");
    expect(readout("Weeks sold / skipped").hint).toContain("of 3");
  });
});

describe("the panels", () => {
  it("numbers the six panels in order", async () => {
    renderWheel();
    await screen.findByRole("table", { name: "Ledger" });
    const names = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(names).toEqual(["NAV", "Portfolio at a bar", "Cycle statistics", "Blotter",
                           "Gate log", "Ledger"]);
    expect(within(await panel("Ledger")).getByText("[6]")).toBeDefined();
  });

  it("draws the NAV chart over the ledger's bars", async () => {
    renderWheel();
    const nav = await panel("NAV");
    expect(await within(nav).findByRole("figure", {
      name: "NAV, with the stock, the held strike and the cost basis" })).toBeDefined();
    expect(within(nav).getByText("7 hourly bars")).toBeDefined();
    expect(nav.querySelector("svg")).not.toBeNull();
  });

  it("says when the symbol has no wheel run", async () => {
    renderWheel("/wheel/QQQ");
    const blotter = await panel("Blotter");
    expect(await within(blotter).findByText("No results for QQQ / wheel.")).toBeDefined();
    expect(readout("Ending NAV").value).toBe("—");
  });

  it("names no rule by its ID outside an ID column (PO, WD-22)", async () => {
    renderWheel();
    await screen.findByRole("table", { name: "Ledger" });
    expect(screen.getByRole("main").textContent).not.toMatch(/W-[A-Z]\d/);
  });
});

describe("the portfolio at a bar", () => {
  it("opens on the last bar", async () => {
    renderWheel();
    const p = await portfolio();
    expect(p.Bar).toBe("2026-04-13 16:00 ET");
    expect(p.Holding).toBe("Cash only, no position");
    expect(p["Short put"]).toBe("none");
    expect(p.NAV).toBe("$25,502.50");
  });

  it("shows the bar the URL names: cash reserved and free, and the short put", async () => {
    renderWheel(`/wheel/NVDA?bar=${encodeURIComponent(BAR_2)}`);
    const p = await portfolio();
    expect(p.Bar).toBe("2026-03-30 16:00 ET");
    expect(p.Holding).toBe("A short put, secured by cash");
    expect(p["NVDA last trade"]).toBe("$167.0000");
    expect(p.Cash).toBe("$25,142.50");
    expect(p["Reserved for the put (strike × 100)"]).toBe("$16,250.00");
    expect(p["Free cash"]).toBe("$8,892.50");
    expect(p["Short put"]).toContain("1 × NVDAP022616250.U^D26");
    expect(p["Short put"]).toContain("NVDA  260402P00162500");
    expect(p["Short put"]).toContain("strike $162.50 · expires 2026-04-02");
    expect(p["Short put"]).toContain("mark $1.2000 · value −$120.00 · delta −0.25");
    expect(p["Short call"]).toBe("none");
    expect(p.NAV).toBe("$25,022.50");
  });

  it("falls back to the last bar for a bar the ledger doesn't have", async () => {
    renderWheel("/wheel/NVDA?bar=2026-01-01T10%3A00%3A00-05%3A00");
    expect((await portfolio()).Bar).toBe("2026-04-13 16:00 ET");
  });

  it("shows shares at their mark under a call, with the cost basis and a stale mark flagged",
     async () => {
    renderWheel(`/wheel/NVDA?bar=${encodeURIComponent("2026-04-06T16:00:00-04:00")}`);
    const p = await portfolio();
    expect(p.Holding).toBe("Shares, with a covered call");
    expect(p["Shares, at their mark"]).toBe("100 sh × $163.0000 = $16,300.00");
    expect(p["Cost basis, per share"]).toBe("$159.9750");
    expect(p.Flags).toBe("stale_call");
    const table = await screen.findByRole("table", { name: "Portfolio" });
    const stale = within(table).getByTitle("last valid mid carried; never filled");
    expect(stale.textContent).toBe("$1.1000");
    expect(stale.className).toBe("pm-flag");
  });

  it("steps a bar either way, keeping it in the URL, and stops at the ends", async () => {
    renderWheel(`/wheel/NVDA?bar=${encodeURIComponent(BAR_2)}`);
    await portfolio();
    fireEvent.click(screen.getByRole("button", { name: "Next bar" }));
    await waitFor(async () => expect((await portfolio()).Bar).toBe("2026-04-02 16:00 ET"));
    expect(bar()).toBe("2026-04-02T16:00:00-04:00");
    fireEvent.click(screen.getByRole("button", { name: "Previous bar" }));
    fireEvent.click(screen.getByRole("button", { name: "Previous bar" }));
    await waitFor(async () => expect((await portfolio()).Bar).toBe("2026-03-30 10:00 ET"));
    expect(screen.getByRole("button", { name: "Previous bar" })).toHaveProperty("disabled", true);
  });

  it("shows the bar whose time is clicked in the ledger, and outlines its row", async () => {
    renderWheel();
    const ledger = await screen.findByRole("table", { name: "Ledger" });
    fireEvent.click(within(ledger).getByRole("button", { name: "2026-04-02 16:00 ET" }));
    await waitFor(async () => expect((await portfolio()).Holding).toBe("Shares, no call sold yet"));
    expect(bar()).toBe("2026-04-02T16:00:00-04:00");
    const chosen = bodyRows(ledger).filter((r) => r.getAttribute("aria-selected") === "true");
    expect(chosen.map((r) => r.className)).toEqual(["pm-target"]);
    expect(chosen[0]?.textContent).toContain("2026-04-02 16:00 ET");
  });
});

describe("cycle statistics", () => {
  it("counts the weeks, how each option ended, the cycles, the premium and the states",
     async () => {
    renderWheel();
    const c = kv(await screen.findByRole("table", { name: "Cycle statistics" }));
    expect(c["Weeks sold / skipped"]).toBe("2 / 1, of 3");
    expect(c["Skips, by reason"]).toBe("No liquid bar 1");
    expect(c["Puts sold"]).toBe("1: 0 expired, 1 assigned");
    expect(c["Calls sold"]).toBe("1: 0 expired, 1 called away");
    expect(c["Complete cycles (assigned, then called away)"]).toBe("1");
    expect(c["Premium collected, net of fees"]).toBe("$252.50");
    expect(c["Bars in short put"]).toBe("28.6%");
    expect(c["Bars in shares"]).toBe("14.3%");
  });

  it("links a skip's reason to its rule on the review page", async () => {
    renderWheel();
    const table = await screen.findByRole("table", { name: "Cycle statistics" });
    const link = within(table).getByRole("link", { name: "No liquid bar" });
    expect(link.getAttribute("href")).toBe("/wheel-review/NVDA/W-T1");
    expect(link.getAttribute("title")).toBe("Entry trigger: when → Entry trigger: then");
  });
});

describe("the blotter", () => {
  it("shows each trade's sides, fills and Trade P&L on the closing rows", async () => {
    renderWheel();
    const blotter = await screen.findByRole("table", { name: "Blotter" });
    expect(bodyRows(blotter)).toHaveLength(6);
    const assign = rowAt(blotter, 1);
    expect(assign.textContent).toContain("ASSIGN");
    expect(assign.textContent).toContain("+$142.50");
    const buy = rowAt(blotter, 2);
    expect(within(buy).getByText("BUY").className).toBe("pm-up");
    expect(buy.textContent).toContain("−$16,250.00");
    expect(rowAt(blotter, 5).textContent).toContain("+$250.00");
    expect(rowAt(blotter, 0).textContent).toContain("NVDA  260402P00162500");
  });

  it("names each rule by what it did, linked to its row on the review page", async () => {
    renderWheel();
    const blotter = await screen.findByRole("table", { name: "Blotter" });
    const link = within(rowAt(blotter, 1)).getByRole("link", { name: "Put assigned" });
    expect(link.getAttribute("href")).toBe("/wheel-review/NVDA/W-X2");
    const filter = screen.getByRole("button", { name: /Called away/ });
    fireEvent.click(filter);
    await waitFor(() => expect(bodyRows(blotter)).toHaveLength(2));
  });
});

describe("the gate log and the ledger", () => {
  it("shows each week's pick and outcome, a skip's reason linked", async () => {
    renderWheel();
    const log = await screen.findByRole("table", { name: "Gate log" });
    expect(rowAt(log, 0).textContent).toContain("delta −0.29 (target −0.30)");
    expect(rowAt(log, 0).textContent).toContain("mid $1.4250 · spread 0.70%");
    expect(rowAt(log, 1).textContent).toContain("Call");
    const skipped = rowAt(log, 2);
    expect(within(skipped).getByText("skipped").className).toBe("pm-skip");
    expect(within(skipped).getByRole("link", { name: "No liquid bar" })).toBeDefined();
  });

  it("filters the ledger by what the book holds, in words", async () => {
    renderWheel();
    const ledger = await screen.findByRole("table", { name: "Ledger" });
    fireEvent.click(screen.getByRole("button", { name: /^Covered call/ }));
    await waitFor(() => expect(bodyRows(ledger)).toHaveLength(2));
  });
});
