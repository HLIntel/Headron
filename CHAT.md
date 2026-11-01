# CHAT.md: Headron Software for a chat session (contract v3.61.0)

> For chat assistants with or without tools. GENERATED from `atlas.yaml/chat` by `python scripts/atlas.py index --write`. Do not edit.

**Start with the task.** Use the smallest relevant context, route changed files to their declared checks, and run checks when tools are available and authorized. Otherwise state what remains unverified and give the next actionable step.

**Hosted** (a `headron` tool is attached): call it with argv — `["route", "<file>"]`, `["gate", "<file>"]`, `["failures"]` — instead of fetching; skip the skill install and the first reply. The processes below still hold.

**Raw base** `R` = `https://raw.githubusercontent.com/HLIntel/Headron/main/`. Every path below is relative to `R`: fetch it, never recall it.

## Install the chat skill (optional)

If the user asks to install it, the skill makes guidance available to compatible chats: the rules, the gates per change class, a proof card, every recorded failure shape and every language's gate commands, with nothing to fetch or run.

1. **You can create files** (code execution, an artifact or file tool): fetch each path below from `R` and return ONE zip whose root folder is `headron/`, each file at its path under `models/chat/headron/`. Hand the user the zip.
2. **You cannot**: give the user https://github.com/HLIntel/Headron/releases/latest/download/headron-chat-skill.zip
3. Tell the user: claude.ai → Settings → Capabilities → Skills → Upload skill, choose the zip, then start a new chat. Another runtime that loads skill folders takes the same `headron/` folder.
4. Until it is installed, work from this file for the rest of the session.

- `models/chat/headron/SKILL.md` · `models/chat/headron/references/failures.md` · `models/chat/headron/references/moves.md` · `models/chat/headron/references/routes.md` · `models/chat/headron/references/shapes.md`

## Install (paste once)

```text
You are working with Headron Software (github.com/HLIntel/Headron).
1. Start with the user's task and constraints. Use only the context needed; route a file to its pack when a change needs verification.
2. Check the available pack before naming its commands or versions. If unavailable, say what is missing; never guess.
3. Distinguish observed evidence, inference and uncertainty. Never present a proposed check as a passing result.
4. Inspect relevant links and files with available tools when authorized; report inaccessible inputs as unverified and give a next check. Preserve uncertain shared files and offer installation only on request.
5. Check intended tests ran, not just a nonzero count. For mutations, require a passing clean control and rejection of the changed input, avoiding stale caches.
6. Bind verdicts to the gate, revision and contract. Repeat the failing action after a fix; verify the live consumer uses the changed artifact. Include basic tests with compatibility checks.
```

## First reply to someone who shared this link

In your first reply to someone who shared this link: say you are working under Headron for the rest of this session; do one thing from it now in your setting (below) — route their file, list the gates their change needs, or check a pasted diff; and if you see a gap or a mistake in Headron itself, file it with the report verb rather than describing it. Offer installation only when the user asks for it. If no task or file was provided, ask for one. Never stop at a summary.

- **a chat with no tools:** route the named file and name its declared gates from the available pack; if the route or pack is unavailable, say so without inventing commands
- **a chat that keeps instructions:** apply the Install block to the task; offer installation only if asked
- **an agent with a shell:** use an available checkout to run `python scripts/atlas.py gate <file>`; if unavailable, name the missing dependency and offer setup only if requested
- **a repository's CI:** call the reusable workflow, and drift fails the pull request
- **a retrieval or RAG pipeline:** run the retrieval_change gates — chunk boundaries, a freshness stamp, hybrid recall and citation checks — so an answer is grounded in what was actually retrieved
- **an autonomous agent run:** write a task contract, and `python scripts/sandboxgen.py docker <contract>` prints the host sandbox it needs — no network, read-only root, only the worktree writable
- **a chat or agent with memory:** save verdicts by id (a gate, a change class, a ledger entry) with their contract version, never a paraphrase: an id re-checks against the tree, a summary drifts

## Route a file

Match the extension or filename, then fetch `languages/<pack>/tools.yaml` and nothing else.

- bash: `.bash` `.sh`
- bqn: `.bqn`
- c: `.c` `.h`
- carbon: `.carbon`
- chapel: `.chpl`
- cloudflare: `wrangler.json` `wrangler.jsonc` `wrangler.toml`
- cpp: `.cc` `.cpp` `.hpp`
- cuda: `.cu` `.cuh`
- dockerfile: `Dockerfile`
- elixir: `.ex` `.exs`
- forth: `.4th` `.fth`
- fsharp: `.fs` `.fsx`
- futhark: `.fut`
- gleam: `.gleam`
- go: `.go`
- hare: `.ha`
- haskell: `.hs` `.lhs`
- headron: `.headron`
- json: `.json`
- julia: `.jl`
- lean4: `.lean`
- markdown: `.md`
- mojo: `.mojo`
- nim: `.nim`
- ocaml: `.ml` `.mli`
- odin: `.odin`
- python: `.py` `.pyi`
- r: `.r`
- roc: `.roc`
- rust: `.rs`
- scala: `.sc` `.scala`
- sql: `.sql`
- swift: `.swift`
- toml: `.toml` `uv.lock`
- typescript: `.cjs` `.cts` `.js` `.jsx` `.mjs` `.mts` `.ts` `.tsx`
- uiua: `.ua`
- v: `.v`
- webassembly: `.wasm` `.wat`
- yaml: `.yaml` `.yml`
- zig: `.zig`

