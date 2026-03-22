###
#   Processor module parses the output of scraping module by
#   either static analisys or with the help of the llm
###

import asyncio
import uuid
from contextlib import nullcontext

from sqlalchemy import select

from db.schema import ttScrProcessedTable, ttScrRunTable, ttScrTargetTable
from db.session import session
from models.types import ScrTargetConfig
from logging import getLogger

log = getLogger(__name__)

async def _get_processor_config(target_id: int):
    async with session() as s:
        q = select(ttScrTargetTable).where(ttScrTargetTable.id == target_id)
        r = await s.execute(q)
        result = r.scalar_one()

    config = ScrTargetConfig(**result.config)

    return config.processor


async def try_get_existing(run: ttScrRunTable) -> ttScrProcessedTable:
    async with session() as s:
        q = select(ttScrProcessedTable).where(ttScrProcessedTable.run_id == run.id)
        resp = await s.execute(q)
        result = resp.scalar_one_or_none()
        if not result:
            result = ttScrProcessedTable(
                run_id=run.id,
                target_id=run.target_id,
                o_filepath=uuid.uuid4(),
            )
            s.add(result)
            await s.flush()
    return result


async def process_file(
    run: ttScrRunTable,
    stop_condition: asyncio.Event | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> bool:
    """Takes a ttScrRunTable rows, processes their output files and saves its result to ttScrProcessedTable"""
    if stop_condition and stop_condition.is_set():
        return False

    async with semaphore or nullcontext():
        run_to_process = await try_get_existing(run)
        processor_config = _get_processor_config(run.target_id)

    return True
