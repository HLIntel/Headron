---
name: sync
description: Pull the default branch, arm stranded pull requests and remove finished lane worktrees.
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---

Run, from the default branch's checkout:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/branchstate.py" --sync
```

It removes a lane worktree only when its work is in the default branch, no process stands in it, it
holds no uncommitted or untracked file and it sat idle past the bound. Report each tree it KEPT with the
reason it printed; never remove a kept tree by force.
