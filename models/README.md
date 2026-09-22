# Models and Runtime Hosts

Model adapters sit below `MODEL.md` and above the language/integration Atlas. Editor/agent hosts are included here when they materially change how models access code and tools.

| Runtime/host | Adapter | Distinct operating surface |
|---|---|---|
| Claude Code | `claude/` | CLAUDE.md, Skills, hooks, MCP, subagents |
| Cursor | `cursor/` | rules, Skills, MCP, editor/workspace context |
| OpenAI/Codex | `openai/` | reasoning, tools, MCP, connectors, API |
| OpenCode | `opencode/` | terminal/provider flexibility, agent workspace |
| Hermes | `hermes/` | persistent memory, Skills, messaging, bots, multi-provider |
| VS Code | `vscode/` | editor, language services, debugger, tasks, Git, remote dev, MCP/agents |
| LLM | `llm/` | provider endpoints, credentials, routing |
| Agents | `agents/` | generic agent lifecycle/capability model |

Each adapter should stay thin. The engineering contract belongs in `MODEL.md`.
