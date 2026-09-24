# Tool Orchestration

The cleanest agent workflow is a bounded composition of specialized tools, not a universal tool dump.

## Tool-inside-tool model

```text
model/runtime
   |
   v
Atlas router
   |
   +--> native compiler / LSP / debugger / tests
   +--> semantic repository context
   +--> GitHub repository/PR/issue state
   +--> current docs
   +--> browser/UI
   +--> database
   +--> security analysis
   |
   v
independent verifier
   |
   v
CI / release gate
```

A higher-level tool can orchestrate lower-level tools, but each lower layer keeps one authoritative responsibility.

## Composition rule

1. Route by artifact and task.
2. Load native language tooling first.
3. Add one semantic repository layer when symbol/context retrieval materially helps.
4. Add GitHub only when GitHub state or automation is needed.
5. Add docs only when current external API information is needed.
6. Add browser/database/security only for those capability classes.
7. Finish with deterministic verification.

## Capability graph

| Capability | Authority | Extension |
|---|---|---|
| compile/type | compiler/type checker | LSP |
| symbols/context | LSP | Serena |
| repo/PR state | Git/gh/GitHub | GitHub MCP |
| current docs | upstream docs | Context7 |
| browser | browser runtime | Playwright |
| database | native client/query plan | DBHub |
| source security | CodeQL/native scanner | Semgrep |
| dependencies | package manager + lockfile | Dependabot/dependency review |
| secrets | secret manager/environment | GitHub secret scanning |
| proof | Lean kernel | AI assistant |
| runtime | profiler/telemetry | observability backend |
| review | diff + deterministic checks | Copilot review |

## Profiles

`core-code` = native + GitHub + Serena where supported.

`docs` = upstream docs + Context7 when needed.

`browser` = native HTTP tests + Playwright.

`database` = native DB tooling + DBHub read-only exploration.

`security` = CodeQL/native + Semgrep + dependency/secret controls.

`polyglot` = native tools on both sides + schema/ABI + boundary tests.

## The “inside tools” rule

Use a tool as an orchestrator only when it reduces duplicated context or control.

Good:
`CodeQL finding -> Copilot Autofix proposal -> native tests -> CI`

Good:
`Atlas route -> language guide -> Serena semantic lookup -> exact symbol edit -> compiler/test`

Good:
`GitHub MCP -> issue/PR state -> focused file retrieval -> local/native verification`

Avoid:
`agent -> MCP -> agent -> MCP -> shell -> browser -> database` for a task that one native tool can solve.

## Tool budgets

Bound model/tool calls, repository reads, browser/database queries, retries, execution time, changed paths, and external side effects.

The best tool is the smallest one that crosses the required capability boundary.

## Verification ladder

**This page used to state its own order, and it was the fourth in the tree.** `atlas.yaml`
declares the tiers, [docs/VERIFY.md](../docs/VERIFY.md) renders them in a generated block, and
`MODEL.md` names them — so a fourth ordering here could only disagree with three documents at
once. The tiers are `fast → standard → deep → release`, cheapest sufficient first, and what each
one adds is generated from the declaration rather than written here.

Ask the atlas for the answer to one change:

```bash
python scripts/atlas.py plan path/to/file.ext --task debugging --change source_change --json
```
