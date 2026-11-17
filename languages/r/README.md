# R

**Status:** production

## Purpose
Statistics, applied data analysis and reproducible reporting, where the model and its diagnostics matter more than the program around them.

## Why this route exists
It fills statistics and the CRAN ecosystem, which no other route in this atlas reached.

## Stack
renv -> styler -> R CMD check -> testthat -> Rprof.

## Common mistakes
- an analysis with no seed, so the number cannot be regenerated
- `install.packages` with no lockfile, so the environment is unrecorded
- growing a data frame inside a loop
- a silently coerced column type changing a result without an error
- reporting a point estimate with no interval and no diagnostic

The avoid list, boundary contract, verify loop and learning loop live in the [operating card](#operating-card) below.

Official: https://cran.r-project.org/manuals.html

## Operating card

**Route:** statistics, applied analysis, model diagnostics, reproducible reports.

**Fast path:** `renv::restore()` → `styler` → `testthat` → `R CMD check` on anything shipped as a package.

**Native authority:** R itself, `R CMD check`, the CRAN toolchain and the model's own diagnostics.

**Pair with:** Python for orchestration and ML plumbing; SQL for the data it reads; Rust or C++ over Rcpp for a hot numeric core.

**Boundary:** a data contract at the edge — column names, types, units and missingness stated, because a silently coerced column is the most common defect in this language.

**Avoid:** `attach()`, `setwd()` in a script, `T`/`F` instead of `TRUE`/`FALSE`, growing a data frame in a loop, an analysis with no seed and no session record.

**Reliability:** a pinned project library, a set seed, and a session record beside every result — a number that cannot be regenerated is not a result.

**Verify:** the fast path above, every step.

**AI learning loop:** read the data contract → reproduce one figure → change one assumption on purpose → re-check the diagnostics, never only the point estimate.

**Research:** https://cran.r-project.org/manuals.html · https://www.tidyverse.org/ · https://adv-r.hadley.nz/
