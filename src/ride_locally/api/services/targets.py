from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ride_locally.db.schema import ScrTargetTable
from ride_locally.models.targets import GetTargetsResponse, NewScrTarget, ScrTarget


async def create_target(*, db: AsyncSession, body: NewScrTarget) -> ScrTarget:
    row = ScrTargetTable(
        name=body.name,
        url=body.url,
        config=body.config.model_dump(mode="json"),
        is_active=body.is_active,
        schedule_cron=body.schedule_cron,
        carrier_id=body.carrier_id,
    )

    db.add(row)
    await db.commit()
    await db.refresh(row)

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
        conditions.append(ScrTargetTable.is_active == (True if active == "true" else False))

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
