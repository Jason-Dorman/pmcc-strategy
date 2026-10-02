// Typed tokens (DEC-70, UI-SPEC §3): the colour names tokens.css defines, and the numeric layout
// constants from theme.py. Components use these; they never re-type a value as a literal.

/** Every colour token in tokens.css, by its CSS variable's name without the dashes. */
export const COLOR_TOKENS = [
  "bg",
  "surface",
  "surface-alt",
  "border",
  "grid",
  "text",
  "text-muted",
  "text-inverse",
  "accent",
  "accent-dim",
  "mark",
  "trade",
  "trade-edge",
  "positive",
  "negative",
  "warn",
  "nav-line",
  "margin-im",
  "margin-mm",
  "fit-line",
  "identity-line",
] as const;

export type ColorToken = (typeof COLOR_TOKENS)[number];

/**
 * The chart roles (PO, DEC-04), each the palette colour tokens.css points it at. A chart names a
 * role, never the colour behind it, so a role can move to another colour in one edit.
 */
export const ROLE_TOKENS = {
  "long-leg": "nav-line",
  "short-leg": "mark",
  "strategy-quant": "nav-line",
  "strategy-baseline": "mark",
  "available-funds": "text",
} as const satisfies Record<string, ColorToken>;

export type RoleToken = keyof typeof ROLE_TOKENS;

/** A colour token's current value, read from the document at render time (the charts). */
export function color(token: ColorToken | RoleToken | "negative-shade",
                      root: Element = document.documentElement): string {
  return getComputedStyle(root).getPropertyValue(`--${token}`).trim();
}

// Grid: ten columns divide into 5 + 5 and 6 + 4 (theme.py).
export const GRID_COLUMNS = 10;
export const W_FULL = 10;
export const W_HALF = 5;
export const W_HERO = 6;
export const W_SIDECAR = 4;
export type PanelWidth = typeof W_FULL | typeof W_HALF | typeof W_HERO | typeof W_SIDECAR;

// Breakpoints: ≥ 1400 the 10-column grid; 1101–1399 two columns; ≤ 1100 one (DG §4).
export const BREAK_TWO_COL = 1400;
export const BREAK_ONE_COL = 1100;

// Figures and tables.
export const PANEL_FIGURE_HEIGHT = 360;
export const HERO_FIGURE_HEIGHT = 600;
export const FIGURE_MIN_WIDTH = 520;
export const HERO_MIN_WIDTH = 680;
export const TABLE_MIN_WIDTH = 720;
export const TABLE_MAX_HEIGHT = 420;
export const TABLE_FONT_SIZE = 11.5;
// A virtualized table's fixed row: a RIC over its OCC symbol (shell.css's .pm-table-fixed).
export const TABLE_ROW_HEIGHT = 42;
// Rows a virtualized table renders past the visible ones, each way.
export const TABLE_OVERSCAN = 12;

// The account chart: NAV is a series, IM and MM are rulers (theme.py ACCOUNT_LINES).
export const ACCOUNT_LINES = {
  nav: { width: 2.2, dash: "solid" },
  im: { width: 1.4, dash: "dashed" },
  mm: { width: 1.2, dash: "dotted" },
} as const;

// Marker sizes: a mid, a print, an account event (theme.py).
export const SIZE_MARK = 4;
export const SIZE_TRADE = 6;
export const ACCOUNT_MARKER_SIZE = 5;
