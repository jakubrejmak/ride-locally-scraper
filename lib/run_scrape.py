from sqlalchemy.ext.asyncio import AsyncEngine
from db.schema import ttScrTargetTable
import asyncio
from contextlib import nullcontext


async def run_scrape(
    target: ttScrTargetTable,
    engine: AsyncEngine,
    stop_condition: asyncio.Event | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> bool:
    async with semaphore or nullcontext():
        if stop_condition and stop_condition.is_set():
            return False
        # body
        return True
