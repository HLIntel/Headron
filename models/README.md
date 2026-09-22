# Models

The model layer adapts one repository contract to multiple AI coding runtimes.

| Runtime | Guide | Primary capability |
|---|---|---|
| Claude Code | [claude](claude/README.md) | agentic coding + Skills/hooks/MCP/subagents |
| Cursor | [cursor](cursor/README.md) | editor-first coding + rules/skills/MCP |
| OpenAI/Codex | [openai](openai/README.md) | reasoning + tools/MCP/connectors/API |
| OpenCode | [opencode](opencode/README.md) | provider-flexible terminal coding |
| Hermes | [hermes](hermes/README.md) | persistent agent + bots + memory |
| LLM providers | [llm](llm/README.md) | endpoint/credential/provider layer |
| routing | [ROUTING.md](ROUTING.md) | dynamic capability selection |
| agent layer | [agents](agents/README.md) | generic agent design |

Repository guarantees remain model-independent.