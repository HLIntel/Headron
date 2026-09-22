# VS Code Runtime / Agent-Host Adapter

VS Code is the interactive editor, debugger, task launcher, remote-development client, source-control surface, and optional AI/MCP host. It is a host layer, not a model provider.

## Map

| Atlas need | VS Code surface |
|---|---|
| source navigation | language extensions / language servers |
| editing/refactoring | editor + language service |
| debugging | Run and Debug + debugger extension |
| test loop | Test Explorer + test/debug adapters |
| deterministic commands | integrated terminal + Tasks |
| launch/attach | `.vscode/launch.json` |
| repository ergonomics | workspace settings + Git |
| multi-project work | multi-root workspaces |
| remote code/runtime | SSH, WSL, Dev Containers, Codespaces |
| AI models | model picker / BYOK / Copilot where available |
| custom agent roles | `.github/agents/*.agent.md` |
| external AI capabilities | MCP |
| authoritative enforcement | CI/rulesets/policy outside VS Code |

## Routing

Use VS Code for interactive state and human inspection. Route autonomous or long-running terminal-native coding to OpenCode/Hermes as appropriate.

`task -> model/runtime -> worktree -> VS Code inspect/debug -> verify`

For a debugging task:
`reproduce -> attach/launch debugger -> breakpoint/stack/locals -> isolate cause -> patch -> regression test -> full verification`

For a performance task:
`reproduce workload -> profile -> inspect hot path -> patch -> benchmark -> compare -> verify`

For concurrency:
`reproduce interleaving/deadlock/race -> runtime-specific detector/debugger -> inspect state -> bound workers/queues/time -> regression test`

## OpenCode coexistence

Keep OpenCode's workspace as the agent execution surface. Open the same worktree in VS Code when one writer owns it.

When tasks are parallel, prefer:
`worktree-A -> OpenCode agent A -> VS Code A`
`worktree-B -> OpenCode agent B -> VS Code B`

Do not let two autonomous writers mutate the same worktree without explicit coordination.

## Tool discipline

Use the smallest surface:
- navigation -> symbols/search
- debugging -> debugger
- builds/tests -> Tasks/terminal
- external services -> narrow MCP/connector
- GitHub operations -> Git/gh/GitHub tools according to `integrations/GITHUB.md`
- security -> scanners/CI
- enforcement -> hooks/CI/policy

Do not duplicate the full MODEL contract here.

## Security

Workspace tasks, extensions, MCP servers, and agent tools can execute or cause actions. Review repository-provided configuration before trusting it; never commit secrets. Keep destructive actions outside ordinary coding tasks or require explicit approval.

Official: https://code.visualstudio.com/docs/
