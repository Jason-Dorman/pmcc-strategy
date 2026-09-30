// Token lint (UI-SPEC §10, DG §5 rule 1): no colour, font name or pixel value anywhere in the
// site's source outside src/theme/. The old project's grep test, ported: a restyle is then an edit
// to the tokens, never a hunt through components.
import { describe, expect, it } from "vitest";

// Every source file, as text: src/theme/ and the generated types are exempt, and so are tests.
const SOURCES: Record<string, string> = {
  ...import.meta.glob(["../**/*.{ts,tsx,css}", "!./**", "!../types/generated/**", "!../**/*.test.*"],
                      { query: "?raw", import: "default", eager: true }),
  ...import.meta.glob("../../index.html", { query: "?raw", import: "default", eager: true }),
};

const RULES: readonly [string, RegExp][] = [
  ["a hex colour", /#[0-9a-fA-F]{3,8}\b/],
  ["an rgb() or hsl() colour", /\b(?:rgba?|hsla?)\(/],
  ["a font name", /Space Grotesk|JetBrains Mono|\bInter\b|monospace|sans-serif|\bserif\b/],
  ["a pixel value", /\b\d+(?:\.\d+)?px\b/],
  ["an arbitrary Tailwind value", /\w-\[[^\]]+\]/],
];

function violations(text: string): string[] {
  return RULES.filter(([, pattern]) => pattern.test(text)).map(([what]) => what);
}

describe("token lint", () => {
  it("finds the source it guards, and not the theme", () => {
    const names = Object.keys(SOURCES);
    expect(names).toContain("../components/Panel.tsx");
    expect(names).toContain("../../index.html");
    expect(names.filter((n) => n.startsWith("./") || n.includes("generated"))).toEqual([]);
  });

  it("reads every file's text, stylesheets included", () => {
    const empty = Object.entries(SOURCES).filter(([, text]) => text.trim() === "");
    expect(empty.map(([name]) => name)).toEqual([]);
  });

  it.each(Object.entries(SOURCES))("%s holds no literal style", (_name, text) => {
    expect(violations(text)).toEqual([]);
  });

  it.each([
    ["color: #ff4d6d", "a hex colour"],
    ["background: rgba(0,0,0,0.5)", "an rgb() or hsl() colour"],
    ["font-family: 'JetBrains Mono'", "a font name"],
    ['style={{ width: "12px" }}', "a pixel value"],
    ['className="text-[11.5px]"', "an arbitrary Tailwind value"],
  ])("catches %s", (planted, what) => {
    expect(violations(planted)).toContain(what);
  });

  it("allows Tailwind's spacing utilities", () => {
    expect(violations('className="px-3 py-1 gap-2"')).toEqual([]);
  });
});
