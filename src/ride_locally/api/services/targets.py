from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ride_locally.db.schema import ScrTargetTable
from ride_locally.models.targets import GetTargetsResponse, NewScrTarget, ScrTarget


def _to_model(row: ScrTargetTable) -> ScrTarget:
    return ScrTarget(
        id=row.id,
        name=row.name,
        url=row.url,
        config=row.config,
        is_active=row.is_active,
        schedule_cron=row.schedule_cron,
        carrier_id=row.carrier_id,
    )


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

    return _to_model(row)


async def list_targets(
    *,
    db: AsyncSession,
    page: int,
    per_page: int,
    search: str | None,
    is_active: bool | None,
) -> GetTargetsResponse:
    q = select(ScrTargetTable)
    total_q = select(func.count()).select_from(ScrTargetTable)

    if is_active is not None:
        q = q.where(ScrTargetTable.is_active == is_active)
        total_q = total_q.where(ScrTargetTable.is_active == is_active)

    if search:
        search_pattern = f"%{search}%"
        search_filter = or_(
            ScrTargetTable.name.ilike(search_pattern),
            ScrTargetTable.url.ilike(search_pattern),
        )
        q = q.where(search_filter)
        total_q = total_q.where(search_filter)

    row_offset = (page - 1) * per_page
    q = q.order_by(ScrTargetTable.id.desc()).offset(row_offset).limit(per_page)

    rows = (await db.execute(q)).scalars().all()
    total = (await db.execute(total_q)).scalar_one()

    return GetTargetsResponse(
        items=[_to_model(row) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
    )
