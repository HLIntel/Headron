# Package and Tool Catalog

Packages are organized by engineering capability.

## Python
uv, Ruff, Pyright, pytest, Hypothesis, Pydantic, msgspec, attrs, immutables, AnyIO, HTTPX, cachetools, OpenTelemetry, Polars, PyArrow, DuckDB, orjson where its workload-specific tradeoffs justify it.

## Rust
Cargo, rust-analyzer, rustfmt, Clippy, Tokio, Tower, Axum, Reqwest, Serde, tracing, Moka, Governor, proptest, loom, Miri, Criterion, cargo-audit, cargo-deny.

## Go
gofmt, go vet, staticcheck, race detector, fuzzing, pprof, PGO, x/sync, x/time/rate, slog, OpenTelemetry.

## TypeScript
tsc strict mode, ESLint, typescript-eslint, Vitest, Ajv, Valibot/Zod, p-queue, Bottleneck, Playwright for browser integration where needed.

## C++
CMake, Ninja, clang/LLVM, clang-tidy, ASan/UBSan/TSan, GoogleTest/Catch2, GDB/LLDB, CMake presets, Conan/vcpkg as appropriate.

## Zig
zig build, zig fmt, zig test, std.testing, explicit allocators, zig cc.

## Mojo
Mojo/Modular toolchain, Python interoperability, accelerator/GPU facilities; verify current compiler/API details before standardizing.

## Julia
Pkg, Revise, BenchmarkTools, Profile, Arrow, Tables, DataFrames, CUDA ecosystem where GPU work is justified.

## Elixir/Gleam
Mix, ExUnit, Credo, Dialyzer, Telemetry, OTP, Broadway; Gleam compiler/formatter/test/build tooling and gleam_otp.

## Nim
Nim compiler, Nimble, ORC/ARC memory management, C/C++/JS backends, macro/compile-time facilities.

## V
V compiler/tooling, v fmt, v test, sum types, Option/Result, channels; verify memory-management maturity before relying on autofree.

## Haskell/F#
GHC/Cabal/Stack/HLS/QuickCheck/ghcid-style tooling; .NET SDK/FSharp.Core/FsCheck/FSharp.Data for F#.

## Parallel/research
Chapel, Futhark, Julia, Mojo, BQN, Uiua.

## Quantum
QDK/Q#, Qiskit, Silq.

Selection rule: choose the smallest dependency surface that provides the needed guarantee or capability. Reassess libraries whose defaults conflict with the repository invariants.