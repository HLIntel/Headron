# Anti-Blob Engineering

A blob is a module, artifact, generated file, or data object that grows beyond useful reasoning and control boundaries.

## Code blobs

Advisory review triggers:
- source file approaching ~600 lines
- source file above ~1,000 lines
- function/method approaching ~80 lines
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

The Atlas harness warns on tracked code files over 1,000 lines and selected binary/blob extensions over 2 MB.
