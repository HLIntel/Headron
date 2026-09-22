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
