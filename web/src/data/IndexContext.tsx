// The index, loaded once at startup and shared by every page (ARCHITECTURE §13).
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import type { Index } from "../types/generated/index";
import { loadIndex, SchemaMismatchError, type Fetcher } from "./loader";
import type { Loaded } from "./state";

const IndexContext = createContext<Loaded<Index>>({ kind: "loading" });

export function failure(error: unknown): Loaded<never> {
  if (error instanceof SchemaMismatchError) {
    return { kind: "mismatch", message: error.message };
  }
  return { kind: "error", message: error instanceof Error ? error.message : String(error) };
}

export function IndexProvider({ children, fetcher }: { children: ReactNode; fetcher?: Fetcher }) {
  const [state, setState] = useState<Loaded<Index>>({ kind: "loading" });
  useEffect(() => {
    let live = true;
    loadIndex(fetcher)
      .then((value) => live && setState({ kind: "ready", value }))
      .catch((error: unknown) => live && setState(failure(error)));
    return () => {
      live = false;
    };
  }, [fetcher]);
  return <IndexContext.Provider value={state}>{children}</IndexContext.Provider>;
}

export function useIndex(): Loaded<Index> {
  return useContext(IndexContext);
}
