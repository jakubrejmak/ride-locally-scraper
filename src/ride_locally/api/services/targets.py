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
    is_active: bool | None,
) -> GetTargetsResponse:
    conditions = []

    if is_active is not None:
        conditions.append(ScrTargetTable.is_active == is_active)

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
