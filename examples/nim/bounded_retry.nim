## A retry with an ATTEMPT CAP and a BACKOFF CAP, not a retry loop.
##
## The defect this kills: a retry that never stops. Without a cap on attempts the loop outlives
## the caller; without a cap on the delay, exponential backoff sleeps for hours by attempt 20.
## Both bounds are asserted, and the run exits non-zero when either is broken.
##
## Verify: nim c --hints:off --out:/tmp/bounded_retry examples/nim/bounded_retry.nim && /tmp/bounded_retry

type Outcome = object
  succeeded: bool
  attempts: int
  delays: seq[int]

proc retry(failuresBeforeSuccess, maxAttempts, baseMs, capMs: int): Outcome =
  var delay = baseMs
  for attempt in 1 .. maxAttempts:
    result.attempts = attempt
    if attempt > failuresBeforeSuccess:
      result.succeeded = true
      return
    result.delays.add(delay)
    delay = min(delay * 2, capMs)   # the BACKOFF CAP: doubling stops at capMs

let recovers = retry(failuresBeforeSuccess = 2, maxAttempts = 5, baseMs = 100, capMs = 1000)
doAssert recovers.succeeded and recovers.attempts == 3

let neverRecovers = retry(failuresBeforeSuccess = 99, maxAttempts = 6, baseMs = 100, capMs = 1000)
doAssert not neverRecovers.succeeded
doAssert neverRecovers.attempts == 6, "the ATTEMPT CAP must stop the loop"
doAssert neverRecovers.delays == @[100, 200, 400, 800, 1000, 1000], "the BACKOFF CAP must hold"

echo "bounded_retry: ok"
