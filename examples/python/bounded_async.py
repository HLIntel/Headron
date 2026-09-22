"""Fixed worker pool: bounded tasks, bounded queue, hard deadline."""

import asyncio


async def process(item: str) -> None:
    await asyncio.sleep(0.01)


async def run(items: list[str]) -> None:
    queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=64)

    async def worker() -> None:
        while True:
            item = await queue.get()
            try:
                if item is None:
                    return
                await process(item)
            finally:
                queue.task_done()

    async with asyncio.timeout(30):
        async with asyncio.TaskGroup() as group:
            for _ in range(32):
                group.create_task(worker())

            for item in items:
                await queue.put(item)

            await queue.join()

            for _ in range(32):
                await queue.put(None)


if __name__ == "__main__":
    asyncio.run(run([str(i) for i in range(1000)]))
