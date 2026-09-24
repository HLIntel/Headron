# Certification — what this repository can prove, per check

**An aggregate score hides which check fell.** Branch-Protection can drop three points while
Pinned-Dependencies rises three and the total does not move, so this page is organised per check
and `config/github-controls.json` carries **a floor per check**, not one floor for the score.
`python scripts/ghaudit.py` reports every check that is below its floor, and the floors only ever
move up.

Nothing on this page states the current score. The instrument does:

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

## OpenSSF Scorecard, check by check

Floors are declared in [config/github-controls.json](../config/github-controls.json) and were
measured at contract v2.0.0.

| check | floor | what this repository does | what would raise it | status |
|---|---|---|---|---|
| **Token-Permissions** | 10 | Every workflow declares `permissions: contents: read` and raises it only per job. Enforced by the `least_privilege` hard invariant, which fails the contract on a workflow with no read-only floor. | — | held |
| **Dangerous-Workflow** | 10 | No `pull_request_target`, no script injection from an untrusted context. `atlas.py check` fails on a privileged trigger. | — | held |
| **Binary-Artifacts** | 10 | No executables in the tree. The `code_blobs_are_bounded` and `no_unbounded_growth` invariants cap what may enter. | — | held |
| **License** | 10 | MIT, detected by GitHub and asserted by `ghaudit.py` against `config/github-controls.json`. | — | held |
| **CI-Tests** | 10 | Atlas CI runs the mutation tests BEFORE the contract on every pull request. | — | held |
| **SAST** | 10 | CodeQL default setup over Python and Actions, plus its two contexts required for merge. | — | held |
| **Vulnerabilities** | 10 | No open advisories. `Dependency Review` is a required check; Dependabot security updates are on. | — | held |
| **Dependency-Update-Tool** | 10 | Dependabot covers GitHub Actions — which is what now maintains the SHA pins below. | — | held |
| **Pinned-Dependencies** | 0 | Every action was pinned to a commit SHA at v2.1.0, with the release tag kept in a trailing comment so Dependabot can still bump it. Two of the references were not even tags: `codeql-action@v4` and `dependency-review-action@v5` are release BRANCHES, so "pinned to v4" meant "whatever that branch points at today". | rises on the next scan | done, awaiting rescan |
| **Security-Policy** | 4 | SECURITY.md exists and names the reporting route. Scorecard also looks for a reachable link or address in it. | add the advisories URL — done at v2.1.0 | done, awaiting rescan |
| **Branch-Protection** | 3 | `main-protection` requires a pull request, four status checks and linear history, and forbids deletion and force-push. Branches must now be up to date before merge. | the remaining points need ≥1 approving review and no admin bypass | OWNER DECISION: a solo maintainer cannot approve their own pull request, so requiring a review would make the bypass load-bearing rather than optional |
| **Code-Review** | 0 | Every change since v1.3.0 has gone through a pull request with required checks. | Scorecard counts APPROVALS, not pull requests | STRUCTURAL: needs a second person, or a review bot whose approval Scorecard recognises |
| **Contributors** | 0 | One maintainer. | contributors from two or more organisations | STRUCTURAL |
| **CII-Best-Practices** | 0 | Nothing registered. | register the project at bestpractices.dev and answer the criteria — most are already satisfied and evidenced below | OWNER ACTION: one sign-in, nothing to build |
| **Fuzzing** | 0 | No fuzzing integration. | OSS-Fuzz or ClusterFuzzLite | DECIDED AGAINST for now: the attack surface is a local CLI over files in its own repository. A property test over the router is the proportionate instrument, and `atlas_test.py` already asserts ten route edge cases. |
| **Maintained** | 0 | Active development. | commit and issue activity in the trailing 90 days | held while work continues |
| **Packaging** | — | Nothing is published to a package index, deliberately — `pyproject.toml` says so. | inconclusive (-1), not a failure | N/A by design |
| **Signed-Releases** | — | Releases are cut from annotated tags; artifacts are not signed. | inconclusive (-1) because there are no build artifacts to sign | N/A while nothing is published |

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
