// The frame every page shares (UI-SPEC §2): the command bar, the page's strategy and name, the
// page-level banners, then the page. Every strategy runs on one symbol, so there is no symbol
// picker (PO, LD-36): the symbol comes from the route, or is the index's first.
import { Outlet, useLocation } from "react-router-dom";

import { CommandBar } from "../components/CommandBar";
import { WarningBanner } from "../components/WarningBanner";
import { useIndex } from "../data/IndexContext";
import type { Loaded } from "../data/state";
import type { Index } from "../types/generated/index";
import { parsePath, strategyOf, type Page } from "./pages";

function synthetic(index: Index): boolean {
  return index.symbols.some((s) => s.runs.some((r) => r.data_source === "synthetic"));
}

function Banners({ index }: { index: Loaded<Index> }) {
  if (index.kind === "mismatch") {
    return <WarningBanner>Schema mismatch: {index.message}. Rebuild the site.</WarningBanner>;
  }
  if (index.kind === "error") {
    return <WarningBanner>The site&apos;s data didn&apos;t load: {index.message}</WarningBanner>;
  }
  if (index.kind === "ready" && synthetic(index.value)) {
    return <WarningBanner>Synthetic data — not market results.</WarningBanner>; // DEC-74
  }
  return null;
}

/** `PMCC backtest › Quant`: which strategy a page belongs to (PO, LD-36). */
function Crumb({ page }: { page: Page }) {
  return (
    <div className="pm-crumb">
      <span>{strategyOf(page).label}</span>
      <span className="pm-crumb-sep" aria-hidden="true">›</span>
      <span>{page.label}</span>
    </div>
  );
}

export function AppShell() {
  const index = useIndex();
  const { page, symbol: routed } = parsePath(useLocation().pathname);
  const symbol = routed ?? (index.kind === "ready" ? index.value.symbols[0]?.symbol : undefined);
  return (
    <>
      <CommandBar current={page} symbol={symbol} />
      {page && <Crumb page={page} />}
      <Banners index={index} />
      <Outlet />
    </>
  );
}
