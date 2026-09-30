// What a panel shows until the backlog item that builds it lands (P4-06's scaffold).
import type { ReactNode } from "react";

import { Empty, Loading } from "../components/Note";
import type { PanelSpec } from "../components/PanelGrid";
import type { Loaded } from "../data/state";
import type { PanelWidth } from "../theme/tokens";

export function toCome(item: string, detail?: string): ReactNode {
  return <Empty>{detail ? `${detail} · ` : ""}Built at {item}.</Empty>;
}

export function panel(key: string, name: string, width: PanelWidth, body: ReactNode,
                      numbered = true): PanelSpec {
  return { key, name, width, numbered, body };
}

/** A panel body for loaded data: the flat loading block, an in-panel state, or `ready`. */
export function whenLoaded<T>(state: Loaded<T>, ready: (value: T) => ReactNode): ReactNode {
  switch (state.kind) {
    case "loading":
      return <Loading />;
    case "ready":
      return ready(state.value);
    case "missing":
      return <Empty>No results for {state.what}.</Empty>;
    default:
      return <Empty>{state.message}</Empty>;
  }
}
