import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.tasks.auto_cancel_unapproved_orders")
def auto_cancel_unapproved_orders() -> dict:
    """
    Job HORARIO
    1. Encontrar OrderApprovals com auto_cancel_at expirado
    2. Cancelar order
    3. Libertar stock
    4. Notificar buyer
    """
    logger.info("Starting auto-cancel for unapproved orders.")
    # TODO: Implementar cancelamento automatico de orders nao aprovadas.
    return {"status": "ok", "task": "auto_cancel_unapproved_orders"}
