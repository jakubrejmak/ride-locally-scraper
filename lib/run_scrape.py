###
#   scraper service
###

import asyncio
import uuid
from pathlib import Path
from datetime import datetime, UTC
from sqlalchemy import select, update, insert
from db.schema import ttScrTargetTable, ttScrRunTable, ScrapeStatus
from db.session import session
from contextlib import nullcontext
from models.types import ScrTargetConfig, ScrTargetResult, ScrScriptResult, NewScrTarget
from lib.scrapers.run_firecrawl import run_firecrawl
from lib.scrapers.run_scrapling import run_scrapling
from logging import getLogger

log = getLogger(__file__)

SCR_OUTPUT_DIR = Path(__file__).parent.parent / "output_files" / "o_scraper"


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
                raise ValueError(f"Field '{field}': length {len(val)} exceeds max {col.type.length}")  # type: ignore[union-attr]

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
        await s.flush()

    return diff if diff else None


async def handle_new_targets(new_targets: list[NewScrTarget] | None) -> tuple[list[NewScrTarget], list[NewScrTarget]]:
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
        await s.flush()

    return added, failed


def save_result(result: ScrTargetResult | None) -> str | None:
    SCR_OUTPUT_DIR.mkdir(exist_ok=True)

    if result is None or len(result.data) < 1:
        return None
    elif len(result.data) == 1:
        file = Path(SCR_OUTPUT_DIR) / f"{uuid.uuid4().hex}.{result.data[0].ext}"
        with open(file, "wb") as f:
            f.write(result.data[0].bytes)
        return str(file.absolute())
    else:
        outdir = Path(SCR_OUTPUT_DIR) / f"{uuid.uuid4().hex}"
        Path(outdir).mkdir(parents=True, exist_ok=True)
        for d in result.data:
            file = outdir / f"{uuid.uuid4().hex}.{d.ext}"
            with open(file, "wb") as f:
                f.write(d.bytes)
        return str(outdir.absolute())


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
        run.started_at = datetime.now(UTC)
        async with session() as s:
            s.add(run)
            await s.flush()

        try:
            config = ScrTargetConfig.model_validate(target.config)

            match config.scrape_method:
                case "firecrawl":
                    assert config.firecrawl_conf
                    result = await run_firecrawl(target.url, config.firecrawl_conf)
                case "scrapling":
                    assert config.scrapling_conf
                    result = await run_scrapling(target.url, config.scrapling_conf)
                case _:
                    raise ValueError("No scrape method provided")

            if isinstance(result, ScrTargetResult):
                # save the file and point the DB to its location
                filepath = save_result(result)
                run.o_filepath = filepath
            elif isinstance(result, ScrScriptResult):
                # modify current target
                await handle_self_update(target, result.self_update)
                # add new targets to session
                await handle_new_targets(result.new_targets)
                # save the file and point the DB to its location
                filepath = save_result(result.run_result)
                run.o_filepath = filepath

            async with session() as s:
                run.status = ScrapeStatus.success
                run.finished_at = datetime.now(UTC)
                s.add(run)
                await s.flush()

        except Exception as e:
            log.error(e)
            async with session() as s:
                run.status = ScrapeStatus.failed
                run.finished_at = datetime.now(UTC)
                run.error_message = str(e)
                s.add(run)
                await s.flush()
            return False

    return True
