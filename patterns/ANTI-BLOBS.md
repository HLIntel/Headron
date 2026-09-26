# Anti-Blob Engineering

A blob is a module, artifact, generated file, or data object that grows beyond useful reasoning and control boundaries.

## Code blobs

Advisory review triggers:
- a source file approaching the file cap (`atlascore.MAX_CODE_LINES`, enforced)
- a function approaching the function cap `astshape.py` enforces and prints each run
- unrelated domains in one module
- high side-effect density
- giant mixed-responsibility routers
- generated code mixed with hand-maintained code

Split by ownership, domain, lifecycle, or failure boundary.

## Artifact blobs

Avoid committing build outputs, dependency caches, generated binaries, model weights, credentials, database dumps, temporary logs, or large archives that do not serve source history.

Use release artifacts, package registries, object storage, Git LFS, or reproducible generation when an artifact genuinely belongs outside source control.

## Payload blobs

Every large external payload should have a schema, size limit, streaming/chunking policy, retention, cleanup path, and source of truth.

## AI rule

Never ask an agent to rewrite a large file before identifying its responsibilities and dependency graph. Large-context rewrites increase accidental semantic mutation.

The Atlas harness fails on tracked code files over `atlascore.MAX_CODE_LINES` and on selected binary/blob extensions over `atlascore.MAX_BLOB_BYTES`.

## What enforces this now

- **`scripts/astshape.py`** refuses two functions with the same canonical AST — names, literals and
  docstrings erased — because a generator repeats a SHAPE far more often than a string. It caught
  two invariants written separately that compiled identically; they are now one helper.
- **The caps are a ratchet that only falls**, and they have: 278 → 262 → 259 → 239 → 232 → 221 →
  210 → 202, each step a function the gate refused and a split that earned it.
- **The install footprint is bounded too** — `context_policy/install_footprint`, in bytes, with a
  rise required to name what earned it. Moving this repository's own maintenance out of the wheel
  took a consumer's install from 212 KiB to 160 KiB. *(measured at v2.25.0)*
