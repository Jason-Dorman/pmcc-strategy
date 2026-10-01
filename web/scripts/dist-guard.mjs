// The dist guard (ARCHITECTURE §14): the built site must never reach LSEG or load fonts from
// Google; it serves everything from its own origin (Spec › Frontend constraints, DEC-72). CI runs
// it on web/dist before deploying: `node scripts/dist-guard.mjs dist`.
//
// It looks for hosts, not words: the results themselves say `"data_source":"lseg"`, and the
// footer links to github.com and r's source to FRED, all of which are fine (DEC-97).
import { readdir, readFile } from "node:fs/promises";
import { join, relative } from "node:path";
import { pathToFileURL } from "node:url";

export const FORBIDDEN = [
  ["LSEG's local proxy", /localhost:9000/],
  ["an LSEG or Refinitiv URL", /https?:\/\/[^\s"'<>)]*(?:lseg|refinitiv)/i],
  ["Google Fonts", /fonts\.(?:googleapis|gstatic)\.com/],
];

/** What `text` names that the site must not: one entry per rule it breaks. */
export function findings(text) {
  return FORBIDDEN.filter(([, pattern]) => pattern.test(text)).map(([what]) => what);
}

async function files(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map((e) => (e.isDirectory() ? files(join(dir, e.name)) : [join(dir, e.name)])),
  );
  return nested.flat();
}

/** Every `file: rule` broken under `dir`; throws if `dir` holds no files at all. */
export async function guard(dir) {
  const found = await files(dir);
  if (found.length === 0) throw new Error(`${dir} is empty: build the site first`);
  const broken = [];
  for (const file of found) {
    const text = await readFile(file, "utf8");
    for (const what of findings(text)) broken.push(`${relative(dir, file)}: ${what}`);
  }
  return { files: found.length, broken };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const dir = process.argv[2] ?? "dist";
  try {
    const { files: count, broken } = await guard(dir);
    for (const line of broken) console.error(line);
    if (broken.length > 0) {
      console.error(`dist guard: ${broken.length} forbidden reference(s) in ${dir}`);
      process.exit(1);
    }
    console.log(`dist guard: ${count} files in ${dir}, no forbidden host`);
  } catch (error) {
    console.error(`dist guard: ${error instanceof Error ? error.message : String(error)}`);
    process.exit(1);
  }
}
