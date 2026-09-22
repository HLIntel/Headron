import PQueue from "p-queue";

const queue = new PQueue({
  concurrency: 16,
  timeout: 10_000,
  throwOnTimeout: true,
});

export async function run(items: Iterable<string>): Promise<void> {
  const maxPending = 64;
  let submitted = 0;

  for (const item of items) {
    await queue.add(() => processItem(item));
    submitted += 1;

    if (submitted >= maxPending) {
      await queue.onSizeLessThan(maxPending);
    }
  }

  await queue.onIdle();
}

async function processItem(item: string): Promise<void> {
  void item;
}
