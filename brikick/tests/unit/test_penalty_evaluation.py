import pytest

from services.penalty_service import evaluate_user_penalties


@pytest.mark.asyncio
async def test_penalty_evaluation_no_issues(db_session):
    await evaluate_user_penalties(user_id=1, db=db_session)
