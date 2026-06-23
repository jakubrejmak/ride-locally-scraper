from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ride_locally.config import config

security = HTTPBearer()
credentials_dep = Depends(security)
Credentials = Annotated[HTTPAuthorizationCredentials, credentials_dep]


def get_user_id(credentials: Credentials) -> int:
    token = credentials.credentials

    try:
        payload = jwt.decode(token, config.JWT_SECRET, config.JWT_ALGORITHM)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    user_id = int(payload["sub"])

    return user_id


user_id_dep = Depends(get_user_id)
UserId = Annotated[int, user_id_dep]
