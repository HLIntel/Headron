# MCP + Language Matrix

Native first. MCP second.

The compiler, language server, debugger, formatter, test runner, profiler, and package manager
remain authoritative. MCP extends capability where the native stack does not provide efficient
agent access. `atlas.yaml/tool_profiles` declares what activates; `integrations/MCP-PROFILES.md`
maps tasks to profiles.

## Shared MCP roles

| Role | Capability |
|---|---|
| remote forge | repository, code, issues, PRs, CI runs, security context |
| semantic edit | semantic code retrieval and editing through the language server (LSP-backed) |
| browser | browser / UI automation and integration tests |
| docs | current library and framework documentation |
| database | multi-database SQL and schema inspection with explicit guardrails |
| security scan | deterministic static security scanning |

See `integrations/MCP-PROFILES.md` for which role a task justifies and how to enable it.
Enable only the profile the task names — an unused server's tool descriptions are paid on every
request: `atlas.yaml/developer_baseline/mcp`.

## Language routing

The pattern is always: **native toolchain first, MCP second, only where the native stack lacks
efficient agent access.**

- **Python** — native language server / type checker / formatter / test runner / debugger; add semantic-edit, forge, docs, security-scan.
- **Rust** — native language server / compiler / linter / debugger; add semantic-edit, forge, docs, security-scan.
- **Go** — native language server / debugger / formatter / test runner / race detector / profiler; add semantic-edit, forge, docs, security-scan.
- **TypeScript / JavaScript** — native TS service / debugger / test stack; add semantic-edit, forge, docs, browser, security-scan.
- **C / C++** — native compiler / language server / debugger / sanitizers; add semantic-edit, forge, docs, security-scan where supported.
- **Zig** — native language server / toolchain; add semantic-edit, forge, docs, security-scan where supported.
- **Mojo** — native accelerator stack; forge + docs; semantic MCP only when parser support is verified.
- **Julia** — native language server / package manager / profiler; add semantic-edit, forge, docs, security-scan.
- **Elixir / Gleam** — native BEAM / LSP / build tooling; add semantic-edit, forge, docs, security-scan.
- **Haskell / F#** — native language server / compiler / formatter; add semantic-edit, forge, docs, security-scan.
- **Lean 4** — native extension / build system / kernel; add semantic-edit, forge, docs.
- **SQL** — native database clients / migration tools first; add database (read-only), forge, docs.
- **Bash** — terminal / shell linter / language server first; add semantic-edit, forge, security-scan; avoid shell-execution MCP duplication.
- **WebAssembly / WASI** — native compiler / runtime / component tooling first; add forge, docs.
- **CUDA** — native compiler / debugger / profiler first; add semantic-edit, forge, docs, security-scan where supported.
- **Carbon / Roc** — experimental native toolchains; forge + docs; semantic MCP only after support verification.
- **Nim / V / Odin / Hare / OCaml / Scala / R / Forth and other low-volume languages** — native toolchain first; forge + docs; semantic MCP only after support verification.

## Profiles

Defined once in [MCP-PROFILES.md](MCP-PROFILES.md) and machine-readable as `atlas.yaml/tool_profiles`.

Do not enable every server at once.
