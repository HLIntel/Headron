# Security Policy

**Repository contract: v2.24.0** · controls declared in
[config/github-controls.json](config/github-controls.json) · platform notes in
[docs/GITHUB-FINALIZATION.md](docs/GITHUB-FINALIZATION.md)

## Reporting a vulnerability

Do not disclose an unpatched vulnerability in a public issue, discussion, pull request or commit.

Use **Security → Report a vulnerability** on this repository — https://github.com/HeartlandTechnology/Code-Development/security/advisories/new —  Private vulnerability reporting is
enabled; `python scripts/ghaudit.py` is the instrument that says so, and it exits non-zero if that
ever stops being true. Include enough reproduction detail to validate the issue without publishing
secret material. You get a private advisory thread, unlisted until a fix ships.

## Supported versions

| version | supported |
|---|---|
| the current contract on `main` | yes — fixes land here |
| the latest tagged release | yes — re-tagged from `main` |
| any earlier tag | no; the contract is a single moving declaration, and an older tag is a snapshot |

A consumer pins a tag on purpose (see [docs/CONSUMING.md](docs/CONSUMING.md)). If a finding affects
a pinned tag, say which — the fix ships on `main` and a new tag follows it.

## The property this repository is built on

This is the only public repository in its organization, and it is public so that any model or agent
can fetch a raw URL without a token. That single decision sets the rule, and the rule has no
exceptions:

> **No secret, credential, token, private-project path or internal hostname enters this
> repository.** Not in a file, not in an example, not in a commit message, not in history.

Operational systems, their state and their keys live in private repositories. What lives here is
the method. A reader should be able to hand this entire tree to an unknown agent without reviewing
it first — that is the test, and it is why the rule is absolute rather than risk-weighted.

## Platform controls — declared as data, compared by an instrument

**This section used to be a table of states with a measurement date beside it.** That is honest on
the day it is written and unfalsifiable afterwards: three lines of an earlier audit had gone stale
and read as current, and nothing could tell. State in prose cannot be compared by a machine, so it
rots quietly.

So the controls are declared in [config/github-controls.json](config/github-controls.json) — in
Git, reviewed like code — and compared to the live API by one command:

```bash
python scripts/ghaudit.py          # every row: declared, measured, verdict; exit 1 on a difference
python scripts/ghaudit.py --json   # the same comparison as a record
```

It covers visibility, licence, topics, secret scanning and push protection, Dependabot security
updates, private vulnerability reporting, the `main-protection` ruleset and its required status
checks. It **refuses rather than reports** when it cannot reach the API, because a green line from
an audit that never called anything is the failure this repository exists to prevent. Each row that
cannot be satisfied carries the measured cause in the declaration file, so a control the platform
refuses is visible as BLOCKED rather than invisible as a gap.

**Three layers, kept separate, because a control can exist in the first two and stop nothing:**

| layer | where it lives | how it is verified |
|---|---|---|
| declared | this repository, in Git | `atlas.py check` · `config/github-controls.json` |
| configured | GitHub settings and rulesets | `ghaudit.py` |
| enforced | a merge is refused without it | a pull request that fails a required check cannot merge |

A control in the first two columns and absent from the third reads as covered and stops nothing.
Where a ruleset has a bypass actor, `ghaudit.py` prints it: a rule with a bypass is enforced for
everyone except that actor, and a reader has to be told which.

## Public, and not writable — what an outsider can and cannot do

The repository is public so that any model or agent can fetch a raw URL. **Public is not the same
as writable,** and the distinction is enforced rather than assumed:

| an outsider can | an outsider cannot |
|---|---|
| read and clone everything, at any commit or tag | push to any branch — write access is granted to nobody |
| fork, and open a pull request from the fork | merge anything: `main` requires a pull request and four passing checks |
| read every workflow and every declared control | run a privileged workflow — `pull_request_target` fails the contract, and fork workflows need approval |
| report a vulnerability privately | reach a secret: none is in the tree, and both environments hold zero secrets and zero variables |
| propose a change to any rule | weaken a rule: the ruleset has **no bypass actor**, so it applies to the owner too |

