# Certification — what this repository can prove, per check

**An aggregate score hides which check fell.** Branch-Protection can drop three points while
Pinned-Dependencies rises three and the total does not move, so this page is organised per check
and `config/github-controls.json` carries **a floor per check**, not one floor for the score.
`python scripts/ghaudit.py` reports every check that is below its floor, and the floors only ever
move up.

**Worked example of why this page is per check — a RECORDED EVENT, not a current reading:** at
v2.2.0 the aggregate rose while SAST fell behind it. A single floor on the total would have
reported that as an improvement. The numbers are in
[config/github-controls.json](../config/github-controls.json), beside the floor they moved against;
this page does not restate them, and neither should anything else.

**Nothing on this page states a current score, including in the table below.** The instrument does:

```bash
python scripts/ghaudit.py     # per-check floors, the live aggregate, and every DIFF
```

What each instrument proves, and who closes what it does not: [INSTRUMENTS](INSTRUMENTS.md). OpenSSF Scorecard and Best Practices, check by check: [OPENSSF](OPENSSF.md).

## What this repository already is

An openly licensed project (MIT), continuously tested on every pull request (mutation tests before
the contract), security-scanned (CodeQL over Python and Actions, secret scanning with push
protection), dependency-managed (Dependabot plus a required Dependency Review), documented
(a generated index, an operating model, and a research file that labels its claims), and governed
by a ruleset that requires a pull request and four passing checks before a merge.

Each of those is verifiable rather than asserted: the table below names the mechanism, and the
instrument re-measures it.

## The badges, and what each one is worth

A badge is a claim a stranger reads in two seconds, so each one has to be measured by somebody
other than this repository. **None of these is a static image or a number typed into a file** — the
licence and version badges read the repository itself, and the rest are rendered by the service
that does the measuring.

| badge | served by | what it actually tells a reader | the instrument that settles it |
|---|---|---|---|
| Atlas CI | GitHub Actions | the contract and the mutation tests passed on `main` at the last run | `python scripts/atlas.py check` — the exit code, on your tree, now. The badge is about one branch at one moment; the command is about yours. |
| OpenSSF Scorecard | scorecard.dev | an aggregate over automated supply-chain checks | `python scripts/ghaudit.py` — it compares **every check against its own floor**, prints what each open arm is worth, and refuses to project if the weight model stops reproducing the published score |
| OpenSSF Scorecard workflow | GitHub Actions | the scan itself ran and published its results | `ghaudit.py` prints the published scan's own date, so a green workflow beside a stale score is visible rather than implied |
| M8ven Score | m8ven.ai, Live Monitored | an outside MCP trust grade: static analysis of the code (credential flow, sensitive files, obfuscation, licence) plus reputation, re-verified on every push. A new project's grade is capped until it earns adoption, so the letter moves on stars, not commits | `ghaudit.py` floors the **code** sub-score from `config/github-controls.json` and prints the grade, the verified commit beside the main HEAD, and the freshness tier, so a picture of an old commit is visible rather than implied |
| licence | shields.io, reading this repository | the repository has a detected OSI licence | `ghaudit.py` compares the detected SPDX id to the declared one in `config/github-controls.json` |
| contract version | shields.io, reading the tags | the newest tag, which is the newest released contract | `ghaudit.py` fails on a tag with no release, and `atlas.py check` fails when the version string disagrees across its declared sites |

**No badge here is the last word on anything.** Each row names the command whose exit code settles
it, because a badge is a cached picture of a past run and an instrument is a measurement of now.
That is the whole reason the column changed: a badge cannot be prevented from going stale, so it
is never left standing alone.

**Not yet earned:** the OpenSSF Best Practices badge needs the project registered at
bestpractices.dev — one sign-in. The answer sheet below is the paste, generated from
[config/openssf-best-practices.json](../config/openssf-best-practices.json), and every evidence
path is a link the contract validates.

<!-- BEGIN generated: best-practices (python scripts/atlas.py index --write) -->
Derived from `config/openssf-best-practices.json` — 30 criteria at the **passing** level, each with the file that answers it. Registration at https://www.bestpractices.dev is a sign-in and a paste.

