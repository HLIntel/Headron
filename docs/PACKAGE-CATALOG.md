# Packages, tools and CLIs — where each roster lives

This page held two hand-written lists: a repository-wide tool list and an MCP list. Both are owned
elsewhere, and a second copy can only disagree.

| roster | owner | how to read it |
|---|---|---|
| what the harness needs | [pyproject.toml](../pyproject.toml) and [scripts/requirements.lock.txt](../scripts/requirements.lock.txt) | rendered below from the declaration; `python scripts/atlas.py doctor` says whether this machine has it |
| what a language needs | `languages/<route>/tools.yaml` | `python scripts/atlas.py route <file>`; `python scripts/packprobe.py --mode smoke` says which of those commands actually run here |
| which MCP servers a task may activate | [atlas.yaml](../atlas.yaml) `tool_profiles` | rendered in [wiki/CODE-ROUTING.md](../wiki/CODE-ROUTING.md); the example configuration is [.vscode/mcp.json.example](../.vscode/mcp.json.example), pinned, not `@latest` |
| what CI installs | [.github/workflows/atlas-ci.yml](../.github/workflows/atlas-ci.yml) | hash-pinned from the lock, with `--require-hashes` |

**Native language tooling stays canonical.** MCP servers, AI tools and IDE extensions extend
capability; they never replace a compiler, an LSP, a debugger, a test runner, a profiler or a
package manager. A capability is derived from the running process, never from a roster — which is
why every roster above names the instrument that answers for it.

## The packages table, generated from the declaration

It lives here rather than on the landing page because it grows by a row per package, and the
landing page is held to a byte budget that only falls.

<!-- BEGIN generated: packages (python scripts/atlas.py index --write) -->
The atlas is not a library you install. One Python dependency runs the harness; every
language toolchain is declared by a pack and installed by the machine that needs it.

| package surface | value | where it is declared |
|---|---|---|
| harness package | `thea-harness` | declared in `pyproject.toml`; nothing is published to an index |
| python required | `>=3.11` | `pyproject.toml` |
| runtime dependency | `pyyaml>=6.0.3,<7` | `scripts/requirements.txt`, mirrored in `pyproject.toml` |
| what CI actually installs | `scripts/requirements.lock.txt` | hash-pinned and installed with `--require-hashes`; the contract asserts the pin sits inside the range above |
| quality extra | `ruff` | `pyproject.toml` `[project.optional-dependencies]` |
| language toolchains | declared per pack, installed by nobody here | `languages/<route>/tools.yaml`; run `python scripts/packprobe.py --mode smoke` |
<!-- END generated: packages -->
