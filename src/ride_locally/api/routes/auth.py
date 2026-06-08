from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, model_validator

from ride_locally.api.services.auth import auth_user, create_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def email_or_username(self) -> "LoginRequest":
        if not self.username and not self.email:
            raise ValueError("The request must contain either an 'email' or 'username'")
        return self


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


@router.post("/login")
async def login(body: LoginRequest) -> TokenResponse:
    user = await auth_user(
        email=body.email, username=body.username, password=body.password
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token, expires_at = create_token(user.id)

    return TokenResponse(access_token=token, expires_at=expires_at)
