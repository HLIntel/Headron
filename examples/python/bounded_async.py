"""Bounded concurrent work with an explicit deadline."""

import asyncio


async def process(item: str) -> None:
    await asyncio.sleep(0.01)


async def run(items: list[str]) -> None:
    semaphore = asyncio.Semaphore(32)

    async def bounded(item: str) -> None:
        async with semaphore:
            await process(item)

    async with asyncio.timeout(30):
        async with asyncio.TaskGroup() as group:
            for item in items:
                group.create_task(bounded(item))


if __name__ == "__main__":
    asyncio.run(run([str(i) for i in range(1000)]))