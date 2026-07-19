// Build-time loader over the index source tree (../index/**/metadata.json).
// Mirrors scripts/build.py's namespace derivation: the package directory's
// parent path relative to index/ (e.g. "github.com/grimoire-rs").
import fs from "node:fs";
import path from "node:path";

export interface Package {
  name: string;
  kind: string;
  ref: string;
  description?: string;
  repository?: string;
  namespace: string;
  owner?: { github: string; id?: number };
  // Enrichment sidecar (enrich/<namespace>/<name>/data.json), refreshed by
  // CI from the registry. All optional: the catalog renders without them.
  title?: string;
  summary?: string;
  version?: string;
  license?: string;
  keywords?: string[];
  created?: string;
  deprecated?: string | null;
  replacedBy?: string;
  tags?: string[];
  logo?: string;
  hasReadme?: boolean;
  hasChangelog?: boolean;
}

// import.meta.url is rewritten to the bundled chunk path at build time, so
// locate the repo root by walking up from cwd (works from site/ and root).
export function repoRoot(): string {
  let dir = process.cwd();
  for (;;) {
    if (
      fs.existsSync(path.join(dir, "index")) &&
      fs.existsSync(path.join(dir, "scripts", "build.py"))
    ) {
      return dir;
    }
    const parent = path.dirname(dir);
    if (parent === dir) {
      throw new Error(`index/ not found walking up from ${process.cwd()}`);
    }
    dir = parent;
  }
}

export function loadPackages(): Package[] {
  const ROOT = repoRoot();
  const INDEX_DIR = path.join(ROOT, "index");
  const entries = fs.readdirSync(INDEX_DIR, {
    recursive: true,
    withFileTypes: true,
  });
  const packages: Package[] = [];
  for (const entry of entries) {
    if (!entry.isFile() || entry.name !== "metadata.json") continue;
    const file = path.join(entry.parentPath, entry.name);
    const meta = JSON.parse(fs.readFileSync(file, "utf8"));
    const namespace = path
      .relative(INDEX_DIR, path.dirname(path.dirname(file)))
      .split(path.sep)
      .join("/");
    // Sidecar fields spread first so the announcement-owned index metadata
    // always wins on overlap. descDigest is CI bookkeeping — never ship it
    // (mirrors build.py's pop before all.json).
    const enrichFile = path.join(ROOT, "enrich", namespace, meta.name, "data.json");
    const { descDigest: _descDigest, ...enrich } = fs.existsSync(enrichFile)
      ? JSON.parse(fs.readFileSync(enrichFile, "utf8"))
      : {};
    packages.push({
      ...enrich,
      name: meta.name,
      kind: meta.kind,
      ref: meta.ref,
      description: meta.description,
      repository: meta.repository,
      namespace,
      owner: meta.owner,
    });
  }
  return packages.sort((a, b) => a.name.localeCompare(b.name));
}

// MDN-standard Intl.RelativeTimeFormat rollup (no date library).
const RTF = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const TIME_DIVISIONS: [number, Intl.RelativeTimeFormatUnit][] = [
  [60, "seconds"],
  [60, "minutes"],
  [24, "hours"],
  [7, "days"],
  [4.34524, "weeks"],
  [12, "months"],
  [Infinity, "years"],
];

export function timeAgo(iso: string): string {
  const ms = new Date(iso).getTime();
  if (!Number.isFinite(ms)) return ""; // unparseable: caller hides the element
  let duration = (ms - Date.now()) / 1000;
  for (const [amount, unit] of TIME_DIVISIONS) {
    if (Math.abs(duration) < amount) return RTF.format(Math.round(duration), unit);
    duration /= amount;
  }
  return RTF.format(Math.round(duration), "years");
}
