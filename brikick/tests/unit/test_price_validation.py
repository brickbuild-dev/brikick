from decimal import Decimal

import pytest

from services.price_validation import validate_lot_price


@pytest.mark.asyncio
async def test_price_validation_allows_missing_guide(db_session):
    result = await validate_lot_price(
        db_session,
        catalog_item_id=1,
        color_id=1,
        condition="N",
        unit_price=Decimal("2.00"),
        store_id=1,
    )
    assert result.valid is True
