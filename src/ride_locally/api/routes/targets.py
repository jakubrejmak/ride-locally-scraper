from ride_locally.api.deps.get_user import get_user_id
from fastapi import APIRouter, Depends

from ride_locally.models.targets import NewScrTarget

router = APIRouter(
    prefix="/targets", tags=["targets"], dependencies=[Depends(get_user_id)]
)


@router.patch("/add")
async def add_target(body: NewScrTarget):
    pass
