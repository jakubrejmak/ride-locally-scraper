from datetime import datetime, timedelta, timezone
from logging import getLogger

from croniter import croniter
from sqlalchemy import select, text, update

from ride_locally.db.schema import ScrapeStatus, ScrRunTable, ScrTargetTable
from ride_locally.db.session import session
from ride_locally.models.targets import ScrRun, ScrTarget, ScrTargetConfig

###
# shared claim / release helpers
#
# every worker action is one targeted SQL statement keyed by id. no ORM row
# objects flow across function boundaries; snapshots (ScrTarget / ScrRun)
# are frozen-by-convention and are the only shape workers ever see.
###

log = getLogger(__name__)

# how long to wait before retrying a failed scrape, when the target has no
# cron or when the next cron slot is farther out than this. keeps transient
# failures from waiting a full cron cycle to retry.
_SCRAPE_RETRY_DELAY = timedelta(minutes=5)


async def get_target_config(target_id: int) -> ScrTargetConfig:
    async with session() as s:
        q = select(ScrTargetTable.config).where(ScrTargetTable.id == target_id)
        r = await s.execute(q)
        cfg = r.scalar_one()
    return ScrTargetConfig.model_validate(cfg)


###
# scraper
###


async def claim_scrape_target(worker_id: str) -> ScrTarget | None:
    async with session() as s:
        r = await s.execute(
            text(
                """
                UPDATE scr_targets AS t
                SET claimed_at = now(), claimed_by = :wid
                FROM (
                    SELECT id FROM scr_targets
                    WHERE is_active
                      AND claimed_at IS NULL
                      AND (next_due_at IS NULL OR next_due_at <= now())
                    ORDER BY priority DESC, next_due_at ASC NULLS FIRST
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                ) picked
                WHERE t.id = picked.id
                RETURNING t.*
                """
            ),
            {"wid": worker_id},
        )
        row = r.mappings().one_or_none()
        await s.commit()
    if row is None:
        return None
    return ScrTarget.model_validate(row)


async def release_scrape_target(target: ScrTarget, success: bool) -> None:
    # clear the claim and set the next eligibility instant.
    #   success + cron  -> next cron slot (normal cadence)
    #   success + no cron -> NULL (one-shot done, never reschedules)
    #   failure         -> now + retry delay, OR next cron slot if that is
    #                       sooner (never delay a scheduled slot to accommodate
    #                       a retry).
    now = datetime.now(timezone.utc)
    cron_next = (
        croniter(target.schedule_cron, now).get_next(datetime)
        if target.schedule_cron
        else None
    )

    if success:
        next_due = cron_next
    else:
        retry_at = now + _SCRAPE_RETRY_DELAY
        next_due = min(retry_at, cron_next) if cron_next else retry_at

    async with session() as s:
        await s.execute(
            update(ScrTargetTable)
            .where(ScrTargetTable.id == target.id)
            .values(claimed_at=None, claimed_by=None, next_due_at=next_due)
        )
        await s.commit()


###
# processor
###


async def claim_processor_run(worker_id: str) -> ScrRun | None:
    async with session() as s:
        r = await s.execute(
            text(
                """
                UPDATE scr_runs AS r
                SET claimed_at = now(), claimed_by = :wid
                FROM (
                    SELECT id FROM scr_runs
                    WHERE status = 'pending'
                      AND should_process
                      AND claimed_at IS NULL
                    ORDER BY priority DESC, created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                ) picked
                WHERE r.id = picked.id
                RETURNING r.*
            """
            ),
            {"wid": worker_id},
        )
        row = r.mappings().one_or_none()
        await s.commit()
    if row is None:
        return None
    return ScrRun.model_validate(row)


async def release_processor_run(run_id: int) -> None:
    # status/finished_at were written by run_process. we only unstick the claim.
    async with session() as s:
        await s.execute(
            update(ScrRunTable)
            .where(ScrRunTable.id == run_id)
            .values(claimed_at=None, claimed_by=None)
        )
        await s.commit()


###
# reaper
###


async def reap_stale_claims(threshold_seconds: int) -> int:
    """Release rows whose worker died mid-job. Returns count of rows freed.

    Status rules per table:
      scr_targets: no status column - just clear the claim, trigger fires
                   scr_target_ready NOTIFY.
      scr_runs:    'running' -> 'pending' so it re-enters the claim query.
                   'failed' / 'success' -> claim cleared only, status untouched
                   (never resurrect a terminal state).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=threshold_seconds)
    freed = 0
    async with session() as s:
        r = await s.execute(
            update(ScrTargetTable)
            .where(ScrTargetTable.claimed_at.is_not(None))
            .where(ScrTargetTable.claimed_at < cutoff)
            .values(claimed_at=None, claimed_by=None)
        )
        freed += r.rowcount or 0  # pyright: ignore[reportAttributeAccessIssue]

        # running -> pending: revive stuck in-flight jobs
        r = await s.execute(
            update(ScrRunTable)
            .where(ScrRunTable.claimed_at.is_not(None))
            .where(ScrRunTable.claimed_at < cutoff)
            .where(ScrRunTable.status == ScrapeStatus.running)
            .values(
                claimed_at=None,
                claimed_by=None,
                status=ScrapeStatus.pending,
            )
        )
        freed += r.rowcount or 0  # pyright: ignore[reportAttributeAccessIssue]

        # any other stale-claimed run (pending / failed / success where the
        # release itself crashed) - just unstick the claim, leave status alone.
        r = await s.execute(
            update(ScrRunTable)
            .where(ScrRunTable.claimed_at.is_not(None))
            .where(ScrRunTable.claimed_at < cutoff)
            .where(ScrRunTable.status != ScrapeStatus.running)
            .values(claimed_at=None, claimed_by=None)
        )
        freed += r.rowcount or 0  # pyright: ignore[reportAttributeAccessIssue]

        await s.commit()

    return freed
