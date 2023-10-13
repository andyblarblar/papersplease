from datetime import timedelta, datetime

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
