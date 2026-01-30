from decimal import Decimal

from core.exceptions import FairShippingError


def validate_fair_shipping(shipping_cost: Decimal, benchmark_max: Decimal) -> None:
    if shipping_cost > benchmark_max:
        raise FairShippingError(
            shipping_cost=shipping_cost,
            benchmark_max=benchmark_max,
        )
