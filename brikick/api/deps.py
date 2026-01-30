from collections.abc import AsyncGenerator

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_current_user_id(
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
) -> int:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header.",
        )
    return x_user_id
