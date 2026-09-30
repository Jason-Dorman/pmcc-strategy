// The data loader (ARCHITECTURE §13): index.json at startup, each run's file on demand, cached in
// memory by path. Everything is fetched relative to the document, so the site works under any
// Pages path and makes no cross-origin request (DEC-73). A file of another schema version is
// refused, and the page shows a schema-mismatch banner (UI-SPEC §8).
import type { Index } from "../types/generated/index";
import type { RunResult } from "../types/generated/run_result";
import { SCHEMA_VERSION } from "../types/generated/version";

export const DATA_ROOT = "data/";

export class SchemaMismatchError extends Error {
  constructor(
    readonly path: string,
    readonly found: unknown,
  ) {
    super(`${path} is schema version ${String(found)}; this site reads ${SCHEMA_VERSION}`);
  }
}

export type Fetcher = (url: string) => Promise<Response>;

async function fetchJson(path: string, fetcher: Fetcher): Promise<unknown> {
  const response = await fetcher(DATA_ROOT + path);
  if (!response.ok) {
    throw new Error(`${path}: HTTP ${response.status}`);
  }
  return response.json();
}

function checked<T>(path: string, data: unknown): T {
  const found = (data as { schema_version?: unknown } | null)?.schema_version;
  if (found !== SCHEMA_VERSION) {
    throw new SchemaMismatchError(path, found);
  }
  return data as T;
}

export async function loadIndex(fetcher: Fetcher = fetch): Promise<Index> {
  return checked<Index>("index.json", await fetchJson("index.json", fetcher));
}

const runs = new Map<string, Promise<RunResult>>();

/** A run's file by its index path, fetched once per page load. */
export function loadRun(path: string, fetcher: Fetcher = fetch): Promise<RunResult> {
  let pending = runs.get(path);
  if (pending === undefined) {
    pending = fetchJson(path, fetcher).then((data) => checked<RunResult>(path, data));
    pending.catch(() => runs.delete(path)); // a failed load is asked again next time
    runs.set(path, pending);
  }
  return pending;
}

/** Forget cached runs (tests). */
export function clearRunCache(): void {
  runs.clear();
}
