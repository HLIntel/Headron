# Bash / Shell

**Status:** automation/foundational

## Purpose
CI, deployment glue, local automation, process orchestration, and system setup.

## Baseline
Use strict/error-aware shell conventions appropriate to the script, quote variables, validate inputs, and make cleanup explicit.

## Common mistakes
- unquoted variables
- unchecked command failures
- unsafe globbing
- assuming working directory
- parsing human-readable command output
- background jobs with no wait/cancellation
- secrets in shell history/logs

## Streamline
Keep shell as orchestration glue. Move complex logic into a typed language when data structures, tests, or error handling become substantial.

Prefer machine-readable command modes where available.

## AI directive
Generated shell must show error handling, cleanup, quoting, working-directory assumptions, and whether commands are destructive.

## Verify
ShellCheck, formatting, isolated test fixtures, and dry-run modes where supported.

Sources: https://www.gnu.org/software/bash/manual/ and https://www.shellcheck.net/