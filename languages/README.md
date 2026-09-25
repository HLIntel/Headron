# Languages

Use [ATLAS.md](ATLAS.md) to choose by workload. Each language has a stable overview plus a compact `OPERATING.md` card for AI/code routing.

**Language route:** `README.md → OPERATING.md → task profile → native tools → boundary tests → verification`.

| Family | Languages |
|---|---|
| Application/orchestration | Python, TypeScript |
| Systems/infrastructure | Rust, Go, C, C++, Zig, Nim, V, Hare, Odin |
| Data/accelerator/HPC | Julia, Mojo, Futhark, Chapel, CUDA |
| Functional/correctness | Haskell, F#, Elixir, Gleam, Roc, Lean 4 |
| Language research | Carbon, BQN, Uiua |
| Boundary/runtime | SQL, Bash, WebAssembly/WASI |
| Quantum | Quantum, Q#, Silq, Qiskit |

## Operating cards

Every route has an `OPERATING.md` containing its fast path, native authority, pairing strategy, boundary contract, anti-patterns, reliability practices, verification loop, AI learning loop, and primary research links. See [PACK-SPEC.md](PACK-SPEC.md).

## Cross-language practice

Use [systems/POLYGLOT-ENGINEERING.md](../systems/POLYGLOT-ENGINEERING.md) when multiple languages intentionally share one product. Define the boundary before choosing the second language.

## Language index

<!-- BEGIN generated: language-index (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/artifact_routes` — 36 routes, 36 tool manifests.

| route | guide | operating card | tool manifest |
|---|---|---|---|
| `quantum` | [guide](quantum/README.md) | [card](quantum/OPERATING.md) | none |
| `bash` | [guide](bash/README.md) | [card](bash/OPERATING.md) | [tools.yaml](bash/tools.yaml) |
| `bqn` | [guide](bqn/README.md) | [card](bqn/OPERATING.md) | [tools.yaml](bqn/tools.yaml) |
| `c` | [guide](c/README.md) | [card](c/OPERATING.md) | [tools.yaml](c/tools.yaml) |
| `carbon` | [guide](carbon/README.md) | [card](carbon/OPERATING.md) | [tools.yaml](carbon/tools.yaml) |
| `chapel` | [guide](chapel/README.md) | [card](chapel/OPERATING.md) | [tools.yaml](chapel/tools.yaml) |
| `cloudflare` | [guide](cloudflare/README.md) | [card](cloudflare/OPERATING.md) | [tools.yaml](cloudflare/tools.yaml) |
| `cpp` | [guide](cpp/README.md) | [card](cpp/OPERATING.md) | [tools.yaml](cpp/tools.yaml) |
| `cuda` | [guide](cuda/README.md) | [card](cuda/OPERATING.md) | [tools.yaml](cuda/tools.yaml) |
| `elixir` | [guide](elixir/README.md) | [card](elixir/OPERATING.md) | [tools.yaml](elixir/tools.yaml) |
| `forth` | [guide](forth/README.md) | [card](forth/OPERATING.md) | [tools.yaml](forth/tools.yaml) |
| `fsharp` | [guide](fsharp/README.md) | [card](fsharp/OPERATING.md) | [tools.yaml](fsharp/tools.yaml) |
| `futhark` | [guide](futhark/README.md) | [card](futhark/OPERATING.md) | [tools.yaml](futhark/tools.yaml) |
| `gleam` | [guide](gleam/README.md) | [card](gleam/OPERATING.md) | [tools.yaml](gleam/tools.yaml) |
| `go` | [guide](go/README.md) | [card](go/OPERATING.md) | [tools.yaml](go/tools.yaml) |
| `hare` | [guide](hare/README.md) | [card](hare/OPERATING.md) | [tools.yaml](hare/tools.yaml) |
| `haskell` | [guide](haskell/README.md) | [card](haskell/OPERATING.md) | [tools.yaml](haskell/tools.yaml) |
| `julia` | [guide](julia/README.md) | [card](julia/OPERATING.md) | [tools.yaml](julia/tools.yaml) |
| `lean4` | [guide](lean4/README.md) | [card](lean4/OPERATING.md) | [tools.yaml](lean4/tools.yaml) |
| `mojo` | [guide](mojo/README.md) | [card](mojo/OPERATING.md) | [tools.yaml](mojo/tools.yaml) |
| `nim` | [guide](nim/README.md) | [card](nim/OPERATING.md) | [tools.yaml](nim/tools.yaml) |
| `ocaml` | [guide](ocaml/README.md) | [card](ocaml/OPERATING.md) | [tools.yaml](ocaml/tools.yaml) |
| `odin` | [guide](odin/README.md) | [card](odin/OPERATING.md) | [tools.yaml](odin/tools.yaml) |
| `python` | [guide](python/README.md) | [card](python/OPERATING.md) | [tools.yaml](python/tools.yaml) |
| `quantum/qsharp` | [guide](quantum/qsharp/README.md) | [card](quantum/qsharp/OPERATING.md) | [tools.yaml](quantum/qsharp/tools.yaml) |
| `quantum/silq` | [guide](quantum/silq/README.md) | [card](quantum/silq/OPERATING.md) | [tools.yaml](quantum/silq/tools.yaml) |
| `r` | [guide](r/README.md) | [card](r/OPERATING.md) | [tools.yaml](r/tools.yaml) |
| `roc` | [guide](roc/README.md) | [card](roc/OPERATING.md) | [tools.yaml](roc/tools.yaml) |
| `rust` | [guide](rust/README.md) | [card](rust/OPERATING.md) | [tools.yaml](rust/tools.yaml) |
| `scala` | [guide](scala/README.md) | [card](scala/OPERATING.md) | [tools.yaml](scala/tools.yaml) |
| `sql` | [guide](sql/README.md) | [card](sql/OPERATING.md) | [tools.yaml](sql/tools.yaml) |
| `swift` | [guide](swift/README.md) | [card](swift/OPERATING.md) | [tools.yaml](swift/tools.yaml) |
| `typescript` | [guide](typescript/README.md) | [card](typescript/OPERATING.md) | [tools.yaml](typescript/tools.yaml) |
| `uiua` | [guide](uiua/README.md) | [card](uiua/OPERATING.md) | [tools.yaml](uiua/tools.yaml) |
| `v` | [guide](v/README.md) | [card](v/OPERATING.md) | [tools.yaml](v/tools.yaml) |
| `webassembly` | [guide](webassembly/README.md) | [card](webassembly/OPERATING.md) | [tools.yaml](webassembly/tools.yaml) |
| `zig` | [guide](zig/README.md) | [card](zig/OPERATING.md) | [tools.yaml](zig/tools.yaml) |
<!-- END generated: language-index -->
