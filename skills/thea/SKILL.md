---
name: thea
description: Log a break, mistake, error, bug, drift or bad result to Thea's failure ledger so the build prevents it. Use when the AI gets something wrong, or on /thea.
user-invocable: true
---

# thea — feed Thea's failure ledger

Portable across agents: a skill folder any skill-aware runtime can load, and plain instructions any
other model can follow. The ledger is `atlas.yaml/agent_failure_modes` in Thea Software
(github.com/HeartlandIntel/thea-software); work in a branch, never on main. One entry per SHAPE.

## Before the change: read the lesson for it

`thea failures --for <file-or-task>` returns the few recorded shapes that share words with what you are
about to change, each with its tell and the move that replaces it (`do:`). Make that move; `thea successes
--for <task>` lists moves directly, each with when it applies and how to verify it was made.

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
2. **Draft it:** `python scripts/atlas.py failures <id> --draft '<what happened>'` prints a recorded
   id's bump, or the nearest shapes and an entry line. Same mechanism: bump `sightings`, sharpen
   `tell`, go to 5. A second sighting means a guard is now owed.
3. **New shape, six lines or fewer:** `shape` (the mechanism), `looks_like` (how it reads from outside,
   usually as success), `tell` (the one observable that separates it from its neighbours),
   `sightings: 1`, `prevented_by`, and EITHER `enforced_by: [module.function]` OR `unenforceable` plus
   `closed_by` plus `intake: <contract version>`. Fill the drafted line's blank fields and run it:
   it generates every value and reads the entry back — never hand-quote YAML.
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

## Success

One ledger entry exists, on a branch, naming a SHAPE:

- The entry is in `atlas.yaml/agent_failure_modes` on a **branch — never main** — and the branch or
  PR is named in the output. thea is the PUBLIC repo: no secret and no private path, ever.
- It names the SHAPE, not the instance, and states **the one observable that separates it** from
  correct behaviour. An entry a guard cannot be written against is prose.
- It carries the instance COUNT. A second sighting is a rule; a third means the evidence was there
  twice and nothing was built.
- A run that describes the failure in chat and lands no entry has failed, however good the
  description was.
