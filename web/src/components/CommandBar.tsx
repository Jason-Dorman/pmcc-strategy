// The command bar (UI-SPEC §2): the wordmark on the left; on the right the identity line, the nav
// (the current page amber) and the symbol select.
import { Link } from "react-router-dom";

import { PAGES, pagePath, type Page } from "../app/pages";
import { WORDMARK } from "../app/site";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";

export interface CommandBarProps {
  ident: string;
  current: Page | undefined;
  symbol: string | undefined;
  symbols: readonly string[];
  onSymbol: (symbol: string) => void;
}

export function CommandBar({ ident, current, symbol, symbols, onSymbol }: CommandBarProps) {
  return (
    <header className="pm-bar">
      <div className="pm-wordmark">{WORDMARK}</div>
      <div className="pm-bar-right">
        <div className="pm-ident">{ident}</div>
        <nav className="pm-nav" aria-label="Pages">
          {PAGES.map((page) => (
            <Link
              key={page.key}
              to={pagePath(page, symbol)}
              className={page.key === current?.key ? "on" : undefined}
              aria-current={page.key === current?.key ? "page" : undefined}
            >
              {page.label}
            </Link>
          ))}
        </nav>
        {symbols.length > 0 && (
          <Select value={symbol ?? ""} onValueChange={onSymbol}>
            <SelectTrigger aria-label="Symbol">
              <SelectValue placeholder="Symbol" />
            </SelectTrigger>
            <SelectContent>
              {symbols.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
    </header>
  );
}
