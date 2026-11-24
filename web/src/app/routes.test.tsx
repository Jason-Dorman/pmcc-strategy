// Every route renders (P4-06's done-when), with the command bar and no footer (PO, DEC-121), over
// a stubbed fetch: the site's data comes only from its own origin.
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { IndexProvider } from "../data/IndexContext";
import { clearRunCache } from "../data/loader";
import { Data } from "../pages/Data";
import { fakeFetch, FILES, INDEX } from "../test/fixtures";
import { AppRoutes } from "./routes";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <IndexProvider>
        <AppRoutes />
      </IndexProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(fakeFetch()));
});
afterEach(() => {
  cleanup();
  clearRunCache();
  vi.unstubAllGlobals();
});

async function panelNames(): Promise<string[]> {
  await screen.findByRole("main");
  return screen.queryAllByRole("region").map((r) => r.getAttribute("aria-label") ?? "");
}

const ROUTES: [string, string][] = [
  ["/compare/NVDA", "NAV — baseline vs quant"],
  ["/baseline/NVDA", "Blotter"],
  ["/quant/NVDA", "Gate log"],
  ["/wheel/NVDA", "Portfolio at a bar"],
  ["/wheel-review/NVDA", "Verdicts"],
  ["/wheel-review/NVDA/W-X2", "Rules"],
  ["/live/NVDA", "Nightly run log"],
  ["/thesis", "Daily tracker"],
  ["/rules", "Entry rules"],
  ["/rules/X-S3", "Exit rules"],
  ["/methodology", "Discovery"],
  ["/methodology/NVDA", "Fill model"],
  ["/universe", "Symbol suitability"],
  ["/data", "Data connection required"],
  ["/data/NVDA", "Data connection required"],
];

