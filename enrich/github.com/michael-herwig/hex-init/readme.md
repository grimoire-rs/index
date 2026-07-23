# hex

Tiered multi-agent swarm orchestration for the full feature lifecycle:
planning, contract-first TDD execution, adversarial review, and
architecture design. Generalized, client-neutral — no assumptions about
which AI coding client you run it in.

## Quickstart

```sh
grim add ghcr.io/michael-herwig/hex
```

Then, in a project:

```
/hex-init
/hex-plan <task>
```

`/hex-init` audits your project's context (CLAUDE.md/AGENTS.md-equivalent)
for what the swarm needs — how to verify, where specs/plans live — and
bootstraps its own memory file. `/hex-plan` decomposes a task into a
reviewed, contract-first plan; `/hex-execute` implements it;
`/hex-review` runs an adversarial pass before it lands; `/hex-architect`
handles decisions that are hard to reverse.

## Members

| Skill | What it does |
|---|---|
| [`hex-core`](hex-core/) | Shared reference library — worker roles, model matrix, swarm protocol, memory spec. Never invoked directly. |
| [`hex-init`](hex-init/) | Audits and bootstraps a project for the swarm: verification, conventions, `.agents/memory/hex.md`. |
| [`hex-plan`](hex-plan/) | Decomposes a feature/issue/PR into a contract-first TDD plan through discover, research, design, decompose, and review. |
| [`hex-execute`](hex-execute/) | Implements a plan or free-text task: stub, specify, implement, review-fix loop, commit. |
| [`hex-review`](hex-review/) | Adversarial pre-merge review of a branch, PR, or diff — reports findings and a verdict, never auto-fixes. |
| [`hex-architect`](hex-architect/) | Design specs, ADRs, and trade-off analysis for decisions that are hard to reverse. |

## Tier grammar

Every orchestrator (except `hex-init`, which has no tiers) scales its work
through one shared tier **vocabulary** — `low|medium|high`+`auto` mean the
same thing in every project:

| Tier | Intent |
|---|---|
| `low` | Two-way door: flag/option change, doc edit, ≤3 files, one area |
| `medium` | One-way-door, medium blast radius: new command, new storage/index layout, 1–2 areas |
| `high` | One-way-door, high blast radius: new module/package, breaking API, cross-area, protocol change |
| `auto` (default) | The orchestrator classifies signals and picks one of the above, shown at the approval gate |

`xhigh` and `max` are reserved for future overlay stacks — the classifier
never emits them; an explicit request for either runs `high` instead.

Per-tier **content** — phase spawn counts (via `tiers`), and later the phase
plan itself (via `workflows`, reserved for a future release) in
`hex.md › Preferences`, see
[`config.md`](hex-core/references/config.md) — is project-overridable and
announced whenever a project redefines it, **even when the resolved counts
equal shipped**: the label never travels without its deltas.

Each orchestrator asks for exactly **one approval**, before any work
starts, showing the fully resolved tier, overlays, and spawn set with
where each choice came from. No mid-flow questions.

## Two-layer knowledge

hex is the outer loop, not a second source of truth. Anything the swarm
needs to know about *your project* — how to verify, where specs/plans
live, which rules matter — belongs in your project's own context
(CLAUDE.md, AGENTS.md, or equivalent), where every agent already reads
it; `/hex-init` audits that context and helps you fill gaps, it never
duplicates them into hex's own config.

The second layer, `.agents/memory/hex.md`, is swarm memory, not
project knowledge: an AI-maintained file the orchestrators read and
update themselves, holding cached pointers (not copies), user-owned
orchestration preferences — model overrides, perspectives of interest —
and working memory like active-plan tracking. It's plain markdown, meant
to be committed and shared across a team.

## Positioning

hex is a spec-driven-development toolkit like [github/spec-kit] and
[openspec.dev], and reuses their good ideas — but it is a **multi-agent
swarm**, not a single agent following a script, and it closes the SDD loop
neither competitor closes.

| Axis | hex | spec-kit | OpenSpec |
|---|---|---|---|
| Execution model | Tiered swarm: parallel work packages in git worktrees, topological merge, contract-first TDD | Single agent, sequential (`/implement`); worktree/DAG only in unreviewed community extensions | Single agent |
| Full SDD lifecycle | plan → execute → review → **fold-back into the spec** | plan → implement; no fold-back | plan → **fold-back** → but review is a 3-item checklist |
| Spec fold-back | A converged, approved plan's deltas fold back into the project's own spec home, guarded against silent requirement loss | — | Its one structural lead — but the deterministic guard was regressed into "use your judgment" |
| Config depth | Per-path reviewers, per-tier counts, tier lineage, capability-class model routing, a cross-model adversary — all as user config | Presets/workflow engine, but no swarm to configure | Minimal |
| Cross-repo work | One decision spanning many repos, one plan, one ID space, one union review | Separate projects | **Open** — its own issue #725, unsolved by Stores |
| Review rigor | Staged adversarial panel + a four-level **severity ladder** + an optional cross-model gate | Single-agent analyze | Single-agent, no severity type |

hex's lead is the swarm layer plus the fold-back that closes the loop: it
folds delivered, reviewed, converged work back into the project's spec (the
gap that leaves a spec-kit or bare-review project authoring its next plan
against a stale spec), and it coordinates a change across repos — the problem
OpenSpec's own tracker still lists as open.

[github/spec-kit]: https://github.com/github/spec-kit
[openspec.dev]: https://openspec.dev

## Non-goals

The deliberate trade-offs — where a competitor keeps a residual edge and hex
declines to chase it:

- **No deterministic parser or schema validation.** The client is the
  runtime; hex ships markdown an LLM reads, so its guarantees are prose that
  degrades gracefully, never a schema a binary checks (`DESIGN.md`). This is
  irreducible and it is the moat — portability across clients — not a gap to
  close. A project that needs a validating parser wants a different tool.
- **Not chasing 34-client breadth.** spec-kit integrates dozens of clients
  through a per-client command-rewriting pipeline; hex stays client-neutral
  with plain dash-named skills and refuses that maintenance tax. Breadth is a
  cost we decline, not a race we are losing.
- **Full phase-reshaping config is v2.** A project can already re-weight
  spawn counts and reviewers per tier; forking a tier's whole *phase plan* as
  config ships a release later. It is schedule-gated, not design-gated — the
  format is specified today
  ([`config.md`](hex-core/references/config.md#workflows)).

## License

Apache-2.0.
