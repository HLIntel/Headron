# Languages

Use [ATLAS.md](ATLAS.md) to choose by workload. Each language has one guide, `README.md`, ending in a compact `## Operating card` section for AI/code routing.

**Language route:** `README.md → operating card → task profile → native tools → boundary tests → verification`.

| Family | Languages |
|---|---|
| Application/orchestration | Python, TypeScript |
| Systems/infrastructure | Rust, Go, C, C++, Zig, Nim, V, Hare, Odin, Swift, Forth |
| Data/accelerator/HPC | Julia, Mojo, Futhark, Chapel, CUDA, R |
| Functional/correctness | Haskell, F#, Elixir, Gleam, Roc, Lean 4, OCaml, Scala |
| Language research | Carbon, BQN, Uiua |
| Boundary/runtime | SQL, Bash, WebAssembly/WASI, Cloudflare Workers |

## Operating cards

Every route's `README.md` ends in a `## Operating card` section containing its fast path, native authority, pairing strategy, boundary contract, anti-patterns, reliability practices, verification loop, AI learning loop, and primary research links. The card's
fields are the ones `atlas.py check` counts (`cards` and `labels` in its summary line); the
manifest beside it is [PACK-TOOLS-SPEC.md](PACK-TOOLS-SPEC.md).

**Load one card, never every card:** the current language, the task profile, and only the boundary
cards the change needs. A pack links authoritative references instead of copying them: commands,
invariants, failure modes and routing decisions live here, exhaustive reference upstream.

**Use a second language because the contracts compose**, not because more languages look
sophisticated: define the boundary first, then give ownership to the language whose native
guarantees reduce total system complexity.

## Cross-language practice

Use [docs/systems/POLYGLOT-ENGINEERING.md](../docs/systems/POLYGLOT-ENGINEERING.md) when multiple languages intentionally share one product. Define the boundary before choosing the second language.

## Language index

<!-- BEGIN generated: language-index (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/artifact_routes` — 40 routes + 0 umbrella, 40 tool manifests.

| route | guide | operating card | tool manifest |
|---|---|---|---|
| `bash` | [guide](bash/README.md) | [card](bash/README.md#operating-card) | `tools.yaml` |
| `bqn` | [guide](bqn/README.md) | [card](bqn/README.md#operating-card) | `tools.yaml` |
| `c` | [guide](c/README.md) | [card](c/README.md#operating-card) | `tools.yaml` |
| `carbon` | [guide](carbon/README.md) | [card](carbon/README.md#operating-card) | `tools.yaml` |
| `chapel` | [guide](chapel/README.md) | [card](chapel/README.md#operating-card) | `tools.yaml` |
| `cloudflare` | [guide](cloudflare/README.md) | [card](cloudflare/README.md#operating-card) | `tools.yaml` |
| `cpp` | [guide](cpp/README.md) | [card](cpp/README.md#operating-card) | `tools.yaml` |
| `cuda` | [guide](cuda/README.md) | [card](cuda/README.md#operating-card) | `tools.yaml` |
| `dockerfile` | [guide](dockerfile/README.md) | [card](dockerfile/README.md#operating-card) | `tools.yaml` |
| `elixir` | [guide](elixir/README.md) | [card](elixir/README.md#operating-card) | `tools.yaml` |
| `forth` | [guide](forth/README.md) | [card](forth/README.md#operating-card) | `tools.yaml` |
| `fsharp` | [guide](fsharp/README.md) | [card](fsharp/README.md#operating-card) | `tools.yaml` |
| `futhark` | [guide](futhark/README.md) | [card](futhark/README.md#operating-card) | `tools.yaml` |
| `gleam` | [guide](gleam/README.md) | [card](gleam/README.md#operating-card) | `tools.yaml` |
| `go` | [guide](go/README.md) | [card](go/README.md#operating-card) | `tools.yaml` |
| `hare` | [guide](hare/README.md) | [card](hare/README.md#operating-card) | `tools.yaml` |
| `haskell` | [guide](haskell/README.md) | [card](haskell/README.md#operating-card) | `tools.yaml` |
| `headron` | [guide](headron/README.md) | [card](headron/README.md#operating-card) | `tools.yaml` |
| `json` | [guide](json/README.md) | [card](json/README.md#operating-card) | `tools.yaml` |
| `julia` | [guide](julia/README.md) | [card](julia/README.md#operating-card) | `tools.yaml` |
| `lean4` | [guide](lean4/README.md) | [card](lean4/README.md#operating-card) | `tools.yaml` |
| `markdown` | [guide](markdown/README.md) | [card](markdown/README.md#operating-card) | `tools.yaml` |
| `mojo` | [guide](mojo/README.md) | [card](mojo/README.md#operating-card) | `tools.yaml` |
| `nim` | [guide](nim/README.md) | [card](nim/README.md#operating-card) | `tools.yaml` |
| `ocaml` | [guide](ocaml/README.md) | [card](ocaml/README.md#operating-card) | `tools.yaml` |
| `odin` | [guide](odin/README.md) | [card](odin/README.md#operating-card) | `tools.yaml` |
| `python` | [guide](python/README.md) | [card](python/README.md#operating-card) | `tools.yaml` |
| `r` | [guide](r/README.md) | [card](r/README.md#operating-card) | `tools.yaml` |
| `roc` | [guide](roc/README.md) | [card](roc/README.md#operating-card) | `tools.yaml` |
| `rust` | [guide](rust/README.md) | [card](rust/README.md#operating-card) | `tools.yaml` |
| `scala` | [guide](scala/README.md) | [card](scala/README.md#operating-card) | `tools.yaml` |
| `sql` | [guide](sql/README.md) | [card](sql/README.md#operating-card) | `tools.yaml` |
| `swift` | [guide](swift/README.md) | [card](swift/README.md#operating-card) | `tools.yaml` |
| `toml` | [guide](toml/README.md) | [card](toml/README.md#operating-card) | `tools.yaml` |
| `typescript` | [guide](typescript/README.md) | [card](typescript/README.md#operating-card) | `tools.yaml` |
| `uiua` | [guide](uiua/README.md) | [card](uiua/README.md#operating-card) | `tools.yaml` |
| `v` | [guide](v/README.md) | [card](v/README.md#operating-card) | `tools.yaml` |
| `webassembly` | [guide](webassembly/README.md) | [card](webassembly/README.md#operating-card) | `tools.yaml` |
| `yaml` | [guide](yaml/README.md) | [card](yaml/README.md#operating-card) | `tools.yaml` |
| `zig` | [guide](zig/README.md) | [card](zig/README.md#operating-card) | `tools.yaml` |
<!-- END generated: language-index -->
