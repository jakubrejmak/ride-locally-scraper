###
#   scraper service
###

import asyncio
from contextlib import nullcontext
from datetime import UTC, datetime
from logging import getLogger

from db.schema import ScrapeStatus, ttScrRunTable, ttScrTargetTable
from db.session import session
from conf import config
from lib.files import save_result
from lib.scrapers.run_firecrawl import run_firecrawl
from lib.scrapers.run_scrapling import run_scrapling
from models.files import ScrRunResult
from models.scrapers import FirecrawlConfig, ScraplingConfig
from models.targets import NewScrTarget, ScrScriptResult, ScrTargetConfig

log = getLogger(__file__)


def new_target_to_row(new_target: NewScrTarget) -> ttScrTargetTable:
    data = new_target.model_dump()
    mapper = ttScrTargetTable.__table__.columns

    for field, val in data.items():
        if field not in mapper:
            raise ValueError(f"Field '{field}' does not exist on ttScrTargetTable")
        col = mapper[field]
        expected = col.type.python_type
        if val is None:
            if not col.nullable:
                raise ValueError(f"Field '{field}' is not nullable")
            continue
        if not isinstance(val, expected):
            raise TypeError(
                f"Field '{field}': expected {expected.__name__}, got {type(val).__name__}"
            )
        if hasattr(col.type, "length") and col.type.length and isinstance(val, str):  # type: ignore[union-attr]
            if len(val) > col.type.length:  # type: ignore[union-attr]
                raise ValueError(
                    f"Field '{field}': length {len(val)} exceeds max {col.type.length}"  # type: ignore[union-attr]
                )

    return ttScrTargetTable(**data)


async def handle_self_update(
    target: ttScrTargetTable, self_update: NewScrTarget | None
) -> dict | None:
    if self_update is None:
        return None

    validated = new_target_to_row(self_update)
    fields = [
        c.key
        for c in ttScrTargetTable.__table__.columns
        if c.key not in ("id", "created_at", "updated_at")
    ]

    diff = {}
    for field in fields:
        current_val = getattr(target, field)
        new_val = getattr(validated, field)
        if current_val != new_val:
            diff[field] = {"current": current_val, "new": new_val}
            setattr(target, field, new_val)

    async with session() as s:
        s.add(target)
        await s.commit()

    return diff if diff else None


async def handle_new_targets(
    new_targets: list[NewScrTarget] | None,
) -> tuple[list[NewScrTarget], list[NewScrTarget]]:
    if new_targets is None:
        return [], []

    added: list[NewScrTarget] = []
    failed: list[NewScrTarget] = []
    async with session() as s:
        for t in new_targets:
            try:
                row = new_target_to_row(t)
                s.add(row)
                added.append(t)
            except Exception:
                log.error(f"Failed to create target: {t}")
                failed.append(t)
        await s.commit()

    return added, failed


async def _mark_as_error(run: ttScrRunTable, message: str | None):
    async with session() as s:
        run.status = ScrapeStatus.failed
        run.finished_at = datetime.now(UTC)
        run.error_message = message
        s.add(run)
        await s.commit()


async def run_scrape(
    target: ttScrTargetTable,
    stop_condition: asyncio.Event | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> bool:
    """Takes a target and saves its result to ttScrRunTable"""
    if stop_condition and stop_condition.is_set():
        return False
    async with semaphore or nullcontext():
        # create run row in ttScrRunTable and save the result into its output
        run = ttScrRunTable(target_id=target.id)
        run.status = ScrapeStatus.pending
        run.started_at = datetime.now(UTC)
        async with session() as s:
            s.add(run)
            await s.commit()

        try:
            target_config = ScrTargetConfig.model_validate(target.config)

            match target_config.scraper:
                case FirecrawlConfig() as scraper:
                    result = await run_firecrawl(target.url, scraper)
                case ScraplingConfig() as scraper:
                    result = await run_scrapling(target.url, scraper)
                case _:
                    raise ValueError("No scrape method provided")

            if isinstance(result, ScrRunResult):
                # save the file and point the DB to its location
                if result:
                    filepath = save_result(result, config.SCR_OUTPUT_DIR)
                    run.o_filepath = filepath
            elif isinstance(result, ScrScriptResult):
                # modify current target
                await handle_self_update(target, result.self_update)
                # add new targets to session
                await handle_new_targets(result.new_targets)
                # save the file and point the DB to its location
                if result.run_result:
                    filepath = save_result(result.run_result, config.SCR_OUTPUT_DIR)
                    run.o_filepath = filepath

            async with session() as s:
                run.status = ScrapeStatus.success
                run.finished_at = datetime.now(UTC)
                s.add(run)
                await s.commit()

        except Exception as e:
            log.error(e)
            await _mark_as_error(run, str(e))
            return False
        except BaseException as e:
            log.error(e)
            await _mark_as_error(run, str(e))
            raise

    return True
