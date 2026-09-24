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
| `interact` | Met | [.github/pull_request_template.md](../.github/pull_request_template.md) — the template asks what would prove the goal met |
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
| `dependency_monitoring` | Met | [.github/dependabot.yml](../.github/dependabot.yml) — every manifest that exists; Dependency Review required for merge |
<!-- END generated: best-practices -->

## OpenSSF Scorecard, check by check

Floors are declared once and rendered here:

<!-- BEGIN generated: scorecard-floors (python scripts/atlas.py index --write) -->
Derived from `config/github-controls.json`: 16 checks carry a floor, and the
aggregate floor is 6.7. `python scripts/ghaudit.py` prints the live value beside each
one and reports every check below its floor — this page states no measurement.

| check | floor |
|---|---|
| `Binary-Artifacts` | 10 |
| `Branch-Protection` | 3 |
| `CI-Tests` | 10 |
| `CII-Best-Practices` | 0 |
| `Code-Review` | 0 |
| `Contributors` | 0 |
| `Dangerous-Workflow` | 10 |
| `Dependency-Update-Tool` | 10 |
| `Fuzzing` | 0 |
| `License` | 10 |
| `Maintained` | 0 |
| `Pinned-Dependencies` | 10 |
| `SAST` | 10 |
| `Security-Policy` | 10 |
| `Token-Permissions` | 10 |
| `Vulnerabilities` | 10 |
<!-- END generated: scorecard-floors -->


| check | what this repository does | what would raise it | status |
|---|---|---|---|
| **Token-Permissions** | Every workflow declares `permissions: contents: read` and raises it only per job. Enforced by the `least_privilege` hard invariant, which fails the contract on a workflow with no read-only floor. | — | held |
| **Dangerous-Workflow** | No `pull_request_target`, no script injection from an untrusted context. `atlas.py check` fails on a privileged trigger. | — | held |
| **Binary-Artifacts** | No executables in the tree. The `code_blobs_are_bounded` and `no_unbounded_growth` invariants cap what may enter. | — | held |
| **License** | MIT, detected by GitHub and asserted by `ghaudit.py` against `config/github-controls.json`. | — | held |
| **CI-Tests** | Atlas CI runs the mutation tests BEFORE the contract on every pull request. | — | held |
| **SAST** | CodeQL default setup over Python and Actions, with both contexts required for merge. | **below its floor, and reported rather than excused:** the scan reports that not every recent commit was checked, and the unchecked ones predate the pull-request flow. It clears once five consecutive commits have landed through pull requests. | OPEN, with an expiry — lowering the floor would turn a ratchet into a record of whatever happened last |
| **Vulnerabilities** | No open advisories. `Dependency Review` is a required check; Dependabot security updates are on. | — | held |
| **Dependency-Update-Tool** | Dependabot covers GitHub Actions — which is what now maintains the SHA pins below. | — | held |
| **Pinned-Dependencies** | Every action was pinned to a commit SHA at v2.1.0, with the release tag kept in a trailing comment so Dependabot can still bump it. Two of the references were not even tags: `codeql-action@v4` and `dependency-review-action@v5` are release BRANCHES, so "pinned to v4" meant "whatever that branch points at". | — | **held at 10** since the rescan after v2.2.0 |
| **Security-Policy** | SECURITY.md exists and names the reporting route. Scorecard also looks for a reachable link or address in it. | add the advisories URL — done at v2.1.0 | done, awaiting rescan |
| **Branch-Protection** | `main-protection` requires a pull request, four status checks and linear history, and forbids deletion and force-push. Branches must now be up to date before merge. | **the scan names each one:** administrator bypass, stale-review dismissal, required approvers, codeowners review, last-push approval. Bypass and stale-review dismissal were closed at v2.2.0; the other three each require a second person to approve a pull request | OWNER DECISION: a solo maintainer cannot approve their own pull request, so requiring a review would make the bypass load-bearing rather than optional |
| **Code-Review** | Every change since v1.3.0 has gone through a pull request with required checks. | Scorecard counts APPROVALS, not pull requests | STRUCTURAL: needs a second person, or a review bot whose approval Scorecard recognises |
| **Contributors** | One maintainer. | contributors from two or more organisations | STRUCTURAL |
| **CII-Best-Practices** | Nothing registered. | register the project at bestpractices.dev and answer the criteria — most are already satisfied and evidenced below | OWNER ACTION: one sign-in, nothing to build |
| **Fuzzing** | `examples/go` is a real module with `FuzzPool`, a target that drives the bounded worker pool with generated limits and job counts and asserts the four properties the pool exists for: no panic, concurrency never past the declared limit, no goroutine outliving the call, and a non-positive limit refused rather than defaulted. CI fuzzes it for a bounded 30 seconds on every pull request; the seed corpus runs in `go test`. A seeded property sweep also covers the router and the entry grammar. | — | DECIDED AGAINST for now: the attack surface is a local CLI over files in its own repository. A property test over the router is the proportionate instrument, and `atlas_test.py` already asserts ten route edge cases. |
| **Maintained** | **Measured cause, from the scan's own SARIF: "project was created within the last 90 days"** — not inactivity. Scorecard warns on young repositories on purpose. | time, plus continued activity | TIME: it clears itself once the repository is older than the window |
| **Packaging** | Nothing is published to a package index, deliberately — `pyproject.toml` says so. | inconclusive (-1), not a failure | N/A by design |
| **Signed-Releases** | `.github/workflows/release.yml` builds one **deterministic** tarball of the routing surface — sorted entries, zeroed ownership, fixed mtime — attests its provenance as a signed in-toto bundle, and attaches the artifact, its digest and the bundle to the release. It refuses to build a tree that fails its own contract. | — | landed at v2.5.0; the next tag is the proof |

