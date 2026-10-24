# Entry and landing plan: any agent, short front, same verdict

Goal: any agent (Claude, Codex, Gemini, or another) enters this repository, learns the three
commands, and gets one verdict with minimal context. Verification strength stays where it is.
What changes is the ceremony at the front of the repo and at the end of a task.

## What is measured now

- `python3 scripts/atlas.py check`: exit 0 on this branch. Wall time measured once, on this
  worktree, in the PR body.
- Entry: `CLAUDE.md` points at `AGENTS.md`. `AGENTS.md` is generated from `atlas.yaml` and
  carries the rule list and the recurring-mistakes list. The `agent` entry-path budget in
  `atlas.yaml/context_policy` measures the WORST single alternative (`measure: worst_alternative`)
  plus `.agent/bootstrap.json`. That worst alternative is `llms.txt`, not `AGENTS.md`: the
  instrument reads `AGENTS.md` as smaller and does not count it toward the number. Cutting
  `AGENTS.md` therefore moves no measured entry cost. A cut that does move it has to land in
  `llms.txt` or `.agent/bootstrap.json`, and stay inside the slack band.
- Landing: `python scripts/branchstate.py --land` pulls, rebases, runs the gates in a clean
  checkout of HEAD, pushes, opens the pull request, and arms auto-merge. The clean-checkout cost
  is unmeasured.
- Push guard: `.githooks/pre-push` refuses a bare push of a lane. Only the landing sets the
  bypass variable.

## Friction, in order of cost

1. **Front.** The generated `AGENTS.md` front is long before the first useful command. A reader
   needs the commands first and the rules second.
2. **Every change pays the full set.** The landing runs the clean-checkout gates for every
   change, including docs-only changes. No changed-path scope exists for local runs.
3. **Auto-merge on every land.** A land that must stay open needs a manual disarm afterward.
4. **Plugin surface overlaps the MCP lane.** `.claude-plugin/`, `server.json` and the MCP server
   belong to the `claude/thea-mcp-marketplace` lane. This lane does not edit them.

## Change list

| # | Change | Where | Status |
|---|---|---|---|
| 1 | This plan, linked from the index | `docs/ENTRY-PLAN.md`, `docs/INDEX.md` | this branch |
| 2 | Shorten the entry that sets the budget: `llms.txt` front, not `AGENTS.md` (see What is measured) | `llms.txt`, `.agent/bootstrap.json`, budget in `atlas.yaml/context_policy` | next; a cut below the slack band fails `check`, so the band is the proof |
| 3 | Docs-only changes run the cheap gates locally; the full done set stays at landing and in CI | `atlas.yaml/verification_policy` | proposal; needs an instrument that proves the scope is right |
| 4 | A landing flag that opens the pull request without arming auto-merge | `scripts/branchstate.py` | proposal; needs a roster entry with `proves`, `does_not_prove`, `closed_by` |
| 5 | Plugin manifests and MCP surface | `.claude-plugin/`, `server.json` | left to `claude/thea-mcp-marketplace` |

## What this plan does not change

- No gate is removed. The done set, the clean-checkout landing, and CI are unchanged.
- No version bump: the contract does not change in this branch.
- The README lane (`claude/readme-overhaul`) and its PR are untouched.

## How to check the plan

```bash
python3 scripts/atlas.py check    # exit code is the verdict
```

Change 2 is the first code change. Its proof is the same `check` exit code, plus the size of
the generated front before and after, recorded in the PR body.
