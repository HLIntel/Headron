/-- Double 1..100 and sum. The `example` below IS the self-check: `decide`
    evaluates the proposition at compile time, so a wrong sum fails the build. -/
def doubledSum : Nat :=
  (List.range 100).foldl (fun acc i => acc + (i + 1) * 2) 0

example : doubledSum = 10100 := by decide

def main : IO Unit := do
  IO.println s!"bounded: 1 assertion held — doubledSum = {doubledSum}, proved by decide"
