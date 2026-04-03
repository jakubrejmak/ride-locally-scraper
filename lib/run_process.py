###
#   Processor module parses the output of scraping module by
#   either static analysis or with the help of the llm
###

import asyncio
from contextlib import nullcontext
from datetime import UTC, datetime
from logging import getLogger

from sqlalchemy import select

from conf import config
from db.schema import ProcessStatus, ttScrProcessedTable, ttScrRunTable
from db.session import session
from lib.files import read_result, save_result
from lib.processors.preprocess import preprocess_file
from lib.processors.process_llm import llm_process_file
from lib.target_utils import get_target_config
from models.files import ProcessResult, ScrRunResult
from models.processors import LLMProcessorConfig

log = getLogger(__name__)


async def _get_existing_processed(run_id: int) -> ttScrProcessedTable | None:
    async with session() as s:
        q = select(ttScrProcessedTable).where(ttScrProcessedTable.run_id == run_id)
        resp = await s.execute(q)
        result = resp.scalar_one_or_none()
    return result


async def _get_process_row(run: ttScrRunTable) -> ttScrProcessedTable:
    to_process = await _get_existing_processed(run.id)
    if not to_process:
        to_process = ttScrProcessedTable(
            run_id=run.id,
            target_id=run.target_id,
            o_filepath=None,
            started_at=datetime.now(UTC),
        )

    to_process.status = ProcessStatus.running

    async with session() as s:
        s.add(to_process)
        await s.commit()

    return to_process


async def _mark_as_error(run: ttScrProcessedTable, message: str | None):
    async with session() as s:
        run.status = ProcessStatus.failed
        run.finished_at = datetime.now(UTC)
        run.error_message = message
        s.add(run)
        await s.commit()


async def run_process(
    run: ttScrRunTable,
    stop_condition: asyncio.Event | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> bool:
    """Takes a ttScrRunTable row, processes its output file and saves the result to ttScrProcessedTable"""
    if stop_condition and stop_condition.is_set():
        return False

    if run.o_filepath is None:
        raise ValueError(f"Scrape run: '{run.id}' has no output filepath to process")

    async with semaphore or nullcontext():
        # in contrast to allowing multiple runs per target there needs to be exactly one process per run, hence the get existing function
        to_process = await _get_process_row(run)

        try:
            target_config = await get_target_config(run.target_id)
            scr_result = read_result(run.o_filepath, ScrRunResult)
            if not scr_result:
                raise Exception(
                    f"read_result could not read valid result data from path: '{run.o_filepath}'"
                )

            # if preprocessor is configured, run it to transform scr_result before feeding to actual processor
            if target_config.preprocessor is not None:
                scr_result = await preprocess_file(
                    scr_result, target_config.preprocessor
                )
                if not scr_result:
                    raise Exception("Preprocessor could not produce valid result data")

            # process scr_result into statically parseable output
            match target_config.processor:
                case LLMProcessorConfig() as cfg:
                    result = await llm_process_file(scr_result, cfg)
                case None:
                    raise ValueError("No processor config found")
                case _:
                    raise ValueError("Unknown processor method")

            if not isinstance(result, ProcessResult):
                raise ValueError("Processor did not return a valid ProcessResult")

            filepath = save_result(result, config.PCS_OUTPUT_DIR)
            if not filepath:
                raise ValueError("Processor result did not produce any output files")

            async with session() as s:
                to_process.status = ProcessStatus.success
                to_process.finished_at = datetime.now(UTC)
                to_process.o_filepath = filepath
                await s.commit()

        except Exception as e:
            log.error(e)
            await _mark_as_error(to_process, str(e))
            return False
        except BaseException as e:
            log.error(e)
            await _mark_as_error(to_process, str(e))
            raise

    return True
