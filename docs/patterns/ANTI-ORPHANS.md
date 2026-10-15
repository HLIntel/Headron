# Anti-Orphans

An orphan is a durable artifact without a discoverable owner, route, reference, test, or explicit declaration.

## Classes
documentation; language guide; model adapter; script; dependency; schema; workflow; generated artifact.

## Detection graph
~~~text
Git-tracked files
 -> Markdown/local links
 -> index membership
 -> artifact routes
 -> model adapters
 -> scripts/workflows
 -> dependency analyzers
~~~

For TypeScript, Knip can detect unused files, exports, and dependencies. For Python, deptry can detect unused or missing dependencies:
https://knip.dev/
https://deptry.com/

Treat findings as evidence, because dynamic entrypoints and generated/config files can create legitimate reachability gaps.

## Repair order
1. determine whether it is generated, dynamic, or an entrypoint
2. identify the owner/consumer
3. add an explicit reference or entry declaration
4. add a regression/contract check where omission would recur
5. delete only when reachability and ownership are disproven
6. rerun the harness

Do not make destructive cleanup the default automated action.

## AI rule
Agents may propose orphan removal; the harness should report and classify before deletion.

## What enforces this now

- **A pack that ships nothing runnable** is counted, named and ratcheted:
  `context_policy/example_coverage`. `exrun.py` prints its COVERAGE beside its pass count, because
  it once reported "10 passed, 0 failed" and said nothing about the routes it never looked at.
- **A module in the tree and in no roster** fails: every `scripts/*.py` must be named by
  `atlas.yaml/instruments`, and must be either shipped in the wheel or declared development-only.
- **A shipped module importing a development-only one** fails — a break invisible from a checkout,
  where every module is present, and fatal for a consumer at import time.
- **A pack reachable only by knowing its name** fails: every route must appear in a
  `language_selection` axis, because a roster answers "what is supported" and never "what to use".
