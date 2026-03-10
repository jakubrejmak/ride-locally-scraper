###
#   Processor module parses the output of scraping module by
#   either static analisys or with the help of the llm
###

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import select
import uuid
from db.schema import ttScrTargetTable, ttScrProcessedTable, ttScrRunTable
import asyncio
from contextlib import nullcontext


async def try_get_existing(session: AsyncSession, run: ttScrRunTable) -> ttScrProcessedTable:
    q = select(ttScrProcessedTable).where(ttScrProcessedTable.run_id == run.id)
    resp = await session.execute(q)
    result = resp.scalar_one_or_none()
    if not result:
        result = ttScrProcessedTable(
            run_id=run.id,
            target_id=run.target_id,
            o_filepath=uuid.uuid4(),
        )
        session.add(result)
        await session.flush()
    return result


async def process_file(
    run: ttScrRunTable,
    engine: AsyncEngine,
    stop_condition: asyncio.Event | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> bool:
    """Takes a ttScrRunTable rows, processes their output files and saves its result to ttScrProcessedTable"""
    if stop_condition and stop_condition.is_set():
        return False

    async with semaphore or nullcontext():
        async with AsyncSession(engine) as session:
            exists = await try_get_existing(session, run)
        return True

    return True
