# Packages, tools and CLIs — where each roster lives

This page held two hand-written lists: a repository-wide tool list and an MCP list. Both are owned
elsewhere, and a second copy can only disagree.

| roster | owner | how to read it |
|---|---|---|
| what the harness needs | [pyproject.toml](../pyproject.toml) and [scripts/requirements.lock.txt](../scripts/requirements.lock.txt) | rendered in [the README's packages table](../README.md#packages-and-dependencies); `python scripts/atlas.py doctor` says whether this machine has it |
| what a language needs | `languages/<route>/tools.yaml` | `python scripts/atlas.py route <file>`; `python scripts/packprobe.py --mode smoke` says which of those commands actually run here |
| which MCP servers a task may activate | [atlas.yaml](../atlas.yaml) `tool_profiles` | rendered in [wiki/CODE-ROUTING.md](../wiki/CODE-ROUTING.md); the example configuration is [.vscode/mcp.json.example](../.vscode/mcp.json.example), pinned, not `@latest` |
| what CI installs | [.github/workflows/atlas-ci.yml](../.github/workflows/atlas-ci.yml) | hash-pinned from the lock, with `--require-hashes` |

**Native language tooling stays canonical.** MCP servers, AI tools and IDE extensions extend
capability; they never replace a compiler, an LSP, a debugger, a test runner, a profiler or a
package manager. A capability is derived from the running process, never from a roster — which is
why every roster above names the instrument that answers for it.
