# Agent Layer

Agents are scoped capabilities inside the model system.

Every agent needs:
- purpose
- tools
- permissions
- workspace
- budget
- termination condition
- verification
- recovery path

## Agent classes
`scout`, `planner`, `researcher`, `coder`, `tester`, `security-reviewer`, `benchmarker`, `release-agent`

## Minimal handoff
```json
{"status":"verified","changed_files":[],"tests":[],"risks":[],"next_action":null}
```

Use isolated contexts/worktrees for broad exploration. Parent agents receive compact evidence-backed findings.