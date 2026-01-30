from services.rating import RatingInputs, compute_rating_score


def test_rating_score_weighted_sum():
    inputs = RatingInputs(
        shipments_sla_score=80,
        response_sla_score=90,
        dispute_score=70,
        cancellation_score=85,
        price_fairness_score=95,
        activity_score=75,
    )
    score = compute_rating_score(inputs)
    assert isinstance(score, float)
    assert score > 0
