###
#   Processor module parses the output of scraping module by
#   either static analysis or with the help of the llm
###

from datetime import datetime, timezone
from logging import getLogger

from sqlalchemy import insert, select, update

from ride_locally.config import config
from ride_locally.db.schema import ProcessStatus, ScrProcessedTable
from ride_locally.db.session import session
from ride_locally.models.ScraperRun import ScrRun
from ride_locally.models.files import FileResult
from ride_locally.models.processors import LLMProcessorConfig
from ride_locally.worker.files import read_result, save_result
from ride_locally.worker.preprocessor.preprocess import preprocess_file
from ride_locally.worker.processors.process_llm import llm_process_files
from ride_locally.worker.utils.shared import get_target_config

log = getLogger(__name__)


async def _get_or_create_processed(run: ScrRun) -> int:
    # exactly one processed row per run. if a previous attempt crashed we
    # reuse the same row rather than piling up siblings.
    async with session() as s:
        q = select(ScrProcessedTable.id).where(ScrProcessedTable.run_id == run.id)
        r = await s.execute(q)
        existing = r.scalar_one_or_none()

        if existing is not None:
            await s.execute(
                update(ScrProcessedTable)
                .where(ScrProcessedTable.id == existing)
                .values(
                    status=ProcessStatus.running,
                    started_at=datetime.now(timezone.utc),
                    error_message=None,
                )
            )
            await s.commit()
            return existing

        r = await s.execute(
            insert(ScrProcessedTable)
            .values(
                run_id=run.id,
                target_id=run.target_id,
                status=ProcessStatus.running,
                started_at=datetime.now(timezone.utc),
                o_filepath=None,
            )
            .returning(ScrProcessedTable.id)
        )
        new_id = r.scalar_one()
        await s.commit()
        return new_id


async def _mark_success(processed_id: int, o_filepath: str) -> None:
    async with session() as s:
        await s.execute(
            update(ScrProcessedTable)
            .where(ScrProcessedTable.id == processed_id)
            .values(
                status=ProcessStatus.success,
                finished_at=datetime.now(timezone.utc),
                o_filepath=o_filepath,
            )
        )
        await s.commit()


async def _mark_error(processed_id: int, message: str | None) -> None:
    async with session() as s:
        await s.execute(
            update(ScrProcessedTable)
            .where(ScrProcessedTable.id == processed_id)
            .values(
                status=ProcessStatus.failed,
                finished_at=datetime.now(timezone.utc),
                error_message=message,
            )
        )
        await s.commit()


async def run_process(run: ScrRun) -> bool:
    """Takes a run snapshot, processes its output file, records to scr_processed."""
    if run.o_filepath is None:
        raise ValueError(f"scrape run: '{run.id}' has no output filepath to process")

    processed_id = await _get_or_create_processed(run)

    try:
        target_config = await get_target_config(run.target_id)
        scr_result = read_result(run.o_filepath, FileResult)
        if not scr_result:
            raise Exception(
                f"read_result could not read valid result data from path: '{run.o_filepath}'"
            )

        # if preprocessor is configured, run it to transform scr_result before feeding to actual processor
        if target_config.preprocessor is not None:
            scr_result = await preprocess_file(scr_result, target_config.preprocessor)
            if not scr_result:
                raise Exception("Preprocessor could not produce valid result data")

        # process scr_result into statically parseable output
        match target_config.processor:
            case LLMProcessorConfig() as cfg:
                results = await llm_process_files(scr_result, cfg)
            case None:
                raise ValueError("No processor config found")
            case _:
                raise ValueError("Unknown processor method")

        if not isinstance(results, FileResult):
            raise ValueError("Processor did not return a valid FileResult")

        filepath = save_result(results, config.PROCESSOR_OUTPUT_DIR)
        if not filepath:
            raise ValueError("Processor result did not produce any output files")

        await _mark_success(processed_id, filepath)

    except Exception as e:
        log.error(e)
        await _mark_error(processed_id, str(e))
        return False
    except BaseException as e:
        log.error(e)
        await _mark_error(processed_id, str(e))
        raise

    return True
