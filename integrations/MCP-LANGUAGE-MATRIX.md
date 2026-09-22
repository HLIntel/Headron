# MCP + VS Code Language Matrix

Native first. MCP second.

The compiler, LSP, debugger, formatter, test runner, profiler, and package manager remain authoritative. MCP extends capability where the native stack does not provide efficient agent access.

## Shared MCP layer

| MCP | Current status | Role |
|---|---|---|
| GitHub MCP Server | MIT, official, self-hostable | GitHub repositories, code, issues, PRs, Actions, security context |
| Serena | free/open-source; overall project GPL-3.0-or-later | semantic code retrieval/editing through LSP |
| Playwright MCP | Apache-2.0, local | browser/UI automation and integration tests |
| Context7 | MIT MCP server; hosted service optional | current library/framework documentation |
| DBHub | MIT, local | multi-database SQL/schema access with guardrails |
| Semgrep MCP | official Semgrep CLI integration | deterministic security scanning |

VS Code supports MCP through its gallery and workspace/user configuration. Local MCP servers are executable code and should be reviewed/trusted before startup.

## Language routing
- Python: native Python/Pyright/Ruff/debugger/pytest; add Serena, GitHub, Context7, Semgrep.
- Rust: native rust-analyzer/Cargo/Clippy/debugger; add Serena, GitHub, Context7, Semgrep.
- Go: native gopls/Delve/gofmt/test/race/pprof; add Serena, GitHub, Context7, Semgrep.
- TypeScript/JavaScript: native TS service/Node debugger/test stack; add Serena, GitHub, Context7, Playwright, Semgrep.
- C/C++: clangd/compiler/debugger/sanitizers first; Serena + GitHub + Context7 + Semgrep where useful.
- Zig: ZLS/zig toolchain first; Serena + GitHub + Context7 + Semgrep where supported.
- Mojo: native Modular/Mojo/accelerator stack; GitHub + Context7, semantic MCP only when parser support is verified.
- Julia: Julia extension/LanguageServer.jl/Pkg/profiler; Serena + GitHub + Context7 + Semgrep.
- Elixir/Gleam: native BEAM/LSP/Mix/Gleam tooling; Serena + GitHub + Context7 + Semgrep.
- Nim/V/Odin/Hare/Futhark/Chapel/BQN/Uiua: native toolchain first; GitHub + Context7; semantic MCP only after support verification.
- Haskell/F#: HLS/GHC or .NET/FsAutoComplete first; Serena + GitHub + Context7 + Semgrep.
- Lean 4: Lean extension/Lake/elan/kernel; Serena + GitHub + Context7.
- Carbon/Roc: experimental native toolchains; GitHub + Context7; semantic MCP only after support verification.
- Q#/Qiskit/Silq: native quantum tooling; GitHub + Context7; generic semantic layer only where supported.
- CUDA: CUDA/NVIDIA compiler/debugger/profiler first; Serena + GitHub + Context7 + Semgrep where supported.
- SQL: database clients/migrations/plans first; DBHub + GitHub + Context7, defaulting to read-only connections.
- Bash: terminal/ShellCheck/bash LSP first; Serena + GitHub + Semgrep; avoid shell-execution MCP duplication.
- WebAssembly/WASI: native compiler/runtime/component tooling first; GitHub + Context7.

## Profiles
Core-code = GitHub + Serena + native language tools.
Docs = Context7.
Browser = Playwright.
Security = Semgrep + native scanners.
Database = DBHub + database-native tooling.
Polyglot = Core-code + native toolchains for each side + boundary tests.

Do not enable every server at once.
