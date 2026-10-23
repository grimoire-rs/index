# grim-essentials

Teaches your coding agent to work with [grim](https://grimoire.rs), the package
manager for AI-agent config, and to write good config of its own.

## What it is for

- **Using grim.** Ask the agent to find, install, update or publish skills,
  rules, agents and MCP servers, and it drives the `grim` CLI for you.
- **Writing agent config.** Ask it to write or review a skill, a rule, an agent
  definition or an always-on instruction, and it follows proven patterns: when
  to use which, how long each should be, how to make a skill trigger.
- **Packaging for grim.** Ask it to turn a skill, rule, agent, MCP server, hook
  or bundle into something `grim build` and `grim release` accept.

## How to use it

Install the plugin, then talk to your agent as usual. The skills load on their
own when a request matches, for example:

- "Find a code review skill and install it into this project."
- "Review this SKILL.md and tell me why it never triggers."
- "Package `skills/release-notes` and publish it to our registry."

Add the marketplace and install the plugin from it; the
[marketplace README](https://github.com/grimoire-rs/marketplace#add-this-marketplace)
has the commands for each client. If you use grim, install the bundle instead
to get pinned, updatable copies:

```sh
grim add ghcr.io/grimoire-rs/bundles/grim-essentials:0
```
