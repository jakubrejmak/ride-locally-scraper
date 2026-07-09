from datetime import datetime, timezone
from typing import Literal

from croniter import croniter
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ride_locally.db.schema import ScrTargetTable
from ride_locally.models.targets import (
    GetTargetsResponse,
    NewScrTarget,
    PatchScrTarget,
    ScrTarget,
)


async def create_target(*, db: AsyncSession, body: NewScrTarget) -> ScrTarget:
    # new targets default to immediately due unless the caller specified
    # next_due_at (e.g. "create this but don't run until midnight").
    next_due = body.next_due_at or datetime.now(timezone.utc)

    row = ScrTargetTable(
        name=body.name,
        url=body.url,
        config=body.config.model_dump(mode="json"),
        is_active=body.is_active,
        schedule_cron=body.schedule_cron,
        carrier_id=body.carrier_id,
        priority=body.priority,
        next_due_at=next_due,
    )

    db.add(row)
    await db.commit()
    await db.refresh(row)

    return ScrTarget.model_validate(row)


async def patch_target(
    *, db: AsyncSession, target_id: int, body: PatchScrTarget
) -> ScrTarget:
    # rejected while claimed - a running scrape's release would clobber the
    # caller's changes on next_due_at. simpler to disallow than to reconcile.
    current = await db.get(ScrTargetTable, target_id)
    if current is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "target not found")
    if current.claimed_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "target is currently being scraped; try again after it finishes",
        )

    patch = body.model_dump(exclude_unset=True)
    if "config" in patch and body.config is not None:
        patch["config"] = body.config.model_dump(mode="json")

    # if schedule_cron changed and the caller didn't also override next_due_at,
    # recompute next_due_at so the new cadence takes effect from now.
    if "schedule_cron" in patch and "next_due_at" not in patch:
        new_cron = patch["schedule_cron"]
        patch["next_due_at"] = (
            croniter(new_cron, datetime.now(timezone.utc)).get_next(datetime)
            if new_cron
            else None
        )

    if patch:
        await db.execute(
            update(ScrTargetTable).where(ScrTargetTable.id == target_id).values(**patch)
        )
        await db.commit()

    refreshed = await db.get(ScrTargetTable, target_id)
    return ScrTarget.model_validate(refreshed)


async def request_run_now(*, db: AsyncSession, target_id: int) -> ScrTarget:
    # single atomic UPDATE: sets next_due_at = now() only if the target is
    # both active and free. trigger fires NOTIFY, next idle worker claims it.
    now = datetime.now(timezone.utc)
    r = await db.execute(
        update(ScrTargetTable)
        .where(ScrTargetTable.id == target_id)
        .where(ScrTargetTable.is_active)
        .where(ScrTargetTable.claimed_at.is_(None))
        .values(next_due_at=now)
        .returning(ScrTargetTable)
    )
    row = r.scalar_one_or_none()
    await db.commit()

    if row is None:
        # figure out why for a useful error message
        existing = await db.get(ScrTargetTable, target_id)
        if existing is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "target not found")
        if not existing.is_active:
            raise HTTPException(status.HTTP_409_CONFLICT, "target is inactive")
        raise HTTPException(
            status.HTTP_409_CONFLICT, "target is currently being scraped"
        )

    return ScrTarget.model_validate(row)


async def list_targets(
    *,
    db: AsyncSession,
    page: int,
    per_page: int,
    search: str | None,
    active: Literal["true", "false", "both"] = "both",
) -> GetTargetsResponse:
    conditions = []

    if active != "both":
        conditions.append(
            ScrTargetTable.is_active == (True if active == "true" else False)
        )

    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        conditions.append(
            or_(
                ScrTargetTable.name.ilike(pattern, escape="\\"),
                ScrTargetTable.url.ilike(pattern, escape="\\"),
            )
        )

    q = (
        select(ScrTargetTable)
        .where(*conditions)
        .order_by(ScrTargetTable.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    total_q = select(func.count()).select_from(ScrTargetTable).where(*conditions)

    rows = (await db.execute(q)).scalars().all()
    total = (await db.execute(total_q)).scalar_one()

    return GetTargetsResponse(
        items=[ScrTarget.model_validate(row) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
    )
