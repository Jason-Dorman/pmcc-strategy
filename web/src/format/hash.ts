// A hash or commit, shortened for the manifest footer; the full value is its title.
export function short(hash: string, length = 8): string {
  return hash.slice(0, length);
}
