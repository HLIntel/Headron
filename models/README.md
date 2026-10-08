# Models and Runtime Hosts

Model adapters sit below MODEL.md and above the language/integration Atlas.

Every runtime and its adapter: the generated roster in [MODEL.md](../MODEL.md).

See [ROUTING.md](ROUTING.md) for task and host routing.

## Where you use it

<!-- BEGIN generated: settings (python scripts/atlas.py index --write) -->
| where you use it | what Thea does there |
|---|---|
| A chat with no tools | name the format, typecheck and test commands for any file they name (the route table below, then that pack's tools.yaml), review a pasted diff against the gates, and turn a goal into the checklist of gates its change class requires |
| A chat that keeps instructions | paste the Install block once, and every later chat starts routed, labels its claims and files breaks with the report verb |
| An agent with a shell | clone a release tag and run `python scripts/atlas.py gate <file>` — the numbered commands that prove a change to that file — then `python scripts/enforce.py install` in the repository being changed, so a commit that fails its own toolchain's check is refused |
| A repository's CI | call the reusable workflow, and drift fails the pull request |
| A retrieval or RAG pipeline | run the retrieval_change gates — chunk boundaries, a freshness stamp, hybrid recall and citation checks — so an answer is grounded in what was actually retrieved |
| An autonomous agent run | write a task contract, and `python scripts/sandboxgen.py docker <contract>` prints the host sandbox it needs — no network, read-only root, only the worktree writable |
| A chat or agent with memory | save verdicts by id (a gate, a change class, a ledger entry) with their contract version, never a paraphrase: an id re-checks against the tree, a summary drifts |
<!-- END generated: settings -->

## What each runtime reads before it starts

<!-- BEGIN generated: runtime-entry (python scripts/atlas.py index --write) -->
| runtime | loads by itself | ~tokens |
|---|---|---|
| **Claude Code** | `CLAUDE.md` | 1,049 |
| Codex | `AGENTS.md` | 982 |
| Cursor | `AGENTS.md` | 982 |
| opencode | `AGENTS.md` | 982 |
| Hermes | `.agent/bootstrap.json` | 646 |
| any model given a link | `llms.txt` | 1,088 |
| any chat assistant | `CHAT.md` | 2,572 |

Measured from each file on every build.
<!-- END generated: runtime-entry -->
