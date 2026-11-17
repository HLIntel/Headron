# Contributing to Headron Software

Thanks for helping. Headron Software holds itself to the rules it hands agents, so a change lands the same way
whether a person or an agent wrote it. House words (receipt, ledger, pack, ratchet and the rest)
are defined once in the [glossary](docs/VERIFY.md#glossary).

## Three steps

1. **Ask where to go.** `headron port <file>` names the [route](docs/VERIFY.md#glossary), the [gates](docs/VERIFY.md#glossary) and the lessons for that file.
   Read [AGENTS.md](AGENTS.md) for the rules that fail the build; do not read the tree breadth-first.
2. **Prove the change.** `headron gate <file> <gate>` prints the one command that proves each gate;
   `headron verify` runs the whole done set. Judge by the exit code, never by the output.
3. **[Land](docs/VERIFY.md#glossary) it.** `python scripts/branchstate.py --land` opens the pull request; a bare push of a [topic branch](docs/VERIFY.md#glossary)
   is refused. A behaviour change bumps the contract per [docs/VERSIONING.md](docs/VERSIONING.md).

## What gets refused

- A count or a date typed into prose: generate it, or name the instrument that prints it.
- A hand edit to a generated file: change `atlas.yaml` and run `python scripts/atlas.py index --write`.
- A new rule with no [seeded defect](docs/VERIFY.md#glossary): every rule ships a case that proves it fires.

## Reporting

Bugs and ideas: open an issue with the form. Security reports: [SECURITY.md](SECURITY.md), never a
public issue.
