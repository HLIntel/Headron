;; Bounded: double 1..100 and sum; `run` returns 10100.
;; The start function IS the self-check: instantiation traps unless the sum holds.
;; Run: wasmtime bounded.wat   (silent exit = pass; trap = fail)
(module
  (func $run (result i32)
    (local $i i32) (local $total i32)
    (local.set $i (i32.const 1))
    (local.set $total (i32.const 0))
    (block $done
      (loop $loop
        (br_if $done (i32.gt_u (local.get $i) (i32.const 100)))
        (local.set $total
          (i32.add (local.get $total)
                   (i32.mul (local.get $i) (i32.const 2))))
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $loop)))
    (local.get $total))
  (export "run" (func $run))
  (func $check
    (if (i32.ne (call $run) (i32.const 10100))
      (then unreachable)))
  (start $check))
