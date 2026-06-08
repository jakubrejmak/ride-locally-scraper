from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select

from ride_locally.config import config
from ride_locally.db.schema import ApiUserTable
from ride_locally.db.session import session

ph = PasswordHasher()


def create_token(user_id: int) -> tuple[str, datetime]:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {"sub": str(user_id), "exp": expire}

    return jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM), expire


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
    try:
        ph.verify(user.password_hash, password)
    except VerifyMismatchError:
        return None

    return user
