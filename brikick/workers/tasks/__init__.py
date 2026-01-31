"""Celery tasks package."""

from workers.tasks import badges, order_approval, penalties, price_guide, rating, shipping_proof

__all__ = [
    "badges",
    "order_approval",
    "penalties",
    "price_guide",
    "rating",
    "shipping_proof",
]