## OpenSSF Best Practices (bestpractices.dev) — the passing-level criteria

Registration is one sign-in by the repository owner; this table is the evidence to paste, and the
criteria are grouped the way that questionnaire asks them.

| criterion | evidence in this repository |
|---|---|
| project website and description | [README.md](../README.md), [ABOUT.md](../ABOUT.md), and a generated [llms.txt](../llms.txt) for machine readers |
| OSI-approved licence | [LICENSE](../LICENSE) — MIT, asserted by `ghaudit.py` |
| documentation of the basics and the interface | [docs/INDEX.md](INDEX.md), [MODEL.md](../MODEL.md), per-route guides and operating cards |
| public version-controlled source | this repository, public deliberately |
| unique versioning and a changelog | [docs/VERSIONING.md](VERSIONING.md) — one line per version, the only changelog, enforced across six files by `atlas.py check` |
| release notes for each release | GitHub releases cut from annotated tags; `ghaudit.py` fails on a tag with no release |
| bug and vulnerability reporting process | [SECURITY.md](../SECURITY.md), with private vulnerability reporting enabled and verified by instrument |
| working build and automated test suite | `python scripts/atlas.py check` and `python scripts/atlas_test.py`, both run in CI on every pull request |
| tests added with new functionality | every rule the contract enforces has a planted-defect case; the case count is asserted so a skipped case cannot print a full pass |
| warning flags enabled and clean | `ruff check` configured in [pyproject.toml](../pyproject.toml), enabled only for rules the tree already satisfies |
| secure development knowledge | [docs/ENGINEERING-CONCEPTS.md](ENGINEERING-CONCEPTS.md) pairs each concept with the mechanism that implements it |
| no leaked credentials | the absolute rule in SECURITY.md, plus secret scanning with push protection, plus a contract check that fails on a tracked `.env` |
| static analysis | CodeQL over Python and GitHub Actions, required for merge |
| dependency vulnerability checking | Dependabot security updates and a required Dependency Review |
| continuous integration | Atlas CI on every push, pull request and merge group |

**Two criteria need a decision rather than a document:** a second reviewer (see Code-Review above),
and cryptographically signed releases, which only becomes meaningful once something is published.

## The honest limits

- **A ruleset with a bypass actor is advisory for that actor.** `ghaudit.py` prints the bypass list
  beside the verdict so a green audit cannot imply that nobody can skip.
- **Two secret-scanning controls are declared and refused by the platform** — non-provider patterns
  and validity checks. The measured cause is in the declaration file; they are reported as BLOCKED,
  which is neither a pass nor a silent gap.
- **A badge is a claim.** The badges in the README are served by the projects that measure them, so
  they change when the measurement changes. None of them is a picture typed into this repository.
