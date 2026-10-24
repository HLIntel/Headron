# Examples

Worked examples, each one self-verifying: every file asserts its own invariants and exits
non-zero when one fails.

<!-- BEGIN generated: examples-index (python scripts/atlas.py index --write) -->
Derived from the tree and `atlas.yaml/example_runners`. Every row is executed by
`python scripts/exrun.py`, which CI runs before the contract.

| example | route | how it runs |
|---|---|---|
| `examples/bash/refuse_on_missing.sh` | `bash` | `bash examples/bash/refuse_on_missing.sh` |
| `examples/bqn/sum_of_squares.bqn` | `bqn` | `bqn examples/bqn/sum_of_squares.bqn` |
| `examples/c/bounded_read.c` | `c` | `clang -std=c17 -Wall -Wextra -Werror -fsanitize=address,undefined examples/c/bounded_read.c -o {out}` |
| `examples/carbon/minimal.carbon` | `carbon` | `carbon run examples/carbon/minimal.carbon` |
| `examples/chapel/bounded.chpl` | `chapel` | `chpl examples/chapel/bounded.chpl -o {out}` |
| `examples/cloudflare/worker.mjs` | `typescript` | `node examples/cloudflare/worker.mjs` |
| `examples/cloudflare/wrangler.jsonc` | `cloudflare` | `wrangler deploy --dry-run --config examples/cloudflare/wrangler.jsonc --outdir {out}` |
| `examples/cpp/bounded_view.cpp` | `cpp` | `clang++ -std=c++20 -Wall -Wextra -Werror -fsanitize=address,undefined examples/cpp/bounded_view.cpp -o {out}` |
| `examples/cuda/bounded.cu` | `cuda` | `nvcc examples/cuda/bounded.cu -o {out}` |
| `examples/dockerfile/Dockerfile` | `dockerfile` | `hadolint --failure-threshold error examples/dockerfile/Dockerfile` |
| `examples/elixir/bounded_queue.exs` | `elixir` | `elixir examples/elixir/bounded_queue.exs` |
| `examples/forth/bounded.fth` | `forth` | `gforth examples/forth/bounded.fth` |
| `examples/fsharp/BoundedRetry.fsx` | `fsharp` | `dotnet fsi examples/fsharp/BoundedRetry.fsx` |
| `examples/futhark/bounded.fut` | `futhark` | `futhark run examples/futhark/bounded.fut` |
| `examples/git/worktree-layout.sh` | `bash` | `bash examples/git/worktree-layout.sh` |
| `examples/gleam/gleam.toml` | `toml` | `python3 -c import sys, tomllib; [tomllib.loads(open(f, encoding="utf-8").read()) for f in sys.argv[1:]] examples/gleam/gleam.toml` |
| `examples/gleam/src/bounded.gleam` | `gleam` | `gleam run` |
| `examples/go/bounded_worker.go` | `go` | `go vet .` |
| `examples/go/bounded_worker_test.go` | `go` | `go vet .` |
| `examples/hare/bounded.ha` | `hare` | `hare run examples/hare/bounded.ha` |
| `examples/haskell/BoundedSlice.hs` | `haskell` | `runghc examples/haskell/BoundedSlice.hs` |
| `examples/julia/bounded.jl` | `julia` | `julia examples/julia/bounded.jl` |
| `examples/lean4/bounded.lean` | `lean4` | `lean --run examples/lean4/bounded.lean` |
| `examples/mojo/bounded.mojo` | `mojo` | `mojo examples/mojo/bounded.mojo` |
| `examples/nim/bounded_retry.nim` | `nim` | `nim c --hints:off --out:{out} examples/nim/bounded_retry.nim` |
| `examples/ocaml/bounded_slice.ml` | `ocaml` | `ocaml examples/ocaml/bounded_slice.ml` |
| `examples/odin/bounded.odin` | `odin` | `odin run examples/odin/bounded.odin -file` |
| `examples/python/bounded_async.py` | `python` | `python3 examples/python/bounded_async.py` |
| `examples/python/caching_strategies.py` | `python` | `python3 examples/python/caching_strategies.py` |
| `examples/r/bounded.R` | `r` | `Rscript examples/r/bounded.R` |
| `examples/roc/double.roc` | `roc` | `roc check examples/roc/double.roc` |
| `examples/rust/bounded_retry.rs` | `rust` | `rustc --edition 2021 -D warnings examples/rust/bounded_retry.rs -o {out}` |
| `examples/scala/bounded.scala` | `scala` | `scala examples/scala/bounded.scala` |
| `examples/sql/bounded_query.sql` | `sql` | `sqlite3 :memory: .read 'examples/sql/bounded_query.sql'` |
| `examples/swift/bounded_task.swift` | `swift` | `swiftc -parse-as-library examples/swift/bounded_task.swift -o {out}` |
| `examples/thea/delegate.thea` | `thea` | `thea compile examples/thea/delegate.thea` |
| `examples/thea/deploy.thea` | `thea` | `thea compile examples/thea/deploy.thea` |
| `examples/thea/polyglot.thea` | `thea` | `thea compile examples/thea/polyglot.thea` |
| `examples/thea/review.thea` | `thea` | `thea compile examples/thea/review.thea` |
| `examples/typescript/bounded_queue.ts` | `typescript` | `node examples/typescript/bounded_queue.ts` |
| `examples/uiua/bounded.ua` | `uiua` | `uiua run --no-format examples/uiua/bounded.ua` |
| `examples/v/bounded.v` | `v` | `v run examples/v/bounded.v` |
| `examples/webassembly/bounded.wat` | `webassembly` | `wasmtime examples/webassembly/bounded.wat` |
| `examples/webhooks/github_verify.py` | `python` | `python3 examples/webhooks/github_verify.py` |
| `examples/yaml/service.yaml` | `yaml` | `yamllint -d {extends: relaxed, rules: {line-length: disable}} examples/yaml/service.yaml` |
| `examples/zig/bounded_buffer.zig` | `zig` | `zig test examples/zig/bounded_buffer.zig` |
<!-- END generated: examples-index -->

## The rule these follow

**Standard library first.** Two of these examples once imported a package that was never
installed, so they could not run at all — an example nobody can execute is a skeleton, which is
exactly what this repository refuses in a language pack. If an example needs a dependency, it
needs a reason first.
