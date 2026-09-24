# Language Tool Manifests

A manifest lives at `languages/<route>/tools.yaml` and answers **what to activate**, not what
exists. Atlas reads it to construct the smallest useful environment for one file and one task.

- **The shape:** [tools.schema.json](tools.schema.json) — the one declaration, machine-readable.
- **The authoring contract:** [languages/PACK-TOOLS-SPEC.md](../languages/PACK-TOOLS-SPEC.md) — the
  rules, and the required skeleton generated from that schema.

This file previously listed its own roster of fourteen capability groups. **The manifests never had
those fields**, so a pack author following this page wrote keys nothing read: a third declaration
that agreed with neither of the other two. The roster now lives in one place, and this page covers
only what that place does not.

## Selection rule

`task + artifact + boundary + risk` selects the tools. Do not activate a whole manifest by
default; `policy.default_tools` is what activates unasked, and `atlas.py check` caps it.

Native language tooling is authoritative. MCP servers, AI tools and IDE extensions augment it and
never replace it.

## Severity and verification

Findings are classified `blocker`, `error`, `warning`, `info` or `baseline`; the meanings and the
per-change required gates are declared in [atlas.yaml](../atlas.yaml) under `verification_policy`
and enforced from there. See [docs/VERIFY.md](../docs/VERIFY.md).

## Two instruments, two different claims

| instrument | answers |
|---|---|
| `python scripts/atlas.py check` | does every manifest conform to the schema? |
| `python scripts/packprobe.py` | which declared commands does PATH resolve on THIS machine? |

Neither proves a pack was exercised against its toolchain. That is what `provenance.verify` and a
codespace are for — see [.devcontainer/README.md](../.devcontainer/README.md).