describe("routes", () => {
  it.each(ROUTES)("%s renders its panels", async (path, panel) => {
    renderAt(path);
    expect(await screen.findByRole("region", { name: panel })).toBeDefined();
    expect(screen.getByText("Algo Trading Strategies")).toBeDefined();
    expect(screen.queryByRole("contentinfo")).toBeNull();
  });

  it("opens the home page from #/: a headline, then a tile per strategy, the thesis first (LD-36, "
     + "LD-37, TD-28)", async () => {
    renderAt("/");
    expect(await screen.findByRole("heading", { level: 1 })).toBeDefined();
    const tiles = screen.getAllByRole("region").map((r) => r.querySelector("h2")?.textContent);
    expect(tiles).toEqual(["Volatility Thesis", "Wheel forward test", "Wheel backtest",
                           "PMCC backtest"]);
    expect(document.querySelector(".pm-crumb")).toBeNull();
    const chips = (name: string) => within(screen.getByRole("list", { name: `${name} pages` }))
      .getAllByRole("link").map((a) => [a.textContent, a.getAttribute("href")]);
    expect(chips("Volatility Thesis")).toEqual([["Overview →", "/thesis"]]);
    expect(chips("Wheel forward test")).toEqual([["Overview →", "/live/NVDA"]]);
    expect(chips("Wheel backtest")).toEqual([["Wheel →", "/wheel/NVDA"],
                                             ["Wheel review →", "/wheel-review/NVDA"]]);
    expect(chips("PMCC backtest")).toEqual([
      ["Compare →", "/compare/NVDA"], ["Baseline →", "/baseline/NVDA"],
      ["Quant →", "/quant/NVDA"], ["Rules →", "/rules"],
      ["Methodology →", "/methodology/NVDA"]]);
    const name = within(screen.getByRole("region", { name: "PMCC backtest" }))
      .getByRole("heading", { level: 2 });
    expect(within(name).getByRole("link").getAttribute("href")).toBe("/compare/NVDA");
  });

  it("gives each tile its figure from its own file, and says when the live wheel last ran",
     async () => {
    renderAt("/");
    const live = await screen.findByRole("region", { name: "Wheel forward test" });
    expect(await within(live).findByText("Selling a $155 put")).toBeDefined(); // LSEG's pick (LD-35)
    expect(live.textContent).toContain("Delta −0.32 · IV 88.2% · expires Nov 20");
    expect(screen.getByText(/Last nightly run 2026-11-17 22:00 ET/)).toBeDefined();
    const wheel = screen.getByRole("region", { name: "Wheel backtest" });
    expect(within(wheel).getByText("+$4,171.50")).toBeDefined();
    expect(wheel.textContent).toContain("16.7% · Sharpe 1.57");
    expect(wheel.textContent).toContain("Backtest · Mar 30 – Sep 25");
    const pmcc = screen.getByRole("region", { name: "PMCC backtest" });
    expect(await within(pmcc).findByText("+$3,672.50")).toBeDefined();
    expect(pmcc.textContent).toContain("24.5% baseline · quant +$3,303.50");
  });

  it("says so on the live tile when there's no open order", async () => {
    vi.stubGlobal("fetch", vi.fn(fakeFetch({ ...FILES,
      "data/live.json": { ...(FILES["data/live.json"] as object), orders: [] } })));
    renderAt("/");
    const live = await screen.findByRole("region", { name: "Wheel forward test" });
    expect(await within(live).findByText("No trade open")).toBeDefined();
  });

  it("marks the current strategy, and the current page in its menu", async () => {
    renderAt("/quant/NVDA");
    await panelNames();
    const nav = screen.getByRole("navigation", { name: "Strategies" });
    const pmcc = within(nav).getByRole("button", { name: /PMCC backtest/ });
    expect(pmcc.classList.contains("on")).toBe(true);
    expect(within(nav).getByRole("button", { name: /Wheel backtest/ }).classList.contains("on"))
      .toBe(false);
    fireEvent.click(pmcc);
    const quant = within(nav).getByRole("link", { name: "Quant" });
    expect(quant.getAttribute("aria-current")).toBe("page");
  });

  it("names the page's strategy above it", async () => {
    renderAt("/wheel-review/NVDA");
    await panelNames();
    expect(document.querySelector(".pm-crumb")?.textContent).toBe("Wheel backtest›Wheel review");
  });

  it("shows the quant page's optional sections", async () => {
    renderAt("/quant/NVDA");
    await screen.findByRole("table", { name: "Gate log" });
    expect(await panelNames()).toEqual(expect.arrayContaining(
      ["Gate log", "Position Greeks", "Greek attribution"]));
  });

  it("leaves the gate log off the baseline's page, which renumbers (DEC-120)", async () => {
    renderAt("/baseline/NVDA");
    await screen.findByRole("table", { name: "Blotter" });
    const names = await panelNames();
    expect(names).not.toContain("Gate log");
    expect(names).toEqual(expect.arrayContaining(["Position Greeks", "Greek attribution"]));
    const ledger = screen.getByRole("region", { name: "Ledger" });
    expect(within(ledger).getByText("[6]")).toBeDefined();
  });

  it("says in the panel when a symbol has no results", async () => {
    renderAt("/quant/QQQ");
    expect(await screen.findAllByText("No results for QQQ / quant_pmcc.")).not.toHaveLength(0);
  });

  it("shows a schema mismatch banner", async () => {
    const stale = { "data/index.json": { ...INDEX, schema_version: 1 } };
    vi.stubGlobal("fetch", vi.fn(fakeFetch(stale)));
    renderAt("/rules");
    expect((await screen.findByRole("alert")).textContent).toContain("Schema mismatch");
  });

  it("shows the synthetic-data banner on synthetic results", async () => {
    const symbols = INDEX.symbols.map((s) => ({
      ...s,
      runs: s.runs.map((r) => ({ ...r, data_source: "synthetic" as const })),
    }));
    vi.stubGlobal("fetch", vi.fn(fakeFetch({ "data/index.json": { ...INDEX, symbols } })));
    renderAt("/rules");
    const banner = await screen.findByRole("alert");
    expect(banner.textContent).toBe("Synthetic data — not market results.");
  });
});

// ---- the adversarial review's regressions (P4-06 review, DEC-97) --------------------------------

