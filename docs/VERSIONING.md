# Repository Versioning

Current version: 3.54.0

Version tracks the behavioral and tooling contract — **not the content**. Adding a paragraph to a
guide is not a version change; changing what the harness enforces, what a route resolves to, or
what a gate requires always is.

## The same-commit rule

A contract, route, MCP role, CI/security policy, verification requirement, canonical structure, or
repository operating-policy change updates **MODEL.md, VERSION, README.md, ABOUT.md, the affected
docs/patterns/adapters, and atlas.yaml together, in one commit.**

This is enforced, not requested. `atlas.py check` reads `VERSION` and fails when the ONE line
each site declares for it (`atlas.yaml/version_sites`, a pattern per file) disagrees, or when
`atlas.yaml`'s `version` does. **One declaration, read at a named line** — until 2.29.0 the rule
asked only whether the string appeared anywhere in a file, and a generated stamp satisfied it while
the README's navigation line named a release two versions old.

## What earns which bump

| bump | earns it |
|---|---|
| **major** | a route, manifest or contract shape that existing consumers must change to satisfy. Worked case: 2.0.0 renamed `provenance.authored` to `provenance.since` and bumped the manifest's own `schema` to 2 — a reader pinned to format 1 is told, rather than left to find a field missing. |
| **minor** | a new enforced check, a new instrument, a new invariant, a new route, or a gate that now blocks something it did not |
| **patch** | a correction inside the existing contract — a repaired check, a fixed parser, a stale claim re-measured |

**A new instrument is a minor bump even if no rule changed**, because the next reader's options
changed. Skipping the bump is how a tool ends up in the tree that nothing announces.

## Release procedure

The changelog line and the release are **two different artifacts, and for a long time only the
first existed** — 17 versions were named here and never tagged, so no reader could fetch the tree
any of them described. A version with no tag is a claim with no artifact.

1. `python scripts/atlas.py check` → must exit 0.
2. `python scripts/atlas_test.py` → must report all cases pass.
3. `ruff check .` → must exit 0.
4. Bump the six places above in one commit.
5. Add exactly one line here: `<version> <what changed, in one sentence>`.
6. `git tag -a v<version> -m "<the same sentence>"` on that commit.
7. Push the tag, then cut the GitHub release from it.

**Entries are kept in ascending semver order.** They were not: the list ran
`1.0.1 → 1.1.0 → 1.0.2 → 1.0.0`, which made three versions unreadable in sequence and is the
reason this section exists.

## One line per version, and it is the only changelog

No `CHANGELOG.md`, no release-notes generator, no conventional-commit tooling. A second changelog
is a second declaration: one copy goes stale and the next reader cannot tell which is live. The
commit message carries the detail; this file carries the sentence.

