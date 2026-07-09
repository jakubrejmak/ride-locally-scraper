from fastapi import APIRouter

from ride_locally.api.deps.get_session import DBSession
from ride_locally.api.deps.get_user import user_id_dep
from ride_locally.models.targets import GetTargetsResponse, NewScrTarget, ScrTarget
from ride_locally.worker.run_scrape import run_scrape

router = APIRouter(
    prefix="/scraper",
    tags=["scraper"],
    dependencies=[user_id_dep],
)

@router.post("/run")
async def run_scrape_now(target: ScrTarget):
    pass
