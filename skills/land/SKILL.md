---
name: land
description: Land this lane — rebase, run the suite, push, open the pull request and arm auto-merge, as one step.
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---

Run, from the lane's own worktree:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/branchstate.py" --land
```

The exit code is the verdict, never a step that printed ok. On a non-zero exit, read what it refused,
fix the cause on this lane and land again; never push the lane by hand. A lane that is already in the
default branch reports FINISHED before any suite runs: run `/thea:sync` from the default branch next.
