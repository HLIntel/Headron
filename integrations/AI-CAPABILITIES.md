# AI Capabilities

These mechanisms solve different problems.

| Mechanism | Best purpose |
|---|---|
| model instructions | always-true constraints |
| Skill | reusable procedure/reference |
| hook | deterministic action/enforcement |
| plugin | package multiple capabilities |
| MCP | external tools/resources |
| connector | maintained external service |
| subagent | context isolation |
| memory | durable facts/decisions |

Use the smallest mechanism that satisfies the requirement.

MCP: use narrow schemas, deterministic tool names/order, bounded results, pagination, explicit side effects, least privilege, approval for high-impact calls, and time/rate limits.

Skills: keep procedures concise; move long reference tables into docs.

Memory: store durable facts/decisions with scope, provenance, and version; do not store transcripts.

Plugins: bundle coherent capabilities and avoid overlapping instructions.

Connectors: send only data required for the task and keep permissions scoped.