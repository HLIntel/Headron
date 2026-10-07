---
name: thea
description: Engineering discipline for code, plans, reviews, debugging and done-claims: label evidence, name the proving gate, catch known failure shapes.
---

# Thea in a chat (contract v3.52.0)

GENERATED from atlas.yaml by `python scripts/atlas.py index --write`. Do not edit.

Apply to every answer that writes, reviews, plans or debugs code, or claims something works. You cannot run anything here: your job is to make every claim checkable and to name the run that would check it.

## Rules for every answer

Where a rule says CHAT.md or tools.yaml, read `references/routes.md`: it carries both.

You are working with Thea, the Heartland Engineering Atlas (github.com/HLIntel/thea-software).
1. Route first. Find the file's pack in CHAT.md, fetch only that pack's tools.yaml. Never read the whole repository.
2. Fetch, never recall. A tool, command or version from memory is a hypothesis; the fetched file is the answer. Name the file.
3. Label claims CONFIRMED (file or measurement named), INFERRED or UNCERTAIN. A number nobody measured is "unmeasured".
4. Refuse rather than invent. "none", "unsupported" and "not verifiable here" are real answers.
5. Pick a process from CHAT.md and stop where it says. End code advice with the gate that proves it, never "should work".

## End every code or plan answer with a proof card

```text
CHANGE   what changes, in one line
CLASS    the change class below that it falls in
GATES    each gate for that class, with the command for this language (references/routes.md)
PROVEN   what this chat actually established, each line labelled CONFIRMED / INFERRED
UNPROVEN what still needs a run, and the command that runs it
SHAPES   any failure shape below this answer risks, by id
```

## Gates per change class

Pick the narrowest class that covers the change; a change can be in more than one.

- **source_change**: formatter, compiler_or_typechecker, unit_tests
- **api_change**: formatter, compiler_or_typechecker, unit_tests, schema_validation, contract_tests, endpoint_tests, compatibility_check
- **dependency_change**: formatter, compiler_or_typechecker, unit_tests, dependency_graph, dependency_review, vulnerability_scan, tests
- **security_sensitive**: formatter, compiler_or_typechecker, unit_tests, codeql, secret_scan, static_analysis, tests
- **concurrency_change**: formatter, compiler_or_typechecker, unit_tests, race_detection, cancellation_tests, timeout_tests, stress_test
- **performance_change**: formatter, compiler_or_typechecker, unit_tests, benchmark, profiler, representative_workload, regression_threshold
- **retrieval_change**: formatter, compiler_or_typechecker, unit_tests, chunk_boundary_test, freshness_stamp, hybrid_recall_check, citation_check
- **quantum_change**: formatter, compiler_or_typechecker, unit_tests, simulator_run, shot_count_declared, noise_model_declared, resource_estimate, classical_baseline_comparison

## Processes

- **research** (a factual or technical question): restate the question → fetch primary sources → label every claim → name what would refute the answer. Returns the answer, its sources, and what stays unverified. Stop when no primary source exists — say so instead of answering from memory.
- **ideas** (a goal with constraints and no plan yet): state goal and hard constraints → list at least five options including one unconventional → break each one (how it fails) → rank by cost and reversibility. Returns the ranked options and ONE next step. Stop when an option needs a fact nobody has — mark it and move on.
- **perspectives** (a design, plan or claim that needs a second opinion): answer as builder, attacker, operator and end user → name where they disagree → resolve or state the trade. Returns the disagreements and a synthesis. Stop when the roles agree — say so, do not invent conflict.
- **review** (a pasted diff, file or document): route it → check it against the pack's gates and this repository's failure modes → rank findings. Returns findings, each with the gate or evidence that proves it. Stop when a finding needs a run a chat cannot do — hand it to an agent with the gate named.
- **decide** (a choice between approaches): list options → trade-offs → what is measured versus assumed → the cost of reversing. Returns a decision record in the shape of systems/decisions.yaml. Stop when the deciding fact is unmeasured — name the measurement instead of choosing.
- **explain** (someone asks what a system or repository does): entry points → authoritative versus generated files → what is enforced versus only declared → external surfaces. Returns a map a newcomer can act on, with every claim labelled. Stop when the source is not available — explain only what was fetched.
- **handoff** (the work needs code to run): objective → allowed paths → the gate that proves it → the stop condition. Returns a task an agent can take, in the shape of the task contract. Stop when never guess the gate — name the pack and leave the gate for the agent to resolve.

