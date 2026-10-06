# OpenSSF — Scorecard and Best Practices

Part of [CERTIFICATION](CERTIFICATION.md).

## OpenSSF Scorecard, check by check

Floors are declared once and rendered here:

<!-- BEGIN generated: scorecard-floors (python scripts/atlas.py index --write) -->
Derived from `config/github-controls.json`: 17 checks carry a floor, and the
aggregate floor is 7.5. `python scripts/ghaudit.py` prints the live value beside each
one and reports every check below its floor — this page states no measurement.

| check | floor |
|---|---|
| `Binary-Artifacts` | 10 |
| `Branch-Protection` | 4 |
| `CI-Tests` | 10 |
| `CII-Best-Practices` | 0 |
| `Code-Review` | 0 |
| `Contributors` | 0 |
| `Dangerous-Workflow` | 10 |
| `Dependency-Update-Tool` | 10 |
| `Fuzzing` | 10 |
| `License` | 10 |
| `Maintained` | 0 |
| `Pinned-Dependencies` | 10 |
| `SAST` | 10 |
| `Security-Policy` | 10 |
| `Signed-Releases` | 10 |
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
| **SAST** | CodeQL default setup over Python and Actions, with both contexts required for merge. | **nothing — CLOSED at v2.27.0**, measured 10, "SAST tool is run on all commits". It sat at 8 from v2.0.0 while it healed, reported and never excused, because the unchecked commits predated the pull-request flow. | CLOSED, and it closed exactly as the shortfall predicted — which is the evidence that reporting a shortfall beats lowering the floor to hide it |
| **Vulnerabilities** | No open advisories. `Dependency Review` is a required check; Dependabot security updates are on. | — | held |
| **Dependency-Update-Tool** | Dependabot covers every manifest that exists — GitHub Actions (which maintains the SHA pins below), the pip lock, the Go module and the ClusterFuzzLite Dockerfile; `atlas.py check` refuses a duplicate (ecosystem, directory) pair. | — | held |
| **Pinned-Dependencies** | Every action was pinned to a commit SHA at v2.1.0, with the release tag kept in a trailing comment so Dependabot can still bump it. Two of the references were not even tags: `codeql-action@v4` and `dependency-review-action@v5` are release BRANCHES, so "pinned to v4" meant "whatever that branch points at". | — | **held at 10** since the rescan after v2.2.0 |
| **Security-Policy** | SECURITY.md exists and names the reporting route. Scorecard also looks for a reachable link or address in it. | add the advisories URL — done at v2.1.0 | done, awaiting rescan |
| **Branch-Protection** | `main-protection` requires a pull request, four status checks and linear history, forbids deletion and force-push, dismisses stale reviews, requires threads resolved and up-to-date branches, and carries no bypass actor. Measured 4 of 10 at v2.27.0. | **the scan names each one:** required approvers, codeowners review, last-push approval — Scorecard's tiers 3 to 5, and every one of them counts an approval | AT THE SOLO CEILING: setting any of them has two outcomes, both worse than the 4. Every merge wedges because nobody can approve, or a bypass actor is added to unwedge it — and a control with a bypass is a declared control that enforces nothing |
| **Code-Review** | Every change since v1.3.0 has gone through a pull request with required checks; measured 0 of 9 changesets approved at v2.27.0. | Scorecard counts APPROVING REVIEWS, and GitHub does not let an author approve their own | STRUCTURAL: a second human reviewer. A review account held by the sole maintainer would raise the number while approving nothing, so it is REFUSED — this is a supply-chain trust signal, and manufacturing one is the failure this repository exists to refuse |
| **Contributors** | One maintainer. | contributors from two or more organisations | STRUCTURAL |
| **CII-Best-Practices** | Nothing registered. | register the project at bestpractices.dev and answer the criteria — most are already satisfied and evidenced below | OWNER ACTION: one sign-in, nothing to build |
| **Fuzzing** | `examples/go` is a real module with `FuzzPool`, a target that drives the bounded worker pool with generated limits and job counts and asserts the four properties the pool exists for: no panic, concurrency never past the declared limit, no goroutine outliving the call, and a non-positive limit refused rather than defaulted. CI fuzzes it for a bounded 30 seconds on every pull request; the seed corpus runs in `go test`. A seeded property sweep also covers the router and the entry grammar, and ClusterFuzzLite (`.github/workflows/cflite-pr.yml`) fuzzes every target under `fuzz/` — the manifest entry grammar with the router, and the JSONC reader — with AddressSanitizer for a bounded 120 seconds in code-change mode on every pull request. | — | held |
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
| unique versioning and a changelog | [docs/VERSIONING.md](VERSIONING.md) — one line per version, the only changelog, enforced across every declared version site (`atlas.yaml/version_sites`) by `atlas.py check` |
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

**One criterion needs a decision rather than a document:** a second reviewer (see Code-Review above).
Signed releases are attested in `release.yml` (see Signed-Releases above).
