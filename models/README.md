# Models and Runtime Hosts

Model adapters sit below MODEL.md and above the language/integration Atlas.

| Runtime/host | Adapter |
|---|---|
| Claude Code | [claude/](claude/README.md) |
| Cursor | [cursor/](cursor/README.md) |
| OpenAI/Codex | [openai/](openai/README.md) |
| OpenCode | [opencode/](opencode/README.md) |
| Hermes | [hermes/](hermes/README.md) |
| VS Code | [vscode/](vscode/README.md) |
| LLM | [llm/](llm/README.md) |
| Agents | [agents/](agents/README.md) |

See [ROUTING.md](ROUTING.md) for task and host routing.

## What each runtime reads before it starts

<!-- BEGIN generated: runtime-entry (python scripts/atlas.py index --write) -->
| runtime | loads by itself | ~tokens |
|---|---|---|
| **Claude Code** | `CLAUDE.md` | 1,095 |
| Codex | `AGENTS.md` | 1,027 |
| Cursor | `AGENTS.md` | 1,027 |
| opencode | `AGENTS.md` | 1,027 |
| Zed | `AGENTS.md` | 1,027 |
| Hermes | `.agent/bootstrap.json` | 641 |
| any model given a link | `llms.txt` | 1,097 |
| any chat assistant | `CHAT.md` | 2,281 |

Measured from each file on every build.
<!-- END generated: runtime-entry -->
