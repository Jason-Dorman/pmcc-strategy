// The command bar (UI-SPEC §2; PO, LD-36): the wordmark on the left, a link to the home page;
// on the right a menu per strategy, the live wheel first, its pages inside. The live wheel has
// one page, so its entry is a plain link. The current strategy is amber.
import { Link } from "react-router-dom";

import { pageOf, pagePath, STRATEGIES, type Page, type Strategy } from "../app/pages";
import { WORDMARK } from "../app/site";
import { NavMenu } from "./NavMenu";

export interface CommandBarProps {
  current: Page | undefined;
  symbol: string | undefined;
}

function Entry({ strategy, current, symbol }: { strategy: Strategy } & CommandBarProps) {
  const on = current?.strategy === strategy.key;
  const items = strategy.menu.map((key) => {
    const page = pageOf(key);
    return { key, label: page.label, to: pagePath(page, symbol), current: key === current?.key };
  });
  const [only] = items;
  if (items.length === 1 && only) {
    return (
      <Link to={only.to} className={on ? "pm-menu-button on" : "pm-menu-button"}
            aria-current={only.current ? "page" : undefined}>
        {strategy.label}
      </Link>
    );
  }
  return <NavMenu label={strategy.label} on={on} items={items} />;
}

export function CommandBar({ current, symbol }: CommandBarProps) {
  return (
    <header className="pm-bar">
      <Link to="/" className="pm-wordmark">{WORDMARK}</Link>
      <nav className="pm-nav" aria-label="Strategies">
        {STRATEGIES.map((s) => (
          <Entry key={s.key} strategy={s} current={current} symbol={symbol} />
        ))}
      </nav>
    </header>
  );
}
