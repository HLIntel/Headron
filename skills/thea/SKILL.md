---
name: thea
description: Record a break, mistake, error, bug, drift or bad result in Thea Software's failure ledger the moment it is seen, so the build learns to prevent it. Use proactively whenever the AI itself gets something wrong, and when a person types /thea <what went wrong>.
user-invocable: true
---

# thea — feed Thea's failure ledger

Portable across agents: a skill folder any skill-aware runtime can load, and plain instructions any
other model can follow. The ledger is `atlas.yaml/agent_failure_modes` in Thea Software
(github.com/HeartlandIntel/thea-software); work in a branch, never on main. One entry per SHAPE.

## When to run it — people, agents and models alike

Run it the moment any of these happens, in the same turn, before moving on:
- a gate, test, build or check fails, or passes only after a retry;
- an answer, command, path or number turns out wrong, invented or stale;
- a guard fires on correct work, or stays silent on broken work;
- a document, count, name or version disagrees with the tree (drift);
- a result looks better than expected and nobody has attacked it yet;
- a person says "that's wrong", or you catch yourself undoing your own last step.

## Steps

1. **Name the shape, not the instance:** a snake_case id starting `a_` or `an_` that names the
   mechanism, never the file it happened in.
2. **Dedupe first.** Read every ledger id, `shape` and `tell`. Same mechanism: bump `sightings`,
   sharpen `tell`, go to 5. A second sighting means a guard is now owed.
3. **New shape, six lines or fewer:** `shape` (the mechanism), `looks_like` (how it reads from outside,
   usually as success), `tell` (the one observable that separates it from its neighbours),
   `sightings: 1`, `prevented_by`, and EITHER `enforced_by: [module.function]` OR `unenforceable` plus
   `closed_by` plus `intake: <contract version>`.
4. **Guard it now when you can:** a check that fails on the shape, a planted case in
   `scripts/atlas_test.py` with its expected count raised, and a clean sweep of the whole tree.
   Intake must graduate within two minor versions; the build refuses it after that.
5. **Fix the cause** when the break is in work this session produced. Never caption a bad result.
6. **Verify:** stage, `python scripts/atlas.py index --write`, stage, then `python scripts/atlas.py check`
   and `python scripts/atlas_test.py`, judged on the exit code; land with `python scripts/branchstate.py --land`.
7. **Report one line:** `id · new | sighting N · guarded | intake`.

A chat that cannot edit files answers with the entry itself, ready to paste. Stamp the contract
version, never a calendar date. Sweep with a scanner or `command grep`: an agent shell's grep may
skip ignored files.
