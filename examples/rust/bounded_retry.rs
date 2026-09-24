//! A retry with a DEADLINE and an idempotency key, not a retry loop.
//!
//! The defect this kills: retrying a non-idempotent operation. The first attempt may have
//! succeeded and only its response been lost, so a blind retry creates a second effect. The key
//! is what makes the second attempt safe; the deadline is what makes the loop terminate.
//!
//! Verify: rustc --edition 2021 -D warnings examples/rust/bounded_retry.rs -o /tmp/bounded_retry
//!         && /tmp/bounded_retry
use std::collections::HashMap;
use std::time::Duration;

#[derive(Debug, PartialEq)]
enum Outcome {
    Applied(u64),
    AlreadyApplied(u64),
    GaveUp { attempts: u32 },
}

/// A store that has seen keys before. `apply` is safe to call twice with the same key.
struct Ledger {
    seen: HashMap<String, u64>,
    fail_first: u32,
}

impl Ledger {
    fn apply(&mut self, key: &str, amount: u64) -> Result<Outcome, &'static str> {
        if let Some(previous) = self.seen.get(key) {
            // THE WHOLE POINT: the second call returns the FIRST result rather than a second effect.
            return Ok(Outcome::AlreadyApplied(*previous));
        }
        if self.fail_first > 0 {
            self.fail_first -= 1;
            return Err("transport failed after the request may have been delivered");
        }
        self.seen.insert(key.to_string(), amount);
        Ok(Outcome::Applied(amount))
    }
}

fn with_retry(ledger: &mut Ledger, key: &str, amount: u64, budget: Duration) -> Outcome {
    // A BUDGET IN TIME, not a count of attempts: a count with a backoff has no stated bound.
    let mut waited = Duration::ZERO;
    let mut backoff = Duration::from_millis(1);
    let mut attempts = 0;
    while waited < budget {
        attempts += 1;
        match ledger.apply(key, amount) {
            Ok(outcome) => return outcome,
            Err(_transient) => {
                waited += backoff;
                backoff *= 2;
            }
        }
    }
    Outcome::GaveUp { attempts }
}

fn main() {
    let mut ledger = Ledger { seen: HashMap::new(), fail_first: 2 };

    let first = with_retry(&mut ledger, "transfer-7", 500, Duration::from_millis(50));
    assert_eq!(first, Outcome::Applied(500), "the retry eventually applied it exactly once");

    let again = with_retry(&mut ledger, "transfer-7", 500, Duration::from_millis(50));
    assert_eq!(again, Outcome::AlreadyApplied(500), "a repeat with the same key had no second effect");
    assert_eq!(ledger.seen.len(), 1, "one effect for two calls");

    let mut hopeless = Ledger { seen: HashMap::new(), fail_first: u32::MAX };
    match with_retry(&mut hopeless, "transfer-8", 1, Duration::from_millis(4)) {
        Outcome::GaveUp { attempts } => assert!(attempts >= 1, "it reported how many times it tried"),
        other => panic!("a permanently failing call must give up, got {other:?}"),
    }

    println!("bounded_retry: 4 assertions held — one effect, deadline honoured, giving up is a result");
}
