from db.schema import ScrTargetTable
import asyncio
from contextlib import nullcontext


async def run_scrape(
    target: ScrTargetTable,
    stop_condition: asyncio.Event | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> bool:
    async with semaphore or nullcontext():
        if stop_condition and stop_condition.is_set():
            return False
        # body
        return True