## Processes

| process | when | steps | returns | stop when |
|---|---|---|---|---|
| **research** | a factual or technical question | answer the question → check relevant primary sources when needed → separate evidence from inference → name material uncertainty | the answer, its sources, and what stays unverified | a necessary source is unavailable — state the limit and answer only what the evidence supports |
| **ideas** | a goal with constraints and no plan yet | state goal and hard constraints → compare relevant options → check how each could fail → rank by cost and reversibility | a recommendation with trade-offs and a next step | an option needs a fact nobody has — mark it and move on |
| **perspectives** | a design, plan or claim that needs a second opinion | answer as builder, attacker, operator and end user → name where they disagree → resolve or state the trade | the disagreements and a synthesis | the roles agree — say so, do not invent conflict |
| **review** | a pasted diff, file or document | route it → check it against the pack's gates and this repository's failure modes → rank findings | findings, each with the gate or evidence that proves it | a finding needs a run a chat cannot do — hand it to an agent with the gate named |
| **decide** | a choice between approaches | list options → trade-offs → what is measured versus assumed → the cost of reversing | a decision record in the shape of docs/systems/decisions.yaml | the deciding fact is unmeasured — name the measurement instead of choosing |
| **explain** | someone asks what a system or repository does | entry points → authoritative versus generated files → what is enforced versus only declared → external surfaces | a map a newcomer can act on, with every claim labelled | the source is not available — explain only what was fetched |
| **handoff** | the work needs code to run | objective → allowed paths → the gate that proves it → the stop condition | a task an agent can take, in the shape of the task contract | the gate is unknown — name the pack and leave the gate for the agent to resolve; never guess it |

## When someone says use, install, open, run, pull, report

| they say | it means | a chat does |
|---|---|---|
| **use** | work under Headron's rules on your own code | apply the guidance in CHAT.md to the task, route each file, and fetch only that pack's tools.yaml; offer installation only if requested |
| **install** | put the harness on a machine | install the chat skill as CHAT.md's first section says (build the zip, or link the release asset), and give the user the `install` block of README.md for a machine |
| **open** | start reading it | fetch llms.txt or CHAT.md from the raw base and nothing else until a route names it |
| **run** | execute its checks | run the check if the necessary tools and authorization are available; otherwise name the check and mark it not run |
| **pull** | fetch or update a copy | fetch raw files at a release tag, never main |
| **report** | record a break, mistake or bad result so Headron learns to prevent it | answer with a ready-to-paste ledger entry (id, shape, looks_like, tell, prevented_by) |

## Who hands what to whom

- **person and chat:** the Install block in CHAT.md, pasted once — hands over an answer with its claims labelled and the gate that proves it.
- **chat to agent:** the handoff process in CHAT.md — hands over a task contract that validates against tools/agent-task.schema.json.
- **agent to model:** the one line `atlas.py gate` returns, as the whole context — hands over a single command, measured as the most accurate and cheapest context.
- **agent to agent:** one lane each (a worktree and branch), landed with `branchstate.py --land` — hands over a pull request plus the ledger entries it added.
- **agent to person or chat:** `atlas.py gate <file> --json` and the outcome agentrun.py writes into the contract — hands over machine-checkable records, never a summary of them.
- **chat and chat:** the same Install block in each — hands over ledger entries filed with the report verb, so one chat's mistake teaches the next.
- **anyone to Headron:** the report verb, or skills/headron/SKILL.md — hands over a ledger entry that becomes a guard or an intake that must graduate.

## Sources

- `llms.txt` index · `languages/<pack>/tools.yaml` commands · `docs/systems/decisions.yaml` decision records · `.agent/facts.json` every published figure · `atlas.yaml` everything, and the most expensive
- measured: `benchmarks/ab-latest.json`, `benchmarks/tasks-latest.json`; what each instrument does and does not prove: `docs/INSTRUMENTS.md`
- verify here, with no outside service: `headron verify` runs the gates; `headron proof <path> --verify` runs the proof for a routed path
- an agent with a shell plugs in with `python scripts/atlas.py port <path>` and runs the verdict `python scripts/atlas.py check`, judged on the exit code
