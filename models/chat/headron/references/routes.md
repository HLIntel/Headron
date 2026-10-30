# Routes: file → pack → gate commands

GENERATED from the gate resolver and language manifests. Commands may need a file, project, or configuration operand; replace placeholders and consult the pack manifest before running them. For absent gates, see `languages/<pack>/tools.yaml` in https://github.com/HLIntel/Headron; do not treat a tool name as a passing check.

| pack | files | formatter | compiler_or_typechecker | unit_tests |
|---|---|---|---|---|
| bash | `.bash` `.sh` | `shfmt -d` | `bash -n <file>` | `bats` |
| bqn | `.bqn` | not runnable; see pack guidance | not runnable; see pack guidance | not runnable; see pack guidance |
| c | `.c` `.h` | `clang-format --dry-run --Werror` | `clang -std=c17 -fsyntax-only` | `ctest --test-dir build --output-on-failure` |
| carbon | `.carbon` | not runnable; see pack guidance | not runnable; see pack guidance | `bazel test` |
| chapel | `.chpl` | not runnable; see pack guidance | `chpl` | `mason test` |
| cloudflare | `wrangler.json` `wrangler.jsonc` `wrangler.toml` | not runnable; see pack guidance | `wrangler deploy --dry-run --config <config-file>` | `vitest run` |
| cpp | `.cc` `.cpp` `.hpp` | `clang-format --dry-run --Werror` | `clang++ -std=c++20 -fsyntax-only` | `ctest` |
| cuda | `.cu` `.cuh` | `clang-format --dry-run --Werror` | `nvcc` | `ctest` |
| dockerfile | `Dockerfile` | not runnable; see pack guidance | `hadolint --failure-threshold error` | not runnable; see pack guidance |
| elixir | `.ex` `.exs` | `mix format --check-formatted` | `elixir -e 'Enum.each(System.argv(), fn f -> Code.string_to_quoted!(File.read!(f), file: f) end)' <file>` | `mix test` |
| forth | `.4th` `.fth` | not runnable; see pack guidance | not runnable; see pack guidance | not runnable; see pack guidance |
| fsharp | `.fs` `.fsx` | `fantomas --check` | `dotnet build` | `dotnet test` |
| futhark | `.fut` | `futhark fmt --check` | `futhark check` | `futhark test` |
| gleam | `.gleam` | `gleam format --check` | `gleam check` | `gleam test` |
| go | `.go` | not runnable; see pack guidance | `go vet ./...` | `go test` |
| hare | `.ha` | not runnable; see pack guidance | not runnable; see pack guidance | `hare test` |
| haskell | `.hs` `.lhs` | `ormolu --mode check` | `ghc -fno-code` | `cabal test` |
| headron | `.headron` | not runnable; see pack guidance | `headron compile` | not runnable; see pack guidance |
| json | `.json` | `prettier --check` | `jq empty <file>` | not runnable; supply a project-specific target or schema |
| julia | `.jl` | not runnable; see pack guidance | `julia --startup-file=no -e 'for f in ARGS; ex = Meta.parseall(read(f, String); filename=f); any(a -> a isa Expr && a.head in (:error, :incomplete), ex.args) && (println(stderr, "syntax error: ", f); exit(1)); end' <file>` | not runnable; see pack guidance |
| lean4 | `.lean` | not runnable; see pack guidance | `lean` | `lake test` |
| markdown | `.md` | `prettier --check` | not runnable; see pack guidance | not runnable; see pack guidance |
| mojo | `.mojo` | not runnable; see pack guidance | not runnable; see pack guidance | not runnable; supply a project-specific target or schema |
| nim | `.nim` | not runnable; see pack guidance | `nim check` | `testament` |
| ocaml | `.ml` `.mli` | `ocamlformat --check` | `ocamlc -i` | `dune test` |
| odin | `.odin` | not runnable; see pack guidance | `odin check -file` | `odin test` |
| python | `.py` `.pyi` | `ruff format --check` | `python3 -c 'import ast,sys; [ast.parse(open(f, encoding="utf-8").read(), f) for f in sys.argv[1:]]' <file>` | `pytest` |
| r | `.r` | not runnable; see pack guidance | `Rscript -e 'for (f in commandArgs(TRUE)) invisible(parse(f))' <file>` | `R CMD check` |
| roc | `.roc` | `roc format --check` | `roc check` | `roc test` |
| rust | `.rs` | `rustfmt --check` | `rustc <file>` | `cargo test` |
| scala | `.sc` `.scala` | `scalafmt --test` | `scalac` | `sbt test` |
| sql | `.sql` | not runnable; see pack guidance | not runnable; see pack guidance | not runnable; see pack guidance |
| swift | `.swift` | `swift-format lint --strict` | `swiftc -parse-as-library -typecheck` | `swift test` |
| toml | `.toml` `uv.lock` | `taplo fmt --check` | `python3 -c 'import sys, tomllib; [tomllib.loads(open(f, encoding="utf-8").read()) for f in sys.argv[1:]]' <file>` | not runnable; see pack guidance |
| typescript | `.cjs` `.cts` `.js` `.jsx` `.mjs` `.mts` `.ts` `.tsx` | `prettier --check` | `tsc --noEmit` | `vitest run` |
| uiua | `.ua` | not runnable; see pack guidance | not runnable; see pack guidance | `uiua test` |
| v | `.v` | `v fmt -verify` | not runnable; see pack guidance | `v test` |
| webassembly | `.wasm` `.wat` | not runnable; see pack guidance | not runnable; see pack guidance | not runnable; see pack guidance |
| yaml | `.yaml` `.yml` | `prettier --check` | `yamllint -d '{extends: relaxed, rules: {line-length: disable}}'` | not runnable; supply a project-specific target or schema |
| zig | `.zig` | `zig fmt --check` | `zig ast-check` | `zig test` |
