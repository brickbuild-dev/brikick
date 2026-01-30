from decimal import Decimal

from services.shipping_fairness import validate_fair_shipping


def test_validate_fair_shipping_allows_within_benchmark():
    validate_fair_shipping(Decimal("5.00"), Decimal("10.00"))