| criterion | answer | evidence |
|---|---|---|
| `description_good` | Met | [README.md](../README.md) — what it is, who it is for, and one command that answers |
| `interact` | Met | [.github/pull_request_template.md](../.github/pull_request_template.md) — the template asks for verification evidence per layer and a breakage-review checklist |
| `contribution` | Met | [docs/VERSIONING.md](VERSIONING.md) — the release procedure and the same-commit rule |
| `license_location` | Met | [LICENSE](../LICENSE) — MIT, at the standard path |
| `floss_license_osi` | Met | [LICENSE](../LICENSE) — OSI-approved |
| `documentation_basics` | Met | [docs/INDEX.md](INDEX.md) — generated index |
| `documentation_interface` | Met | [MODEL.md](../MODEL.md) — the operating model, plus per-route guides and cards |
| `repo_public` | Met | [SECURITY.md](../SECURITY.md) — public deliberately; the policy states why and what that costs |
| `repo_track` | Met | [docs/GIT-WORKTREES.md](GIT-WORKTREES.md) — git, with lane rules |
| `repo_interim` | Met | [wiki/BRANCH-WORKTREES.md](../wiki/BRANCH-WORKTREES.md) — every change lands through a lane and a pull request |
| `version_unique` | Met | [VERSION](../VERSION) — semver, asserted identical across six files by atlas.py check |
| `release_notes` | Met | [docs/VERSIONING.md](VERSIONING.md) — one line per version, the only changelog; ghaudit fails on a tag with no release |
| `report_process` | Met | [SECURITY.md](../SECURITY.md) — issues, and private advisories |
| `vulnerability_report_private` | Met | [SECURITY.md](../SECURITY.md) — private vulnerability reporting enabled, asserted by ghaudit.py |
| `build` | Met | [scripts/requirements.lock.txt](../scripts/requirements.lock.txt) — hash-pinned install; the harness runs from a bare checkout |
| `build_reproducible` | Met | [.github/workflows/release.yml](../.github/workflows/release.yml) — deterministic tarball, sorted, zeroed ownership, epoch mtime, attested |
| `test` | Met | [scripts/atlas_test.py](../scripts/atlas_test.py) — a planted defect per rule, with the case count asserted |
| `test_invocation` | Met | [scripts/check_contract.py](../scripts/check_contract.py) — one command, working from any directory |
| `test_most` | Met | [docs/VERIFY.md](VERIFY.md) — every rule the contract enforces has a case; coverage is reported, never targeted |
| `test_continuous_integration` | Met | [.github/workflows/atlas-ci.yml](../.github/workflows/atlas-ci.yml) — mutation tests run before the contract on every pull request |
| `tests_are_added` | Met | [docs/ENGINEERING-CONCEPTS.md](ENGINEERING-CONCEPTS.md) — the second sighting of a shape requires a mutation-tested guard |
| `warnings` | Met | [pyproject.toml](../pyproject.toml) — ruff enabled only for rules the tree already satisfies, so the gate is never silenced |
| `warnings_fixed` | Met | [pyproject.toml](../pyproject.toml) — clean, enforced in CI |
| `know_secure_design` | Met | [docs/ENGINEERING-CONCEPTS.md](ENGINEERING-CONCEPTS.md) — least privilege, fail-safe defaults, and every concept paired with its mechanism |
| `know_common_errors` | Met | [patterns/BOUNDARY-BREAKAGE.md](../patterns/BOUNDARY-BREAKAGE.md) — boundary contracts and the failure tests for them |
| `no_leaked_credentials` | Met | [config/github-controls.json](../config/github-controls.json) — secret scanning and push protection, compared by ghaudit; the contract fails on a tracked .env |
| `static_analysis` | Met | [docs/CERTIFICATION.md](CERTIFICATION.md) — CodeQL default setup, two contexts required for merge |
| `static_analysis_fixed` | Met | [docs/CERTIFICATION.md](CERTIFICATION.md) — the one clear-text-logging alert was fixed in code, not suppressed |
| `dynamic_analysis` | Met | [fuzz/fuzz_manifest_entry.py](../fuzz/fuzz_manifest_entry.py) — coverage-guided fuzzing of the grammar and router, plus a Go fuzz target for the pool |
| `dependency_monitoring` | Met | [.github/dependabot.yml](../.github/dependabot.yml) — every manifest that exists, including the ClusterFuzzLite Dockerfile; Dependency Review required for merge |
<!-- END generated: best-practices -->

