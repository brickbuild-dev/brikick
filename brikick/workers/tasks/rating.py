import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.tasks.calculate_user_ratings")
def calculate_user_ratings() -> dict:
    """
    Job SEMANAL
    Para cada user activo:
    1. Calcular metricas raw
    2. Normalizar para 0-100
    3. Aplicar pesos dos factores
    4. Calcular score final
    5. Atribuir tier
    """
    logger.info("Starting user rating calculation job.")
    # TODO: Implementar pipeline completo de rating.
    return {"status": "ok", "task": "calculate_user_ratings"}


@celery_app.task(name="workers.tasks.calculate_sla_metrics")
def calculate_sla_metrics() -> dict:
    """
    Job DIARIO
    Para cada store:
    1. Contar orders por tier de shipping time
    2. Contar mensagens por tier de response time
    3. Calcular scores
    """
    logger.info("Starting SLA metrics calculation job.")
    # TODO: Implementar calculo de SLA metrics.
    return {"status": "ok", "task": "calculate_sla_metrics"}
