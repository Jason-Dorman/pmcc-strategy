// One run's result for a page: found through the index by symbol and run ID, then loaded on
// demand and cached (ARCHITECTURE §13). A run the index lacks is "missing", never an error.
import { useEffect, useState } from "react";

import type { Index, IndexRun } from "../types/generated/index";
import type { RunResult } from "../types/generated/run_result";
import { failure, useIndex } from "./IndexContext";
import { loadRun } from "./loader";
import type { Loaded } from "./state";

export function findRun(index: Index, symbol: string, runId: string): IndexRun | undefined {
  return index.symbols.find((s) => s.symbol === symbol)?.runs.find((r) => r.run_id === runId);
}

export function useRun(symbol: string, runId: string): Loaded<RunResult> {
  const index = useIndex();
  const entry = index.kind === "ready" ? findRun(index.value, symbol, runId) : undefined;
  const path = entry?.path;
  const [loaded, setLoaded] = useState<{ path: string; state: Loaded<RunResult> } | null>(null);

  useEffect(() => {
    if (path === undefined) return;
    let live = true;
    loadRun(path)
      .then((value) => live && setLoaded({ path, state: { kind: "ready", value } }))
      .catch((error: unknown) => live && setLoaded({ path, state: failure(error) }));
    return () => {
      live = false;
    };
  }, [path]);

  if (index.kind !== "ready") return index;
  if (path === undefined) return { kind: "missing", what: `${symbol} / ${runId}` };
  return loaded?.path === path ? loaded.state : { kind: "loading" };
}
