# Models

Model adapters sit below `MODEL.md` and above the language/integration Atlas.

| Runtime | Adapter | Distinct operating surface |
|---|---|---|
| Claude Code | `claude/` | CLAUDE.md, Skills, hooks, MCP, subagents |
| Cursor | `cursor/` | rules, Skills, MCP, editor/workspace context |
| OpenAI/Codex | `openai/` | reasoning, tools, MCP, connectors, API |
| OpenCode | `opencode/` | terminal/provider flexibility |
| Hermes | `hermes/` | persistent memory, Skills, messaging, bots, multi-provider |
| LLM | `llm/` | provider endpoints, credentials, routing |
| Agents | `agents/` | generic agent lifecycle/capability model |

Each adapter should stay thin. The engineering contract belongs in `MODEL.md`.