# Entry and landing plan

Goal: an agent enters through a short, generated front, finds the gates for its change, and
reports a verdict without weakening verification. `llms.txt` is the entry for a bare model;
`AGENTS.md` and `.agent/bootstrap.json` are generated from the contract. The context policy
measures the entry path, and the contract check enforces its budget.

For a change, use the route and gates named by the entry. The full done set is declared in
`atlas.yaml/verification_policy` and run by `python scripts/verify.py`. The landing command
`python scripts/branchstate.py --land` prepares a clean checkout, runs its gates, pushes,
opens a pull request and arms auto-merge. Required checks must still pass before a merge.

## Open design work

- A cheaper local path for documentation-only changes needs an instrument that proves the
  selected scope is sufficient. Full verification remains required for landing.
- A landing option that opens a pull request without arming auto-merge needs an explicit
  contract and a test of its behavior. The current landing command arms auto-merge.

The plugin manifests and read-only MCP server have their own contracts; changes to them need
their own routes and verification. This plan does not establish that a hosted verifier is
healthy or that every client can connect.
