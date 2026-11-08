# Polyglot benchmark: eight public repositories

Contract 3.62.0. Base `46f4437f`, change `aa7befc3` on branch `fix/polyglot-bench`. The schema follow-up `e61dd73a`
changes no verdict. The commit that adds this page carries its date.

## Before and after

The change goes into every repository the same way. The 119 frozen picks are up to 2 tracked files per route,
taken in `git ls-files` order. They are removed from a scratch base commit, so `headron verify --base <scratch> --jobs 2` sees
exactly those files as the change. Both sides used the same picks, the same clones and the same machine, back to back.

| Measure | Before `46f4437f` | After `aa7befc3` |
|---|---|---|
| verify rows (gate × file) | 225 | 249 |
| FAIL | 82 | 58 |
| PASS | 115 | 118 |
| NOT RUN, each with a stated why | 28 | 73 |
| tracebacks across port, init, check, verify and 357 per-file calls | 0 | 0 |
| untracked files left in the 8 clones | 4 | 0 |
| ignored files left in the 8 clones | 12 | 13 |
| files routed / tracked, all 8 repos | 1734 / 2505 | 1734 / 2505 |

Verdict moves, per row id: FAIL→NOT RUN 23, FAIL→PASS 2, PASS→NOT RUN 1, new FAIL 1, new NOT RUN 21, new PASS 2.
There are more rows because a per-project runner that cannot be placed now reports one row per file. Before, it
ran once from the tree root and failed once.

**What the 24 fewer FAIL rows were.** In each case a project verb (`cargo test`, `go test ./...`, `go vet ./...`,
`mix test`, `swift test`, `vitest run`, `ctest`, `tsc --noEmit`) ran from the checkout root, or from a directory
with no project. Or a single-file runner (`bats`, `testament`, `odin test`) was given a file it does not read. Now
each gate runs from the project home its record names, `cd <cwd> && <argv>`. When there is no project,
the row is NOT RUN, with a why that names the missing marker.

**The two new PASS rows.** These are `cargo test` in the crates `base64.rs` and `bf.rs` (benchmarks). Before, a
standalone `rustc` failed on a crate member with E0432 and no test ran.

**The one PASS lost.** This is `rustc build.rs` in ripgrep. `build.rs` is a member of the Cargo project, so
`rustc` alone was compiling it outside its crate. The pass proved nothing about the crate, and it left a binary behind.

**The one new FAIL is environment.** In ripgrep, `cargo test` now runs in the crate and reports
`ripgrep@15.2.0 requires rustc 1.96`. This machine's toolchain is older than the project's MSRV.

## Wall time

| Repo | Pinned | Tracked | Routed | verify s, before → after | Gate tools s | Headron's own s |
|---|---|---|---|---|---|---|
| benchmarks | `5bc68b3` | 242 | 121 | 13.78 → 18.90 | 6.6 → 11.7 | 7.18 → 7.20 |
| dockerfiles | `8ff9913` | 321 | 257 | 3.77 → 3.84 | 0.6 → 0.4 | 3.17 → 3.44 |
| flask | `49943b5` | 236 | 108 | 5.74 → 5.16 | 2.9 → 2.6 | 2.84 → 2.56 |
| fzf | `c7bf2b8` | 164 | 125 | 3.04 → 7.36 | 1.1 → 5.4 | 1.94 → 1.96 |
| gleam-stdlib | `ac093e4` | 62 | 54 | 11.03 → 10.53 | 8.8 → 8.3 | 2.23 → 2.23 |
| phoenix | `79fdbb5` | 510 | 317 | 5.48 → 5.04 | 2.8 → 2.6 | 2.68 → 2.44 |
| ripgrep | `91f5d22` | 226 | 148 | 3.76 → 2.99 | 1.6 → 0.8 | 2.16 → 2.19 |
| zod | `19c40d2` | 744 | 604 | 4.46 → 4.24 | 2.5 → 2.3 | 1.96 → 1.94 |
| **total** | | 2505 | 1734 | 51.06 → 58.06 | 26.9 → 33.5 | 24.16 → 23.96 |

- "Gate tools" is the sum of the row seconds: the consumer's own compilers, formatters and test runners. "Headron's own" is
  verify wall minus that sum. Gates ran with `--jobs 2`, so this is a floor, not an exact share.
- The 7.0 s rise is all in gate tools. `cargo test` and `go test ./...` now run real test suites in their projects
  (benchmarks, fzf). Headron's own share is flat at 24.16 → 23.96 s.
- **Noise floor.** Two runs of the same base, with the same picks, totalled 69.63 s and 51.06 s. Their verdict tallies
  were identical. Wall time here moves by more than the change does, so the verdicts are the result and the seconds are
  context. Each side is one run. The after side ran first, at load 2.49. The before side followed at load 3.31.
- In process, routing plus every gate record took 1.00 → 1.13 s for all 2505 tracked files. Per-file CLI medians
  were 0.17 s for `route`, 0.17 s for `gate` and 0.18 s for `port`, the same on both sides (n = 119 each).

## Second change: adoption and dialect

Branch `fix/gate-adoption`, measured against `aa7befc3`'s tree (`19d5d001`) with the same 119 picks, back to back. A
style formatter now runs only where the repository adopts it: its config file sits between the file and the
repository top, or a build, hook, CI or `.editorconfig` file there names it or sets a key only it reads. `jq`
skips a file that strict JSON refuses and the JSONC reader takes. hadolint skips a BuildKit heredoc. Each skipped
row is NOT RUN, with that why.

