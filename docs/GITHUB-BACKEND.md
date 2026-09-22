# GitHub Backend Control Plane

GitHub is the repository's durable control plane, not merely a code host.

## Use each surface for one job

| Surface | Job | Rule |
|---|---|---|
| Issues | goals, defects, research questions | one problem/decision per issue |
| Labels | routing metadata | `kind/` + `lang/` + `area/` + optional `risk/`/`runtime/` |
| Projects | portfolio/state view | track outcomes, not every tiny task |
| Pull requests | reviewable change | small diff + verification evidence |
| Actions | authoritative enforcement | local success is insufficient |
| CodeQL | source-security analysis | treat findings as code changes requiring verification |
| Dependency graph | dependency inventory | feed dependency review/Dependabot decisions |
| Dependabot | update automation | review lockfile/transitive impact |
| Secret scanning | exposure detection | push protection prevents supported leaks |
| Releases | versioned durable artifacts | tie release to verified commit |
| CODEOWNERS | ownership routing | security/build/core boundaries get explicit owners |
| Discussions/wiki | durable learning | promote repeated decisions into repo docs |

## Label grammar

Prefer composable labels over giant labels:

`kind/bug`, `kind/feature`, `kind/research`, `kind/tooling`

`lang/python`, `lang/rust`, `lang/go`, `lang/typescript`, etc.

`area/api`, `area/db`, `area/cache`, `area/agent`, `area/mcp`, `area/ci`, `area/security`, `area/perf`

`risk/security`, `risk/breakage`, `risk/migration`, `risk/compatibility`

`runtime/vscode`, `runtime/opencode`, `runtime/github-actions`, `runtime/cloud`

Do not create a label for every adjective. Labels should change routing or reporting.

## Goal routing

Every non-trivial issue should be classifiable as:

`goal → language → boundary → task profile → tools → verification → artifact`

The issue body should name the goal and acceptance test. The implementation should not invent a new goal halfway through the change.

## Backend truth rule

GitHub metadata is coordination state; source code, manifests, lockfiles, CI configuration, and tests remain technical truth. Never encode a technical invariant only in an issue label.

## Anti-noise rule

Use Projects for strategic work, Issues for actionable work, PRs for changes, Actions for enforcement, and docs for durable knowledge. Do not duplicate the same state in five surfaces.
