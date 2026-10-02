// The data loader (ARCHITECTURE §13): index.json at startup, each run's file (and a symbol's or
// the universe's files) on demand, cached in memory by path. Everything is fetched relative to the document, so the site works under any
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

const files = new Map<string, Promise<unknown>>();

/** A results file by its index path (a run, a symbol's or the universe's), fetched once per
 * page load. */
export function loadFile<T>(path: string, fetcher: Fetcher = fetch): Promise<T> {
  let pending = files.get(path);
  if (pending === undefined) {
    pending = fetchJson(path, fetcher).then((data) => checked<T>(path, data));
    pending.catch(() => files.delete(path)); // a failed load is asked again next time
    files.set(path, pending);
  }
  return pending as Promise<T>;
}

/** A run's file by its index path. */
export function loadRun(path: string, fetcher: Fetcher = fetch): Promise<RunResult> {
  return loadFile<RunResult>(path, fetcher);
}

/** Forget cached files (tests). */
export function clearRunCache(): void {
  files.clear();
}
