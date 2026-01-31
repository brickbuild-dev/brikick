import pytest
from fastapi import HTTPException

import api.deps as deps


@pytest.mark.asyncio
async def test_get_current_user_id_missing_header():
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user_id(x_user_id=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_missing_user(db_session):
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(user_id=999999, db=db_session)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_db_yields_session(monkeypatch, db_session):
    async def fake_get_session():
        yield db_session

    monkeypatch.setattr(deps, "get_session", fake_get_session)

    sessions = []
    async for session in deps.get_db():
        sessions.append(session)
        break
    assert sessions[0] is db_session
