from pydantic import BaseModel
from sqlalchemy import select

from ride_locally.db.schema import ScrTargetTable
from ride_locally.db.session import session
from ride_locally.models.ScraperTargetConfig import ScraperTargetConfig


###
# shared
###


async def get_target_config(target_id: int) -> ScraperTargetConfig:
    async with session() as s:
        q = select(ScrTargetTable.config).where(ScrTargetTable.id == target_id)
        r = await s.execute(q)
        cfg = r.scalar_one()
    return ScraperTargetConfig.model_validate(cfg)


def diff_model_against(
    updated: BaseModel,
        current: BaseModel,
    *,
    columns: set[str] | None = None,
) -> dict:
    """
    Returns fields set on updated that differ from current. Optionally filtered to `columns`
    """
    dumped_updated = updated.model_dump(include=updated.model_fields_set)
    dumped_current = current.model_dump(include=current.model_fields_set)
    if columns is not None:
        dumped_updated = {k: v for k, v in dumped_updated.items() if
                          k in columns}
    return {k: v for k, v in dumped_updated.items() if
            v != dumped_current.get(k)}
