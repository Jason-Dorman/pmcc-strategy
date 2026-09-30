import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeFetch, FILES, INDEX } from "../test/fixtures";
import { clearRunCache, loadIndex, loadRun, SchemaMismatchError } from "./loader";

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
});
