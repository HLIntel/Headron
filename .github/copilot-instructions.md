# Copilot instructions

**The rules are generated, not written here.** Read [AGENTS.md](../AGENTS.md) — it is produced
from `atlas.yaml` and the tree by `python scripts/atlas.py index --write`, and `atlas.py check`
fails when it drifts. This file exists because Copilot reads this path, and it stays a pointer so
there is no fourth copy of the same body.

## The three things worth repeating here

1. **Route before you read.** `python scripts/atlas.py route <path> --json` gives the language
   pack, its operating card, its tool manifest, the label, the branch lane and the gates. Reading
   this repository breadth-first is the failure it exists to prevent.
2. **Never type a count, a date or a tool name into prose.** Counts are generated, claims are
   stamped with a contract version, and a tool's name lives in `languages/<route>/tools.yaml`
   where an instrument can check it. Each of those is enforced, and each has a planted defect in
   `scripts/atlas_test.py` proving the check still bites.
3. **Verify on the exit code.** `python scripts/atlas.py check` is the verdict; a suggestion that
   looks right and fails the contract is a failing change. Suggested code for a pull request must
   also satisfy the gate for its change class — the classes are generated into
   [docs/VERIFY.md](../docs/VERIFY.md).

**Copilot code review is a second opinion, never the gate.** The required checks are `Contract`,
`Dependency Review` and the two CodeQL analyses, declared in
[config/github-controls.json](../config/github-controls.json) and compared by
`python scripts/ghaudit.py`.
