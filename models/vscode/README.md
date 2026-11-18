# VS Code adapter

Rules: [CLAUDE.md](../../CLAUDE.md), [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Files in this repository, none of which is a contract:

| file | what it does |
|---|---|
| [headron.code-workspace](../../headron.code-workspace) | multi-root Microsoft workspace with unified settings and extension recommendations |
| [.vscode/extensions.json](../../.vscode/extensions.json) | workspace-recommended extensions (Copilot, Python, Ruff) |
| [.vscode/mcp.json.example](../../.vscode/mcp.json.example) | MCP servers, **pinned** — copy to `mcp.json`, never `@latest` |
| [.vscode/tasks.json](../../.vscode/tasks.json) | the instruments as tasks, so a verdict is one keystroke |
| [.vscode/launch.json](../../.vscode/launch.json) | debug the harness itself |

## What it is routed for

`interactive_edit`, and `ide_is_not_enforcement` is a hard invariant with a check behind it: an
editor setting is a convenience, never a gate. The gate is CI and the ruleset.

## The mistake it makes

**Trusting a green editor.** Extensions lint what they were configured for and nothing else.
`python scripts/atlas.py check` is the repository's verdict; the editor is a preview of it.

Official: https://code.visualstudio.com/docs
