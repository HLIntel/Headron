// A retry with a DECLARED ceiling, where giving up is a result rather than an exception.
//
// The defect this kills: a retry loop whose exit is an exception, so the caller cannot tell
// "failed after the declared attempts" from "failed for a reason nobody planned for". Both
// unwind the stack identically, and only one of them is a bug.
//
// Verify: dotnet fsi examples/fsharp/BoundedRetry.fsx

// Giving up is a VALUE. Error carries how many attempts were actually spent, so a caller can
// tell an immediate failure from an exhausted budget - which are different faults.
type Outcome<'a> =
    | Ok of 'a * int
    | GaveUp of int

let retryBounded (maxAttempts: int) (work: int -> 'a option) : Outcome<'a> =
    let rec go attempt =
        if attempt > maxAttempts then GaveUp(maxAttempts)
        else
            match work attempt with
            | Some value -> Ok(value, attempt)
            | None -> go (attempt + 1)
    if maxAttempts < 1 then GaveUp 0 else go 1

let mutable failures = 0
let check name ok =
    if not ok then
        printfn "FAILED: %s" name
        failures <- failures + 1

// Succeeds on the third attempt, inside a budget of five.
check "succeeds inside the budget" (retryBounded 5 (fun n -> if n = 3 then Some "done" else None) = Ok("done", 3))
// Never succeeds: the budget is spent and the outcome SAYS so.
check "gives up as a value" (retryBounded 3 (fun _ -> None) = GaveUp 3)
// The first attempt counts: a budget of one is one attempt, not zero and not two.
check "a budget of one is one attempt" (retryBounded 1 (fun n -> if n = 1 then Some n else None) = Ok(1, 1))
check "a budget of one that fails" (retryBounded 1 (fun _ -> None) = GaveUp 1)
// A non-positive budget performs NO work; it does not quietly become one attempt.
check "a zero budget does no work" (retryBounded 0 (fun _ -> Some "never") = GaveUp 0)

if failures > 0 then exit 1
printfn "BoundedRetry: 5 assertions held - giving up is a value, and the budget is exact"
