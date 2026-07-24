import { useMemo, useState } from "preact/hooks";
import { timeAgo, type Package } from "../lib/catalog";

// Known kinds get stable chip ordering + badge colors; unknown kinds
// (future schema growth) still render with a neutral badge.
const KNOWN_KINDS = ["skill", "rule", "agent", "mcp", "bundle"];

function kindOrder(kind: string): number {
  const i = KNOWN_KINDS.indexOf(kind);
  return i === -1 ? KNOWN_KINDS.length : i;
}

type Sort = "name" | "updated";

// Deprecated packages sink to the bottom regardless of sort mode; the
// chosen sort only orders within the two groups.
function compare(a: Package, b: Package, sort: Sort): number {
  const dep = Number(!!a.deprecated) - Number(!!b.deprecated);
  if (dep !== 0) return dep;
  if (sort === "name") return a.name.localeCompare(b.name);
  if (!a.created || !b.created) return (a.created ? 0 : 1) - (b.created ? 0 : 1);
  return new Date(b.created).getTime() - new Date(a.created).getTime();
}

// The two install scopes wear the same glyphs as the VS Code extension, so
// "project" and "global" read identically in both: codicons `root-folder`
// and `globe` (@vscode/codicons 0.0.45, CC-BY-4.0), copied as paths rather
// than pulling in the icon font for two icons.
const SCOPE_PROJECT =
  "M4.5 7C2.019 7 0 9.019 0 11.5C0 13.981 2.019 16 4.5 16C6.981 16 9 13.981 9 11.5C9 9.019 6.981 7 4.5 7ZM4.5 15C2.57 15 1 13.43 1 11.5C1 9.57 2.57 8 4.5 8C6.43 8 8 9.57 8 11.5C8 13.43 6.43 15 4.5 15ZM7 11.5C7 12.881 5.881 14 4.5 14C3.119 14 2 12.881 2 11.5C2 10.119 3.119 9 4.5 9C5.881 9 7 10.119 7 11.5ZM15 6.5V11.5C15 12.881 13.881 14 12.5 14H10V13H12.5C13.328 13 14 12.328 14 11.5V6.5C14 5.672 13.328 5 12.5 5H8.207L7.207 6H5.586C5.719 6 5.846 5.947 5.94 5.854L7.294 4.5L5.94 3.146C5.846 3.052 5.719 3 5.586 3H3.5C2.672 3 2 3.672 2 4.5V6H1V4.5C1 3.119 2.119 2 3.5 2H5.586C5.984 2 6.365 2.158 6.647 2.439L8.208 4H12.501C13.882 4 15.001 5.119 15.001 6.5H15Z";
const SCOPE_GLOBAL =
  "M8 1C4.141 1 1 4.141 1 8C1 11.859 4.141 15 8 15C11.859 15 15 11.859 15 8C15 4.141 11.859 1 8 1ZM8 14C7.422 14 6.686 12.906 6.288 11H9.713C9.315 12.906 8.579 14 8.001 14H8ZM6.121 10C6.044 9.392 6 8.723 6 8C6 7.277 6.044 6.608 6.121 6H9.878C9.955 6.608 9.999 7.277 9.999 8C9.999 8.723 9.955 9.392 9.878 10H6.121ZM2 8C2 7.299 2.121 6.626 2.343 6H5.121C5.041 6.656 5 7.332 5 8C5 8.668 5.041 9.344 5.121 10H2.343C2.121 9.374 2 8.701 2 8ZM8 2C8.578 2 9.314 3.094 9.712 5H6.287C6.685 3.094 7.422 2 8 2ZM10.879 6H13.657C13.879 6.626 14 7.299 14 8C14 8.701 13.879 9.374 13.657 10H10.879C10.959 9.344 11 8.668 11 8C11 7.332 10.959 6.656 10.879 6ZM13.195 5H10.722C10.516 3.938 10.199 2.98 9.775 2.268C11.228 2.719 12.446 3.707 13.195 5ZM6.226 2.268C5.802 2.98 5.484 3.938 5.279 5H2.806C3.556 3.707 4.774 2.718 6.226 2.268ZM2.805 11H5.278C5.484 12.062 5.801 13.02 6.225 13.732C4.772 13.281 3.554 12.293 2.805 11ZM9.774 13.732C10.198 13.02 10.516 12.062 10.721 11H13.194C12.444 12.293 11.226 13.282 9.774 13.732Z";
const CHECK =
  "M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 1 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z";

function CopyButton({
  command,
  variant = "default",
}: {
  command: string;
  variant?: "default" | "global";
}) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(command).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button
      type="button"
      class={copied ? "copy copied" : "copy"}
      title={command}
      aria-label={`Copy: ${command}`}
      onClick={copy}
    >
      <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true">
        <path d={copied ? CHECK : variant === "global" ? SCOPE_GLOBAL : SCOPE_PROJECT} />
      </svg>
    </button>
  );
}

