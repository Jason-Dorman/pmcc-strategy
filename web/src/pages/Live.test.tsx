// The live page (L4-01; UI-SPEC §6 › Live) over the fixture `live.json`: the readouts from the
// latest night, the algorithm with its rules, the open orders and the file itself, Sanji's files
// before he writes them, and the run log, newest first, with each pick's quote (PO, LD-15).
import { cleanup, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearRunCache } from "../data/loader";
import { FILES } from "../test/fixtures";
import { LIVE, QUOTED } from "../test/liveFixtures";
import { bodyRows, column, panel, readout, renderLive, rowAt, sortBy } from "../test/page";
import { orderFile } from "./live/sections";

afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

describe("readouts", () => {
  it("read the latest night: a failed run names its rule and says no order was made", async () => {
    renderLive();
    await screen.findByRole("table", { name: "Nightly run log" });
    expect(readout("State").value).toBe("—");
    expect(readout("Next session").value).toBe("2026-11-18");
    expect(readout("Tonight's decision").value).toBe("Failed");
    expect(readout("Tonight's decision").hint).toMatch(/^L-B1: Sanji's prices end/);
    expect(readout("Last run").value).toBe("2026-11-17 22:00 ET");
    expect(readout("Last run").hint).toContain("it failed, so no new order");
  });

  it("go by the row's outcome: an order row without a pick still reads as an order", async () => {
    const row = { ...QUOTED, pick: null };
    renderLive("/live/NVDA", { ...FILES, "data/live.json": { ...LIVE, runs: [row] } });
    await screen.findByRole("table", { name: "Nightly run log" });
    expect(readout("Tonight's decision").value).toBe("Order");
    expect(readout("Tonight's decision").hint).toMatch(/^L-O1: sell 1 155.00 put/);
  });

  it("show an order night's option and its delta", async () => {
    renderLive("/live/NVDA", { ...FILES, "data/live.json": { ...LIVE, runs: [QUOTED] } });
    await screen.findByRole("table", { name: "Nightly run log" });
    expect(readout("State").value).toBe("Cash");
    expect(readout("Cash").value).toBe("$25,000.00");
    expect(readout("Cost basis").value).toBe("—");
    expect(readout("Tonight's decision").value).toBe("Sell 1 put");
    expect(readout("Tonight's decision").hint).toBe(
      "$155 put, 2026-11-20; delta −0.32 at the close");
  });
});

describe("the panels", () => {
  it("lead with the algorithm, unnumbered, then the orders, Sanji's files and the log", async () => {
    renderLive();
    await screen.findByRole("table", { name: "Nightly run log" });
    const names = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(names).toEqual(["The algorithm", "Open orders", "Positions", "Fills",
                           "Nightly run log"]);
    expect(within(await panel("Open orders")).getByText("[1]")).toBeDefined();
    expect(within(await panel("Nightly run log")).getByText("[4]")).toBeDefined();
  });

  it("say why the wheel, from the backtest, and link to its review", async () => {
    renderLive();
    const algorithm = await panel("The algorithm");
    await within(algorithm).findByRole("table", { name: "Live wheel rules" });
    expect(algorithm.textContent).toContain("+$4,171.50 (16.7%) on $25,000.00");
    expect(algorithm.textContent).toContain("Sharpe of 1.57 against the baseline PMCC's 1.24");
    const link = within(algorithm).getByRole("link", { name: "The wheel's backtest review" });
    expect(link.getAttribute("href")).toBe("/wheel-review/NVDA");
    const rules = within(algorithm).getByRole("table", { name: "Live wheel rules" });
    expect(column(rules, 0)).toEqual(["L-B1", "L-P3", "L-O1"]);
  });

  it("list the open orders, and the file as it's written", async () => {
    renderLive();
    const orders = await screen.findByRole("table", { name: "Open orders" });
    const cells = [...rowAt(orders, 0).querySelectorAll("td")].map((c) => c.textContent);
    expect(cells).toEqual(["wheel-2026-11-16-P-155", "2026-11-16", "Sell to open (SHT)", "1",
                           "put", "2026-11-20", "155", "Limit, mid", "open"]);
    const file = (await panel("Open orders")).querySelector("pre")?.textContent ?? "";
    expect(JSON.parse(file)).toEqual([{ id: "wheel-2026-11-16-P-155", for: "2026-11-16",
      order_type: "lmt", action: "SHT", qty: 1, underlying: 4815747, contract: "put",
      expiry: "2026-11-20", strike: "155", ref: "open", lmt_prc: "mid" }]);
  });

  it("write the file in the order page's field order, absent fields left out", () => {
    const [order] = LIVE.orders;
    if (!order) throw new Error("no order");
    const shares = { ...order, contract: "underlying", expiry: null, strike: null, ref: null };
    expect(Object.keys((JSON.parse(orderFile([shares])) as object[])[0] ?? {})).toEqual(
      ["id", "for", "order_type", "action", "qty", "underlying", "contract", "lmt_prc"]);
    expect(orderFile([])).toBe("[]");
  });

  it("say so when there are no open orders", async () => {
    renderLive("/live/NVDA", { ...FILES, "data/live.json": { ...LIVE, orders: [] } });
    const orders = await panel("Open orders");
    expect(await within(orders).findByText("No open orders tonight.")).toBeDefined();
  });

  it("show Sanji's files as he writes them, and say so before he does", async () => {
    renderLive();
    expect(await within(await panel("Positions")).findByText("No positions yet.")).toBeDefined();
    expect(within(await panel("Fills")).getByText("No fills yet.")).toBeDefined();
    cleanup();
    clearRunCache();
    const text = '[{"symbol": "NVDA", "cash": 24876.123456789}]\n'; // his key order, his digits
    renderLive("/live/NVDA", { ...FILES, "data/live.json": {
      ...LIVE, fills: { path: "mkt/fills.json", text } } });
    const fills = await panel("Fills");
    const file = await within(fills).findByLabelText("mkt/fills.json");
    expect(file.textContent).toBe(text);
  });

  it("sort strikes by value, not as text", async () => {
    const at = (strike: string) => ({ ...LIVE.orders[0], id: `o-${strike}`, strike });
    const orders = [at("155"), at("92.5"), at("1000")];
    renderLive("/live/NVDA", { ...FILES, "data/live.json": { ...LIVE, orders } });
    const table = await screen.findByRole("table", { name: "Open orders" });
    await sortBy(table, /Strike/);
    expect(column(table, 6)).toEqual(["92.5", "155", "1000"]);
  });

  it("log every night, newest first, with each pick's quote and a dash before it was kept",
     async () => {
    renderLive();
    const log = await screen.findByRole("table", { name: "Nightly run log" });
    expect(bodyRows(log)).toHaveLength(3);
    expect(column(log, 4)).toEqual(["Failed", "Order", "Order"]);
    expect(column(log, 7)).toEqual(["", "$155 put, 2026-11-20", "$155 put, 2026-11-20"]);
    expect(column(log, 10)).toEqual(["", "$2.4100", "—"]); // bid
    expect(column(log, 12)).toEqual(["", "$2.4350", "—"]); // mid
    expect(column(log, 13)).toEqual(["", "2.1%", "—"]); // spread
  });

  it("say when the route's symbol isn't the one the live wheel trades", async () => {
    renderLive("/live/QQQ");
    const orders = await panel("Open orders");
    expect(await within(orders).findByText("The live wheel trades NVDA, not QQQ.")).toBeDefined();
  });

  it("say when the export wrote no live file", async () => {
    const files = { ...FILES, "data/index.json": { ...(FILES["data/index.json"] as object),
                                                   live: null } };
    renderLive("/live/NVDA", files);
    const orders = await panel("Open orders");
    expect(await within(orders).findByText("No results for the live wheel.")).toBeDefined();
  });
});
