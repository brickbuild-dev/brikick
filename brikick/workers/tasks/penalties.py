import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.tasks.evaluate_penalties")
def evaluate_penalties() -> dict:
    """
    Job DIARIO
    Para cada user com issues recentes:
    1. Contar issues activos
    2. Avaliar se deve escalar penalizacao
    """
    logger.info("Starting penalties evaluation job.")
    # TODO: Implementar avaliacao diaria de penalizacoes.
    return {"status": "ok", "task": "evaluate_penalties"}
