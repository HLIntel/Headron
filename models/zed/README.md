# Zed adapter

Rules: [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Zed's agent reads the first file it finds from `.rules`, `.cursorrules`, `.windsurfrules`, `.clinerules`,
`AGENT.md` and `AGENTS.md`, in that order. This repository tracks only `AGENTS.md`, so that is the one
it loads. Vendor reference: [Zed instructions](https://zed.dev/docs/ai/instructions).

## Dynamic connectivity & unbreakable discovery

Zed works inside the editor, beside the diff. To ensure unbreakable connectivity:
- **Dual-path invocation:** Run `headron port <file> --frame agent --json` (or fallback `python scripts/atlas.py port <file> --frame agent --json`).
- **Structured output:** Depend on `--json` records (`tools/atlas-output.schema.json`), never volatile prose.
- **Fail-safe verification:** Run the contract and verify strictly by exit code:
  ```bash
  python scripts/atlas.py check && python scripts/verify.py
  ```

## Native tools stay

Zed keeps every tool it ships with, configured in its own user and project settings, and it may
add, replace or drop any of them without asking Headron. Headron is added to this layer, never swapped
in for it: its terminal runs `headron` / `python scripts/atlas.py`, git runs the pre-commit hook, and an MCP context server may
mount the read-only route. An install writes only the git hook and never edits this runtime's tool
configuration (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`).

## The mistake it makes

**An older rule file that hides the rules.** Only the first match loads, so a leftover `.rules` or
`.cursorrules` in your repository means `AGENTS.md` is never read, and nothing says so. Remove that file
or reduce it to a pointer at `AGENTS.md`.
