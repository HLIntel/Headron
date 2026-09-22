# Bash Operating Card

**Route:** build glue, CI, deployment wrappers, local harnesses, diagnostics.

**Fast path:** `set -euo pipefail` where appropriate → shellcheck → shfmt → bounded commands.

**Native authority:** shell + platform utilities; document portability assumptions.

**Pair with:** Python/Go/Rust for logic that has state, parsing, concurrency, or complex error handling.

**Boundary:** quote variables, validate paths, avoid eval, use explicit temporary directories and cleanup traps.

**Avoid:** parsing JSON with grep, recursive `rm`, unbounded loops, silent error suppression, secret leakage in command output.

**Reliability:** timeouts, traps, cleanup, explicit exit codes, bounded retries.

**Verify:** shellcheck → shfmt check → dry-run where possible → CI execution.

**AI learning loop:** prefer existing project commands; do not replace robust tooling with bespoke shell parsing.

**Research:** https://www.gnu.org/software/bash/manual/ · https://www.shellcheck.net/
