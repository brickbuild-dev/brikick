import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.tasks.check_shipping_proof_deadlines")
def check_shipping_proof_deadlines() -> dict:
    """
    Job HORARIO
    1. Encontrar orders sem tracking com deadline expirado
    2. Se nao ha prova: criar disputa automatica
    3. Criar issue para vendedor
    """
    logger.info("Starting shipping proof deadline checks.")
    # TODO: Implementar verificacao de provas de envio.
    return {"status": "ok", "task": "check_shipping_proof_deadlines"}
