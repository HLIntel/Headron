# Code-Specific Routing

Routing should answer four questions before an agent edits code:

1. **What language/toolchain owns this artifact?**
2. **What task is being performed?**
3. **Which runtime/model/MCP profile is justified?**
4. **How will the result be verified?**

## Precedence

Use the first unambiguous signal:

```text
explicit task/path override
    -> artifact extension
    -> project manifest
    -> language directory
    -> issue/PR labels
    -> generic fallback
```

When signals conflict, the more specific artifact or explicit task wins and the conflict should be recorded rather than silently guessed.

## Extension route

| Artifact | Route | Native authority | Typical MCP/profile add-ons |
|---|---|---|---|
| `.py/.pyi` | Python | Python + Ruff + Pyright + pytest | core-code, docs, security |
| `.rs` | Rust | rust-analyzer + Cargo + Clippy + debugger | core-code, docs, security |
| `.go` | Go | gopls + gofmt + test/race/pprof | core-code, docs, security |
| `.ts/.tsx` | TypeScript | TS service + Node debugger/test stack | core-code, docs, browser, security |
| `.c/.h` | C | clangd + compiler + debugger/sanitizers | core-code, docs, security |
| `.cpp/.cc/.hpp` | C++ | clangd + compiler + debugger/sanitizers | core-code, docs, security |
| `.zig` | Zig | ZLS + Zig toolchain | core-code, docs, security where supported |
| `.mojo` | Mojo | Modular/Mojo/accelerator toolchain | GitHub + docs; semantic MCP only when verified |
| `.jl` | Julia | Julia extension + LanguageServer.jl + Pkg/profiler | core-code, docs, security |
| `.ex/.exs` | Elixir | Mix + BEAM/OTP + native LSP | core-code, docs, security |
| `.gleam` | Gleam | Gleam compiler/formatter/test + BEAM | core-code, docs, security |
| `.nim` | Nim | Nim compiler/Nimble | GitHub + docs; semantic MCP after support verification |
| `.v` | V | V compiler/formatter/test | GitHub + docs; semantic MCP after support verification |
| `.odin` | Odin | Odin compiler/toolchain | GitHub + docs; semantic MCP after support verification |
| `.ha` | Hare | Hare compiler/toolchain | GitHub + docs; semantic MCP after support verification |
| `.fut` | Futhark | Futhark compiler/backend | GitHub + docs; semantic MCP after support verification |
| `.hs/.lhs` | Haskell | GHC + HLS + test tooling | core-code, docs, security |
| `.fs/.fsx` | F# | .NET SDK + FsAutoComplete | core-code, docs, security |
| `.chpl` | Chapel | Chapel compiler + parallel tooling | GitHub + docs; native profiling |
| `.bqn` | BQN | BQN runtime/tooling | GitHub + docs |
| `.ua` | Uiua | Uiua runtime/tooling | GitHub + docs |
| `.lean` | Lean 4 | Lean + Lake + elan + kernel | GitHub + docs; kernel remains authority |
| `.carbon` | Carbon | Carbon toolchain/research stack | GitHub + docs; semantic MCP only when verified |
| `.roc` | Roc | Roc toolchain | GitHub + docs; semantic MCP only when verified |
| `.qs` | Q# | QDK/Q# toolchain | GitHub + docs |
| `.cu/.cuh` | CUDA | CUDA compiler + debugger/profiler | core-code, docs, security where supported |
| `.sql` | SQL | database-native client/migrations/plans | database, docs, security |
| `.sh/.bash` | Bash | terminal + ShellCheck + Bash LSP | core-code/security; avoid shell-exec duplication |
| `.wat/.wasm` | WebAssembly/WASI | compiler/runtime/component tooling | GitHub + docs |

See [atlas.yaml](../atlas.yaml) for the machine-readable extension route.

## Task route

| Task | Primary execution | Typical verification |
|---|---|---|
| mechanical | fast model + deterministic CLI | focused check |
| implementation | coding model + native language stack | tests + diff review |
| debugging | debugger + minimal repro | regression test |
| architecture | strong reasoning + ADR + worktree | boundary/contract review |
| research | research model + primary sources | source-backed notes |
| security | verifier + native scanners | independent security check |
| performance | profiler + benchmark | representative workload |
| parallel development | worktree + scoped agent | merge/diff/CI |
| polyglot | schema + native toolchains | boundary integration test |

## Runtime/MCP rule

Use the smallest profile that satisfies the task:

- `core-code`: repository context + semantic code navigation
- `docs`: external/current package documentation
- `browser`: browser/UI execution
- `security`: static/security scanning
- `database`: bounded database access
- `polyglot`: core-code plus native tools on both sides and boundary tests

Native compiler/LSP/debugger/test/profiler output remains authoritative.

## Routing command

```bash
python scripts/atlas.py route path/to/file.py
python scripts/atlas.py route path/to/file.rs
python scripts/atlas.py route path/to/schema.sql
```

Do not route a task to an MCP solely because an MCP exists. Route by capability need.
