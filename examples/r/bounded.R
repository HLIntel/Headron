# Bounded retry: a flaky operation gets at most `tries` attempts, then the error escapes.
# Run: Rscript bounded.R
flaky <- local({
  attempts <- 0L
  function() {
    attempts <<- attempts + 1L
    if (attempts < 3L) stop("flaky failure")
    "ok"
  }
})

bounded_retry <- function(op, tries) {
  stopifnot(tries >= 1L)
  for (n in seq_len(tries)) {
    result <- tryCatch(op(), error = function(e) e)
    if (!inherits(result, "error")) return(list(value = result, attempts = n))
  }
  stop("exhausted all ", tries, " attempts")
}

out <- bounded_retry(flaky, 5L)
stopifnot(identical(out$value, "ok"), identical(out$attempts, 3L))
cat("bounded: 2 assertions held — flaky op succeeded on attempt 3 of at most 5\n")
