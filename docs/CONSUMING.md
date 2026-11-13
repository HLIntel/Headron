# Consuming this atlas from somewhere else

This repository is public so that any model, agent or machine can fetch a raw URL without a token.
That is the whole reason it holds no secret. Here is how to use it from another repository, a
knowledge vault, an agent runtime or a product of your own — and what not to do.

## Build your own product

The public repository is the reusable product surface: CLI, MCP server, contracts, verification
engine, adapters, schemas, examples and documentation. Under the MIT License you may fork, modify,
rebrand, embed, host, sublicense or sell software built from that surface, including commercial and
closed-source products. Keep the required license notice; no HLIntel account or service is required.

Keep product-specific configuration, credentials, customer data, deployment state and internal
hostnames in your own private operational boundary. That separation protects users and operators;
it does not limit the kinds of products you can build. Headron-Harness and other HLIntel-operated companions
are optional examples of products consuming the same public interfaces.

## Four ways in, cheapest first

| you want | fetch |
|---|---|
| the machine-readable entry point | `llms.txt` — generated, so it cannot name a document that does not exist |
| the routing table itself | `atlas.yaml` — routes, gates, task profiles, instruments, code-shape caps |
| one language's authority | `languages/<route>/tools.yaml`, validated against `tools/tools.schema.json` |
| the instructions an agent runtime loads | `AGENTS.md` is the contract; `CLAUDE.md` points to it. Other runtimes can start with `llms.txt` or their adapter in [MODEL.md](../MODEL.md) |

```bash
REPO=HLIntel/Headron
TAG=$(gh release view --repo "$REPO" --json tagName -q .tagName)   # the latest release, READ — never typed
curl -fsSL "https://raw.githubusercontent.com/$REPO/$TAG/atlas.yaml" -o atlas.yaml   # PIN A TAG, never main
curl -fsSL "https://raw.githubusercontent.com/$REPO/$TAG/llms.txt"
```

**Pin a tag.** `main` moves; a tag does not. Every release carries a one-line changelog entry in
`docs/VERSIONING.md`, and the contract version is asserted at a declared line in every version site, so the tag
you pinned tells you exactly which rules you got.

## If you want the artifact rather than the tree

Each release carries a deterministic tarball of the routing surface, its digest, and a **signed
in-toto provenance bundle**. Verify before trusting it — an artifact you did not verify is one
somebody else vouched for:

```bash
gh release download "$TAG" --repo "$REPO" --pattern 'atlas-*'
gh attestation verify "atlas-$TAG.tar.gz" --repo "$REPO"   # exit 0 or it failed
shasum -a 256 -c "atlas-$TAG.tar.gz.sha256"
```

The tarball is built with sorted entries, zeroed ownership and an epoch mtime, so the same commit
produces the same bytes. That is what makes the attestation worth having.

## Do not vendor the whole tree

Copying the repository into yours creates a second copy that ages, and **neither copy can tell you
it is the stale one** — the failure this atlas is built to prevent. Instead:

- **Route, do not import.** Fetch `atlas.yaml` and resolve a route; fetch the one pack you need.
- **Take the rule, not the paragraph.** The durable content is the mechanism and the measurement
  beside it. A copied paragraph loses the instrument that made it true.
- **If you must copy a manifest, copy its `provenance` too.** It states what has not been
  confirmed against a real toolchain, and that is the part a reader needs most.

## Running the harness against your own repository

`headron init`, run once inside the repository, checks this machine for the tools its checks call, lists the
checks a change to each of its languages must pass, writes the agent wiring (an `AGENTS.md` block, a
`CLAUDE.md` import of it, a `.mcp.json` server and a Codex `config.toml` server, each idempotent and leaving your own text
alone) and runs those checks once on the code as it is. `--no-wiring` skips agent configuration and hooks;
`--no-run` skips the initial checks. Use both to inspect the setup without wiring or running checks.

For a local repository without an origin, choose the comparison commit explicitly:
`headron verify --base HEAD` checks uncommitted changes against the current commit.
Use an earlier base to include committed work. Commit an initial baseline first in
a new repository. A missing or invalid base remains NOT RUN and names the remedy.
Fast incremental loop: `headron verify --changed` (and `--change <class>`) speeds edit feedback.

Verification executes the repository's declared tools. Those tools can write files
or use the network; inspect the commands and use your host's isolation when needed.
The read-only MCP interface refuses `verify` and process execution. It can discover
the gates; execute them through the CLI with the permissions you intend.

An installed command can use an explicit atlas root while working in another repository:

```bash
HEADRON_ROOT=/path/to/atlas headron gate src/main.go unit_tests
HEADRON_ROOT=/path/to/atlas headron route src/main.go --json
```

`gate` prints the one command a gate runs for that file, and nothing else — measured as the most
accurate answer a model can be handed, at a tenth of the tokens of the whole pack. Its `--json`
record is frozen in `tools/atlas-output.schema.json` with `route`, `plan` and `process`.

