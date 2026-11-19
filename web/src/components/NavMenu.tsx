// A strategy's menu in the command bar (UI-SPEC §2; PO, LD-36): a button that shows and hides
// a list of links to its pages, the disclosure pattern for site navigation (no menu roles, so
// Tab moves through the links). It closes on a link, on Escape, and on a click or focus outside.
import { useEffect, useId, useRef, useState, type FocusEvent } from "react";
import { Link } from "react-router-dom";

export interface NavItem {
  key: string;
  label: string;
  to: string;
  current: boolean;
}

export function NavMenu({ label, on, items }: { label: string; on: boolean;
                                                items: readonly NavItem[] }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const id = useId();

  useEffect(() => {
    if (!open) return undefined;
    const away = (e: PointerEvent) => {
      if (e.target instanceof Node && !root.current?.contains(e.target)) setOpen(false);
    };
    const escape = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setOpen(false);
      button.current?.focus();
    };
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", away);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  const leave = (e: FocusEvent<HTMLDivElement>) => {
    if (!(e.relatedTarget instanceof Node && root.current?.contains(e.relatedTarget))) {
      setOpen(false);
    }
  };

  return (
    <div className="pm-menu" ref={root} onBlur={leave}>
      <button ref={button} type="button" className={on ? "pm-menu-button on" : "pm-menu-button"}
              aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>
        {label}
        <span className="pm-menu-caret" aria-hidden="true">▾</span>
      </button>
      {open && (
        <ul id={id} className="pm-menu-list">
          {items.map((item) => (
            <li key={item.key}>
              <Link to={item.to} className={item.current ? "on" : undefined}
                    aria-current={item.current ? "page" : undefined}
                    onClick={() => setOpen(false)}>
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
