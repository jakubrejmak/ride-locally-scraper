from typing import Annotated

from fastapi import APIRouter, Query, status

from ride_locally.api.deps.get_session import DBSession
from ride_locally.api.deps.get_user import user_id_dep
from ride_locally.api.services.targets import create_target, list_targets
from ride_locally.models.targets import GetTargetsResponse, NewScrTarget, ScrTarget

router = APIRouter(
    prefix="/targets",
    tags=["targets"],
    dependencies=[user_id_dep],
)


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_target(body: NewScrTarget, db: DBSession) -> ScrTarget:
    return await create_target(db=db, body=body)


@router.get("")
async def get_targets(
    db: DBSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 10,
    search: str | None = None,
    is_active: bool | None = None,
) -> GetTargetsResponse:
    return await list_targets(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        is_active=is_active,
    )
