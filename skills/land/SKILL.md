---
name: land
description: Land this topic branch — rebase, run the suite, push, open the pull request and arm auto-merge, as one step.
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---

Run, from the branch's own worktree:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/branchstate.py" --land
```

The exit code is the verdict, never a step that printed ok. On a non-zero exit, read what it refused,
fix the cause on this topic branch and land again; never push the topic branch by hand. A topic branch that is already in the
default branch reports FINISHED before any suite runs: run `/headron:sync` from the default branch next.
