###
#   scraper service
###

from datetime import datetime, timezone
from logging import getLogger
from logging.handlers import RotatingFileHandler

from sqlalchemy import insert, select, update

from ride_locally.config import config
from ride_locally.db.schema import ScrapeStatus, ScrRunTable, ScrTargetTable
from ride_locally.db.session import session
from ride_locally.models.files import FileResult
from ride_locally.models.scrapers import FirecrawlConfig, ScraplingConfig
from ride_locally.models.targets import NewScrTarget, ScrScriptResult, ScrTarget
from ride_locally.worker.files import diff_file_results, save_result
from ride_locally.worker.scrapers.run_firecrawl import run_firecrawl
from ride_locally.worker.scrapers.run_scrapling import run_scrapling

log = getLogger(__name__)
log.addHandler(
    RotatingFileHandler(
        f"{config.LOG_DIR}/scraper.log", mode="a", maxBytes=10_000_000, backupCount=5
    )
)


# columns settable on scr_targets from a NewScrTarget payload. excludes id
# (autoincrement) and created_at/updated_at (server-managed). config is a
# pydantic model - .model_dump() serializes it to the dict JSONB expects.
_NEW_TARGET_COLS = {
    "name",
    "url",
    "config",
    "is_active",
    "schedule_cron",
    "carrier_id",
    "priority",
    "next_due_at",
}


def _target_values(new: NewScrTarget) -> dict:
    # pydantic already validated types + lengths at NewScrTarget construction,
    # so no runtime re-checks needed. dump only DB-writable columns.
    data = new.model_dump()
    return {k: data[k] for k in _NEW_TARGET_COLS if k in data}


async def _get_prev_run_filepath(target_id: int, exclude_run_id: int) -> str | None:
    # most recent finished run for this target, other than the one we just
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


async def handle_self_update(
    target: ScrTarget, self_update: NewScrTarget | None
) -> dict | None:
    # a scraper script may return a NewScrTarget describing how it wants its
    # own row updated (e.g. discovered a new URL for the same source). we
    # compute a diff against the snapshot we have in hand, then issue one
    # targeted UPDATE. no re-fetch, no ORM mutation.
    if self_update is None:
        return None

    new_vals = _target_values(self_update)
    current = target.model_dump()

    diff = {}
    for field, new_val in new_vals.items():
        cur_val = current.get(field)
        if cur_val != new_val:
            diff[field] = {"current": cur_val, "new": new_val}

    if not diff:
        return None

    async with session() as s:
        await s.execute(
            update(ScrTargetTable)
            .where(ScrTargetTable.id == target.id)
            .values(**{k: new_vals[k] for k in diff})
        )
        await s.commit()

    return diff


async def handle_new_targets(
    new_targets: list[NewScrTarget] | None,
) -> tuple[list[NewScrTarget], list[NewScrTarget]]:
    # scraper scripts can spawn new targets (e.g. crawler-style discovery).
    # each insert is isolated so a single bad row doesn't drop the batch.
    if not new_targets:
        return [], []

    added: list[NewScrTarget] = []
    failed: list[NewScrTarget] = []
    now = datetime.now(timezone.utc)

    for t in new_targets:
        try:
            vals = _target_values(t)
            # new targets become immediately due unless the payload set
            # next_due_at explicitly. matches the "create -> run soon" UX.
            vals.setdefault("next_due_at", now)
            async with session() as s:
                await s.execute(insert(ScrTargetTable).values(**vals))
                await s.commit()
            added.append(t)
        except Exception:
            log.error(f"failed to create target: {t}")
            failed.append(t)

    return added, failed


async def _insert_run(target: ScrTarget) -> int:
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
                should_process=True,  # provisional; finalized on success
            )
            .returning(ScrRunTable.id)
        )
        run_id = r.scalar_one()
        await s.commit()
    return run_id


async def _mark_run_success(
    run_id: int, o_filepath: str | None, should_process: bool
) -> None:
    async with session() as s:
        await s.execute(
            update(ScrRunTable)
            .where(ScrRunTable.id == run_id)
            .values(
                status=ScrapeStatus.success,
                finished_at=datetime.now(timezone.utc),
                o_filepath=o_filepath,
                should_process=should_process,
            )
        )
        await s.commit()


async def _mark_run_error(run_id: int, message: str | None) -> None:
    async with session() as s:
        await s.execute(
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


async def run_scrape(target: ScrTarget) -> bool:
    """Takes a target snapshot and records its result to scr_runs."""

    log.info(
        f"started scrape for target: {target.name or target.id} at "
        f"{datetime.now(timezone.utc)}"
    )

    run_id = await _insert_run(target)

    try:
        match target.config.scraper:
            case FirecrawlConfig() as scraper:
                result = await run_firecrawl(target.url, scraper)
            case ScraplingConfig() as scraper:
                result = await run_scrapling(target.url, scraper)
            case _:
                raise ValueError("No scrape method provided")

        o_filepath: str | None = None

        if isinstance(result, FileResult):
            if result:
                o_filepath = save_result(result, config.SCRAPER_OUTPUT_DIR)
        elif isinstance(result, ScrScriptResult):
            await handle_self_update(target, result.self_update)
            await handle_new_targets(result.new_targets)
            if result.run_result:
                o_filepath = save_result(result.run_result, config.SCRAPER_OUTPUT_DIR)

        # decide should_process now, so the processor never has to diff at pop time.
        # rules: no output -> nothing to process.
        #        no previous output -> first run for this target, process it.
        #        otherwise -> process only if content changed.
        should_process = False
        if o_filepath:
            prev = await _get_prev_run_filepath(target.id, run_id)
            if prev is None:
                should_process = True
            else:
                try:
                    should_process = diff_file_results(o_filepath, prev)
                except Exception:
                    # if the diff itself fails (unreadable prev file etc.),
                    # err on the side of processing rather than silently skipping.
                    log.exception(f"diff failed for run {run_id}, defaulting to process")
                    should_process = True

        await _mark_run_success(run_id, o_filepath, should_process)

        log.info(
            f"finished scrape for target: {target.name or target.id} at "
            f"{datetime.now(timezone.utc)}"
        )

    except Exception as e:
        log.error(e)
        await _mark_run_error(run_id, str(e))
        return False
    except BaseException as e:
        log.error(e)
        await _mark_run_error(run_id, str(e))
        raise

    return True