It has **one runtime dependency, and that is the whole closure** — held to the hash lock by the
invariant `dependency_count_is_the_closure` ([DEPENDENCIES.md](DEPENDENCIES.md)). `python scripts/atlas.py
doctor` says whether a machine can run each instrument and, for anything missing, **what stops
working because of it**.

## As a reusable workflow in your CI

[`atlas-reusable.yml`](../.github/workflows/atlas-reusable.yml) routes a pull request's changed
files against a **pinned** atlas and writes the required gates into the job summary. It does not
run them: it cannot know your toolchain, so running them stays your job.

```yaml
jobs:
  atlas:
    uses: HLIntel/Headron/.github/workflows/atlas-reusable.yml@<tag>
    with:
      atlas-ref: <tag>            # a tag or commit, never a branch
      change-class: <profile>     # a key of atlas.yaml/verification_policy/profiles
```

`task`, `process` and `paths` are optional. Leave `paths` empty to use the pull request's own diff.

### As a GitHub Action

[`action.yml`](../action.yml) ("Headron Agentic Code Verification") installs the CLI from the action's own
checkout and runs one `headron` command in your job. Unlike the reusable workflow, it runs the checks.
Pin it to a tag or commit, never a branch:

```yaml
steps:
  # after your checkout step
  - uses: HLIntel/Headron@<tag>
    id: headron
    with:
      command: verify                               # verify, check, plan or port
      mind-key: ${{ secrets.HEADRON_MIND_KEY }}     # optional; leave unset to skip the hosted plan
```

Inputs: `command`, `args`, `mind-key`, `mind-url` (default `https://headron.tech/api/mind`), `mind-files`
(one per line; empty reads the triggering event) and `risk-modifiers` (comma separated).

| output | meaning |
|---|---|
| `mind-status` | inactive when no key is set, otherwise active, invalid key, no active plan, or unavailable |
| `change-classes` | Change classes inferred for the changed files, comma separated |
| `required-gates` | Gates the hosted plan requires for those classes, comma separated |
| `policy-revision` | Revision of the policy the plan was read from |

`action.yml` is the source of truth for these names. The command runs with `HEADRON_ROOT` set to the
action's own checkout, so the atlas is the pinned tag's. Without `mind-key` the Mind step reports
`inactive` and passes. With a key it fails closed: an invalid key, no active plan, an unreachable service,
or changed files it cannot read fails the step. When `mind-files` is empty, check out with
`fetch-depth: 0` so the event's changed files can be read. The hosted plan adds gates; it never replaces
the command's own verdict.

### Evidence and adoption

| question | current evidence |
|---|---|
| Fewer production defects? | The checks can catch defects they cover before a change lands. A production defect reduction has not been measured. |
| Compliance? | Receipts record check results; they do not establish regulatory compliance or replace an auditor's judgment. |
| Developer time? | Routing can narrow an edit loop; setup, checks and review also cost time. Measure the whole workflow in your own project. |
| Existing CI? | The reusable workflow plans gates. Your pipeline must run the selected checks and enforce their results. |
| Audit and incident review? | Retain the receipt alongside the commit, CI logs and relevant approvals. Verify its contents and review every skipped or missing check. |

A receipt records a base commit, policy and input digests, check states and a verdict. Its digest detects
accidental changes, but anyone can recompute it; a trusted signature identifies a signer, not whether the
checks actually ran. It does not record the head commit, run time or CI job link. Retain those separately.
Reused and freshly executed passing checks look the same in a receipt; use `--fresh` where a new run is
required. A skipped check is distinct from a pass, even when the overall verdict is PASS.

For an external repository, `verify --receipt` currently requires an unchanged `atlas.yaml` with a
verification policy at the selected base and in the working tree. Without it, policy pinning fails closed;
installing the CLI or using the reusable workflow alone does not provide a passing consumer receipt.
The local Mind receipt view summarizes the latest local verification record, not a historical archive.

## As an installed command, an MCP server, or a Claude Code plugin

The package declares `headron`, `headron-mcp` and legacy `atlas`. All resolve the atlas by one rule
(`--atlas-root`, then `HEADRON_ROOT`, then `.atlas.yaml`); `headron --where` prints which won. A
`.atlas.yaml` `root:` must top its own git checkout, at its `ref:` if set; a vendored copy refuses. With
none, from contract 3.53.0, the CLI fetches the release tarball of **its own installed version**, checks
its `.sha256` and caches it under `$XDG_CACHE_HOME/headron/atlas-<version>`; a
mismatch or no network refuses, never another version. `HEADRON_NO_FETCH=1` turns that off:

<!-- BEGIN generated: install (python scripts/atlas.py index --write) -->
```bash
# install
uv tool install headron-software && headron doctor
# editable, to change Headron itself
git clone --depth 1 --branch v3.63.0 https://github.com/HLIntel/Headron ~/headron && uv tool install --editable ~/headron && headron doctor
```
<!-- END generated: install -->

The block is executed on every pull request by `python scripts/cli_test.py --install` in a clean home, and
a line elsewhere that installs Headron is refused.

