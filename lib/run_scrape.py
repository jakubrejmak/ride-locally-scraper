###
#   scraper service
###

import asyncio
from pydantic import ValidationError
from datetime import datetime, UTC
from sqlalchemy import select
from db.schema import ttScrTargetTable, ttScrRunTable, ScrapeStatus
from contextlib import nullcontext
from db.session import session
from models.types import ScrTargetConfig, ScrTargetResult, ScrScriptResult
from logging import getLogger

log = getLogger(__file__)

async def handle_self_update(script_result: ScrScriptResult | None) -> str | None:
    return None

async def handle_new_targets(script_result: ScrScriptResult | None) -> str | None:
    return None

async def save_result(result: ScrTargetResult | None) -> str | None:
    return None


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
        async with session() as s:
            s.add(run)

        try:
            config = ScrTargetConfig.model_validate(target.config)
            run.started_at = datetime.now(UTC)

            match config.scrape_method:
                case "firecrawl":
                    from lib.scrapers.run_firecrawl import run_firecrawl
                    assert config.firecrawl_conf
                    result = await run_firecrawl(target.url, config.firecrawl_conf)
                case "scrapling":
                    from lib.scrapers.run_scrapling import run_scrapling
                    assert config.scrapling_conf
                    result = await run_scrapling(target.url, config.scrapling_conf)

            if isinstance(result, ScrTargetResult):
                filepath = await save_result(result)
                run.o_filepath = filepath
            if isinstance(result, ScrScriptResult):
                await handle_self_update(result)
                await handle_new_targets(result)
                filepath = await save_result(result.run_result)

        except Exception as e:
            log.error(e)
            run.status = ScrapeStatus.failed
            run.error_message = str(e)
            return False
        finally:
            async with session() as s:
                await s.flush()

    return True
