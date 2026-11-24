// The thesis page's building blocks (UI-SPEC §6 › Thesis; PO, TD-30): a section of the reading
// sequence, a disclosure, a chart's legend, a check's verdict and a localized "not available".
// Styled by theme/thesis.css, scoped to this page.
import { useId, useState, type ReactNode } from "react";

import type { Verdict } from "./assessment";

export interface SectionSpec {
  id: string;
  /** Its name in the page's contents. */
  nav: string;
}

/** The page's reading sequence, in order. */
export const SECTIONS = [
  { id: "idea", nav: "The idea" },
  { id: "assessment", nav: "Latest assessment" },
  { id: "tracker", nav: "Daily tracker" },
  { id: "evidence", nav: "Evidence" },
  { id: "invalidate", nav: "What would prove it wrong" },
  { id: "cost", nav: "Return and costs" },
  { id: "macro", nav: "Macro" },
  { id: "method", nav: "Methodology" },
] as const satisfies readonly SectionSpec[];

export function Section({ id, title, intro, children }: {
  id: (typeof SECTIONS)[number]["id"];
  title: string;
  intro?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section className="th-section" id={id} aria-labelledby={`${id}-title`} tabIndex={-1}>
      <h2 className="th-h2" id={`${id}-title`}>{title}</h2>
      {intro && <p className="th-intro">{intro}</p>}
      {children}
    </section>
  );
}

/** Jump to a section: the hash is the router's, so a link can't be an anchor. */
function jump(id: string): void {
  const section = document.getElementById(id);
  section?.scrollIntoView({ block: "start" });
  section?.focus({ preventScroll: true });
}

export function Contents() {
  return (
    <nav className="th-contents" aria-label="On this page">
      <ul>
        {SECTIONS.map((s) => (
          <li key={s.id}>
            <button type="button" onClick={() => { jump(s.id); }}>{s.nav}</button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** A disclosure, closed at first, its body built when first opened; `wide` for a chart or table. */
export function Disclosure({ title, wide = false, children }: {
  title: string;
  wide?: boolean;
  children: ReactNode;
}) {
  const [opened, setOpened] = useState(false);
  return (
    <details className={wide ? "th-disclosure th-wide" : "th-disclosure"}
             onToggle={(e) => opened || setOpened(e.currentTarget.open)}>
      <summary>{title}</summary>
      <div className="th-disclosure-body">{opened && children}</div>
    </details>
  );
}

const VERDICTS = {
  met: { icon: "✓", words: "Meets the condition", name: "met" },
  unmet: { icon: "✕", words: "Does not meet the condition", name: "unmet" },
  unknown: { icon: "?", words: "Not assessed", name: "unknown" },
} as const;

/** A check's verdict: an icon and words, never colour alone. */
export function VerdictTag({ met }: { met: Verdict }) {
  const v = met === null ? VERDICTS.unknown : met ? VERDICTS.met : VERDICTS.unmet;
  return (
    <span className={`th-verdict th-verdict-${v.name}`}>
      <span aria-hidden="true">{v.icon}</span> {v.words}
    </span>
  );
}

export interface Key {
  name: string;
  /** Its swatch's class: a line's, a marker's or a shading's (theme/thesis.css). */
  mark: string;
  glyph?: string;
}

/** A chart's legend: a list, so it wraps on a phone and a screen reader hears it. */
export function Legend({ label, keys }: { label: string; keys: readonly Key[] }) {
  return (
    <ul className="th-legend" aria-label={label}>
      {keys.map((k) => (
        <li key={k.name}>
          <span className={`th-key ${k.mark}`} aria-hidden="true">{k.glyph}</span>
          {k.name}
        </li>
      ))}
    </ul>
  );
}

/** What the file doesn't hold, said where it would be. */
export function NotAvailable({ children }: { children: ReactNode }) {
  return <p className="th-missing">{children}</p>;
}

/** A button that shows and hides what it controls. */
export function Toggle({ open, onToggle, show, hide, controls }: {
  open: boolean;
  onToggle: () => void;
  show: string;
  hide: string;
  controls: string;
}) {
  return (
    <button type="button" className="th-button" aria-expanded={open} aria-controls={controls}
            onClick={onToggle}>
      <span aria-hidden="true">{open ? "▾" : "▸"}</span> {open ? hide : show}
    </button>
  );
}

/** A heading of its own inside a section, naming a group of cards or figures. */
export function Titled({ title, children, className }: { title: string; children: ReactNode;
                                                        className: string }) {
  const id = useId();
  return (
    <article className={className} aria-labelledby={id}>
      <h3 className="th-h3" id={id}>{title}</h3>
      {children}
    </article>
  );
}
