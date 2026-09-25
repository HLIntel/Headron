# Examples

Worked examples, each one self-verifying: every file asserts its own invariants and exits
non-zero when one fails. `python scripts/exrun.py` runs them all and reports which toolchains are
absent rather than passing over them silently.

<!-- BEGIN generated: examples-index (python scripts/atlas.py index --write) -->
Derived from the tree and `atlas.yaml/example_runners`. Every row is executed by
`python scripts/exrun.py`, which CI runs before the contract.

| example | route | how it runs |
|---|---|---|
| [examples/bash/refuse_on_missing.sh](bash/refuse_on_missing.sh) | `bash` | `bash examples/bash/refuse_on_missing.sh` |
| [examples/c/bounded_read.c](c/bounded_read.c) | `c` | `clang -std=c17 -Wall -Wextra -Werror -fsanitize=address,undefined examples/c/bounded_read.c -o {out}` |
| [examples/cloudflare/worker.mjs](cloudflare/worker.mjs) | `typescript` | `node examples/cloudflare/worker.mjs` |
| [examples/cloudflare/wrangler.jsonc](cloudflare/wrangler.jsonc) | `cloudflare` | not routed to a runner |
| [examples/cpp/bounded_view.cpp](cpp/bounded_view.cpp) | `cpp` | `clang++ -std=c++20 -Wall -Wextra -Werror -fsanitize=address,undefined examples/cpp/bounded_view.cpp -o {out}` |
| [examples/elixir/bounded_queue.exs](elixir/bounded_queue.exs) | `elixir` | `elixir examples/elixir/bounded_queue.exs` |
| [examples/fsharp/BoundedRetry.fsx](fsharp/BoundedRetry.fsx) | `fsharp` | `dotnet fsi examples/fsharp/BoundedRetry.fsx` |
| [examples/git/worktree-layout.sh](git/worktree-layout.sh) | `bash` | `bash examples/git/worktree-layout.sh` |
| [examples/gleam/gleam.toml](gleam/gleam.toml) | `—` | not routed to a runner |
| [examples/gleam/src/bounded.gleam](gleam/src/bounded.gleam) | `gleam` | `gleam run` |
| [examples/go/bounded_worker.go](go/bounded_worker.go) | `go` | `go vet .` |
| [examples/go/bounded_worker_test.go](go/bounded_worker_test.go) | `go` | `go vet .` |
| [examples/go/go.mod](go/go.mod) | `—` | not routed to a runner |
| [examples/haskell/BoundedSlice.hs](haskell/BoundedSlice.hs) | `haskell` | `runghc examples/haskell/BoundedSlice.hs` |
| [examples/json/schema.json](json/schema.json) | `—` | not routed to a runner |
| [examples/nim/bounded_retry.nim](nim/bounded_retry.nim) | `nim` | `nim c --hints:off --out:{out} examples/nim/bounded_retry.nim` |
| [examples/ocaml/bounded_slice.ml](ocaml/bounded_slice.ml) | `ocaml` | `ocaml examples/ocaml/bounded_slice.ml` |
| [examples/python/bounded_async.py](python/bounded_async.py) | `python` | `python3 examples/python/bounded_async.py` |
| [examples/python/caching_strategies.py](python/caching_strategies.py) | `python` | `python3 examples/python/caching_strategies.py` |
| [examples/rust/bounded_retry.rs](rust/bounded_retry.rs) | `rust` | `rustc --edition 2021 -D warnings examples/rust/bounded_retry.rs -o {out}` |
| [examples/sql/bounded_query.sql](sql/bounded_query.sql) | `sql` | `sqlite3 :memory: .read examples/sql/bounded_query.sql` |
| [examples/swift/bounded_task.swift](swift/bounded_task.swift) | `swift` | `swiftc -parse-as-library examples/swift/bounded_task.swift -o {out}` |
| [examples/typescript/bounded_queue.ts](typescript/bounded_queue.ts) | `typescript` | `node examples/typescript/bounded_queue.ts` |
| [examples/webhooks/github_verify.py](webhooks/github_verify.py) | `python` | `python3 examples/webhooks/github_verify.py` |
| [examples/zig/bounded_buffer.zig](zig/bounded_buffer.zig) | `zig` | `zig test examples/zig/bounded_buffer.zig` |
<!-- END generated: examples-index -->

## The rule these follow

**Standard library first.** Two of these examples once imported a package that was never
installed, so they could not run at all — an example nobody can execute is a skeleton, which is
exactly what this repository refuses in a language pack. If an example needs a dependency, it
needs a reason first.
