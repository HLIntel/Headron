import PQueue from "p-queue";

const queue = new PQueue({
  concurrency: 16,
  timeout: 10_000,
  throwOnTimeout: true,
});

export async function run(items: string[]): Promise<void> {
  await Promise.all(
    items.map((item) => queue.add(() => processItem(item))),
  );
}

async function processItem(item: string): Promise<void> {
  void item;
}