## The honest limits

- **A ruleset with a bypass actor is advisory for that actor.** `ghaudit.py` prints the bypass list
  beside the verdict so a green audit cannot imply that nobody can skip.
- **Two secret-scanning controls are declared and refused by the platform** — non-provider patterns
  and validity checks. The measured cause is in the declaration file; they are reported as BLOCKED,
  which is neither a pass nor a silent gap.
- **A badge is a claim.** The badges in the README are served by the projects that measure them, so
  they change when the measurement changes. None of them is a picture typed into this repository.

## What the numbers do not prove

Read every figure on the landing page narrowly. Each is true of the run that produced it and no wider:

- **Routing and context, not task success.** `bench.py` and `abtest.py` measure whether a model picks the right
  command and what it read; whether an agent then completes a real change is not measured here, and the arms
  that would need a real agent print NOT RUN rather than a simulated number.
- **Authored inside the system it evaluates.** The task suites and their expected answers are written in this
  repository. `abtest.py` holds a set out and `taskbench.py` prints its chance baseline, but neither is an
  independent industry benchmark.
- **Parses and type-checks, not behaviour.** The commit hook runs each file's check-only command; tests and
  behaviour stay with CI and with the pack's own test gate.
- **Bounds the agent that asks.** The controls refuse what a run submits to them; an agent that bypasses the
  harness is bounded only by its host — hence `sandboxgen.py`, and the host rows `agentrun.py` prints UNOBSERVED.
- **Declared is not installed.** A manifest can name a tool this machine lacks; `packprobe.py` reports what
  resolves and runs here, and provenance says what was never exercised against a real toolchain.
- **Retrieval is lexical.** The index misses a paraphrase that shares no vocabulary with the text it should find.

The defensible claim: better routing, verification bookkeeping and refusal behaviour inside the declared test
surface, held by `scoreboard.py` floors. Universal gains in autonomous productivity, correctness or security
are not claimed, because nothing here measures them.

## The agreement graph

Every roster in this atlas points one way — an invariant to its check, an instrument to its script.
Read backwards, they answer the question a reader actually asks before editing: **what does this
file answer for?**

<!-- BEGIN generated: agreement-edges (python scripts/atlas.py index --write) -->
An **edge** is `(file) → (declaration that file answers for)`. It exists when a roster in
`atlas.yaml` names a function, a script or a path and that name resolves to something real.

**291 edges over 79 files.** `agreement_errors` fails the build when any
declaration resolves to none, so coverage is enforced rather than reported.

| kind | declaration → implementation | edges |
|---|---|---|
| `branch_policy` | a landing rule → the function deciding it | 1 |
| `control` | an agent control → its deciding function | 6 |
| `declaration` | — | 1 |
| `effect` | an effect class → its refuser | 6 |
| `failure_mode` | a recorded mistake → what refuses it now | 127 |
| `instrument` | an instrument → its script | 77 |
| `invariant` | a hard invariant → the function enforcing it | 46 |
| `mechanism` | a harvested language mechanism → where it lives | 14 |
| `parser_discipline` | a parsing rule → the reader that enforces it | 13 |

**The target is not edge count.** Adding declarations nothing refuses would raise it and
weaken the repository — the unshipped-arm shape at graph scale. The numbers that matter are
COVERAGE (declarations with an implementation, enforced at 100%) and FILES ANSWERING FOR
NOTHING, which is the one that should fall. `thea agreement <file>` answers for one file;
`thea agreement --impact` reads a diff through the same graph.
<!-- END generated: agreement-edges -->
