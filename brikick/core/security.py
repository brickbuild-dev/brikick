from datetime import datetime, timedelta, timezone

import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import PasswordValueError

from core.config import settings
from core.exceptions import InvalidTokenError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise InvalidTokenError() from exc


def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except (ValueError, PasswordValueError):
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return f"sha256${digest}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith("sha256$"):
        digest = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return hashed_password == f"sha256${digest}"
    return pwd_context.verify(plain_password, hashed_password)
