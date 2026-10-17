-- Bounded map: double 1..100 in parallel; `true` is the whole self-check.
-- Run: futhark run bounded.fut   (prints true iff the sum is 10100)
def main : bool =
  let xs = map (\i -> (i + 1) * 2) (iota 100)
  in reduce (+) 0 xs == 10100
