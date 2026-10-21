###
#   scraper service
###

from datetime import datetime, timezone
from logging import getLogger
from logging.handlers import RotatingFileHandler
from typing import Any

from sqlalchemy import insert, select, update

from ride_locally.config import config
from ride_locally.db.schema import ScrapeStatus, ScrRunTable
from ride_locally.db.session import session
from ride_locally.models.FirecrawlConfig import FirecrawlConfig
from ride_locally.models.ScraperScriptResult import ScrScriptResult
from ride_locally.models.ScraperTarget import ScrapeTarget
from ride_locally.models.ScraplingConfig import ScraplingScriptConfig, \
    ScraplingSimpleConfig
from ride_locally.models.files import FileResult
from ride_locally.worker.files import diff_file_results, save_result, \
    FileOperationException
from ride_locally.worker.scrapers.run_firecrawl import run_firecrawl
from ride_locally.worker.scrapers.run_scrapling import run_scrapling
from ride_locally.worker.utils.scr_target_utils import (
    update_scr_target,
)

log = getLogger(__name__)
log.addHandler(
    RotatingFileHandler(
        f"{config.LOG_DIR}/scraper.log", mode="a", maxBytes=10_000_000,
        backupCount=5
    )
)


async def _get_prev_run_filepath(target_id: int,
                                 exclude_run_id: int) -> str | None:
    # the most recent finished run for this target, other than the one we just
    # created. used to decide should_process = (files differ).
    async with session() as s:
        q = (
            select(ScrRunTable.o_filepath)
            .where(ScrRunTable.target_id == target_id)
            .where(ScrRunTable.id != exclude_run_id)
            .where(ScrRunTable.o_filepath.is_not(None))
            .order_by(ScrRunTable.created_at.desc())
            .limit(1)
        )
        r = await s.execute(q)
        return r.scalar_one_or_none()


async def _insert_run(target: ScrapeTarget) -> int:
    # returning: run.id. priority is denormalized from the target so the
    # processor's claim query can order by priority without joining.
    async with session() as s:
        r = await s.execute(
            insert(ScrRunTable)
            .values(
                target_id=target.id,
                status=ScrapeStatus.running,
                priority=target.priority,
                started_at=datetime.now(timezone.utc),
                should_process=False,  # provisional; finalized on success
            )
            .returning(ScrRunTable.id)
        )
        run_id = r.scalar_one()
        await s.commit()
    return run_id


async def _mark_run_success(
        run_id: int, o_filepath: str | None, should_process: bool,
        run_meta: dict[str, Any] | None
) -> None:
    async with session() as s:
        _ = await s.execute(
            update(ScrRunTable)
            .where(ScrRunTable.id == run_id)
            .values(
                status=ScrapeStatus.success,
                finished_at=datetime.now(timezone.utc),
                o_filepath=o_filepath,
                should_process=should_process,
                meta=run_meta,
            )
        )
        await s.commit()


async def _mark_run_error(run_id: int, message: str | None) -> None:
    async with session() as s:
        _ = await s.execute(
            update(ScrRunTable)
            .where(ScrRunTable.id == run_id)
            .values(
                status=ScrapeStatus.failed,
                finished_at=datetime.now(timezone.utc),
                error_message=message,
                should_process=False,
            )
        )
        await s.commit()


async def run_scrape(target: ScrapeTarget) -> bool:
    """Takes a target snapshot and records its result to scr_runs."""

    log.info(
        f"Started scrape for target: {target.name or target.id} at {datetime.now(timezone.utc)}"
    )

    run_id = await _insert_run(target)

    try:
        match target.config.scraper:
            case FirecrawlConfig() as scraper:
                result = await run_firecrawl(target.url, scraper)

            case ScraplingSimpleConfig() | ScraplingScriptConfig() as scraper:
                result = await run_scrapling(target.url, scraper)

            case _:
                raise ValueError("No scrape method provided")

        o_filepath: str | None = None
        run_meta: dict[str, Any] | None = None

        if isinstance(result, FileResult):
            if result:
                o_filepath = save_result(result, config.SCRAPER_OUTPUT_DIR)

        elif isinstance(result, ScrScriptResult):
            if result.self_update:
                _ = await update_scr_target(target, result.self_update)

            if result.run_file_result:
                o_filepath = save_result(
                    result.run_file_result, config.SCRAPER_OUTPUT_DIR
                )

            run_meta = result.run_meta

        """
        Mark scraper run row with `should_process` flag depending on Scraper output.
        For runs that returned `None` the `should_process` is always False
        """
        should_process = False
        if o_filepath:
            prev = await _get_prev_run_filepath(target.id, run_id)
            if prev is None:
                # if there is no previous run - nothing to diff against -> should_process = True
                should_process = True
            else:
                try:
                    # if previous run exists, diff against current one - if they differ -> should_process = True
                    should_process = diff_file_results(o_filepath, prev)
                except FileOperationException:
                    # if the diff itself fails (unreadable prev file etc.) -> should_process = True
                    log.exception(
                        f"diff failed for run {run_id}, defaulting to should_process = True"
                    )
                    should_process = True

        await _mark_run_success(run_id, o_filepath, should_process, run_meta)

        log.info(
            f"""finished scrape for target: {target.name or target.id} at
            {datetime.now(timezone.utc)}"""
        )

    except Exception as e:
        log.exception(e)
        await _mark_run_error(run_id, str(e))
        return False
    except BaseException as e:
        log.exception(e)
        await _mark_run_error(run_id, str(e))
        raise

    return True
