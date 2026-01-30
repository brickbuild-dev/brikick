from celery import Celery

from core.config import settings

celery_app = Celery(
    "brikick",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.autodiscover_tasks(["workers.tasks"])
