/* A bounded work queue with an explicit deadline, in the standard library only.
 *
 * WHY IT WAS REWRITTEN: this file used to import `p-queue`, so it could not be executed without a
 * package install — an example nobody could run, which is the skeleton this repository refuses.
 * The ladder says standard library before dependency, and a bounded queue is twenty lines.
 *
 * Verify: node examples/typescript/bounded_queue.ts   (exits non-zero if any assertion fails)
 */

type Task<T> = () => Promise<T>;

class BoundedQueue {
  private active = 0;
  private readonly waiting: Array<() => void> = [];
  private readonly limit: number;

  // A PLAIN FIELD, NOT A PARAMETER PROPERTY. Node runs TypeScript by STRIPPING types, so any
  // syntax that would have to be transformed rather than erased is refused —
  // `constructor(private readonly limit: number)` is exactly that, and this file failed to run
  // until it was written out. An example that needs a build step is an example nobody runs.
  constructor(limit: number) {
    if (!Number.isInteger(limit) || limit < 1) {
      throw new RangeError(`concurrency limit must be a positive integer, got ${limit}`);
    }
    this.limit = limit;
  }

  async run<T>(task: Task<T>, deadlineMs: number): Promise<T> {
    if (this.active >= this.limit) {
      await new Promise<void>((resolve) => this.waiting.push(resolve));
    }
    this.active += 1;
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      // EVERY WAIT HAS A DEADLINE. A promise with no timeout is an unbounded wait wearing a type.
      return await Promise.race([
        task(),
        new Promise<never>((_, reject) => {
          timer = setTimeout(() => reject(new Error(`deadline of ${deadlineMs}ms exceeded`)), deadlineMs);
        }),
      ]);
    } finally {
      if (timer !== undefined) clearTimeout(timer);
      this.active -= 1;
      this.waiting.shift()?.();
    }
  }
}

function assert(condition: boolean, message: string): void {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    process.exit(1);
  }
}

async function main(): Promise<void> {
  const queue = new BoundedQueue(2);
  let peak = 0;
  let live = 0;

  const slow = async (ms: number): Promise<number> => {
    live += 1;
    peak = Math.max(peak, live);
    await new Promise((r) => setTimeout(r, ms));
    live -= 1;
    return ms;
  };

  const results = await Promise.all([10, 10, 10, 10, 10].map((ms) => queue.run(() => slow(ms), 1_000)));
  assert(results.length === 5, "every task returned");
  assert(peak <= 2, `concurrency stayed within the declared limit, peaked at ${peak}`);

  // The deadline must fire rather than wait forever.
  let refused = false;
  try {
    await queue.run(() => slow(200), 20);
  } catch (error) {
    refused = error instanceof Error && error.message.includes("deadline");
  }
  assert(refused, "an overrunning task was refused by its deadline");

  let rejected = false;
  try {
    new BoundedQueue(0);
  } catch {
    rejected = true;
  }
  assert(rejected, "a limit of zero was refused at construction, not at the first task");

  console.log("bounded_queue: 4 assertions held — limit enforced, deadline fired, zero refused");
}

void main();
