import asyncio
from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy import select

from conf import config
from db.schema import ScrapeStatus, ScrRunTable, ScrTargetTable
from db.session import session
from lib.files import diff_results
from models.targets import ScrTargetConfig

###
# shared target utils
###


async def put_or_shutdown(queue: asyncio.Queue, item, shutdown_sig) -> bool:
    """Put `item` into `queue`, but bail out if shutdown is signaled while waiting.

    Returns True if the item was enqueued, False if shutdown won the race.
    """
    put_task = asyncio.create_task(queue.put(item))
    shutdown_task = asyncio.create_task(shutdown_sig.wait())
    try:
        done, _ = await asyncio.wait(
            {put_task, shutdown_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if put_task in done:
            return True
        put_task.cancel()
        return False
    finally:
        shutdown_task.cancel()


###
# scraper
###


async def get_target_config(target_id: int) -> ScrTargetConfig:
    async with session() as s:
        q = select(ScrTargetTable).where(ScrTargetTable.id == target_id)
        r = await s.execute(q)
        result = r.scalar_one()

    return ScrTargetConfig.model_validate(result.config)


def is_due(schedule_cron: str | None, poll_interval: int) -> bool:
    if not schedule_cron:
        return True
    now = datetime.now(timezone.utc)
    cron = croniter(schedule_cron, now)
    prev_run = cron.get_prev(datetime)
    # target is due if its last scheduled time falls within the current poll window
    return (now - prev_run).total_seconds() <= poll_interval


async def get_due_scraper_targets() -> list[ScrTargetTable]:
    """Returns a list of `all` active targets that are due to be scraped."""
    async with session() as s:
        q = (
            select(ScrTargetTable)
            .where(ScrTargetTable.is_active)
            .with_for_update(skip_locked=True)
        )
        res = await s.execute(q)
        active_targets: list[ScrTargetTable] = list(res.scalars().all())

        due_targets = []
        for t in active_targets:
            if is_due(t.schedule_cron, config.SCRAPER_POLL_INTERVAL):
                due_targets.append(t)

    return due_targets


###
# processor
###


def _is_scrape_run_updated(run1: ScrRunTable, run2: ScrRunTable) -> bool:
    # TODO return true if run1 and run2 are different
    pass


async def get_due_processor_targets() -> list[ScrRunTable]:
    """Returns a list of `all` active targets that are due to be processed."""

    async with session() as s:
        q = select(ScrRunTable).where(ScrRunTable.status == ScrapeStatus.pending)
        r = await s.execute(q)
        pending_rows: list[ScrRunTable] = list(r.scalars().all())

    # IMPORTANT - the scrape results viable for processing are the ones where
    # scraped_content[run N] != scraped_content[run N - 1]
    to_process = []
    for run in pending_rows:
        async with session() as s:
            q = (
                select(ScrRunTable)
                .where(ScrRunTable.target_id == run.target_id)
                .where(ScrRunTable.id != run.id)
                .order_by(ScrRunTable.created_at)
                .limit(1)
            )
            r = await s.execute(q)
            prev_run = r.scalar_one_or_none()

        if not prev_run or _is_scrape_run_updated(run, prev_run):
            to_process.append(run)

    return []
