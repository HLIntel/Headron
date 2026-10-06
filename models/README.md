# Models and Runtime Hosts

Model adapters sit below MODEL.md and above the language/integration Atlas.

Every runtime and its adapter: the generated roster in [MODEL.md](../MODEL.md).

See [ROUTING.md](ROUTING.md) for task and host routing.

## What each runtime reads before it starts

<!-- BEGIN generated: runtime-entry (python scripts/atlas.py index --write) -->
| runtime | loads by itself | ~tokens |
|---|---|---|
| **Claude Code** | `CLAUDE.md` | 1,070 |
| Codex | `AGENTS.md` | 1,003 |
| Cursor | `AGENTS.md` | 1,003 |
| opencode | `AGENTS.md` | 1,003 |
| Hermes | `.agent/bootstrap.json` | 649 |
| any model given a link | `llms.txt` | 1,083 |
| any chat assistant | `CHAT.md` | 2,362 |

Measured from each file on every build.
<!-- END generated: runtime-entry -->
