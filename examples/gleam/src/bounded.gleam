//// A counter with a CEILING that refuses past it, as a Result the caller must handle.
////
//// The defect this kills: a counter (retries, open connections, queued jobs) that is only ever
//// compared against its limit somewhere else, so one path forgets and the limit is advisory.
//// Here the only way to increment returns Error at the ceiling.
////
//// Verify: cd examples/gleam && gleam run

pub type Counter {
  Counter(value: Int, ceiling: Int)
}

pub fn increment(c: Counter) -> Result(Counter, String) {
  case c.value >= c.ceiling {
    True -> Error("at ceiling")
    False -> Ok(Counter(..c, value: c.value + 1))
  }
}

@external(erlang, "io", "put_chars")
fn put_chars(text: String) -> Nil

pub fn main() -> Nil {
  let start = Counter(value: 0, ceiling: 2)
  let assert Ok(one) = increment(start)
  let assert Ok(two) = increment(one)
  let assert Error("at ceiling") = increment(two)
  let assert 2 = two.value
  put_chars("bounded: ok\n")
}
