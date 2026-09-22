# Agent Layer

Agents are a capability class inside the model layer.

Every agent should have explicit tools, permissions, workspace, resource budget, termination condition, verification loop, and recovery path.

Agent classes:
`planner`, `researcher`, `coder`, `tester`, `security-reviewer`, `benchmark-runner`, `release-agent`

Use isolated contexts for broad exploration and compact evidence-backed handoffs.

Agents are adapted by each model runtime; the repository does not assume one universal agent UX.