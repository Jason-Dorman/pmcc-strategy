// The frame every page shares (UI-SPEC §2): the command bar, the page-level banners, then the
// page. The symbol comes from the route; a page without one keeps the last symbol shown, so the
// nav can link back to it (UI-SPEC §7).
import { useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { CommandBar } from "../components/CommandBar";
import { WarningBanner } from "../components/WarningBanner";
import { useIndex } from "../data/IndexContext";
import type { Loaded } from "../data/state";
import type { Index } from "../types/generated/index";
import { pagePath, parsePath } from "./pages";

function ident(index: Index, symbol: string | undefined): string {
  const window = `${index.window.start} → ${index.window.end}`;
  return symbol ? `${symbol} · hourly · ${window}` : `hourly · ${window}`;
}

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

export function AppShell() {
  const index = useIndex();
  const navigate = useNavigate();
  const { page, symbol: routed } = parsePath(useLocation().pathname);
  const [last, setLast] = useState<string | undefined>(undefined);
  const symbols = index.kind === "ready" ? index.value.symbols.map((s) => s.symbol) : [];
  const symbol = routed ?? last ?? symbols[0];
  if (routed !== undefined && routed !== last) setLast(routed);

  const onSymbol = (next: string) => {
    setLast(next);
    if (page && page.symbol !== "none") navigate(pagePath(page, next));
  };
  return (
    <>
      <CommandBar
        ident={index.kind === "ready" ? ident(index.value, symbol) : ""}
        current={page}
        symbol={symbol}
        symbols={symbols}
        onSymbol={onSymbol}
      />
      <Banners index={index} />
      <Outlet />
    </>
  );
}
