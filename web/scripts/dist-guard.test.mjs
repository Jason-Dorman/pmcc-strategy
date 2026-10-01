// The dist guard (P4-07, ARCHITECTURE §14): it fails on the hosts the site must never reach, and
// passes what a correct build carries.
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { findings, guard } from "./dist-guard.mjs";

describe("dist guard", () => {
  it.each([
    ["fetch('http://localhost:9000/api/status')", "LSEG's local proxy"],
    ["https://api.refinitiv.com/data", "an LSEG or Refinitiv URL"],
    ["src=\"https://workspace.lseg.com/x\"", "an LSEG or Refinitiv URL"],
    ["@import url(https://fonts.googleapis.com/css2?family=Inter)", "Google Fonts"],
    ["https://fonts.gstatic.com/s/inter.woff2", "Google Fonts"],
  ])("refuses %s", (text, what) => {
    expect(findings(text)).toContain(what);
  });

  it.each([
    ['{"data_source":"lseg","ric":"NVDA.O"}'],
    ["https://github.com/Jason-Dorman/pmcc-strategy/commit/abc"],
    ["https://fred.stlouisfed.org/series/DGS3MO"],
    ['new URL("http://localhost")'],
  ])("allows %s", (text) => {
    expect(findings(text)).toEqual([]);
  });

  it("walks every file under the build, nested ones included", async () => {
    const dir = mkdtempSync(join(tmpdir(), "dist-"));
    mkdirSync(join(dir, "assets"));
    writeFileSync(join(dir, "index.html"), "<html></html>");
    writeFileSync(join(dir, "assets", "app.js"), "fetch('http://localhost:9000/x')");

    const result = await guard(dir);

    expect(result.files).toBe(2);
    expect(result.broken).toEqual([`${join("assets", "app.js")}: LSEG's local proxy`]);
  });

  it("refuses an empty build", async () => {
    await expect(guard(mkdtempSync(join(tmpdir(), "dist-")))).rejects.toThrow("is empty");
  });
});
