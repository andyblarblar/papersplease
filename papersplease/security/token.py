import logging
from datetime import timedelta, datetime

from fastapi.security import OAuth2
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi import Request
from fastapi.security.utils import get_authorization_scheme_param
from fastapi import HTTPException
from fastapi import status
from typing import Optional
from typing import Dict

from jose import jwt, JWTError
from pydantic import BaseModel

# Very secure
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Data encoded in the JWT"""
    email: str


def create_access_token(sub: str) -> str:
    """Signs a JWT"""
    encoded_jwt = jwt.encode({"exp": datetime.utcnow() + timedelta(minutes=15), "sub": sub}, SECRET_KEY,
                             algorithm=ALGORITHM)
    return encoded_jwt


def decode(encoded: str) -> TokenData | None:
    """Retrieves the data encoded in the JWT"""
    try:
        payload = jwt.decode(encoded, SECRET_KEY, ALGORITHM)
    except JWTError:
        return None

    email = payload.get("sub")

    return email and TokenData(email=email)


# We add cookies to the normal oauth flow
class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.cookies.get("access_token")

        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                # Break standard and redirect to login
                raise HTTPException(
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer", "Location": "/login"},
                )
            else:
                return None
        return param