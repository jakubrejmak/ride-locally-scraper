from pathlib import Path

from fastapi import APIRouter, HTTPException

from ride_locally.api.deps.get_user import user_id_dep
from ride_locally.config import config

router = APIRouter(
    prefix="/scripts", tags=["scraper-scripts"], dependencies=[user_id_dep]
)


@router.get("/scrapling")
async def get_scrapling_scripts_list(search: str | None = None) -> list[str]:
    scripts = Path(config.SCRAPER_SCRIPTS_DIR) / "scrapling_scripts"

    if not scripts.is_dir():
        raise HTTPException(status_code=404, detail="Scrapling scripts directory not found")

    generator = (
        scripts.iterdir()
        if not search
        else scripts.glob(search)
    )
    return [f.name for f in generator if f.is_file()]


# @router.get("/firecrawl")
# async def get_firecrawl_scripts_list(search: str | None = None) -> list[str]:
#     pass
