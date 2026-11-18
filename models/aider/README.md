# Aider adapter

Rules: [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Aider loads only the files it is told to. The tracked [`.aider.conf.yml`](../../.aider.conf.yml) gives it
`AGENTS.md` as a read-only file. In your own repository, add the same two lines yourself; `headron init`
does not write them:

```yaml
read: AGENTS.md
git-commit-verify: true
```

Vendor reference: [Aider options](https://aider.chat/docs/config/options.html).

## Dynamic connectivity & unbreakable discovery

Aider turns each change into a commit, so a bad step is one revert away. To ensure unbreakable connectivity:
- **Dual-path invocation:** Run `headron port <file> --frame agent --json` (or fallback `python scripts/atlas.py port <file> --frame agent --json`).
- **Structured output:** Depend on `--json` records (`tools/atlas-output.schema.json`), never unpiped chat formatting.
- **Fail-safe verification:** Run verification and inspect the process exit code:
  ```bash
  python scripts/atlas.py check && python scripts/verify.py
  ```

## Native tools stay

Aider keeps its own commands and settings in `.aider.conf.yml`, and it may change them without asking
Headron. Headron is added to this layer, never swapped in for it: run `headron` / `python scripts/atlas.py` from Aider's `/run`
command or your own shell, and git runs the pre-commit hook. An install writes only the git hook and
never edits this runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by
`nativetools.native_agent_tool_errors`).

## The mistake it makes

**Commits that skip the hook.** Aider's defaults are `auto-commits: true` and `git-commit-verify: false`,
which means it commits with `--no-verify` and the pre-commit hook never runs. Set
`git-commit-verify: true`, or the only refusal left is the one in CI.
