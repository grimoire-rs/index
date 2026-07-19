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
      {copied ? (
        <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
          <path
            fill="currentColor"
            d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 1 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"
          />
        </svg>
      ) : variant === "global" ? (
        <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
          <g transform="scale(0.7)">
            <path
              fill="currentColor"
              d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"
            />
            <path
              fill="currentColor"
              d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"
            />
          </g>
          <g fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round">
            <circle cx="12.6" cy="12.6" r="3.1" />
            <path d="M9.5 12.6h6.2" />
            <path d="M12.6 9.5v6.2" />
          </g>
        </svg>
      ) : (
        <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
          <path
            fill="currentColor"
            d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"
          />
          <path
            fill="currentColor"
            d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"
          />
        </svg>
      )}
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
