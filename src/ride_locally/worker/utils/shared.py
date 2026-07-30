from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select

from ride_locally.config import config
from ride_locally.db.schema import ScrTargetTable
from ride_locally.db.session import session
from ride_locally.models.targets import ScrTargetConfig

###
# shared
###


async def get_target_config(target_id: int) -> ScrTargetConfig:
    async with session() as s:
        q = select(ScrTargetTable.config).where(ScrTargetTable.id == target_id)
        r = await s.execute(q)
        cfg = r.scalar_one()
    return ScrTargetConfig.model_validate(cfg)


def diff_model_against(
    updated: BaseModel,
    current: dict,
    *,
    columns: set[str] | None = None,
) -> dict:
    """
    Returns fields where updated differs from current. Optionally filtered to `columns`
    """
    dumped = updated.model_dump()
    if columns is not None:
        dumped = {k: v for k, v in dumped.items() if k in columns}
    return {k: v for k, v in dumped.items() if v != current.get(k)}


def get_prompt_by_filename(
    type: Literal["preprocessor", "processor"], filename: str
) -> str:

    match type:
        case "preprocessor":
            search_dir = Path(config.PREPROCESSOR_PROMPTS_DIR)
        case "processor":
            search_dir = Path(config.PROCESSOR_PROMPTS_DIR)

    file = search_dir / filename

    if not file.is_file():
        raise FileNotFoundError(f"{file} not found")

    return file.read_text(encoding="utf-8")
