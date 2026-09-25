# Code Development Wiki

This is the repository-native wiki/navigation layer for thea.

The wiki complements the repository contract. It should route to canonical files rather than silently replace them.

## Core map

| Question | Page |
|---|---|
| Where does this file route? | [Code Routing](CODE-ROUTING.md) |
| What tools should be composed? | [Tool Orchestration](TOOL-ORCHESTRATION.md) |
| How should production concerns vary by language? | [Language Operations](LANGUAGE-OPERATIONS.md) |
| How should branches/worktrees work? | [Branches and Worktrees](BRANCH-WORKTREES.md) |
| Should each language have its own branch? | [Language Lanes](LANGUAGE-LANES.md) |
| How should issues be tagged? | [Labels and Tags](LABELS-TAGS.md) |
| What GitHub security/AI controls matter? | [GitHub Finalization](../docs/GITHUB-FINALIZATION.md) |
| What can this repository PROVE about itself? | [Certification, per check](../docs/CERTIFICATION.md) |
| Can this machine run the instruments? | `python scripts/atlas.py doctor` |
| Do the live GitHub controls match the declaration? | `python scripts/ghaudit.py` |
| Which declared toolchains actually run here? | `python scripts/packprobe.py --mode smoke` |
| What does a quantum change have to declare? | [Quantum](../languages/quantum/README.md) |
| Which languages were reviewed and refused? | [Language Atlas](../languages/ATLAS.md) |
| What controls the agent? | [MODEL.md](../MODEL.md) |
| What is the machine route? | [atlas.yaml](../atlas.yaml) |
| What are the language guides? | [languages/ATLAS.md](../languages/ATLAS.md) |
| What MCP should be active? | [MCP Language Matrix](../integrations/MCP-LANGUAGE-MATRIX.md) |
| How is verification enforced? | [VERIFY.md](../docs/VERIFY.md) |

## Navigation rule

```text
artifact / issue
   |
   +--> code route
   |
   +--> language guide
   |
   +--> task route
   |
   +--> native tools
   |
   +--> scoped MCP / GitHub capability
   |
   +--> independent verifier
   |
   +--> CI
```

## Where each kind of truth lives

| kind | home | why there |
|---|---|---|
| policy and contracts | repository files, in Git | reviewed like code, and `atlas.py check` fails when a document drifts from `atlas.yaml` |
| platform state | GitHub itself, declared in [config/github-controls.json](../config/github-controls.json) | compared by `ghaudit.py`; prose cannot be compared by a machine, so it rots quietly |
| navigation | this wiki, in-tree | the GitHub-hosted wiki is disabled on purpose — a second, unversioned wiki is a duplicate surface where one copy goes stale and no reader can tell which is live |
| counts and rosters | generated blocks and `llms.txt` | a number typed into prose is stale the moment the tree moves |

**This page routes; it never restates.** If a row here disagrees with the file it points at, the
file wins and the row is the defect.
