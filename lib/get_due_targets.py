from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from db.schema import ttScrTargetTable
from croniter import croniter
from datetime import datetime, timezone
from conf import config
from db.session import session

def is_due(schedule_cron: str | None, poll_interval: int) -> bool:
    if not schedule_cron:
        return True
    now = datetime.now(timezone.utc)
    cron = croniter(schedule_cron, now)
    prev_run = cron.get_prev(datetime)
    # target is due if its last scheduled time falls within the current poll window
    return (now - prev_run).total_seconds() <= poll_interval


async def get_due_targets() -> list[ttScrTargetTable]:
    async with session() as s:
        q = select(ttScrTargetTable).where(ttScrTargetTable.is_active).with_for_update(skip_locked=True)
        res = await s.execute(q)
        active_targets: list[ttScrTargetTable] = list(res.scalars().all())

        due_targets = []
        for t in active_targets:
            if is_due(t.schedule_cron, config.SRC_T_POLL_INTERVAL):
                due_targets.append(t)

    return due_targets