| Measure | Before `19d5d001` | After `fix/gate-adoption` |
|---|---|---|
| verify rows (gate × file) | 249 | 249 |
| FAIL | 58 | 23 |
| PASS | 118 | 88 |
| NOT RUN, each with a stated why | 73 | 138 |
| tracebacks, untracked files left | 0, 0 | 0, 0 |

- **Verdict moves, per row id:** FAIL→NOT RUN 35, PASS→NOT RUN 30, and nothing else. No row moved to FAIL or to PASS.
- **The 35 FAIL rows that left:** `prettier` 19, `shfmt` 8, `taplo` 3, `ruff` 2, `mix format` 1, `jq` 1, `hadolint` 1.
  Before the run, the prediction was 24 to 26 FAIL rows left. It counted the phoenix `mix format` row as staying,
  and it does, but it missed the unadopted `mix format` on `benchmarks/brainfuck/bf.ex`.
- **The 30 PASS rows lost** are formatters these repositories never adopted. A PASS against a style nobody chose
  proves as little as a FAIL against it.
- **Still FAIL by design:** zod `prettier` 4 and phoenix `mix format` 1. Both repositories configure the tool.
- Wall time, context only: verify 53.25 → 46.51 s and gate tools 25.7 → 20.5 s. Headron's own share was 27.55 → 26.01 s.
  The after side ran first, at load 4.47. The before side followed at 13.17, because another suite was running.

## The 23 FAIL rows that remain, hand-checked

| Class | Rows | Evidence |
|---|---|---|
| formatter the repository configures | 5 | zod `prettier` 4, phoenix `mix format` 1 |
| per-file compile without the project's flags | 5 | `clang` without include paths (`libnotify.h`, `libbase64.h`) 3; `swiftc` missing a sibling symbol 2 |
| consumer environment | 11 | missing openssl headers, rustc below MSRV 2, a dependency that fails to build on this Go 2, Hex not installed, no `node_modules` 3, pytest suites with uninstalled dependencies 2 |
| true finding | 2 | Python 2 `print` statements under a Python 3 parse (dockerfiles) |

These classes are INFERRED. The two `swiftc` rows were read
from their first error, not compiled with the project.

## Crashes and coverage gaps

- **Crashes:** 0 tracebacks and 0 in-process route or gate exceptions, on both sides.
- **`headron check` exited 1 in all 8 repositories, on both sides.** In a consumer checkout it checked Headron's own
  contract, and the installed tool environment lacks the locked `rpds-py`, so `dependency_count_is_the_closure`
  failed. Fixed by HLIntel/Headron#489: in a tree that is not Headron's repository, `check` answers NOT RUN with rc 0
  and names `headron verify` as that tree's proof. Re-measured on the same picks: rc 0 in all 8.
- **Unrouted files (771 of 2505)** are mostly content with no gate to run: `.rst` 79, `.eex` 155, images, licences,
  `.gitignore`. Code suffixes with no route include `.rb` (24 across benchmarks and fzf), `.erl` 5, `.cr` 7, `.d` 8,
  `.nu` 3 and `.fish` 3.
- **Not covered by this run:** CI-only gates, a full `verify` on every tracked file, and Windows. These are unmeasured.

## Residuals closed after the run

Re-measured on the same 119 picks, against the last run before these fixes (tree `19d5d001`), one run per side. PASS 88 to 88 (none lost), FAIL 23 to 17,
NOT RUN 138 to 144, 0 tracebacks, and `git status --porcelain --ignored` unchanged in all 8.

- **A per-file `rustc` or `scalac` writes nothing into the checkout.** Per-file `rustc` now runs `--emit=metadata --out-dir` and `scalac`
  runs `-d`, both into one fixed directory under Headron's home, outside every checkout. For `rustc` this is CONFIRMED on a loose file: the
  tree is left clean and a planted type error still fails. `scalac` was not installed, so its behaviour is INFERRED.
- **A file a build names is left to that build.** Per-file `clang`, `clang++` and `swiftc` are NOT RUN when a
  Makefile, CMakeLists.txt or meson.build at or above the file, inside its repository, names it. 6 benchmark FAIL
  rows moved to NOT RUN, each named in its folder's Makefile: the 5 compiled without the project's flags, and
  `base64/test-crypto.cpp`, which was the consumer-environment row for missing openssl headers.
  A build file that does not name the file leaves the per-file gate running.
- The ignored files left after `verify` are the same in both runs: tool caches (`.pytest_cache`, `.ruff_cache`) and
  project builds (cargo `target/`, gleam `build/`, `node_modules`). None is a per-file compile's output.

## Residuals left open

- 10 of the 11 consumer-environment FAIL rows classified above stand: tools or dependencies the clone does not install.
- A library `.rs` file with no `main` outside any crate still fails bare `rustc` (E0601).

## Reproduce

The harness is not part of the tree, since a derived artefact does not belong in a repository. Its procedure: shallow-clone each repository at the pinned SHA.
Then, for each one, run `route --json`, `gate` and `port --frame agent` per picked file, plus `port .`, `init --no-wiring --no-run`
and `check`. Then make a scratch base commit without the picks and run `verify --base <it> --jobs 2 --json`, with
`git status --porcelain --ignored` before and after. The clones are only read. The harness never pushes, opens an issue or opens a pull request.
