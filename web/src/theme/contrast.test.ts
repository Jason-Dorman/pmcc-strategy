// Contrast (UI-SPEC §10, DG §2): every text pairing clears WCAG AA (4.5:1) and every data mark
// clears 3:1 against the grounds it's drawn on. One theme, dark (PO, DEC-03). Also holds the grid
// and breakpoints in shell.css to tokens.ts (DG §6: CSS fails open).
import { describe, expect, it } from "vitest";

import SHELL from "./shell.css?raw";
import { BREAK_ONE_COL, BREAK_TWO_COL, COLOR_TOKENS, GRID_COLUMNS, type ColorToken } from "./tokens";
import TOKENS from "./tokens.css?raw";

function hex(token: ColorToken): string {
  const found = new RegExp(`--${token}:\\s*(#[0-9a-fA-F]{6})\\b`).exec(TOKENS);
  if (!found?.[1]) throw new Error(`tokens.css has no hex value for --${token}`);
  return found[1];
}

function luminance(value: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(value.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * (r ?? 0) + 0.7152 * (g ?? 0) + 0.0722 * (b ?? 0);
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return ((hi ?? 0) + 0.05) / ((lo ?? 0) + 0.05);
}

const GROUNDS: ColorToken[] = ["bg", "surface", "surface-alt"];
const TEXT: ColorToken[] = ["text", "text-muted", "accent", "positive", "negative", "warn"];
const MARKS: ColorToken[] = ["mark", "trade", "nav-line", "margin-im", "margin-mm", "fit-line",
                             "identity-line", "positive", "negative"];

describe("contrast", () => {
  it("defines every colour token as a hex value", () => {
    for (const token of COLOR_TOKENS) expect(hex(token)).toMatch(/^#[0-9a-fA-F]{6}$/);
  });

  it("measures a known pair", () => {
    expect(contrast("#000000", "#ffffff")).toBeCloseTo(21, 5);
  });

  const text = TEXT.flatMap((fg) => GROUNDS.map((bg) => [fg, bg] as const));
  it.each(text)("text %s on %s clears 4.5:1", (fg, bg) => {
    expect(contrast(hex(fg), hex(bg))).toBeGreaterThanOrEqual(4.5);
  });

  it("type on amber clears 4.5:1", () => {
    expect(contrast(hex("text-inverse"), hex("accent"))).toBeGreaterThanOrEqual(4.5);
  });

  const marks = MARKS.flatMap((fg) => (["surface", "surface-alt"] as const).map((bg) => [fg, bg]));
  it.each(marks)("mark %s on %s clears 3:1", (fg, bg) => {
    expect(contrast(hex(fg as ColorToken), hex(bg as ColorToken))).toBeGreaterThanOrEqual(3);
  });
});

describe("shell.css follows tokens.ts", () => {
  it("has a width class for every grid column", () => {
    for (let n = 1; n <= GRID_COLUMNS; n++) {
      expect(SHELL).toContain(`.pm-w${n} { grid-column: span ${n}; }`);
    }
    expect(SHELL).toContain(`repeat(${GRID_COLUMNS}, minmax(0, 1fr))`);
  });

  it("switches bands at the breakpoints", () => {
    expect(SHELL).toContain(
      `@media (max-width: ${BREAK_TWO_COL - 1}px) and (min-width: ${BREAK_ONE_COL + 1}px)`,
    );
    expect(SHELL).toContain(`@media (max-width: ${BREAK_ONE_COL}px)`);
  });
});
