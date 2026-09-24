# OpenAI / Codex adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to Codex — how the atlas is loaded
here, and the mistake this runtime makes.

## How it loads

`AGENTS.md` at the repository root is the convention this runtime reads, and it is **generated**
from the same body as `CLAUDE.md` — one declaration, two files, no drift.

## Use in this order

```bash
python scripts/atlas.py route <path> --json
python scripts/atlas.py check                    # the exit code is the verdict
```

## What it is routed for

`deterministic_repo_edit` and `architecture`, per `atlas.yaml/model_routes`. It is strong at a
narrow, stated change across known files.

## The mistake it makes

**Answering from the diff it can see rather than the route.** A change that touches two languages
has two manifests and two gates; the router says which. Ask before editing, not after.

Official: https://platform.openai.com/docs
