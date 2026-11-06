# Aider adapter

**Adapter, not a second contract.** The rules are generated into [AGENTS.md](../../AGENTS.md), and the
roster of runtimes into [MODEL.md](../../MODEL.md) from `atlas.yaml`. This page carries only what is
specific to Aider: how the atlas is loaded here.

## How it loads

Aider loads only the files it is told to. The tracked [`.aider.conf.yml`](../../.aider.conf.yml) gives it
`AGENTS.md` as a read-only file. In your own repository, add the same two lines yourself; `headron init`
does not write them:

```yaml
read: AGENTS.md
git-commit-verify: true
```

Vendor reference: [Aider options](https://aider.chat/docs/config/options.html).

## Use its strength

Aider turns each change into a commit, so a bad step is one revert away. Run the route before asking for
the change, and the verdict after it:

```bash
headron port <file> --frame agent --json
headron verify
```

## Native tools stay

Aider keeps its own commands and settings in `.aider.conf.yml`, and it may change them without asking
Headron. Headron is added to this layer, never swapped in for it: run `headron` from Aider's `/run`
command or your own shell, and git runs the pre-commit hook. An install writes only the git hook and
never edits this runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by
`nativetools.native_agent_tool_errors`).

## The mistake it makes

**Commits that skip the hook.** Aider's defaults are `auto-commits: true` and `git-commit-verify: false`,
which means it commits with `--no-verify` and the pre-commit hook never runs. Set
`git-commit-verify: true`, or the only refusal left is the one in CI.
