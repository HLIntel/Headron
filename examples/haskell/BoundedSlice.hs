-- A slice that REFUSES an out-of-range request instead of returning a shorter one.
--
-- The defect this kills: `take n . drop k` silently returns fewer elements than asked for when
-- the list is too short. The caller gets a list, and a list of the wrong length is
-- indistinguishable from a list of the right one unless somebody checks — so the truncation
-- travels as a result.
--
-- Verify: runghc examples/haskell/BoundedSlice.hs
module Main (main) where

import Control.Monad (unless)
import System.Exit (exitFailure)

-- Nothing is the REFUSAL, and it is a different constructor from a short list, so the two cannot
-- be confused by a caller that forgot to check a length.
slice :: Int -> Int -> [a] -> Maybe [a]
slice offset count xs
  | offset < 0 || count < 0            = Nothing
  | offset + count > length xs         = Nothing   -- never a clamp
  | otherwise                          = Just (take count (drop offset xs))

check :: String -> Bool -> IO ()
check name ok = unless ok $ putStrLn ("FAILED: " ++ name) >> exitFailure

main :: IO ()
main = do
  let xs = [0 .. 7] :: [Int]
  check "whole"          (slice 0 8 xs == Just xs)
  check "middle"         (slice 2 3 xs == Just [2, 3, 4])
  check "count past end" (slice 0 9 xs == Nothing)
  check "offset past end"(slice 9 0 xs == Nothing)
  check "valid offset, invalid count" (slice 6 4 xs == Nothing)
  -- An empty result is a real answer and is NOT a refusal; the two must stay distinguishable.
  check "empty is not refusal" (slice 8 0 xs == Just [])
  check "negative refused"  (slice (-1) 1 xs == Nothing)
  putStrLn "BoundedSlice: 7 assertions held - refusal, empty, and a negative that does not wrap"
