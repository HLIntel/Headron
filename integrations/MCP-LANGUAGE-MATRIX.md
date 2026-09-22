# MCP + VS Code Language Matrix

Native first. MCP second.

The compiler, LSP, debugger, formatter, test runner, profiler, and package manager are authoritative. MCP is an extension for capabilities they do not efficiently provide.

## Shared free/open-source-oriented MCP layer

| MCP | Status | Role |
|---|---|---|
| GitHub MCP Server | MIT, official, self-hostable | GitHub repo/code/issues/PRs/Actions/security context |
| Serena | MIT, local | semantic code navigation/editing backed by LSP |
| Playwright MCP | Apache-2.0, local | browser automation and UI testing |
| Context7 | MIT server; hosted service optional | current library/framework documentation |
| DBHub | MIT, local | multi-database SQL/schema access with guardrails |
| Semgrep MCP | official Semgrep CLI integration | deterministic security scanning |

VS Code can install MCP servers from its MCP gallery or configure them in workspace/user MCP configuration.

## Python
Native: Python extension, Pyright/Ruff, Python Debugger, pytest.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.
Avoid duplicate Python navigation MCPs.

## Rust
Native: rust-analyzer, Cargo, Clippy, formatter, LLDB/GDB.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.
Avoid replacing compiler diagnostics with MCP.

## Go
Native: gopls/Go extension, Delve, gofmt, tests, race detector, pprof.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.
Avoid treating MCP as a race detector.

## TypeScript / JavaScript
Native: TypeScript language service, ESLint/formatters, test runner, Node debugger.
MCP: Serena, GitHub, Context7, Playwright, Semgrep.
Profile: core-code + docs + browser + security.
Use Playwright for browser integration, not unit logic.

## C
Native: clangd, CMake/Make/Ninja, compiler/debugger, sanitizers.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.
Native compiler and sanitizers remain authoritative.

## C++
Native: clangd, CMake, clang-format/tidy, GDB/LLDB, sanitizers.
MCP: Serena, GitHub, Context7, Semgrep. Experimental C++ MCPs only for a verified gap.
Profile: core-code + docs + security.
Avoid overlapping clangd wrappers.

## Zig
Native: ZLS, zig build/test/fmt, native debugger.
MCP: Serena, GitHub, Context7, Semgrep.
Profile: core-code + docs + security.

## Mojo
Native: Modular/Mojo toolchain and accelerator stack.
MCP: GitHub, Context7, Semgrep where supported; semantic MCP only if the underlying parser supports Mojo.
Profile: core-code + docs + security.
Do not claim a dedicated mature Mojo MCP without current evidence.

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
MCP: GitHub, Context7, Semgrep; generic semantic MCP only if Nim support is verified.
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
MCP: GitHub, Context7; generic semantic MCP only if Hare support is verified.
Profile: core-code + docs.

## Futhark
Native: Futhark compiler/backends and benchmark/profiling tools.
MCP: GitHub, Context7; generic semantic MCP only if Futhark support is verified.
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
MCP: GitHub, Context7; generic semantic MCP only if Chapel support is verified.
Profile: core-code + docs.
Do not confuse VS Code task parallelism with Chapel parallelism.

## BQN
Native: BQN runtime/editor tools.
MCP: GitHub, Context7; generic semantic layer only if useful.
Profile: core-code + docs.

## Uiua
Native: Uiua runtime/editor tools.
MCP: GitHub, Context7; generic semantic layer only if useful.
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

## Common combinations

Code comprehension -> GitHub + Serena
Library work -> GitHub + Serena + Context7
Web application -> GitHub + Serena + Context7 + Playwright
Security -> GitHub + Semgrep + native scanners
Database application -> GitHub + Serena + Context7 + DBHub
Polyglot -> GitHub + supported Serena + Context7 + native toolchains + boundary tests

Do not enable every server simultaneously. Tool count is context and permission surface.
