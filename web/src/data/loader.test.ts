import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeFetch, FILES, INDEX, ROBUSTNESS } from "../test/fixtures";
import { clearRunCache, loadFile, loadIndex, loadRun, SchemaMismatchError } from "./loader";
import { both, type Loaded } from "./state";

afterEach(clearRunCache);

describe("loader", () => {
  it("loads index.json relative to the document", async () => {
    const fetcher = vi.fn(fakeFetch());
    await expect(loadIndex(fetcher)).resolves.toEqual(INDEX);
    expect(fetcher).toHaveBeenCalledWith("data/index.json");
  });

  it("refuses data of another schema version", async () => {
    const stale = fakeFetch({ "data/index.json": { ...INDEX, schema_version: 1 } });
    await expect(loadIndex(stale)).rejects.toBeInstanceOf(SchemaMismatchError);
  });

  it("refuses a run file of another schema version", async () => {
    const stale = { ...(FILES["data/NVDA/quant_pmcc.json"] as object), schema_version: 1 };
    const fetcher = fakeFetch({ "data/NVDA/quant_pmcc.json": stale });
    await expect(loadRun("NVDA/quant_pmcc.json", fetcher)).rejects.toBeInstanceOf(
      SchemaMismatchError,
    );
  });

  it("fetches a run once and serves it from memory after", async () => {
    const fetcher = vi.fn(fakeFetch());
    const first = await loadRun("NVDA/quant_pmcc.json", fetcher);
    const second = await loadRun("NVDA/quant_pmcc.json", fetcher);
    expect(second).toBe(first);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("asks again after a failed load", async () => {
    const missing = vi.fn(fakeFetch({}));
    await expect(loadRun("NVDA/quant_pmcc.json", missing)).rejects.toThrow("HTTP 404");
    const fixed = vi.fn(fakeFetch(FILES));
    await expect(loadRun("NVDA/quant_pmcc.json", fixed)).resolves.toBeDefined();
    expect(fixed).toHaveBeenCalledTimes(1);
  });

  it("loads a symbol's file once, and refuses one of another schema version", async () => {
    const fetcher = vi.fn(fakeFetch());
    await expect(loadFile("NVDA/robustness.json", fetcher)).resolves.toEqual(ROBUSTNESS);
    await loadFile("NVDA/robustness.json", fetcher);
    expect(fetcher).toHaveBeenCalledTimes(1);
    const stale = fakeFetch({ "data/universe/pooled.json": { schema_version: 1 } });
    await expect(loadFile("universe/pooled.json", stale)).rejects.toBeInstanceOf(
      SchemaMismatchError,
    );
  });
});

describe("both", () => {
  const loading: Loaded<number> = { kind: "loading" };
  const missing: Loaded<number> = { kind: "missing", what: "NVDA / quant_pmcc" };
  const ready = (value: number): Loaded<number> => ({ kind: "ready", value });

  it("is ready when both are, with both values", () => {
    expect(both(ready(1), ready(2))).toEqual({ kind: "ready", value: [1, 2] });
  });

  it("shows a load that won't come before one still loading, either way round", () => {
    expect(both(loading, missing)).toBe(missing);
    expect(both(missing, loading)).toBe(missing);
    expect(both(ready(1), loading)).toEqual({ kind: "loading" });
  });
});
