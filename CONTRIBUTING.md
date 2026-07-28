# Contributing to the grim package index

## Layout

| Path | Purpose |
|------|---------|
| `index/` | Package pointers (`metadata.json` per package) — see [README](./README.md) |
| `enrich/` | Registry-refreshed sidecars (README, changelog, logo, versions) — not hand-edited |
| `index.config.json` | Branding and the "add this index" block the site renders |
| `index-policy.json` | Committed trust policy the gate reads: registry-host allowlist, reserved namespaces, trusted bots |
| `dist/` | Build output — generated, not committed |

The gate, the build, the site and the enrichment all live in
[`@grimoire-rs/indexer`](https://github.com/grimoire-rs/indexer); this
repository holds data and thin CI callers. Fix the tooling there.

## Adding or correcting an index entry

Most contributions are a single `index/github.com/<login>/<package>/metadata.json`
pointer, usually opened for you by `grim publish --announce`. Namespace
rules, the metadata schema, and the auto-merge conditions are documented in
the [README's "Publishing a package" section](./README.md#publishing-a-package)
— read that first. Fixing a mistake in your own entry is the same flow:
edit the file, open a PR, the same checks apply.

## Prerequisites

Toolchain (`task`, Node, `grim`) is pinned in [`ocx.toml`](./ocx.toml) and
bootstrapped by [ocx](https://ocx.sh):

- Locally: install direnv, then `direnv allow` — `.envrc` loads it.
- Without direnv: prefix commands with `ocx run go-task -- task ...`.

## Building & Testing

```sh
task build     # compile index/ + render the site into dist/
task enrich    # refresh enrich/ from the live registry (online, needs grim)
task verify    # CI gate: full artifact build
task serve     # build and serve dist/ locally (:8080)
```

There is no test suite here — the code these tasks run lives in
[`@grimoire-rs/indexer`](https://github.com/grimoire-rs/indexer) and is
tested there. What this repository can get wrong is data, and `task build`
fails on a malformed `metadata.json`.

## Commit Conventions

Not CI-enforced here, but repo history follows [Conventional
Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`,
`refactor:`, ...) — keep doing that.

Every commit also needs a `Signed-off-by` line — see [License](#license).
`git commit -s` adds it for you.

## Branch Model

- Branch from `main` — never commit directly to `main`.
- Keep commits atomic and complete — no WIP commits on shared branches.

## Before Submitting

```sh
task verify    # validator self-checks + full artifact build
task dco       # Signed-off-by check on main..HEAD
```

Both must pass before opening a pull request.

## License

This repository is licensed under the [Apache License, Version 2.0](LICENSE),
and contributions are accepted under that same license — inbound matches
outbound, as Apache-2.0 §5 already presumes. Nothing you contribute is
relicensed, and you keep the copyright in your own work.

**There is no CLA.** Instead, sign off your commits under the
[Developer Certificate of Origin](https://developercertificate.org/) — a
one-line statement that you wrote the patch, or otherwise have the right to
submit it under this license:

```sh
git commit -s          # appends: Signed-off-by: Your Name <you@example.com>
```

The name and email must be real, and the sign-off address must match the one
that authored the commit. If you are contributing work owned by an employer,
make sure you have their permission before you sign off.

CI checks this on every pull request that touches anything other than
`index/` — pointer-only PRs are exempt, since that data is
[CC0](./README.md#license), not code under the license above. If you forget,
`git rebase --signoff main..HEAD` fixes the whole branch at once. Run it
yourself with:

```sh
task dco                           # checks main..HEAD
```

The copyright holder named in `LICENSE` is **The Grimoire Authors** — that is
every person with a commit in this repository, as listed by:

```sh
git shortlog -sne
```

No separate contributor list is maintained; git history is the record.
