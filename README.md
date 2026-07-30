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

This repository holds **the data and the CI that acts on it**. The gate,
the build, the site renderer and the registry enrichment all live in
[`@grimoire-rs/indexer`](https://github.com/grimoire-rs/indexer) — fix
tooling there, then bump the dependency here the ordinary npm way.
`package-lock.json` is the single pin: CI runs `npm ci`, so which renderer
judges a contribution is a reviewed fact in this repository rather than a
resolution that happens on a runner.

```sh
npm ci             # install the pinned renderer
npm run dev        # serve this index locally, with live reload
npm run build      # compile index/ and render the site into dist/
npm run enrich     # refresh enrich/ from the live registry (online, needs grim)
npm run ci         # re-render .github/workflows/ after editing index.config.json
npm run ci:check   # fail on drift (what the verify-ci job runs)
```

`task --list` wraps the same scripts, and the toolchain (task, node, grim)
is pinned in [`ocx.toml`](./ocx.toml) and bootstrapped by
[ocx](https://ocx.sh) — locally via direnv (`direnv allow`, PATH comes from
`.envrc`), in CI via `ocx-sh/setup-ocx`. Without direnv, prefix commands
with `ocx run go-task -- task …`.

### The workflows are generated

`.github/workflows/{pages,validate,verify-ci}.yml` are rendered from the
`ci` block of `index.config.json` and committed here. Edit the config and
run `npm run ci`; do not hand-edit the files, because the `verify-ci` job
re-renders and diffs on every push and pull request. Action pins are
excluded from that diff, so Renovate may bump `uses: owner/action@<ref>`
freely. `dco.yml` and `refresh.yml` are this repository's own and are not
generated.

## Running your own index

You do not need to fork this repository — scaffold a fresh one:

```sh
npx @grimoire-rs/indexer init
```

That writes the `index/` tree, the site config, the trust policy, a real
npm project, and the CI for whichever forge your git remote names.
Contributors announce into it with `grim publish --announce`; the gate
decides what auto-merges. Nothing in the default setup needs a secret.

Or start from
[`grimoire-rs/index-template`](https://github.com/grimoire-rs/index-template)
— "Use this template", clone, then `npm install && npm run setup`.

## Running on self-hosted GitLab

Scaffold the index with `"forge": "gitlab"` in the `ci` block (or let
`init` read it off a GitLab remote) and `npm run ci` writes a
`.gitlab-ci.yml` carrying the same gate and a Pages deploy. This
repository is GitHub-hosted, so it ships no GitLab pipeline of its own —
importing it gives you the data, not the CI. Then:

1. Import the repo, protect the default branch.
2. Pointers live at `index/<your-gitlab-host>/<group>/<pkg>/metadata.json`
   (nested groups allowed) with `owner.login` = the group path and
   `owner.id` = the GitLab namespace id. The gate passes when the author
   is a member of the namespace group and all pointer checks pass.
3. **Merging is an instance-side policy.** An MR supplies its own
   `.gitlab-ci.yml`, so a contributor can delete the gate job outright —
   enforce it with a required merge check, protected-branch approval
   rules, or a compliance pipeline, or treat the GitLab gate as advisory.
4. Consume via `index = "https://<host>/<group>/index.git"` (private
   repos work through ambient git credentials) or GitLab Pages.

Full guide: [grimoire.rs — Self-Hosted GitLab Setup][self-hosted].

[self-hosted]: https://grimoire.rs/self-hosted-gitlab.html

## License

Metadata in this repository is [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
