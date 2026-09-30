// Every route renders (P4-06's done-when), with the command bar and the manifest footer, over a
// stubbed fetch: the site's data comes only from its own origin.
import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { IndexProvider } from "../data/IndexContext";
import { clearRunCache } from "../data/loader";
import { fakeFetch, INDEX } from "../test/fixtures";
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
  await screen.findByRole("contentinfo");
  return screen.queryAllByRole("region").map((r) => r.getAttribute("aria-label") ?? "");
}

const ROUTES: [string, string][] = [
  ["/compare/NVDA", "NAV — baseline vs quant"],
  ["/baseline/NVDA", "Blotter"],
  ["/quant/NVDA", "Gate log"],
  ["/rules", "Entry rules"],
  ["/rules/X-S3", "Exit rules"],
  ["/methodology", "Data coverage"],
  ["/methodology/NVDA", "Stated assumptions"],
  ["/universe", "Symbol suitability"],
  ["/data", "Data connection required"],
  ["/data/NVDA", "Data connection required"],
];

describe("routes", () => {
  it.each(ROUTES)("%s renders its panels", async (path, panel) => {
    renderAt(path);
    expect(await screen.findByRole("region", { name: panel })).toBeDefined();
    expect(screen.getByText("PMCC Backtest")).toBeDefined();
    expect(screen.getByRole("contentinfo")).toBeDefined();
  });

  it("opens the first symbol's comparison page from #/", async () => {
    renderAt("/");
    expect(await panelNames()).toContain("NAV — baseline vs quant");
    const window = `${INDEX.window.start} → ${INDEX.window.end}`;
    expect(screen.getByText(`NVDA · hourly · ${window}`)).toBeDefined();
  });

  it("marks the current page in the nav", async () => {
    renderAt("/quant/NVDA");
    await panelNames();
    const nav = screen.getByRole("navigation", { name: "Pages" });
    const quant = within(nav).getByRole("link", { name: "Quant" });
    expect(quant.getAttribute("aria-current")).toBe("page");
  });

  it("links the pages without a symbol back to the last symbol shown", async () => {
    renderAt("/rules");
    await panelNames();
    const nav = screen.getByRole("navigation", { name: "Pages" });
    expect(within(nav).getByRole("link", { name: "Quant" }).getAttribute("href")).toBe(
      "/quant/NVDA",
    );
  });

  it("shows the quant page's optional sections", async () => {
    renderAt("/quant/NVDA");
    await screen.findByText(/1 weeks/);
    expect(await panelNames()).toEqual(expect.arrayContaining(["Gate log", "Greek attribution"]));
  });

  it("leaves them off the baseline's page, which renumbers", async () => {
    renderAt("/baseline/NVDA");
    await screen.findAllByText(/2 rows/);
    const names = await panelNames();
    expect(names).not.toContain("Gate log");
    expect(names).not.toContain("Greek attribution");
    const ledger = screen.getByRole("region", { name: "Ledger" });
    expect(within(ledger).getByText("[6]")).toBeDefined();
  });

  it("shows the run's manifest in the footer, its commit linked", async () => {
    renderAt("/quant/NVDA");
    await screen.findByText(/1 weeks/);
    const footer = screen.getByRole("contentinfo");
    expect(within(footer).getByText("aaaaaaa").getAttribute("href")).toBe(
      `https://github.com/Jason-Dorman/pmcc-strategy/commit/${"a".repeat(40)}`,
    );
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