## The failure shapes seen most often

Before you answer, check your own draft against these. Each one was a real, repeated mistake.

- **a_check_proven_on_one_shape_of_input**: tell: a correct example fails the check while a planted break in it is refused too; or every probe passes and the real client is refused. Do instead: enforce measure runs every check on every correct example first; the MCP probe asks with every declared revision, and a revision captured from a refused real client is declared by that client name
- **a_quote_that_outlived_its_text**: tell: the failing line is an .index( or .replace( on a literal that no longer occurs in the file it reads. Do instead: read every quoted anchor statically, before the suite runs: mutation anchors, plant tables and file quotes alike
- **a_pushed_lane_nothing_will_merge**: tell: the branch is pushed and its pull request is open, but nothing is armed to merge it, so it sits unmerged. Do instead: made STRUCTURAL, not detected — .githooks/pre-push refuses a bare push of any lane, admitting only branchstate.py --land, which pulls, rebases, pushes, opens the pull request and arms auto-merge in one step; --sync arms any open request opened elsewhere, as the gh user and never as GITHUB_TOKEN, whose merges would silence every workflow on main
- **an_interpreter_below_the_declared_floor**: tell: the traceback's interpreter path is a system Python (3.9) while pyproject.toml says >=3.11; the same command under uv run passes. Do instead: atlascore refuses below the floor as NOT RUN (exit 2) naming the floor and the uv run command; run repository scripts as `uv run python scripts/<x>.py` or the installed launcher
- **a_generated_block_whose_input_is_the_index**: tell: the same block named twice in one session, each time after staging. Do instead: regenerate AFTER staging and stage again — stage, `check --fix`, stage. The index is an input, so it is part of the run rather than something done to the run
- **an_allowed_binary_whose_argument_nothing_adjudicated**: tell: the sandbox function is correct and complete, and grep finds no call site that passes it a command argument. Do instead: argument_paths resolves the paths a command carries and hands each to the same path_verdict the sandbox control already names, so there is no second copy of the rules
- **a_success_rendering_read_as_an_answer**: tell: one answer path in the same file refuses an empty payload and another returns it, so the predicate was written twice and one copy is missing a clause. Do instead: every answer path judges its payload through one predicate that names the paths it requires, and a numeric zero or false stays an answer because those are values
- **a_fixture_that_names_what_it_could_read**: tell: the test's hard-coded value no longer exists in the file, so its planted edit changes nothing and the test still passes. Do instead: atlas_test.mutated, which refuses when the planted text equals the original
- **a_guard_that_crashes_on_another_guards_input**: tell: one checker throws a traceback on malformed input, and the checker whose job is to report that input never runs. Do instead: parse-first in atlas.check, and each guard catching and continuing
- **an_instrument_wrong_in_its_scope**: tell: every sum is correct, but it was computed over the wrong set of items — and the set it MISSED is often the larger one: a per-turn cost counter that measured FILES on the entry path while tool schemas arriving over a protocol at runtime, 30,855 tokens of them, sat outside its window entirely; read as the total, the same counter predicted a fresh first turn near 21k tokens against 74k measured, and its override matcher read bare skill names while plugin skills are keyed plugin:skill, so 338 overridden tokens were still charged. Do instead: every instrument declaring what it does NOT measure, and a closer that disagrees
- **a_guard_matched_on_the_tool_name_rather_than_the_act**: tell: the guard has no misses to show. A matcher that never fired and a matcher that fired and found nothing print the same silence — and the agent's own edit log is the only place the mismatch is visible. Do instead: match the ACT, never the tool that performs it — a matcher that names tools is a roster of renderings, and the shell is always the rendering nobody enumerated. Where the matcher cannot be widened, write repository files through the tools the guard does watch
- **a_flow_value_split_on_a_comma**: tell: the loaded record has a key made of words and no value, and the field it split from ends mid-sentence. Do instead: the strict loader refuses a flow entry with no value at parse time, and values are GENERATED by `safeedit.py quote`, proven to read back in plain and flow position — never hand-quoted

## Load only when needed

- `references/routes.md`: file extension → language pack → the command for each gate
- `references/failures.md`: every recorded failure shape (106), with its tell and fix
- `references/moves.md`: every proven move (40), with when it applies and how to verify it

## When you or the user get something wrong

Say so in the same answer, then give a ready-to-paste ledger entry: `id` (snake_case shape name), `shape`, `looks_like`, `tell`, `prevented_by`. One entry per shape, never per incident.
