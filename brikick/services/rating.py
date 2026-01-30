from dataclasses import dataclass


@dataclass(frozen=True)
class RatingInputs:
    shipments_sla_score: float
    response_sla_score: float
    dispute_score: float
    cancellation_score: float
    price_fairness_score: float
    activity_score: float


WEIGHTS = {
    "shipments_sla_score": 0.25,
    "response_sla_score": 0.2,
    "dispute_score": 0.2,
    "cancellation_score": 0.15,
    "price_fairness_score": 0.1,
    "activity_score": 0.1,
}


def compute_rating_score(inputs: RatingInputs) -> float:
    weighted = (
        inputs.shipments_sla_score * WEIGHTS["shipments_sla_score"]
        + inputs.response_sla_score * WEIGHTS["response_sla_score"]
        + inputs.dispute_score * WEIGHTS["dispute_score"]
        + inputs.cancellation_score * WEIGHTS["cancellation_score"]
        + inputs.price_fairness_score * WEIGHTS["price_fairness_score"]
        + inputs.activity_score * WEIGHTS["activity_score"]
    )
    return round(weighted, 4)
