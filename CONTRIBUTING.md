# Contributing to Thea Software

Thanks for helping. Thea holds itself to the rules it hands agents, so a change lands the same way
whether a person or an agent wrote it.

## Three steps

1. **Ask where to go.** `thea port <file>` names the route, the gates and the lessons for that file.
   Read [AGENTS.md](AGENTS.md) for the rules that fail the build; do not read the tree breadth-first.
2. **Prove the change.** `thea gate <file> <gate>` prints the one command that proves each gate;
   `thea verify` runs the whole done set. Judge by the exit code, never by the output.
3. **Land it.** `python scripts/branchstate.py --land` opens the pull request; a bare push of a lane
   is refused. A behaviour change bumps the contract per [docs/VERSIONING.md](docs/VERSIONING.md).

## What gets refused

- A count or a date typed into prose: generate it, or name the instrument that prints it.
- A hand edit to a generated file: change `atlas.yaml` and run `python scripts/atlas.py index --write`.
- A new rule with no planted defect: every rule ships a case that proves it fires.

## Reporting

Bugs and ideas: open an issue with the form. Security reports: [SECURITY.md](SECURITY.md), never a
public issue.
