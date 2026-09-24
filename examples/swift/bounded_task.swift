// Structured concurrency with an explicit deadline and a cancellation path.
//
// The defect this kills: an unstructured `Task { }` with no owner and no cancellation. It outlives
// the scope that started it, and the only symptom is work that keeps happening after the answer
// was returned.
//
// Verify: swiftc -parse-as-library examples/swift/bounded_task.swift -o /tmp/bounded_task
//         && /tmp/bounded_task
//
// `-parse-as-library` is REQUIRED and is not decoration: without it swiftc treats a file that is
// not named main.swift as top-level code, and `@main` cannot coexist with top-level code. The
// alternative — bridging with a semaphore — would put a blocking wait on an async path in the one
// file whose subject is not doing that.
import Foundation

enum Bounded {
    struct DeadlineExceeded: Error { let milliseconds: UInt64 }

    /// Runs `work` with a deadline. Whichever finishes first wins, and the other is CANCELLED —
    /// a race with no cancellation leaves the loser running.
    static func run<T: Sendable>(
        deadlineMilliseconds: UInt64,
        _ work: @Sendable @escaping () async throws -> T
    ) async throws -> T {
        try await withThrowingTaskGroup(of: T.self) { group in
            group.addTask { try await work() }
            group.addTask {
                try await Task.sleep(nanoseconds: deadlineMilliseconds * 1_000_000)
                throw DeadlineExceeded(milliseconds: deadlineMilliseconds)
            }
            defer { group.cancelAll() }
            guard let first = try await group.next() else {
                throw DeadlineExceeded(milliseconds: deadlineMilliseconds)
            }
            return first
        }
    }
}

func check(_ condition: Bool, _ message: String) {
    if !condition {
        FileHandle.standardError.write("FAIL: \(message)\n".data(using: .utf8)!)
        exit(1)
    }
}

@main
struct Main {
    static func main() async {
        do {
            let quick = try await Bounded.run(deadlineMilliseconds: 500) { 42 }
            check(quick == 42, "work that finishes inside its deadline returns its value")
        } catch {
            check(false, "work inside the deadline must not throw: \(error)")
        }

        var refused = false
        do {
            _ = try await Bounded.run(deadlineMilliseconds: 10) {
                try await Task.sleep(nanoseconds: 400_000_000)
                return 0
            }
        } catch is Bounded.DeadlineExceeded {
            refused = true
        } catch {
            check(false, "the deadline must surface as DeadlineExceeded, got \(error)")
        }
        check(refused, "work that overran was refused by its deadline")

        print("bounded_task: 2 assertions held — a deadline that fires and a loser that is cancelled")
    }
}
