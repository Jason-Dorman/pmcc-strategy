// What a page knows about its data while it loads (UI-SPEC §8).
export type Loaded<T> =
  | { kind: "loading" }
  | { kind: "ready"; value: T }
  | { kind: "missing"; what: string } // not in the index: "No results for …"
  | { kind: "mismatch"; message: string } // another schema version
  | { kind: "error"; message: string };

/** Two loads as one: ready when both are, else the first that isn't (a missing run before
 * one still loading, so a panel never waits on a file that won't come). */
export function both<A, B>(a: Loaded<A>, b: Loaded<B>): Loaded<readonly [A, B]> {
  if (a.kind === "ready" && b.kind === "ready") return { kind: "ready", value: [a.value, b.value] };
  if (a.kind !== "ready" && a.kind !== "loading") return a;
  if (b.kind !== "ready" && b.kind !== "loading") return b;
  return { kind: "loading" };
}
