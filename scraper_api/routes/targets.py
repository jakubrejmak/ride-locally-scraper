from fastapi import APIRouter

from models.targets import NewScrTarget

router = APIRouter(prefix="/targets", tags=["targets"])


@router.patch("/add")
async def add_target(target: NewScrTarget):
    pass
