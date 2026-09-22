# Code Development Wiki

This is the repository-native wiki/navigation layer for Code-Development.

The wiki is intentionally complementary to the repository contract. Do not copy the same rule into multiple canonical locations unless the copy is a navigation aid.

## Core map

| Question | Page |
|---|---|
| Where does this file route? | [Code Routing](CODE-ROUTING.md) |
| How should branches/worktrees work? | [Branches and Worktrees](BRANCH-WORKTREES.md) |
| Should each language have its own branch? | [Language Lanes](LANGUAGE-LANES.md) |
| How should issues be tagged? | [Labels and Tags](LABELS-TAGS.md) |
| What controls the agent? | [MODEL.md](../MODEL.md) |
| What is the machine route? | [atlas.yaml](../atlas.yaml) |
| What are the language guides? | [languages/ATLAS.md](../languages/ATLAS.md) |
| What MCP should be active? | [MCP Language Matrix](../integrations/MCP-LANGUAGE-MATRIX.md) |
| How is verification enforced? | [VERIFY.md](../docs/VERIFY.md) |

## Wiki operating rules

1. Start from the artifact, task, or issue rather than from a favorite language or model.
2. Keep language-specific details in the corresponding `languages/<language>/README.md`.
3. Keep machine routing in `atlas.yaml`.
4. Keep control behavior in `MODEL.md`.
5. Use labels for work routing, repository topics for discovery, and Git tags for releases.
6. Use worktrees for concurrent mutable writers; do not use permanent language branches to simulate isolation.
7. Record new mechanisms in research/decisions before turning them into repository-wide defaults.

## Agent navigation pattern

```text
artifact / issue
   |
   +--> artifact extension or manifest
   |
   +--> language guide
   |
   +--> task type
   |
   +--> runtime adapter
   |
   +--> MCP profile
   |
   +--> verification
```

The detailed contract remains in the linked repository documents.
