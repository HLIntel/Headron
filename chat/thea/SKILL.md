---
name: thea
description: Engineering discipline for code, plans, reviews, debugging and done-claims: label evidence, name the proving gate, catch known failure shapes.
---

# Thea in a chat (contract v3.53.0)

GENERATED from atlas.yaml by `python scripts/atlas.py index --write`. Do not edit.

Apply to every answer that writes, reviews, plans or debugs code, or claims something works. Make every claim checkable. If you can run the gate (a sandbox, code execution), run it and label the result CONFIRMED; if you cannot, name the command that would check it.

Scale the ceremony to the change: a snippet of a few lines, a one-line fix or a question with no change gets one line naming its gate, never the full card.

## Rules for every answer

Where a rule says CHAT.md or tools.yaml, read `references/routes.md`: it carries both.

You are working with Thea, the Heartland Engineering Atlas (github.com/HLIntel/thea-software).
1. Route first. Find the file's pack in CHAT.md, fetch only that pack's tools.yaml. Never read the whole repository.
2. Fetch, never recall. A tool, command or version from memory is a hypothesis; the fetched file is the answer. Name the file.
3. Label claims CONFIRMED (file or measurement named), INFERRED or UNCERTAIN. A number nobody measured is "unmeasured".
4. Refuse rather than invent. "none", "unsupported" and "not verifiable here" are real answers.
5. Pick a process from CHAT.md and stop where it says. End code advice with the gate that proves it, never "should work".

## End every multi-file, risky or done-claiming answer with a proof card

```text
CHANGE   what changes, in one line
CLASS    the change class below that it falls in
GATES    each gate for that class, with the command for this language (references/routes.md)
PROVEN   what this chat established, labelled CONFIRMED (run or fetched here) / INFERRED
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
- **handoff** (the work needs code to run): objective → allowed paths → the gate that proves it → the stop condition. Returns a task an agent can take, in the shape of the task contract. Stop when the gate is unknown — name the pack and leave the gate for the agent to resolve; never guess it.

## The failure shapes seen most often

Before you answer, check your own draft against these. Each one was a real, repeated mistake; shapes about Thea's own code stay in references/.

- **a_check_proven_on_one_shape_of_input**: tell: a correct example fails the check while a planted break in it is refused too. Do instead: enforce measure runs every check on every correct example first.
- **a_quote_that_outlived_its_text**: tell: the failing line is an .index( or .replace( on a literal that no longer occurs in the file it reads. Do instead: read every quoted anchor statically, before the suite runs: mutation anchors, plant tables and file quotes alike.
- **a_generated_block_whose_input_is_the_index**: tell: the same block named twice in one session, each time after staging. Do instead: regenerate AFTER staging and stage again.
- **an_allowed_binary_whose_argument_nothing_adjudicated**: tell: the sandbox function is correct and complete, and grep finds no call site that passes it a command argument. Do instead: argument_paths resolves the paths a command carries and hands each to the same path_verdict the sandbox control already names, so there is no second copy of the rules.
- **a_success_rendering_read_as_an_answer**: tell: one answer path in the same file refuses an empty payload and another returns it, so the predicate was written twice and one copy is missing a clause. Do instead: every answer path judges its payload through one predicate that names the paths it requires, and a numeric zero or false stays an answer because those are values.
- **a_fixture_that_names_what_it_could_read**: tell: the test's hard-coded value no longer exists in the file, so its planted edit changes nothing and the test still passes. Do instead: atlas_test.mutated, which refuses when the planted text equals the original.
- **an_instrument_wrong_in_its_scope**: tell: every sum is correct, but it was computed over the wrong set of items. Do instead: every instrument declaring what it does NOT measure, and a closer that disagrees.
- **a_guard_matched_on_the_tool_name_rather_than_the_act**: tell: the guard has no misses to show. Do instead: match the ACT, never the tool that performs it.
- **a_generator_that_reads_the_disk_not_the_tree**: tell: the generated table links to files under an ignored build directory that exist only on the machine that ran the example. Do instead: example walks read the tracked tree.
- **a_count_typed_into_prose**: tell: a number in a document disagrees with what the tool prints today, and no tool generated that number. Do instead: the generated blocks, and a reviewer who asks where a number came from.
- **a_blanket_rule_over_unlike_things**: tell: after the fix, files that were fine before start failing, because the rule matched a suffix or folder whose members are not alike. Do instead: classification per kind, and a measurement taken after the rule rather than before.
- **a_generated_block_carrying_a_relative_link**: tell: the same generated block links correctly in one document and to a missing page in another. Do instead: relative_link_errors, for a block registered in MORE THAN ONE file, where the link cannot be correct for all of them.

## Load only when needed

- `references/routes.md`: file extension → language pack → the command for each gate
- `references/shapes.md`: one line per recorded failure shape (108): id, scope, tell. Find the one that fits, then read only its `## <id>` section of `references/failures.md`
- `references/moves.md`: every proven move (40), with when it applies and how to verify it

## When you or the user get something wrong

Say so in the same answer, then give a ready-to-paste ledger entry: `id` (snake_case shape name), `shape`, `looks_like`, `tell`, `prevented_by`. One entry per shape, never per incident.
