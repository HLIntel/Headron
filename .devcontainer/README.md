# Devcontainer

The container the repository itself needs is small: Python plus PyYAML runs
`scripts/atlas.py`, and `postCreateCommand` runs the contract on create, so a
codespace that boots green has proven the harness works there.

## What a codespace is actually for here

Not editing Markdown — that is faster locally. The use that earns the machine is
**confirming a language pack against the real toolchain**. Every `tools.yaml`
carries a `provenance.verify` list: the entries written from prior knowledge that
nobody has run. In a codespace you can install that one language and check them.

Add the language you are verifying as a devcontainer feature, rebuild, and confirm:

```jsonc
// .devcontainer/devcontainer.json -> "features"
"ghcr.io/devcontainers/features/rust:1": {},
"ghcr.io/devcontainers/features/go:1": {},
"ghcr.io/devcontainers/features/node:1": {}
```

```bash
python scripts/atlas.py learn rust      # the loop, wired to that pack's real tools
rustc --version && cargo clippy --version   # confirm, then drop the name from provenance.verify
```

**One language at a time.** Installing 29 toolchains produces a slow image and
proves nothing: a tool present in a container is not a tool the pack was verified
against. Remove the feature when the verification is done.

## Cost

A personal account includes a monthly core-hour allowance, and a stopped codespace
still bills storage until it is deleted. Stop it when you step away
(`gh codespace stop`) and delete it when the verification is finished
(`gh codespace delete`); it is a workspace, not a home.

## What it is for, and what it deliberately is not

**One language at a time.** This image carries Python and the harness dependency and nothing else,
because a container that installs 35 toolchains takes minutes to boot and proves nothing about any
of them. Add the one language as a devcontainer feature, confirm the pack against it, then remove
the feature — `packprobe.py --mode smoke` is what answers, and its verdict is a fact about THIS
machine rather than about the pack.

That is also why `tool_claims` exists: `declared` is what a manifest asserts, and every rung above
it — available, version-compatible, executed, passed — has to name the environment it was measured
in. A codespace is how a pack earns a rung above the first.