0.9.5 model and runtime routing, progressive context policy, language operating cards, and the GitHub control plane.
0.9.7 YAML-parsed harness, single-sourced task profiles, directory routing, manifest schema validation and a generated language index.
1.0.0 first stable contract: a tool manifest per route, every atlas.yaml restatement generated and drift-checked, provenance on manifests.
1.0.1 mutation tests for the harness, route edge cases, a working-directory-independent entry point, and a devcontainer.
1.0.2 every hard invariant is enforced by a check or declared with its reason; an unowned invariant fails the contract.
1.1.0 hard invariants enforced by real checks over the repository's own artifacts, one planted defect per check, and worktree lifecycle rules.
1.2.0 contract instruments named with their blind spots, packprobe toolchain coverage, and pyproject declaring the tools in use.
1.2.1 private vulnerability reporting enabled with SECURITY.md re-measured against it; the first tagged release.
1.3.0 manifests validated against a JSON Schema, the harness split into router, generators and contract, every instrument declared with its closer.
2.0.0 manifest format 2 stamps provenance with a contract version instead of a date, and any date in a tracked file is refused.
2.1.0 OCaml, Scala, Swift and R routes, an explicit quantum task profile, HTML link checks, and actions pinned to commit SHAs.
2.2.0 every example is runnable and self-verifying under the exrun instrument, with a hash-pinned dependency lock and a seeded router property sweep.
2.3.0 astshape refuses duplicate code structures by canonical hash, the Forth route arrives, and a duplicate extension route fails the contract.
2.3.1 Swift excluded from language detection, with the trigger to reverse it, because a scanner that fails every run gets ignored.
2.4.0 the YAML loader refuses a duplicate key anywhere, and every tracked source file must parse before any other check runs.
2.5.0 a fuzz target for the bounded pool runs on every pull request, and releases ship an attested deterministic tarball.
2.6.0 coverage-guided fuzzing of the entry grammar and router, and cross-reference assertions that check every roster in both directions.
2.6.1 the fuzzing base image pinned by digest after the per-check Scorecard ratchet caught Pinned-Dependencies falling.
2.7.0 every pack declares how its language measures a performance change, and the last unpinned dependency was removed.
2.7.1 Scorecard floors raised to the achieved measurement, so the ratchet follows a rise as strictly as it refuses a fall.
2.7.3 the pyyaml floor and the attestation action updated by hand to the versions the lock and upstream actually pin.
2.26.0 CLAUDE.md and AGENTS.md are generated from one body with llms.txt, and the MODEL.md runtime roster is generated from atlas.yaml.
2.27.0 every pack-gate pair resolves to a runnable command or a declared absence naming its closer, refused when it does neither.
2.28.0 every stop and escalate condition names who decides it, `atlas gate` answers with one command, and a bare sleep is refused.
2.29.0 a version site is read at its declared line, and dependency gates resolve to each package manager's own tree or audit command.
2.30.0 every change class extends source_change, failure modes carry a `tell`, and gates_resolve_distinctly fails any gate collision.
3.0.0 the project became Thea Software and the repository thea-software, with a compatibility path for each renamed interface.
3.1.0 the failure ledger takes an intake entry the moment a break is seen, refused two minors later unless guarded or a standing verdict.
3.2.0 the thea skill ships in the tree, and every entry file maps the report verb to it.
3.3.0 `atlas gate <file>` prints the commands that prove a change there, and a YAML flow value split on a comma is refused.
3.3.1 YAML values are generated by `safeedit.py quote` rather than hand-quoted.
3.4.0 `enforce.py install` writes a pre-commit hook that runs each staged file's check-only command in any repository.
3.5.0 `branchstate --land` refuses to push when a clean checkout of HEAD fails its gates.
3.6.0 workflowbench scores agent commits and handoffs with and without Thea, and every harness subprocess carries a timeout.
3.6.1 a squash-merged lane reads finished, because staleness also compares the lane's tree with the base.
3.7.0 one CLI: an install ships only the launcher, `thea` lists and runs every command, and `thea-mcp` serves them read-only.
3.8.0 a runtime keeps its own tools: native_agent_tools declares where each configures them, and an install may not write there.
3.9.0 `verify.py` runs the done set and reports PASS, FAIL or NOT RUN per gate from its exit code.
3.9.1 entry pages say what Thea is, and verify reports a crashed suite's traceback as the cause.
3.9.2 the MCP route answers only a declared protocol revision and annotates every tool as read-only.
3.10.0 CLAUDE.md imports AGENTS.md, and `enforce.py install` chains an existing pre-commit hook instead of refusing it.
3.10.1 the MCP probe asks with every declared client revision, so a connecting client is never answered with the fallback.
3.11.0 every declaration has a reader: declcheck refuses undeclared words in issue and model routes and a host named as a model.
3.12.0 sandboxgen turns a task contract into container or macOS sandbox settings the runner prints as unobserved.
3.13.0 every plant is journalled so a killed suite run can be restored, and `thea failures` prints the ledger.
3.14.0 scoreboard holds benchmark floors that only rise, orphans refuses dead symbols, and `thea steps` plans one runtime's change.
3.15.0 a merge that bumps VERSION tags and publishes its own release, and `check --json` reports each finding's severity.
3.16.0 the commit hook runs a staged test file under its own runner, and every benchmark floor declares its evidence.
3.17.0 an opt-in MCP edit route applies writes only after the sandbox and budget verdicts, sealing each onto the audit chain.
3.18.0 agentbench runs a headless agent on real bug-fix tasks, and public_tree_leaks_nothing refuses private paths and hosts.
3.19.0 declared agent roles with `thea role`, and `thea resume` rebuilds interrupted work from the tree.
3.20.0 `thea intake` turns a prompt into a task or a blocking question, and verify marks a returning failure RECURRING.
3.21.0 a number typed beside a counted thing fails the build unless stamped with a version, and `thea decide` prints evidence.
3.22.0 the timed session is declared in atlas.yaml/cadence and printed by `thea cadence`.
3.23.0 delegation_contract declares the fields every handoff carries, printed by `thea delegate`.
3.23.1 `branchstate --sync` clears squash-merged lanes by comparing patches rather than ancestry.
3.24.0 a shipped skill's description is bounded by a ratchet, since it is paid on every turn.
3.24.1 the ledger records the rebase-before-refused-push shape that strands a commit in the reflog.
3.25.0 heavyidle and vaultlinks become declared instruments, and lanes are tagged by name before any land or rebase.
3.26.0 every environment input the harness reads is declared, and declcheck refuses an undeclared read or an unread declaration.
3.27.0 `thea shell "<cmd>"` lets any runtime refuse known silent shell shapes before running them.
3.28.0 an unquoted sentence in a YAML flow collection is refused, and every planted-suite anchor must match something.
3.29.0 command verdicts judge the paths an allowed binary's arguments carry, refusing absolute or traversing writes.
3.30.0 a success status with an empty payload is no longer scored as an answer, judged by one shared predicate.
3.31.0 call restrictions become forbidden_calls rows with reasons, and an instrument no gate reaches fails until wired or declared.
3.32.0 `enforce.py check` runs on this repository's own tree, and an undecidable file is skipped rather than refused.
3.33.0 every done-set gate declares whether its verdict depends on the machine, and verify labels such a pass.
3.34.0 syntax trees are cached by content and the planted suite runs first in CI, so it fits its deadline.
3.35.0 contextcost measures MCP tool-schema tax when given tool lists, and a tree-sized working directory is refused.
3.36.0 the `.thea` notation compiles to the agent task contract, with declared effect classes and per-directory scopes.
3.37.0 agreement.index reads every roster backwards, so a file shows what it answers for, and agreement.lock hashes the contract.
3.38.0 contract checks got faster through content-keyed caches, and every control declares the phase in which it can still refuse.
3.39.0 the external editor host and its adapter were retired; runtime rosters list only runtimes that read an entry file.
3.40.0 ledger intake for agent-configuration failure shapes, and both entry-path budgets fell to their measured sizes.
3.41.0 an agent using the installed CLI from another repository branches and lands in its own tree, never the atlas.
3.42.0 `.thea` watch blocks carry ledger shapes, a verdict piped into a filter without pipefail is refused, and `thea landed` arrives.
3.43.0 agent_success_patterns pairs each recurring failure with a reusable move and the functions that prove it.
3.44.0 every Markdown file has a class with a rule: living notes are capped and reachable, records append-only.
3.45.0 no owner-specific names in the tree: leaks refuses terms from an untracked private list, and success moves are checked.
3.46.0 `thea port <target>` returns route, tier, gates, lessons and next commands in one record, and every entry file names it.
3.47.0 `thea brainstorm` checks a strategic decision record, and `thea shell` refuses exposed servers and typed credentials.
3.48.0 route and instrument counts are ratchets that only fall, and a run's receipt carries contract hash, base and head.
3.49.0 YAML and shell artifacts must parse, and `thea shell` refuses git commands that destroy work.
3.50.0 typed judgments with declared bars, and `land` never retries a rebase conflict or failing gate.
3.51.0 stricter routing, verification, landing and tool-surface enforcement released for pinned consumers.
3.52.0 typed judgments for gate sufficiency, edge relevance and failure shape, shebang routing, and a privacy-scanned agent registry.
3.53.0 the package is `thea-software` on the index, and an installed CLI with no checkout downloads its own release tree, sha256-checked and cached, refusing on a mismatch or no network; the documented install is declared once, rendered into README and CONSUMING, and executed on every pull request in a clean home; Thea ships as a chat skill for a chat that can run nothing; main requires `Thea verify`.
3.54.0 one heavy suite per machine: `thea slot` holds a single flock across every repository and agent, hands it down to nested runs, and runs at utility QoS with capped workers; a timed-out gate is NOT RUN; MCP is one tool, `thea {argv}`; verify fails a lane too far behind its default branch; README and INDEX render from one facts record.
