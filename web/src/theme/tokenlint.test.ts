// Token lint (UI-SPEC §10, DG §5 rule 1): no colour, font name or pixel value anywhere in the
// site's source outside src/theme/. The old project's grep test, ported: a restyle is then an edit
// to the tokens, never a hunt through components. Tests are exempt, since they plant samples.
import { describe, expect, it } from "vitest";

// Every source file, as text: src/theme/ and the generated types are exempt, and so are tests.
const SOURCES: Record<string, string> = {
  ...import.meta.glob(["../**/*.{ts,tsx,css}", "!./**", "!../types/generated/**", "!../**/*.test.*"],
                      { query: "?raw", import: "default", eager: true }),
  ...import.meta.glob(["../../index.html", "../../vite.config.ts", "../../eslint.config.js",
                       "../../scripts/*.mjs", "!../../scripts/*.test.mjs"],
                      { query: "?raw", import: "default", eager: true }),
};

// Every source directory the lint must reach, so a narrowed glob can't pass quietly.
const DIRECTORIES = ["app", "components", "components/ui", "data", "format", "lib", "pages"];

const RULES: readonly [string, RegExp][] = [
  ["a hex colour", /#[0-9a-fA-F]{3,8}\b/],
  ["an rgb() or hsl() colour", /\b(?:rgba?|hsla?)\(/],
  ["a font name", /Space Grotesk|JetBrains Mono|\bInter\b|monospace|sans-serif|\bserif\b/],
  ["a pixel value", /\b\d+(?:\.\d+)?px\b/],
  ["an arbitrary Tailwind value", /\w-\[[^\]]+\]/],
  // React adds px to a bare number in a style: `style={{ height: 360 }}` is a pixel literal.
  ["a unitless style number",
   /\b(?:width|height|min[WH]\w*|max[WH]\w*|fontSize|lineHeight|padding\w*|margin\w*|top|left|right|bottom|gap)\s*:\s*-?\d/],
];

function violations(text: string): string[] {
  return RULES.filter(([, pattern]) => pattern.test(text)).map(([what]) => what);
}

describe("token lint", () => {
  it("finds the source it guards, and not the theme", () => {
    const names = Object.keys(SOURCES);
    for (const dir of DIRECTORIES) {
      expect(names.some((n) => n.startsWith(`../${dir}/`)), dir).toBe(true);
    }
    for (const file of ["../main.tsx", "../../index.html", "../../vite.config.ts",
                        "../../eslint.config.js", "../../scripts/gen-types.mjs"]) {
      expect(names).toContain(file);
    }
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
    ["font-size: 11.5px", "a pixel value"],
    ['className="text-[11.5px]"', "an arbitrary Tailwind value"],
    ["style={{ height: 360 }}", "a unitless style number"],
    ["style={{ minWidth: 520 }}", "a unitless style number"],
  ])("catches %s", (planted, what) => {
    expect(violations(planted)).toContain(what);
  });

  it("allows Tailwind's spacing utilities", () => {
    expect(violations('className="px-3 py-1 gap-2"')).toEqual([]);
  });
});
