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

## Instruments — what each one proves, and who closes what it does not

Generated from `atlas.yaml/instruments`. Run them; do not read a number about them from this page.

<!-- BEGIN generated: instruments (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/instruments`. Run them; do not read a number about them from this page. **Every one also declares `closed_by`** — what covers the limit in column three — and `check` refuses an instrument that leaves it empty. A generated block is read wherever it is placed, so this NAMES `atlas.yaml/instruments` rather than linking it: a relative link is correct only for the document it was written in, and moving this block off the landing page broke exactly that.

| instrument | proves | does not prove |
|---|---|---|
| `providers.py` | a measurement reaches any OpenAI-compatible provider through one path, at a declared pace, with keys read by NAME from the… | that the vendor's quota is free of other jobs on the same key — it sees the sum |
| `atlas_guards_test.py` | the guards added at 2.27.0-2.28.0 bite — each plants its defect and asserts the contract refuses it, counted in atlas_test's own… | anything atlas_test.py does not already claim; it is that suite, split for shape |
| `safeedit.py` | a scripted edit to this tree refuses an anchor that matches zero or several times, reads every write back, and refuses a YAML… | that the edit is RIGHT — only that it landed exactly where and how it was aimed |
| `nativetools.py` | every runtime in runtime_entry declares how it keeps its own tools, an install writes no runtime's tool configuration, a tracked… | what a runtime does with its tools at run time, or a configuration outside this tree — a user's home settings… |
| `verify.py` | every gate in verification_policy/done_set was RUN here, and which exited 0 — a gate not run is NOT RUN and the whole run exits… | that a gate's coverage is sufficient — the self-report is shown beside the verdict so a reader judges it, and… |
| `declcheck.py` | issue_routes use only declared words, model_routes name only runtimes, front_end reads what exists and holds no comma fragment,… | that a declaration is WISE — only that a program reads it and it refers to what is there |
| `sandboxgen.py` | a task contract and config/agent-sandbox.json become a host sandbox — docker flags with no network, a read-only root, only the… | that the host ran it, or that a network allowlist is enforced — that is refused, since it needs an egress… |
| `resilience.py` | this harness's own network calls retry only what can succeed (429, 5xx, timeouts), refuse 4xx on first sight, latch on a 402,… | that sibling processes back off — the breaker is per process and a vendor sees the SUM on one credential; nor… |
| `atlas.py check` | the repository satisfies its own contract — links, routes, guides, cards, manifests, labels, generated blocks and files, hard… | that a declared tool exists anywhere, or that a manifest names the right tools |
| `atlas.py route / plan` | the route for one artifact, the precedence rule that resolved it and the evidence for that rule, as text or as a JSON record | that the thing routed to is correct for the task |
| `atlas.py index` | every generated block and generated file in the tree matches what the declaration renders, and rewrites them when it does not —… | that a generated document says something worth saying |
| `atlas.py invariants` | every hard invariant in atlas.yaml is CHECKED by a function or DECLARED with its reason, and names which | that a declared invariant is true of a consuming system |
| `atlas_test.py` | the contract still FAILS on a planted defect — one case per rule, its own case count asserted, and this harness cross-checked… | the truth of a manifest's tool names |
| `check_contract.py` | the contract runs from the repository root, from scripts/ and from an unrelated directory | anything about the contract's content |
| `packprobe.py` | per pack and in total — how many declared entries there are, how many are commands, and (--mode version\|smoke) which of them run… | that a pack was ever exercised end to end, or that a tool absent here is absent elsewhere |
| `atlas.py doctor` | which capabilities THIS machine has — interpreter, PyYAML, git, gh, ruff, jsonschema — and, for each one missing, what stops… | that a present tool is new enough, or anything about the language toolchains the packs declare |
| `astshape.py` | no two Python functions in this repository share a canonical AST — names, literals and docstrings erased — and none exceeds the… | anything about the 34 language packs, whose formatters and linters are their own declared authority, and… |
| `exrun.py` | every example under examples/ RUNS on this machine and its own assertions hold — routed by this repository's own router, with the… | anything about a toolchain that is absent here, or about the rest of a pack's declarations |
| `ghaudit.py` | the live GitHub controls — visibility, secret scanning, rulesets, required checks, topics, licence — match… | that a required check is a good check, or that a bypass actor did not use its bypass |
| `agentpolicy.py` | the five verdicts the autonomous profile names — path, command, budget, approval and scope — decided from atlas.yaml/agent_policy… | that the process asking for a verdict is the one being bounded; an agent that never calls it is not… |
| `agentaudit.py` | the event stream for a task recomputes — every event carries the hash of the one before it, so a removed or edited event is named… | that an event was written for something that happened; a chain covers what it contains, never what was never… |
| `agentrun.py` | a task contract validates, resolves against the router, and runs under every control — and that the final record's changed files,… | that the sandbox rows marked host-observed are satisfied; it prints those UNOBSERVED rather than claiming them |
| `agent_properties_test.py` | seven invariants of the policy core hold over seeded generated inputs — forbidden beats allowed, prefixes stop at a separator,… | that the generator reaches every region; it draws from a declared alphabet |
| `agent_test.py` | every control REFUSES its planted defect and ALLOWS the reference contract — a negative case per control, a held-out contract the… | that the controls are the right controls, or that a real agent calls them |
| `atlas_cli.py` | which atlas an invocation runs against and WHICH rule decided it — an explicit root, the environment, a consumer's pinned config,… | that the resolved atlas is the one the consumer intended, or that a pinned ref is the ref they reviewed |
| `atlasci.py` | every file in a consumer's diff resolves to a route, and what each required gate would run as on that route — failing on a file… | that those gates PASSED; it runs inside a repository whose toolchain it cannot see, and a workflow printing… |
| `atlasindex.py` | an index built on DECLARED boundaries only — no chunk splits a function or a heading — invalidated by content checksum, searched… | semantic recall; the cosine arm matches VOCABULARY OVERLAP, so a paraphrase sharing no terms with the query… |
| `freshness.py` | how far behind each top-level path was last touched, measured in CONTRACT VERSIONS rather than days, against a declared horizon… | that a path past the horizon is WRONG — some paths should not change, which is what the exemption is for; it… |
| `identity.py` | where the owner's name appears in this tree, that the declaration and the tree agree, and exactly which lines a staged rename… | that the successor account exists on the platform, or that the repository has been moved to it; a rewritten… |
| `langbar.py` | what this repository's own .gitattributes makes detectable, per language and in bytes, and that every file declared generated is… | what GitHub will publish; Linguist has heuristics this does not implement |
| `branchstate.py` | how much work exists on a local branch that no remote holds, per branch, in commits and in hours, against a declared bound | that pushed work is safe, or that the remote is reachable; it reads local refs |
| `abtest.py` | whether a language model answers a declared question better WITH this repository's routed context than without it, and what that… | anything about a different model, a different phrasing or a different question — the prompt is part of the… |
| `enforce.py` | a file an agent is about to commit parses and type-checks under its own toolchain's check-only command, in any repository, under… | that the code is correct — tests stay with CI — nor anything about a file whose pack has no check-only… |
| `workflowbench.py` | what agents DO with and without Thea — solo, whether a broken change lands in git with and without the enforce hook; handoff,… | anything beyond the models, tasks and phrasings run; a sample, never an edge |
| `staleness.py` | which tracked files and which areas of the tree were edited longest ago, and which worktrees are finished, stale, locked or… | that an old file is wrong or a stale worktree abandoned; it names what nobody has touched, and a reader… |
| `taskbench.py` | whether a model does reasoning (diagnose a failure from its symptom), process (the gates a described change needs) and… | anything about design, open-ended strategy or arithmetic, which have no declared answer here; the plan and… |
| `bench.py` | the router resolves every declared task — fixed AND held out — against a printed chance baseline, and how much less context the… | that an agent using this atlas completes more tasks; routing and context are what this repository controls,… |
| `knowledge.py` | the knowledge declaration is complete and self-consistent — every data class names how it fails, every layer names what it must… | that any index was actually BUILT this way; a declaration is not an ingestion |
| `contextcost.py` | what this repository hands over BEFORE a route is resolved, in bytes, against a declared band per entry path — and how much… | that the bytes on the entry path are the RIGHT bytes; a short document that misroutes every reader costs more… |
| `commands.py` | every command `thea` answers carries a help line, and the roster a CLI, an MCP server or a front end reads is one parser plus… | that a listed command succeeds; each command's own gate and planted case do that |
| `thea_mcp.py` | an MCP client lists and calls the same commands `thea` answers, with schemas read off the one parser, each call in its own… | that a client renders the result well, or any MCP feature beyond tools — resources and prompts are not… |
| `cli_test.py` | an install shipping only the launcher runs check, doctor, the roster and an instrument from outside the atlas; the roster… | a real pip install on another platform — the staged copy imports exactly what ships, and CI runs it on one OS |
| `packmanifest.py` | every languages/*/tools.yaml conforms to tools/tools.schema.json, through ONE reader, and a schema keyword the reader does not… | that a declared tool is installed or that its command works — packprobe and doctor ask PATH that |
<!-- END generated: instruments -->

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
| **Dependency-Update-Tool** | Dependabot covers GitHub Actions — which is what now maintains the SHA pins below. | — | held |
| **Pinned-Dependencies** | Every action was pinned to a commit SHA at v2.1.0, with the release tag kept in a trailing comment so Dependabot can still bump it. Two of the references were not even tags: `codeql-action@v4` and `dependency-review-action@v5` are release BRANCHES, so "pinned to v4" meant "whatever that branch points at". | — | **held at 10** since the rescan after v2.2.0 |
| **Security-Policy** | SECURITY.md exists and names the reporting route. Scorecard also looks for a reachable link or address in it. | add the advisories URL — done at v2.1.0 | done, awaiting rescan |
| **Branch-Protection** | `main-protection` requires a pull request, four status checks and linear history, forbids deletion and force-push, dismisses stale reviews, requires threads resolved and up-to-date branches, and carries no bypass actor. Measured 4 of 10 at v2.27.0. | **the scan names each one:** required approvers, codeowners review, last-push approval — Scorecard's tiers 3 to 5, and every one of them counts an approval | AT THE SOLO CEILING: setting any of them has two outcomes, both worse than the 4. Every merge wedges because nobody can approve, or a bypass actor is added to unwedge it — and a control with a bypass is a declared control that enforces nothing |
| **Code-Review** | Every change since v1.3.0 has gone through a pull request with required checks; measured 0 of 9 changesets approved at v2.27.0. | Scorecard counts APPROVING REVIEWS, and GitHub does not let an author approve their own | STRUCTURAL: a second human reviewer. A review account held by the sole maintainer would raise the number while approving nothing, so it is REFUSED — this is a supply-chain trust signal, and manufacturing one is the failure this repository exists to refuse |
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
