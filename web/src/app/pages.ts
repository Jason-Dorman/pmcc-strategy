// The site's pages and their routes (UI-SPEC §7, DEC-73). The URL is the state: a page with a
// symbol carries it in its route, and the pages without one link back to the last symbol shown.
export type PageKey =
  | "thesis"
  | "compare"
  | "baseline"
  | "quant"
  | "wheel"
  | "wheel-review"
  | "live"
  | "rules"
  | "methodology"
  | "universe"
  | "data";

export type StrategyKey = "thesis" | "live" | "wheel" | "pmcc";

export interface Page {
  key: PageKey;
  label: string;
  symbol: "required" | "optional" | "none";
  strategy: StrategyKey;
}

export const PAGES: readonly Page[] = [
  { key: "thesis", label: "Overview", symbol: "none", strategy: "thesis" }, // TD-10, TD-28
  { key: "compare", label: "Compare", symbol: "required", strategy: "pmcc" },
  { key: "baseline", label: "Baseline", symbol: "required", strategy: "pmcc" },
  { key: "quant", label: "Quant", symbol: "required", strategy: "pmcc" },
  { key: "wheel", label: "Wheel", symbol: "required", strategy: "wheel" },
  { key: "wheel-review", label: "Wheel review", symbol: "required", strategy: "wheel" },
  { key: "live", label: "Overview", symbol: "required", strategy: "live" }, // LD-16, LD-38
  { key: "rules", label: "Rules", symbol: "none", strategy: "pmcc" },
  { key: "methodology", label: "Methodology", symbol: "optional", strategy: "pmcc" },
  { key: "universe", label: "Universe", symbol: "none", strategy: "pmcc" },
  { key: "data", label: "Data", symbol: "optional", strategy: "pmcc" },
];

export interface Strategy {
  key: StrategyKey;
  label: string;
  /** Its pages in its header menu, in order. Universe and Data are in none (PO, LD-36). */
  menu: readonly PageKey[];
}

/** The site's strategies, the volatility thesis first (PO, TD-28), then the forward test (PO,
 * LD-36): the header's menus and the home page's cards, in this order. */
export const STRATEGIES: readonly Strategy[] = [
  { key: "thesis", label: "Volatility Thesis", menu: ["thesis"] }, // PO, TD-28
  { key: "live", label: "Wheel forward test", menu: ["live"] }, // PO, LD-38
  { key: "wheel", label: "Wheel backtest", menu: ["wheel", "wheel-review"] },
  { key: "pmcc", label: "PMCC backtest",
    menu: ["compare", "baseline", "quant", "rules", "methodology"] },
];

export function pageOf(key: PageKey): Page {
  const page = PAGES.find((p) => p.key === key);
  if (!page) throw new Error(`no page ${key}`);
  return page;
}

export function strategyOf(page: Page): Strategy {
  const strategy = STRATEGIES.find((s) => s.key === page.strategy);
  if (!strategy) throw new Error(`no strategy ${page.strategy}`);
  return strategy;
}

/** The strategy each strategy page shows; the page never checks it otherwise (UI-SPEC §6.2). */
export const STRATEGY_PAGES = { baseline: "baseline_pmcc", quant: "quant_pmcc" } as const;

/** The wheel's own run, which the wheel pages show; its friction runs are `wheel--…` (WD-31). */
export const WHEEL_RUN = "wheel";

/** A wheel rule's row on the wheel review page (WD-22), where the wheel's rules are listed. */
export function wheelRulePath(symbol: string, ruleId: string): string {
  return `/wheel-review/${symbol}/${ruleId}`;
}

export function pagePath(page: Page, symbol: string | undefined): string {
  return page.symbol === "none" || symbol === undefined ? `/${page.key}` : `/${page.key}/${symbol}`;
}

/** The page and symbol a route path names, e.g. `/quant/NVDA`. */
export function parsePath(pathname: string): { page: Page | undefined; symbol: string | undefined } {
  const [key, second] = pathname.split("/").filter(Boolean);
  const page = PAGES.find((p) => p.key === key);
  return { page, symbol: page && page.symbol !== "none" ? second : undefined };
}
