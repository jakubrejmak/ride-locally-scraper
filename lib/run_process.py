###
#   Processor module parses the output of scraping module by
#   either static analysis or with the help of the llm
###

import asyncio
import uuid
from contextlib import nullcontext
from logging import getLogger

from sqlalchemy import select

from conf import config
from db.schema import ttScrProcessedTable, ttScrRunTable, ttScrTargetTable
from db.session import session
from lib.files import save_result
from lib.processors.process_llm import llm_process_file
from models.types import LLMProcessorConfig, ProcessResult, ScrTargetConfig

log = getLogger(__name__)


async def _get_processor_config(target_id: int):
    async with session() as s:
        q = select(ttScrTargetTable).where(ttScrTargetTable.id == target_id)
        r = await s.execute(q)
        result = r.scalar_one()

    target_config = ScrTargetConfig(**result.config)

    return target_config.processor


async def try_get_existing(run: ttScrRunTable) -> ttScrProcessedTable:
    async with session() as s:
        q = select(ttScrProcessedTable).where(ttScrProcessedTable.run_id == run.id)
        resp = await s.execute(q)
        result = resp.scalar_one_or_none()
        if not result:
            result = ttScrProcessedTable(
                run_id=run.id,
                target_id=run.target_id,
                o_filepath=str(uuid.uuid4()),
            )
            s.add(result)
            await s.commit()
    return result


async def run_process(
    run: ttScrRunTable,
    stop_condition: asyncio.Event | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> bool:
    """Takes a ttScrRunTable row, processes its output file and saves the result to ttScrProcessedTable"""
    if stop_condition and stop_condition.is_set():
        return False

    async with semaphore or nullcontext():
        to_process = await try_get_existing(run)
        processor_config = await _get_processor_config(run.target_id)

        try:
            match processor_config:
                case LLMProcessorConfig() as cfg:
                    assert run.o_filepath is not None
                    result = await llm_process_file(run.o_filepath, cfg)
                case None:
                    raise ValueError("No processor config found")
                case _:
                    raise ValueError("Unknown processor method")

            if isinstance(result, ProcessResult):
                filepath = save_result(result, config.PCS_OUTPUT_DIR)
                if filepath:
                    to_process.o_filepath = filepath
                async with session() as s:
                    s.add(to_process)
                    await s.commit()

        except Exception as e:
            log.error(e)
            return False
        except BaseException as e:
            log.error(e)
            raise

    return True
