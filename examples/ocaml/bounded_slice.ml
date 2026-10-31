(* A slice that REFUSES out-of-range bounds instead of raising deep inside a caller.

   The defect this kills: String.sub raising Invalid_argument three frames away from the bad
   index, where nobody knows which input produced it. Returning an option makes the refusal a
   value the caller must handle, at the call site.

   Verify: ocaml examples/ocaml/bounded_slice.ml *)

let slice s ~pos ~len =
  if pos < 0 || len < 0 || pos > String.length s - len then None
  else Some (String.sub s pos len)

let () =
  assert (slice "headronxx" ~pos:0 ~len:5 = Some "headr");
  assert (slice "headronxx" ~pos:5 ~len:4 = Some "onxx");
  assert (slice "headronxx" ~pos:6 ~len:4 = None);   (* one past the end: refused, not raised *)
  assert (slice "headronxx" ~pos:(-1) ~len:2 = None);
  assert (slice "" ~pos:0 ~len:0 = Some "");
  print_endline "bounded_slice: ok"