describe("routes, after review", () => {
  it("shows no synthetic banner on real results", async () => {
    renderAt("/rules");
    await panelNames();
    await screen.findByRole("table", { name: /entry rules/i });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the synthetic banner while any run is synthetic, among real ones", async () => {
    const symbols = INDEX.symbols.map((s) => ({
      ...s,
      runs: s.runs.map((r, i) => (i === 0 ? { ...r, data_source: "synthetic" as const } : r)),
    }));
    vi.stubGlobal("fetch", vi.fn(fakeFetch({ ...FILES, "data/index.json": { ...INDEX, symbols } })));
    renderAt("/quant/NVDA");
    expect((await screen.findByRole("alert")).textContent).toBe(
      "Synthetic data — not market results.",
    );
  });

  it("links the menus to the route's symbol, and from a page without one to the index's",
     async () => {
    renderAt("/quant/QQQ");
    await panelNames();
    const nav = () => screen.getByRole("navigation", { name: "Strategies" });
    fireEvent.click(within(nav()).getByRole("button", { name: /PMCC backtest/ }));
    expect(within(nav()).getByRole("link", { name: "Baseline" }).getAttribute("href"))
      .toBe("/baseline/QQQ");
    fireEvent.click(within(nav()).getByRole("link", { name: "Rules" }));
    await screen.findByRole("region", { name: "Entry rules" });
    fireEvent.click(within(nav()).getByRole("button", { name: /PMCC backtest/ }));
    expect(within(nav()).getByRole("link", { name: "Quant" }).getAttribute("href"))
      .toBe("/quant/NVDA");
  });

  it("numbers only figure and table panels: the comparison's NAV panel is [1]", async () => {
    renderAt("/compare/NVDA");
    const nav = await screen.findByRole("region", { name: "NAV — baseline vs quant" });
    expect(within(nav).getByText("[1]")).toBeDefined();
    const purpose = screen.getByRole("region", { name: "Purpose" });
    expect(within(purpose).queryByText(/^\[\d+\]$/)).toBeNull();
  });
});

describe("the Data page", () => {
  function renderData(hostname: string) {
    return render(
      <MemoryRouter>
        <IndexProvider>
          <Data hostname={hostname} />
        </IndexProvider>
      </MemoryRouter>,
    );
  }

  it("says a data connection is required on github.io", async () => {
    renderData("jason-dorman.github.io");
    expect(await screen.findByText("Data connection required.")).toBeDefined();
    expect(screen.queryByText(/Built at P7-06/)).toBeNull();
  });

  it("shows the local placeholder anywhere else", async () => {
    renderData("localhost");
    expect(await screen.findByText(/Built at P7-06/)).toBeDefined();
    expect(screen.queryByText("Data connection required.")).toBeNull();
  });
});

describe("the strategy menus (PO, LD-36)", () => {
  async function bar() {
    renderAt("/quant/NVDA");
    await screen.findByRole("table", { name: "Gate log" });
    return screen.getByRole("navigation", { name: "Strategies" });
  }

  it("list the strategies, the thesis first, then the live wheel, each a link for its one page "
     + "(TD-28)", async () => {
    const nav = await bar();
    expect([...nav.children].map((c) => c.textContent)).toEqual(
      ["Volatility Thesis", "Wheel forward test", "Wheel backtest▾", "PMCC backtest▾"]);
    expect(within(nav).getByRole("link", { name: "Wheel forward test" }).getAttribute("href"))
      .toBe("/live/NVDA");
    expect(within(nav).getByRole("link", { name: "Volatility Thesis" }).getAttribute("href"))
      .toBe("/thesis");
  });

  it("keep Universe and Data out of every menu, and show no symbol picker or ident",
     async () => {
    const nav = await bar();
    for (const button of within(nav).getAllByRole("button")) fireEvent.click(button);
    const labels = within(nav).getAllByRole("link").map((a) => a.textContent);
    expect(labels).toEqual(["Volatility Thesis", "Wheel forward test", "Wheel", "Wheel review",
                            "Compare", "Baseline", "Quant", "Rules", "Methodology"]);
    expect(screen.queryByRole("combobox", { name: "Symbol" })).toBeNull();
    expect(screen.queryByText(/hourly ·/)).toBeNull();
  });

  it("open on a click, and close on Escape, a click outside, or a link", async () => {
    const nav = await bar();
    const wheel = within(nav).getByRole("button", { name: /Wheel backtest/ });
    expect(wheel.getAttribute("aria-expanded")).toBe("false");
    expect(within(nav).queryByRole("link", { name: "Wheel review" })).toBeNull();
    fireEvent.click(wheel);
    expect(wheel.getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(wheel.getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(wheel);
    fireEvent.click(wheel);
    fireEvent.pointerDown(document.body);
    expect(within(nav).queryByRole("link", { name: "Wheel review" })).toBeNull();
    fireEvent.click(wheel);
    fireEvent.click(within(nav).getByRole("link", { name: "Wheel review" }));
    expect(await screen.findByRole("region", { name: "Verdicts" })).toBeDefined();
    expect(within(nav).queryByRole("link", { name: "Wheel review" })).toBeNull();
  });

  it("lead home from the wordmark", async () => {
    await bar();
    fireEvent.click(screen.getByRole("link", { name: "Algo Trading Strategies" }));
    expect(await screen.findByRole("region", { name: "Wheel forward test" })).toBeDefined();
  });
});
