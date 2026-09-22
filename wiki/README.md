# Code Development Wiki

This is the repository-native wiki/navigation layer for Code-Development.

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

Use the GitHub platform for security/automation state, repository files for policy, and the wiki for efficient navigation and explanation.
