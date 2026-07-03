# grim package index

Package index for [grim](https://grimoire.rs) — the OCI-backed package
manager for AI skills and rules. Served at **https://index.grimoire.rs**.

This repository is a *phone book, not a catalog*: it stores pointers to
packages hosted on OCI registries (GHCR, Docker Hub, private registries).
Versions are resolved live from the registry — the index only answers
"what packages exist and where do they live."

## Layout

```
index/
  github.com/<login>/          # namespace = your GitHub identity
    <package>/
      metadata.json            # pointer + description + ownership
```

Namespaces are derived from GitHub identity — `index/github.com/<login>/`
can only be modified by pull requests authored by `<login>` (or public
members of the `<login>` organization). No reservation process: your
first PR creates your namespace. Vanity namespaces (top-level, without
the `github.com/` prefix) are reserved and require maintainer approval.

## metadata.json

```json
{
  "schema": 1,
  "name": "my-skill",
  "kind": "skill",
  "ref": "ghcr.io/you/skills/my-skill",
  "description": "One-line description shown in grim search.",
  "repository": "https://github.com/you/my-skill",
  "owner": { "github": "you", "id": 12345 }
}
```

| Field | Meaning |
|---|---|
| `schema` | Metadata schema version, currently `1` |
| `name` | Package name — must equal the directory name |
| `kind` | `skill`, `rule`, `agent`, `mcp`, or `bundle` |
| `ref` | OCI reference (registry/repository, no tag) grim resolves against |
| `description` | One line, shown in `grim search` |
| `repository` | Source repository URL |
| `owner.github` | GitHub login owning the namespace |
| `owner.id` | Numeric GitHub account ID (immutable — logins can be recycled) |

## Publishing a package

1. Push your package to any OCI registry (`grim release` / `grim publish`)
2. Open a PR adding `index/github.com/<your-login>/<package>/metadata.json`
   — or let `grim publish --announce` open it for you
3. CI validates and auto-merges when **all** of these hold:
   - only `index/github.com/<ns>/<pkg>/metadata.json` paths changed
   - `<ns>` is the PR author's login, or an org the author is a
     **public** member of
   - `owner.github` matches `<ns>` and `owner.id` matches the account's
     numeric GitHub ID
   - the metadata passes schema validation
   - `ref` is reachable: the registry lists at least one tag (publish
     before you announce)

Anything else (vanity namespaces, script changes, unreachable refs)
falls through to manual maintainer review.

## Consuming

The compiled index is served as static files:

- `https://index.grimoire.rs/all.json` — every package, one array
- `https://index.grimoire.rs/index/github.com/<login>/<package>/metadata.json`
  — single package, path-addressable

grim consumes this via the per-registry `index` property (the built-in
default registry ships with it preconfigured):

```toml
[[registries]]
index = "https://index.grimoire.rs"           # https static files…
# index = "https://github.com/you/index.git"  # …or any git repository
```

When `index` is set, browse/search reads the index instead of the OCI
`/v2/_catalog` endpoint (which GHCR does not offer). Point it at any
fork of this repository — served as static files or as a plain git
repo — to run a private index.

## Development

Toolchain (task, node, python) is pinned in [`ocx.toml`](./ocx.toml) and
bootstrapped by [ocx](https://ocx.sh) — locally via direnv
(`direnv allow`, PATH comes from `.envrc`), in CI via `ocx-sh/setup-ocx`.

```sh
task --list   # all tasks
task verify   # validator self-checks + full artifact build
task serve    # build and serve the composed dist/ on :8080
task dev      # Astro dev server with hot reload (site/ only)
```

Without direnv, prefix commands with `ocx run go-task -- task …`.

## Running on self-hosted GitLab

Fork or import this repository into your GitLab instance — the shipped
`.gitlab-ci.yml` gives you the same validate/auto-merge/Pages pipeline
(the `.github/` workflows stay inert there):

1. Import the repo, protect the default branch.
2. Create a group or project access token (`api` scope, merge rights)
   and set it as the **masked** CI/CD variable `GRIM_INDEX_BOT_TOKEN`.
3. Pointers live at `index/<your-gitlab-host>/<group>/<pkg>/metadata.json`
   (nested groups allowed) with `owner.login` = the group path and
   `owner.id` = the GitLab namespace id. MRs auto-merge when the author
   is a member of the namespace group (`GRIM_INDEX_MIN_ACCESS_LEVEL`,
   default Developer) and all pointer checks pass.
4. Consume via `index = "https://<host>/<group>/index.git"` (private
   repos work through ambient git credentials) or GitLab Pages.

Full guide: [grimoire.rs — Self-Hosted GitLab Setup][self-hosted].

[self-hosted]: https://grimoire.rs/self-hosted-gitlab.html

## License

Metadata in this repository is [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
