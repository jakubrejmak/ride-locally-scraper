from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from ride_locally.api.deps.get_user import get_user_id
from ride_locally.db.schema import ScrTargetTable
from ride_locally.db.session import session
from ride_locally.models.targets import NewScrTarget, ScrTarget

router = APIRouter(
    prefix="/targets", tags=["targets"], dependencies=[Depends(get_user_id)]
)


@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_target(body: NewScrTarget):
    pass


@router.get("/get")
async def get_targets(body: ScrTarget):
    pass
