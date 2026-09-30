// Data (UI-SPEC §6.6, Spec › Data layer): on github.io it says only that a data connection is
// required, since raw LSEG data never leaves the author's machine. What it shows locally is
// DEC-75, asked at P7-06.
import { PageFrame } from "../components/PageFrame";
import { Note } from "../components/Note";
import { W_FULL } from "../theme/tokens";
import { panel, toCome } from "./placeholder";

export function onGithubPages(hostname: string = window.location.hostname): boolean {
  return hostname.endsWith("github.io");
}

export function Data() {
  const body = onGithubPages() ? (
    <Note>
      <b>Data connection required.</b> Raw LSEG data stays on the author&apos;s machine and is served
      only locally, by <code>just serve</code>.
    </Note>
  ) : (
    toCome("P7-06")
  );
  return <PageFrame panels={[panel("data", "Data connection required", W_FULL, body, false)]} />;
}
