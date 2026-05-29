from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ride_locally.config import config

security = HTTPBearer()


def get_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> int | None:
    token = credentials.credentials

    try:
        payload = jwt.decode(token, config.JWT_SECRET, config.JWT_ALGORITHM)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    user_id = int(payload["sub"])

    return user_id
