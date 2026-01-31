from decimal import Decimal

from core.exceptions import PriceCapExceededError


def max_allowed_price(avg_price_6m: Decimal) -> Decimal:
    return avg_price_6m * Decimal("2")


def validate_price_cap(price: Decimal, avg_price_6m: Decimal) -> None:
    max_price = max_allowed_price(avg_price_6m)
    if price > max_price:
        raise PriceCapExceededError(
            price=price,
            limit=max_price,
            avg_price_6m=avg_price_6m,
        )
