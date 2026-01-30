import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.tasks.award_badges")
def award_badges() -> dict:
    """
    Job DIARIO
    1. Verificar badges mensais (expirar os do mes anterior)
    2. Atribuir novos badges baseado em criterios
    3. Verificar milestones atingidos
    """
    logger.info("Starting badge awarding job.")
    # TODO: Implementar logica de atribuicao de badges.
    return {"status": "ok", "task": "award_badges"}
