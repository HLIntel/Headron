# AI Capabilities and Tool Composition

Different mechanisms solve different control problems.

| Mechanism | Best purpose | Authority |
|---|---|---|
| model instructions | always-true operating constraints | advisory |
| Skill | reusable procedure/reference | procedural |
| hook | deterministic action/enforcement | execution |
| plugin | coherent capability bundle | capability |
| MCP | external tools/resources | scoped capability |
| connector | maintained external service | service boundary |
| subagent | context isolation | isolated reasoning |
| memory | durable facts/decisions | persistent context |
| GitHub CodeQL | source security analysis | deterministic analysis |
| Copilot Autofix | targeted remediation proposal | AI proposal |
| Copilot code review | secondary PR review | AI review |
| Dependabot | dependency update automation | automation |
| dependency review | introduced dependency risk check | CI gate |
| secret scanning/push protection | credential leak prevention | platform control |
| Scorecard | supply-chain/workflow hygiene | deterministic analysis |

## Composition

Use the smallest mechanism that satisfies the requirement.

```text
route
 -> native tool
 -> semantic context if needed
 -> external capability if needed
 -> independent verifier
 -> CI
```

Never make an AI tool the only verifier of an AI-generated change.

MCP should use narrow schemas, deterministic tool names/order, bounded results, pagination, explicit side effects, least privilege, approval for high-impact calls, and time/rate limits.

Skills should keep procedures concise and link to durable reference docs rather than duplicating long tables.

Memory should store durable facts/decisions with scope, provenance, and version, not transcripts.

Plugins/connectors should bundle coherent capabilities and avoid overlapping policies.