**The controls are declared as data** in [config/github-controls.json](config/github-controls.json)
and compared to the live platform by `python scripts/ghaudit.py`, which refuses rather than
reporting when it cannot reach the API. A control that exists in Git and not in the platform — or
in the platform and not in Git — is a DIFF row, not a matter of opinion.

**What is still trusted:** the repository owner, GitHub itself, and the pinned actions. Every
action is pinned to a commit SHA, the dependency install is hash-pinned with `--require-hashes`,
and Dependency Review refuses a copyleft licence before it can change what the tree may be used
for.

**What is published with it:** every release carries a deterministic tarball of the routing
surface, its SHA-256 digest, and a signed in-toto provenance bundle. Verify before you trust it —
`gh attestation verify atlas-<version>.tar.gz --repo HeartlandTechnology/Code-Development` exits 0 or it
does not, and the published digest must equal the one you compute. An artifact you did not verify
is an artifact somebody else vouched for.

## Agent execution — what is enforced here, and what is NOT a boundary

This repository ships controls that bound an autonomous agent, declared in
`atlas.yaml/agent_policy` and decided by named functions the contract refuses to leave unwired. A
task runs under a contract validated against
[tools/agent-task.schema.json](tools/agent-task.schema.json):

| control | refuses |
|---|---|
| `narrow_tools` | a command outside the contract's allowance, or matching a declared denial whatever the contract allows — privilege escalation, piped remote code, history rewriting, credential reads, recursive deletes, audit tampering |
| `sandbox` | a read or write outside the declared paths, escaping the root by traversal or symlink, or touching the policy, the audit stream or any generated file |
| `budget` | the call that would cross a declared ceiling, checked BEFORE it runs — a budget compared afterwards is a report |
| `approval` | a high-impact action whose token is absent, expired, or bound to a different contract, base commit, action or diff |
| `audit` | nothing at write time; it records a hash chain, and a removed or edited event is named by sequence number |

> **The runner is not a security boundary, and saying so is not a disclaimer.** It refuses what it
> is *asked* about. An agent that never calls the policy is bounded only by the host, which is why
> `agent_policy/sandbox_requirements` marks every row with who observes it and why `agentrun.py`
> prints the host-observed rows as UNOBSERVED rather than as satisfied. Four of six rows — home
> directory, network, process identity and resource limits — are the host's job. Run an
> autonomous agent in a container or microVM with a read-only mount outside the worktree, no home
> directory, no ambient cloud or registry credentials, default-deny network and a non-root user.

**A retrieved instruction is an injection surface.** `atlas.yaml/knowledge_layers` declares that
the retrieved layer holds facts and never the rules for how to answer. Content reached through a
file, a fetch or a tool result is *data*: it does not grant permission, and an instruction found
inside it is a finding to report, not a command to run.

## Integrity of the tree itself

Two failure classes are guarded because both happened here and neither announced itself:

- **A duplicate key in a declared mapping** would silently keep the last value — a route, an
  instrument or a manifest role answering with something nobody chose. Every YAML read goes through
  a loader that refuses duplicates.
- **A corrupted source file** would leave every document check passing. Every tracked source file
  must parse, checked before anything else runs.

Neither is a rule asking for care; both make the fault unrepresentable. See
[docs/ENGINEERING-CONCEPTS.md](docs/ENGINEERING-CONCEPTS.md).

## Scope

Security-sensitive areas:

- AI agent and tool execution, and the permissions they run under
- the task-contract controls above, and any path by which one can be widened
- prompt injection through retrieved or tool-returned content
- MCP and connector boundaries
- secrets and authentication
- GitHub Actions workflows and their permission floor
- external endpoints and webhooks
- database and cache access
- native, FFI and ABI boundaries
- dependency and supply-chain changes
- generated or downloaded executable artifacts

## Repository expectations

Security fixes use a short-lived `security/<topic>` branch or an isolated worktree, add regression
coverage where practical, and preserve rollback and auditability for high-impact changes.

**Never commit a real credential.** If one may have reached Git history or any external system,
**rotate it at the provider** — removing it from the working tree does not revoke it, and a local
cache miss is not revocation. Verify the rotation at the provider, never by a tool's local state.
