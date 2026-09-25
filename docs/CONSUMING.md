# Consuming this atlas from somewhere else

This repository is public so that any model, agent or machine can fetch a raw URL without a token.
That is the whole reason it holds no secret. Here is how to use it from another repository, a
knowledge vault, or an agent runtime — and what not to do.

## Four ways in, cheapest first

| you want | fetch |
|---|---|
| the machine-readable entry point | `llms.txt` — generated, so it cannot name a document that does not exist |
| the routing table itself | `atlas.yaml` — routes, gates, task profiles, instruments, code-shape caps |
| one language's authority | `languages/<route>/tools.yaml`, validated against `tools/tools.schema.json` |
| the instructions an agent runtime loads | `CLAUDE.md` or `AGENTS.md` — the same body in two conventions |

```bash
REPO=HeartlandIntel/thea-software
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

The harness resolves its root in three ways, so it works outside a checkout of this repository:

```bash
THEA_ROOT=/path/to/atlas python /path/to/scripts/atlas.py gate src/main.go unit_tests
THEA_ROOT=/path/to/atlas python /path/to/scripts/atlas.py route src/main.go --json
```

`gate` prints the one command a gate runs for that file, and nothing else — measured as the most
accurate answer a model can be handed, at a tenth of the tokens of the whole pack. Its `--json`
record is frozen in `tools/atlas-output.schema.json` with `route`, `plan` and `process`.

It has **one runtime dependency, and that is the whole closure** — held to the hash lock by the
invariant `dependency_count_is_the_closure` ([DEPENDENCIES.md](DEPENDENCIES.md)). `python scripts/atlas.py
doctor` says whether a machine can run each instrument and, for anything missing, **what stops
working because of it**.

## For a knowledge vault or a notes system

Store the **verdict and its measurement**, not the prose. A note that says "pin actions by digest"
is worth keeping; a note that restates a table from here will disagree with it within a release.
Link to a tag, record the version you read, and re-fetch rather than re-summarise — the same rule
this repository applies to its own documents.

## What this repository will never contain

No secret, credential, token, private path or internal hostname — not in a file, not in an
example, not in history. That is why it is safe to hand this whole tree to an unknown agent, and
it is the property every consumption route above depends on. See [SECURITY.md](../SECURITY.md).
