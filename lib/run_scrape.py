###
#   scraper service
###

from sqlalchemy.ext.asyncio import AsyncEngine
from db.schema import ttScrTargetTable, ttScrRunTable
import asyncio
from contextlib import nullcontext


async def run_scrape(
    target: ttScrTargetTable,
    engine: AsyncEngine,
    stop_condition: asyncio.Event | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> bool:
    """Takes a target and saves its result to ttScrRunTable"""
    if stop_condition and stop_condition.is_set():
        return False
    async with semaphore or nullcontext():
        # body
        return True
