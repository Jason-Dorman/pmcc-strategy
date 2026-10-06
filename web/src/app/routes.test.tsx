// Every route renders (P4-06's done-when), with the command bar and the manifest footer, over a
// stubbed fetch: the site's data comes only from its own origin.
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { IndexProvider } from "../data/IndexContext";
import { clearRunCache } from "../data/loader";
import { Data } from "../pages/Data";
import { fakeFetch, FILES, INDEX, run } from "../test/fixtures";
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
  ["/methodology", "Discovery"],
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

  it("shows the run's manifest in the footer, its commit linked", async () => {
    renderAt("/quant/NVDA");
    await screen.findByRole("table", { name: "Gate log" });
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

// ---- the adversarial review's regressions (P4-06 review, DEC-97) --------------------------------

describe("routes, after review", () => {
  it("shows no synthetic banner on real results", async () => {
    renderAt("/rules");
    await panelNames();
    await screen.findByText(/NVDA · hourly/);
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

  it("links a page without a symbol back to the last symbol shown", async () => {
    renderAt("/quant/QQQ");
    await panelNames();
    const nav = screen.getByRole("navigation", { name: "Pages" });
    fireEvent.click(within(nav).getByRole("link", { name: "Rules" }));
    await screen.findByRole("region", { name: "Entry rules" });
    const quant = within(screen.getByRole("navigation", { name: "Pages" })).getByRole("link", {
      name: "Quant",
    });
    expect(quant.getAttribute("href")).toBe("/quant/QQQ");
  });

  it("numbers only figure and table panels: the comparison's NAV panel is [1]", async () => {
    renderAt("/compare/NVDA");
    const nav = await screen.findByRole("region", { name: "NAV — baseline vs quant" });
    expect(within(nav).getByText("[1]")).toBeDefined();
    const purpose = screen.getByRole("region", { name: "Purpose" });
    expect(within(purpose).queryByText(/^\[\d+\]$/)).toBeNull();
  });

  it("shows both runs' manifests on the comparison page", async () => {
    renderAt("/compare/NVDA");
    await screen.findByRole("table", { name: "Headline" });
    const footer = screen.getByRole("contentinfo");
    expect(within(footer).getByText("NVDA baseline_pmcc")).toBeDefined();
    expect(within(footer).getByText("NVDA quant_pmcc")).toBeDefined();
  });

  it("shows every manifest field in the footer, the run time in ET", async () => {
    const dirty = run("quant_pmcc", ["gate_log"]);
    dirty.manifest = { ...dirty.manifest, git_dirty: true, data_manifest_hash: "9".repeat(64) };
    vi.stubGlobal("fetch", vi.fn(fakeFetch({ ...FILES, "data/NVDA/quant_pmcc.json": dirty })));
    renderAt("/quant/NVDA");
    await screen.findByRole("table", { name: "Gate log" });
    const footer = screen.getByRole("contentinfo").textContent ?? "";
    expect(footer).toContain("(dirty)");
    expect(footer).toContain("data 99999999");
    expect(footer).toContain("config cccccccc");
    expect(footer).toContain("lock ffffffff");
    expect(footer).toContain("ran 2026-09-30 14:42 ET");
    expect(footer).toContain("source lseg");
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

describe("the symbol select", () => {
  beforeEach(() => {
    // jsdom lacks what Radix's Select calls when it opens.
    Element.prototype.hasPointerCapture = () => false;
    Element.prototype.releasePointerCapture = () => undefined;
    Element.prototype.scrollIntoView = () => undefined;
  });

  it("keeps the page and swaps the symbol", async () => {
    renderAt("/quant/NVDA");
    await screen.findByRole("table", { name: "Gate log" });
    const trigger = screen.getByRole("combobox", { name: "Symbol" });
    fireEvent.pointerDown(trigger, { button: 0, ctrlKey: false, pointerType: "mouse" });
    fireEvent.click(await screen.findByRole("option", { name: "QQQ" }));
    expect(await screen.findAllByText("No results for QQQ / quant_pmcc.")).not.toHaveLength(0);
    const nav = screen.getByRole("navigation", { name: "Pages" });
    expect(within(nav).getByRole("link", { name: "Baseline" }).getAttribute("href")).toBe(
      "/baseline/QQQ",
    );
  });
});
