# Routes: file → pack → gate commands

GENERATED from languages/*/tools.yaml. `none` means no established tool is recorded: say so, never invent one.

| pack | files | formatter | compiler_or_typechecker | unit_tests |
|---|---|---|---|---|
| bash | `.bash` `.sh` | `shfmt -d` | `bash -n` | `bats` |
| bqn | `.bqn` | none | `CBQN` | none |
| c | `.c` `.h` | `clang-format --dry-run --Werror` | `clang|gcc` | `ctest --test-dir build --output-on-failure` |
| carbon | `.carbon` | none | `carbon` | `bazel test` |
| chapel | `.chpl` | none | `chpl` | `mason test` |
| cloudflare | `wrangler.json` `wrangler.jsonc` `wrangler.toml` | none | none | `vitest` |
| cpp | `.cc` `.cpp` `.hpp` | `clang-format --dry-run --Werror` | `clang++|g++` | none |
| cuda | `.cu` `.cuh` | `clang-format --dry-run --Werror` | `nvcc` | none |
| elixir | `.ex` `.exs` | `mix format --check-formatted` | `elixir` | `builtin:ExUnit` |
| forth | `.4th` `.fth` | none | `gforth` | none |
| fsharp | `.fs` `.fsx` | `fantomas --check` | `dotnet build` | `dotnet test` |
| futhark | `.fut` | `futhark fmt` | `futhark check` | `futhark test` |
| gleam | `.gleam` | `gleam format --check` | `gleam check` | `gleam test` |
| go | `.go` | none | `go vet ./...` | `go test` |
| hare | `.ha` | none | `hare` | `hare test` |
| haskell | `.hs` `.lhs` | `ormolu --mode check` | `ghc -fno-code` | none |
| julia | `.jl` | none | `julia` | `builtin:Test (stdlib)` |
| lean4 | `.lean` | none | `lean` | `lake test` |
| mojo | `.mojo` | `mojo format` | `mojo` | `mojo run` |
| nim | `.nim` | `nimpretty` | `nim check` | none |
| ocaml | `.ml` `.mli` | `ocamlformat --check` | `ocamlopt|ocaml` | `dune test` |
| odin | `.odin` | `odinfmt` | `odin check` | `odin test` |
| python | `.py` `.pyi` | `ruff format --check` | `python3 -c import ast,sys; [ast.parse(open(f, encoding="utf-8").read(), f) for f in sys.argv[1:]]` | `pytest` |
| quantum/qsharp | `.qs` | none | `qsc` | none |
| quantum/silq | `.slq` | none | `silq` | `builtin:assert and simulation over the declared shot count` |
| r | `.r` | none | `Rscript` | `R CMD check` |
| roc | `.roc` | `roc format --check` | `roc check` | `roc test` |
| rust | `.rs` | `rustfmt --check` | `rustc` | `cargo test` |
| scala | `.sc` `.scala` | `scalafmt --test` | `scalac` | `sbt test` |
| sql | `.sql` | `sqlfluff format` | `psql|sqlite3` | none |
| swift | `.swift` | `swift-format lint --strict` | `swiftc -parse-as-library -typecheck` | `swift test` |
| typescript | `.cjs` `.cts` `.js` `.jsx` `.mjs` `.mts` `.ts` `.tsx` | `prettier --check` | none | `vitest` |
| uiua | `.ua` | `uiua fmt` | `uiua` | `uiua test` |
| v | `.v` | `v fmt` | `v` | `v test` |
| webassembly | `.wasm` `.wat` | `wasm-tools print` | none | `concept:host toolchain tests under wasmtime` |
| zig | `.zig` | `zig fmt --check` | `zig ast-check` | `zig test` |
