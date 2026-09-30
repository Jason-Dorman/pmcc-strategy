// The site's pages and their routes (UI-SPEC §7, DEC-73). The URL is the state: a page with a
// symbol carries it in its route, and the pages without one link back to the last symbol shown.
export type PageKey =
  | "compare"
  | "baseline"
  | "quant"
  | "rules"
  | "methodology"
  | "universe"
  | "data";

export interface Page {
  key: PageKey;
  label: string;
  symbol: "required" | "optional" | "none";
}

export const PAGES: readonly Page[] = [
  { key: "compare", label: "Compare", symbol: "required" },
  { key: "baseline", label: "Baseline", symbol: "required" },
  { key: "quant", label: "Quant", symbol: "required" },
  { key: "rules", label: "Rules", symbol: "none" },
  { key: "methodology", label: "Methodology", symbol: "optional" },
  { key: "universe", label: "Universe", symbol: "none" },
  { key: "data", label: "Data", symbol: "optional" },
];

/** The strategy each strategy page shows; the page never checks it otherwise (UI-SPEC §6.2). */
export const STRATEGY_PAGES = { baseline: "baseline_pmcc", quant: "quant_pmcc" } as const;

export function pagePath(page: Page, symbol: string | undefined): string {
  return page.symbol === "none" || symbol === undefined ? `/${page.key}` : `/${page.key}/${symbol}`;
}

/** The page and symbol a route path names, e.g. `/quant/NVDA`. */
export function parsePath(pathname: string): { page: Page | undefined; symbol: string | undefined } {
  const [key, second] = pathname.split("/").filter(Boolean);
  const page = PAGES.find((p) => p.key === key);
  return { page, symbol: page && page.symbol !== "none" ? second : undefined };
}
