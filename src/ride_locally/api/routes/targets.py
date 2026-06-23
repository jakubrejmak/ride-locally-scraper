from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from ride_locally.api.deps.get_session import DBSession
from ride_locally.api.deps.get_user import UserId
from ride_locally.api.services.targets import create_target, list_targets
from ride_locally.models.targets import GetTargetsResponse, NewScrTarget, ScrTarget

router = APIRouter(prefix="/targets", tags=["targets"])


@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_target(body: NewScrTarget, _db: DBSession, _user_id: UserId) -> ScrTarget:
    try:
        return await create_target(db=_db, body=body)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add target",
        )


@router.get("/get")
async def get_targets(
    _db: DBSession,
    _user_id: UserId,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> GetTargetsResponse:
    try:
        return await list_targets(
            db=_db,
            page=page,
            per_page=per_page,
            search=search,
            is_active=is_active,
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch targets",
        )
