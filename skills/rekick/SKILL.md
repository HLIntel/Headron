---
name: rekick
description: Restart the checks a forge outage stranded on an open pull request.
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---

Run, from the lane's worktree:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/branchstate.py" --rekick
```

It retries only a job no runner ever acquired; when any check ran and failed it refuses, because that is
the commit — fix it on the lane. The exit code is the verdict.
