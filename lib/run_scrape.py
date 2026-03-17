###
#   scraper service
###

from sqlalchemy.ext.asyncio import AsyncEngine
from db.schema import ttScrTargetTable, ttScrRunTable
import asyncio
from contextlib import nullcontext
from db.session import session
from models.types import ScrTargetConfig, ScrTargetResult, ScrScriptResult

async def save_result(result: ScrTargetResult | ScrScriptResult) -> bool:
    if not result:
        return False
    return True

async def run_scrape(
    target: ttScrTargetTable,
    stop_condition: asyncio.Event | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> bool:
    """Takes a target and saves its result to ttScrRunTable"""
    if stop_condition and stop_condition.is_set():
        return False
    async with semaphore or nullcontext():
        config = ScrTargetConfig.model_validate(target.config)
        match config.scrape_method:
            case "firecrawl":
                from lib.scrapers.run_firecrawl import run_firecrawl
                assert config.firecrawl_conf
                result = await run_firecrawl(target.url, config.firecrawl_conf)
            case "scrapling":
                from lib.scrapers.run_scrapling import run_scrapling
                assert config.scrapling_conf
                result = await run_scrapling(target.url, config.scrapling_conf)
        if result:
            await save_result(result)
    return True
