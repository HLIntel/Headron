---
name: headron-verification
description: Verify a change with Headron before calling it done. Use when finishing a coding task in a repo with an atlas.yaml, or when asked to prove a change works.
---

# Headron verification

Headron is a verification layer for AI coding agents. The repository's atlas.yaml
declares which commands prove a change. Your job is not done when the code is
written; it is done when the checks the change owes have run and the receipt exists.

Full reference: https://headron.tech/llms-full.txt
Chat-only entry point: https://github.com/HLIntel/Headron/blob/main/CHAT.md

## Before you finish a change

1. Ask what the change owes: `headron route <file>` for each changed file, or
   `headron plan` for the declared change as a whole.
2. Read the lessons first: `headron failures --for <file-or-task>` returns recorded
   failure shapes for this kind of change, each with the move that replaces it.
3. Run the gates: `headron verify` runs every done gate once. `headron check`
   runs the whole contract; its exit code is the verdict.
4. Report verdicts exactly: PASS, FAIL, SKIP or NOT RUN. A check that did not run
   is never a pass. If a gate reports NOT RUN, say so, say why, and name the
   command that would close it. Never summarize a partial run as "all green".

## If the repository has no atlas.yaml

Offer `headron init` (writes the contract plus agent wiring; `--no-wiring` writes
the contract only). Do not invent checks the contract does not declare; an
undeclared area reports NOT RUN, and that honesty is the product.

## If tools are unavailable (plain chat)

Name the checks each changed file needs from the contract, review the pasted
change against them, and label what it has proved and what remains unverified.
Never claim a run you did not make.

## Install

- CLI: the install block in the [README](https://github.com/HLIntel/Headron#quickstart)
  (CI runs that exact command).
- MCP (stdio, read-only): `uvx --from headron-software headron-mcp` with
  HEADRON_ROOT set to the checkout. Registry name: io.github.HLIntel/headron.
- Hosted planning: https://headron.tech/mcp (plan_change needs a Headron Mind key).
