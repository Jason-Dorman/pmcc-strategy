// The manifest footer (UI-SPEC §2, Spec › Run manifest): every page shows what produced the
// numbers on it (the commit, linked; the config, data and lockfile hashes; when it ran; and
// where the data came from), so any number traces to its code, config, environment and data.
import { REPO_URL } from "../app/site";
import { short } from "../format/hash";
import { timeET } from "../format/time";
import type { Manifest } from "../types/generated/run_result";

export function ManifestLine({ manifest }: { manifest: Manifest }) {
  return (
    <div>
      <b>{manifest.symbol} {manifest.run_id}</b> · commit{" "}
      <a href={`${REPO_URL}/commit/${manifest.git_sha}`} title={manifest.git_sha}>
        {short(manifest.git_sha, 7)}
      </a>
      {manifest.git_dirty && " (dirty)"} · config{" "}
      <span title={manifest.config_hash}>{short(manifest.config_hash)}</span> · data{" "}
      <span title={manifest.data_manifest_hash}>{short(manifest.data_manifest_hash)}</span> ·
      lock <span title={manifest.lock_hash}>{short(manifest.lock_hash)}</span> · ran{" "}
      {timeET(manifest.run_timestamp)} · pmcc {manifest.pmcc_version} · source{" "}
      {manifest.data_source}
    </div>
  );
}

export function ManifestFooter({ manifests, exporter }: {
  manifests: readonly Manifest[];
  exporter: string | undefined;
}) {
  return (
    <footer className="pm-footer" aria-label="Run manifest">
      {manifests.length === 0 && <div>No run is shown on this page.</div>}
      {manifests.map((m) => (
        <ManifestLine key={`${m.symbol}/${m.run_id}`} manifest={m} />
      ))}
      {exporter && <div>Exported by pmcc {exporter}.</div>}
    </footer>
  );
}
