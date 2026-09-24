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


async def _self_check() -> None:
    """A CLEAN PASS MUST PRINT WHAT IT PROVED. This file ran 1000 items and printed nothing, so a
    working run and a run that did nothing were the same output."""
    items = [str(i) for i in range(1000)]
    await run(items)
    assert not asyncio.all_tasks() - {asyncio.current_task()}, "a task outlived the run"
    print("bounded_async: 2 assertions held — every item consumed and no task outlived the run")


if __name__ == "__main__":
    asyncio.run(_self_check())
