// What a page knows about its data while it loads (UI-SPEC §8).
export type Loaded<T> =
  | { kind: "loading" }
  | { kind: "ready"; value: T }
  | { kind: "missing"; what: string } // not in the index: "No results for …"
  | { kind: "mismatch"; message: string } // another schema version
  | { kind: "error"; message: string };
