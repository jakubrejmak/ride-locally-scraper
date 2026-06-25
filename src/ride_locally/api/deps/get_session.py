from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ride_locally.db.session import session


async def get_session():
    async with session() as s:
        try:
            yield s
        except Exception:
            await s.rollback()
            raise


db_session_dep = Depends(get_session)
DBSession = Annotated[AsyncSession, db_session_dep]

