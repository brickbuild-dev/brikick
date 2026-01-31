from decimal import Decimal

import pytest

from core.exceptions import PriceCapExceededError
from services.price_guide import max_allowed_price, validate_price_cap


def test_max_allowed_price_double_avg():
    assert max_allowed_price(Decimal("1.50")) == Decimal("3.00")


def test_validate_price_cap_allows_within_limit():
    validate_price_cap(Decimal("2.00"), Decimal("1.00"))


def test_validate_price_cap_raises_when_exceeded():
    with pytest.raises(PriceCapExceededError):
        validate_price_cap(Decimal("2.01"), Decimal("1.00"))
