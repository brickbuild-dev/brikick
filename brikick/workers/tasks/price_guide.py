import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.tasks.calculate_price_guides")
def calculate_price_guides() -> dict:
    """
    Job DIARIO
    Calcula avg 6 meses para todas as combinacoes item+color+condition.
    Atualiza tabela price_guide.
    """
    logger.info("Starting price guide calculation job.")
    # TODO: Implementar agregacao de vendas 6m e update de price_guides.
    return {"status": "ok", "task": "calculate_price_guides"}
