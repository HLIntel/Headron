# GitHub Copilot & Workspaces adapter

Rules: [CLAUDE.md](../../CLAUDE.md), [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Copilot and Copilot Workspaces read [.github/copilot-instructions.md](../../.github/copilot-instructions.md) at the repository root, which acts as the instruction pointer to [AGENTS.md](../../AGENTS.md). Keep any Copilot-specific instruction file thin and let it point there: a second copy of the rules is the drift this repository refuses.

## Microsoft Workspaces & Copilot Workspaces

Copilot Workspaces leverages the repository's native specifications:
- Multi-root Microsoft Workspaces: [`headron.code-workspace`](../../headron.code-workspace)
- Containerized dev environments: [`.devcontainer/devcontainer.json`](../../.devcontainer/devcontainer.json)
- Recommended IDE extensions: [`.vscode/extensions.json`](../../.vscode/extensions.json)
- Verification & inspection tasks: [`.vscode/tasks.json`](../../.vscode/tasks.json)

## Dynamic connectivity & unbreakable discovery

To remain resilient against upstream extension or model changes, invoke Headron through its dynamic contract:
- **Dual-path invocation:** Run `headron port <path> --frame agent --json` (or fallback `python scripts/atlas.py port <path> --frame agent --json`).
- **Structured output:** Depend on `--json` records (`tools/atlas-output.schema.json`), never volatile prose summaries.
- **Fail-safe verification:** Judge completion strictly on the process exit code:
  ```bash
  python scripts/atlas.py check
  ```

## What it is routed for

`interactive_edit` — fast inline suggestions, multi-file workspace proposals, and iterative edits with the editor's language diagnostics in the loop.

## Native tools stay

Copilot keeps every native tool it ships with — file, shell, search, edit, terminal, and agent execution tools — configured in its host environment (VS Code, Visual Studio, JetBrains, or GitHub Copilot Workspaces), and it may add, replace or drop any of them without asking Headron. Headron is added to this layer, never swapped in for it: its shell runs `python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through; its MCP client may mount the read-only Headron route beside whatever servers it already has. An install writes only the git hook (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract narrows commands only inside a run that opted into one.

## The mistake it makes

**Accepting completions without gate verification.** Copilot generates fluent syntax that may violate repository invariants, line caps, or import policies. Always verify on the exit code before marking an edit done:
```bash
python scripts/atlas.py check
```

Official: https://github.com/features/copilot
