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

## Python
Native: Python extension, Pyright/Ruff, Python Debugger, pytest.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.
Avoid duplicate Python navigation servers.

## Rust
Native: rust-analyzer, Cargo, Clippy, formatter, LLDB/GDB.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.
Avoid replacing compiler diagnostics with MCP.

## Go
Native: gopls/Go extension, Delve, gofmt, tests, race detector, pprof.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.
MCP does not replace race/pprof.

## TypeScript / JavaScript
Native: TypeScript language service, ESLint/formatters, Node debugger and test tooling.
MCP: Serena, GitHub, Context7, Playwright, Semgrep.
Profile: core-code + docs + browser + security.
Use Playwright for browser integration, not unit logic.

## C
Native: clangd, CMake/Make/Ninja, compiler/debugger, sanitizers.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.

## C++
Native: clangd, CMake, clang-format/tidy, GDB/LLDB, sanitizers.
MCP: Serena, GitHub, Context7, Semgrep; experimental C++ MCPs only for verified gaps.
Profile: core-code + docs + security.

## Zig
Native: ZLS, zig build/test/fmt, native debugger.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.

## Mojo
Native: Modular/Mojo toolchain and accelerator stack.
MCP: GitHub, Context7, Semgrep where supported; semantic MCP only if Mojo parser support is verified.
Profile: core-code + docs + security.

## Julia
Native: Julia extension, LanguageServer.jl, Pkg, profiler/BenchmarkTools.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.

## Elixir
Native: ElixirLS/Next LS, Mix, ExUnit, IEx/OTP.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.

## Gleam
Native: Gleam compiler/build/test/formatter and BEAM tooling.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.

## Nim
Native: Nim compiler/Nimble/tooling.
MCP: GitHub, Context7, Semgrep; semantic MCP only if Nim support is verified.
Profile: core-code + docs + security.
No dedicated Nim MCP is required.

## V
Native: V compiler, formatter, tests and native debugging.
MCP: GitHub, Context7, Semgrep.
Profile: core-code + docs + security.
Prefer native CLI.

## Odin
Native: Odin compiler/tooling and native debugger/graphics stack.
MCP: GitHub, Context7, Semgrep; semantic MCP only if Odin parsing is verified.
Profile: core-code + docs + security.

## Hare
Native: Hare compiler/toolchain and native debugger.
MCP: GitHub, Context7; semantic MCP only if Hare support is verified.
Profile: core-code + docs.

## Futhark
Native: Futhark compiler/backends and benchmark/profiling tools.
MCP: GitHub, Context7; semantic MCP only if Futhark support is verified.
Profile: core-code + docs.

## Haskell
Native: HLS, GHC, Cabal/Stack, profiling.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.

## F#
Native: .NET SDK/compiler, FsAutoComplete/Ionide, formatter, tests.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.

## Chapel
Native: Chapel compiler, task/locale model, profiling/performance tooling.
MCP: GitHub, Context7; semantic MCP only if Chapel support is verified.
Profile: core-code + docs.

## BQN
Native: BQN runtime/editor tools.
MCP: GitHub, Context7; semantic layer only if useful.
Profile: core-code + docs.

## Uiua
Native: Uiua runtime/editor tools.
MCP: GitHub, Context7; semantic layer only if useful.
Profile: core-code + docs.

## Lean 4
Native: Lean VS Code extension, Lake/elan, theorem prover/compiler.
MCP: Serena, GitHub, Context7.
Profile: core-code + docs.
Lean's kernel/compiler is the proof authority.

## Carbon
Native: experimental Carbon compiler/tooling.
MCP: GitHub + Context7; semantic MCP only if parser support is verified.
Profile: core-code + docs.

## Roc
Native: Roc toolchain/editor support.
MCP: GitHub + Context7; semantic MCP only if parser support is verified.
Profile: core-code + docs.

## Q#
Native: Microsoft Quantum Development Kit tooling.
MCP: GitHub + Context7; generic semantic layer only if supported.
Profile: core-code + docs.

## CUDA
Native: CUDA compiler/debugger/profilers and NVIDIA VS Code tooling.
MCP: Serena, GitHub, Context7, Semgrep where supported.
Profile: core-code + docs + security.
Validate performance with CUDA profilers, not MCP output.

## SQL
Native: database-specific clients, migrations, linters, query plans.
MCP: DBHub + GitHub + Context7.
Profile: database + docs.
Default to read-only/non-production connections.

## Bash
Native: terminal, ShellCheck, Bash language server.
MCP: Serena, GitHub, Semgrep.
Profile: core-code + security.
Avoid shell-execution MCPs when direct terminal access exists.

## WebAssembly / WASI
Native: wasm compiler/runtime/component tooling.
MCP: GitHub + Context7; semantic layer only if parser support is verified.
Profile: core-code + docs.

## Quantum / Qiskit / Silq
Native: QDK/Q#, Qiskit, simulator/provider tooling.
MCP: GitHub + Context7; generic semantic layer when supported.
Profile: core-code + docs.
Bound every cloud execution and preserve experiment provenance.

## Combinations
Code comprehension -> GitHub + Serena
Library/framework work -> GitHub + Serena + Context7
Web application -> GitHub + Serena + Context7 + Playwright
Security -> GitHub + Semgrep + native scanners
Database application -> GitHub + Serena + Context7 + DBHub
Polyglot -> GitHub + supported Serena + Context7 + native toolchains + boundary tests

Do not enable every server at once. Tool count is context and permission surface.