export default function Catalog({ packages }: { packages: Package[] }) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<string | null>(null);
  const [sort, setSort] = useState<Sort>("name");

  const kinds = useMemo(() => {
    const counts = new Map<string, number>();
    for (const p of packages) counts.set(p.kind, (counts.get(p.kind) ?? 0) + 1);
    return [...counts.entries()].sort(
      (a, b) => kindOrder(a[0]) - kindOrder(b[0]) || a[0].localeCompare(b[0]),
    );
  }, [packages]);

  const q = query.trim().toLowerCase();
  const shown = packages
    .filter((p) => {
      if (kind && p.kind !== kind) return false;
      if (!q) return true;
      return [
        p.name,
        p.description ?? "",
        p.namespace,
        p.kind,
        p.ref,
        p.summary ?? "",
        (p.keywords ?? []).join(" "),
      ].some((field) => field.toLowerCase().includes(q));
    })
    .sort((a, b) => compare(a, b, sort));

  return (
    <section>
      <div class="controls">
        <input
          type="search"
          placeholder={`Search ${packages.length} packages…`}
          value={query}
          onInput={(e) => setQuery((e.target as HTMLInputElement).value)}
          aria-label="Search packages"
        />
        <div class="chips" role="group" aria-label="Sort by">
          <button
            type="button"
            class={sort === "name" ? "chip active" : "chip"}
            onClick={() => setSort("name")}
          >
            name
          </button>
          <button
            type="button"
            class={sort === "updated" ? "chip active" : "chip"}
            onClick={() => setSort("updated")}
          >
            updated
          </button>
        </div>
        <div class="chips" role="group" aria-label="Filter by kind">
          <button
            type="button"
            class={kind === null ? "chip active" : "chip"}
            onClick={() => setKind(null)}
          >
            all <small>{packages.length}</small>
          </button>
          {kinds.map(([k, count]) => (
            <button
              key={k}
              type="button"
              class={kind === k ? `chip active kind-${k}` : `chip kind-${k}`}
              onClick={() => setKind(kind === k ? null : k)}
            >
              {k} <small>{count}</small>
            </button>
          ))}
        </div>
      </div>

      {shown.length === 0 ? (
        <p class="empty">No packages match.</p>
      ) : (
        <ul class="grid">
          {shown.map((p) => (
            <li key={`${p.namespace}/${p.name}`} class="card">
              <div class="card-head">
                {p.logo ? (
                  <img class="card-logo" src={p.logo} alt="" loading="lazy" />
                ) : (
                  <span
                    class="card-logo card-logo-fallback"
                    aria-hidden="true"
                    style={{ background: `var(--kind-${p.kind}, var(--muted))` }}
                  >
                    {p.name[0]?.toUpperCase()}
                  </span>
                )}
                <h2>
                  <a href={`/p/${p.namespace}/${p.name}/`}>{p.name}</a>
                </h2>
                {p.deprecated ? (
                  <span class="badge deprecated">deprecated</span>
                ) : (
                  <span class={`badge kind-${p.kind}`}>{p.kind}</span>
                )}
              </div>
              <p class="namespace">{p.namespace}</p>
              {(p.version || p.license || p.created) && (
                <div class="meta-row">
                  {p.version && <span class="pill version">v{p.version}</span>}
                  {p.license && <span class="pill license">{p.license}</span>}
                  {p.created && timeAgo(p.created) && (
                    <time class="updated" datetime={p.created} title={p.created}>
                      updated {timeAgo(p.created)}
                    </time>
                  )}
                </div>
              )}
              {p.deprecated && (
                <p class="deprecated-strip">
                  deprecated
                  {p.replacedBy ? ` — replaced by ${p.replacedBy}` : ""}
                </p>
              )}
              {p.description && <p class="description">{p.description}</p>}
              {p.keywords && p.keywords.length > 0 && (
                <div class="keywords">
                  {p.keywords.slice(0, 5).map((kw) => (
                    <button
                      key={kw}
                      type="button"
                      class="chip keyword"
                      onClick={() => setQuery(kw)}
                    >
                      {kw}
                    </button>
                  ))}
                  {p.keywords.length > 5 && (
                    <span class="chip keyword overflow">
                      +{p.keywords.length - 5}
                    </span>
                  )}
                </div>
              )}
              <div class="card-foot">
                <div class="copy-group">
                  <CopyButton command={`grim add ${p.ref}`} />
                  <CopyButton
                    command={`grim add --global ${p.ref}`}
                    variant="global"
                  />
                  <a
                    class="copy vscode"
                    href={`vscode://grimoire-rs.grimoire-vscode/open?repo=${encodeURIComponent(p.ref)}`}
                    title="Open in VS Code (Grimoire extension)"
                    aria-label={`Open ${p.name} in VS Code`}
                  >
                    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                      <path
                        fill="currentColor"
                        d="M23.15 2.587L18.21.21a1.494 1.494 0 0 0-1.705.29l-9.46 8.63-4.12-3.128a.999.999 0 0 0-1.276.057L.327 7.261A1 1 0 0 0 .326 8.74L3.899 12l-3.573 3.26a1 1 0 0 0 .001 1.479L1.65 17.94a.999.999 0 0 0 1.276.057l4.12-3.128 9.46 8.63a1.492 1.492 0 0 0 1.704.29l4.942-2.377A1.5 1.5 0 0 0 24 20.06V3.939a1.5 1.5 0 0 0-.85-1.352zm-5.146 14.861L10.826 12l7.178-5.448v10.896z"
                      />
                    </svg>
                  </a>
                </div>
                {p.repository && (
                  <a
                    class="source"
                    href={p.repository}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    source
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
