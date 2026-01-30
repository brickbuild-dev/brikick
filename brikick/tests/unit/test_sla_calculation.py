from services.rating import RatingInputs, compute_rating_score


def test_sla_score_floor():
    inputs = RatingInputs(
        shipments_sla_score=0,
        response_sla_score=0,
        dispute_score=0,
        cancellation_score=0,
        price_fairness_score=0,
        activity_score=0,
    )
    assert compute_rating_score(inputs) == 0.0
