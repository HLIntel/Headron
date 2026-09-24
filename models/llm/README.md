# Generic provider adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to a generic provider — how the atlas is loaded
here, and the mistake this runtime makes.

## How it loads

Nothing loads automatically, so hand it the two smallest things that answer: `llms.txt` and the
output of `atlas.py route <path> --json`. Both are generated, so neither can describe a document
that does not exist.

## Configuration

[.env.example](.env.example) names the variables and nothing else. **No key, token or endpoint
belongs in this repository** — see [SECURITY.md](../../SECURITY.md), which is the rule the public
visibility of this tree depends on.

## What it is routed for

`research`, per `atlas.yaml/model_routes`: primary sources, an isolated context, a prototype, a
measurement.

## The mistake it makes

**Answering from training rather than the tree.** A tool name recalled from training is a
hypothesis; the pack's `tools.yaml` is the declaration, and `provenance.verify` lists exactly what
that pack has not confirmed. Prefer the file to the memory, every time.
