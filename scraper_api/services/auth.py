from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import select

from conf import config
from db.schema import ApiUserTable
from db.session import session

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(config.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {"sub": str(user_id), "exp": expire}

    return jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)


async def auth_user(
    *, email: str | None, username: str | None, password: str
) -> ApiUserTable | None:
    async with session() as s:
        q = select(ApiUserTable)
        if email is not None:
            q = q.where(ApiUserTable.email == email)
        else:
            q = q.where(ApiUserTable.username == username)
        user = (await s.execute(q)).scalar_one_or_none()

    if user is None:
        return None
    if not pwd_ctx.verify(password, user.password_hash):
        return None

    return user
