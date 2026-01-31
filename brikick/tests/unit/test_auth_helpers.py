import pytest
from fastapi import HTTPException

from api.v1.auth import LoginRequest, login
from tests.factories.user_factory import UserFactory


@pytest.mark.asyncio
async def test_login_direct_success(db_session):
    user = await UserFactory.create(db_session, email="user@example.com", password="secret123")
    payload = LoginRequest(email=user.email, password="secret123")
    result = await login(payload, db_session)
    assert result["user_id"] == user.id
    assert result["token_type"] == "bearer"
    assert "access_token" in result


@pytest.mark.asyncio
async def test_login_direct_invalid_password(db_session):
    user = await UserFactory.create(db_session, email="user2@example.com", password="secret123")
    payload = LoginRequest(email=user.email, password="wrong")
    with pytest.raises(HTTPException):
        await login(payload, db_session)
