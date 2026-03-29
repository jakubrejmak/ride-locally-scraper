###
#   Processor module parses the output of scraping module by
#   either static analysis or with the help of the llm
###

import asyncio
from contextlib import nullcontext
from logging import getLogger

from sqlalchemy import select

from conf import config
from db.schema import ttScrProcessedTable, ttScrRunTable, ttScrTargetTable
from db.session import session
from lib.files import save_result
from lib.processors.process_llm import llm_process_file
from models.files import ProcessResult
from models.processors import LLMProcessorConfig

log = getLogger(__name__)


async def _get_existing_processed(run: ttScrRunTable) -> ttScrProcessedTable | None:
    async with session() as s:
        q = select(ttScrProcessedTable).where(ttScrProcessedTable.run_id == run.id)
        resp = await s.execute(q)
        return resp.scalar_one_or_none()


async def _save_processed_output(run: ttScrRunTable, filepath: str) -> ttScrProcessedTable:
    processed = await _get_existing_processed(run)
    if processed is None:
        processed = ttScrProcessedTable(
            run_id=run.id,
            target_id=run.target_id,
            o_filepath=filepath,
            version=1
        )
    else:
        processed.o_filepath = filepath
        processed.version += 1

    async with session() as s:
        s.add(processed)
        await s.commit()

    return processed


async def run_process(
    run: ttScrRunTable,
    stop_condition: asyncio.Event | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> bool:
    """Takes a ttScrRunTable row, processes its output file and saves the result to ttScrProcessedTable"""
    if stop_condition and stop_condition.is_set():
        return False

    async with semaphore or nullcontext():
        try:
            async with session() as s:
                
            target_config = await _get_target_config(run.target_id)

            if target_config.preprocessor is not None:
                raise NotImplementedError("Preprocessor pipeline is not implemented yet")

            if run.o_filepath is None:
                raise ValueError("Scrape run has no output filepath to process")

            match target_config.processor:
                case LLMProcessorConfig() as cfg:
                    result = await llm_process_file(run.o_filepath, cfg)
                case None:
                    raise ValueError("No processor config found")
                case _:
                    raise ValueError("Unknown processor method")

            if not isinstance(result, ProcessResult):
                raise ValueError("Processor did not return a valid ProcessResult")

            filepath = save_result(result, config.PCS_OUTPUT_DIR)
            if not filepath:
                raise ValueError("Processor result did not produce any output files")

            await _save_processed_output(run, filepath)

        except Exception as e:
            log.error(e)
            return False
        except BaseException as e:
            log.error(e)
            raise

    return True
