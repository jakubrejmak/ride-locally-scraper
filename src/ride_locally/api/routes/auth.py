from typing import Annotated

import jwt
from fastapi import APIRouter, HTTPException, status, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator

from ride_locally.config import config
from ride_locally.api.services.auth import auth_user, create_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str

    @model_validator(mode="after")
    def email_or_username(self) -> "LoginRequest":
        if not self.username and not self.email:
            raise ValueError("The request must contain either an 'email' or 'username'")
        return self


@router.post("/login")
async def login(body: LoginRequest) -> JSONResponse:
    user = await auth_user(
        email=body.email, username=body.username, password=body.password
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token, expires_at = create_token(user.id)
    refresh_token, _ = create_token(user.id, 1440)

    resp = JSONResponse({"token": token, "expires_at": expires_at.isoformat()})
    resp.set_cookie(key="session", value=refresh_token, httponly=True)

    return resp


@router.post("/refresh")
async def refresh_token(session: Annotated[str, Cookie()]) -> JSONResponse:
    payload = jwt.decode(session, config.JWT_REFRESH_SECRET, config.JWT_ALGORITHM)
    user_id = payload["sub"]

    token, expires_at = create_token(user_id)

    resp = JSONResponse({"token": token, "expires_at": expires_at.isoformat()})

    return resp