```bash
headron --where
claude mcp add headron -e HEADRON_ROOT=/path/to/atlas -- headron-mcp   # read-only: every write flag is refused
```

The server offers the `headron {argv}` tool and seven typed tools for the questions an agent asks before
an edit: `port`, `route`, `gate`, `steps`, `failures`, `successes`, `proof`. Each returns
`structuredContent` with `exit`, the `record` or `text`, and the `resolved` path. `failures` and
`successes` refuse an unscoped read; scope it with `for` (a file) or `id`.

### Any MCP client

The server is one stdio process with no model, agent or vendor in it. Any runtime that can launch an MCP
server over stdio can use it with this entry, in the runtime's own config format:

```json
{
  "mcpServers": {
    "headron": {
      "command": "headron-mcp",
      "env": { "HEADRON_ROOT": "/path/to/atlas", "HEADRON_CLIENT_DIR": "/path/to/project" }
    }
  }
}
```

- `HEADRON_CLIENT_DIR` is the directory relative paths resolve against. Set it when the runtime may start the
  server outside the project; a missing directory makes the server exit 2 with the reason on stderr.
- Cursor: `headron init` writes a portable entry, see [its adapter](../models/cursor/README.md#how-it-loads).
- Tool schemas are plain JSON Schema for the arguments; every result carries its verdict in
  `structuredContent` and the same JSON as text, so a client that ignores `structuredContent` still reads it.
- The protocol revisions answered are the ones `atlas.yaml/external_versions` lists. A remote runtime that
  speaks only HTTP reaches this server through a client-side stdio bridge; the server itself does not listen
  on a network port.

### Hosted Mind API & MCP

`https://headron.tech/mcp` speaks MCP over Streamable HTTP. It runs no local toolchain and cannot inspect
your project; the local server above does that.

- **Public, no key:** its resources (the agent guide, llms.txt, and the documentation page) and a
  read_document tool that returns either one.
- **Mind key:** a plan_change tool, listed when hosted Mind is enabled, plans the gates for one or more
  declared change classes plus risk modifiers and returns the plan as structured content. It needs a paid
  Mind API key, sent as an `Authorization: Bearer ak_…` header or, where a client cannot set headers, as
  the tool's api_key argument. A refused call names the cause: invalid key (401), no active plan (402),
  or service unavailable.

```json
{
  "mcpServers": {
    "headron-mind": {
      "url": "https://headron.tech/mcp",
      "headers": {
        "Authorization": "Bearer ak_your_key_here"
      }
    }
  }
}
```

Omit `headers` to use only the public documentation tools. Keys are generated through your account at
[headron.tech/checkout.html](https://headron.tech/checkout.html); current prices are on the
[plans page](https://headron.tech/#plans). See the [Mind API reference](https://headron.tech/mind-api.html).

Or install it as a **Claude Code plugin** — opt-in, nothing loads until you install it:

```bash
claude plugin marketplace add HLIntel/Headron
claude plugin install headron@headron
```

The plugin adds, never subtracts: the read-only MCP route, the `headron` failure-ledger skill, and two
hooks. Before a shell command, `headron shell --hook` puts a string Headron refuses to you as a question,
never a denial; after an edit, `headron port --hook` returns that file's gates as context. Both stay
silent on anything they cannot read. `python scripts/atlas_test.py` runs each hook from the manifest and plants a drift in each.

## For a knowledge vault or a notes system

Store the **verdict and its measurement**, not the prose. A note that says "pin actions by digest"
is worth keeping; a note that restates a table from here will disagree with it within a release.
Link to a tag, record the version you read, and re-fetch rather than re-summarise — the same rule
this repository applies to its own documents.

## What this repository will never contain

No secret, credential, token, private path or internal hostname — not in a file, not in an
example, not in history. That is why it is safe to hand this whole tree to an unknown agent, and
it is the property every consumption route above depends on. See [SECURITY.md](../SECURITY.md).

## Optional HLIntel services

Headron Software is the core product of HLIntel (Headron Layer Intelligence):

- **Headron-Harness:** desktop workspace and local runtime.
- **Headron Web:** browser interface.
- **Headron Enterprise:** organizational offering across desktop and web.
- **Headron MCP:** integration connecting agents and developer tools.
- **HL.Verify:** shared verification capability.
  - _Rules & Gates:_ File-targeted proof obligations and pre-commit enforcers.
  - _Failure Ledger:_ Past agent failure catalog and regression seeds.
- **Mind API:** shared orchestration interface.

<a id="headron-harness-preview-limits"></a>

HLIntel's Headron-Harness desktop preview currently uses ad-hoc signing and manual updates. Of the Headron
software plans only hosted Mind is on sale; Headron-Harness and Team are proposed and cannot be bought
yet, and signed automatic distribution is not offered. These are availability
notes for HLIntel's companion service, not restrictions on the public software or on downstream
products. Optional host hints are advisory; required CI checks enforce merge policy when configured.
