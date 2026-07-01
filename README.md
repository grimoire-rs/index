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
| `kind` | `skill`, `rule`, `agent`, or `bundle` |
| `ref` | OCI reference (registry/repository, no tag) grim resolves against |
| `description` | One line, shown in `grim search` |
| `repository` | Source repository URL |
| `owner.github` | GitHub login owning the namespace |
| `owner.id` | Numeric GitHub account ID (immutable — logins can be recycled) |

## Publishing a package

1. Push your package to any OCI registry (`grim release`)
2. Open a PR adding `index/github.com/<your-login>/<package>/metadata.json`
3. CI validates the manifest and namespace ownership; the PR is merged
   automatically when checks pass

## Consuming

The compiled index is served as static files:

- `https://index.grimoire.rs/all.json` — every package, one array
- `https://index.grimoire.rs/index/github.com/<login>/<package>/metadata.json`
  — single package, path-addressable

grim uses this automatically via the `index` config key (default:
`https://index.grimoire.rs`). Point it at any fork of this repository
served as static files to run a private index.

## License

Metadata in this repository is [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
