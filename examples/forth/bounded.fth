\ Bounded countdown: emits n..1, then proves the stack depth is unchanged.
\ Run: gforth bounded.fth
: countdown ( n -- ) begin dup 0 > while dup . 1- repeat drop ;

: self-check ( -- )
  depth >r
  5 countdown cr
  depth r> = if
    ." bounded: 1 assertion held — 5 items emitted, stack depth unchanged" cr
  else
    ." FAIL: stack depth changed" cr -1 throw
  then ;

self-check
bye
