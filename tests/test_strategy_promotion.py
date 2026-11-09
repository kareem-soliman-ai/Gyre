from gyre.control.promotion import EvaluationReceipt, assess_strategy_promotion


def _receipt(domain: str, **overrides) -> EvaluationReceipt:
    fields = {
        "strategy_id": "measured-control",
        "domain_family": domain,
        "endpoint_id": f"{domain}:outcome",
        "effect_lower_bound": 1.0,
        "harm_delta_upper_bound": 0.0,
        "validated_counterfactual": True,
        "independent_evaluation": True,
        "matched_budget": True,
        "strong_baseline": True,
    }
    fields.update(overrides)
    return EvaluationReceipt(**fields)


def test_synthetic_or_self_evaluated_receipt_cannot_promote():
    report = assess_strategy_promotion(
        "measured-control",
        (
            _receipt("repo-rescue", validated_counterfactual=False),
            _receipt("data-repair", independent_evaluation=False),
        ),
    )
    assert not report.eligible
    assert "insufficient_independent_domains" in report.reasons


def test_positive_result_without_matched_budget_cannot_promote():
    report = assess_strategy_promotion(
        "measured-control",
        (
            _receipt("repo-rescue"),
            _receipt("data-repair", matched_budget=False),
        ),
    )
    assert not report.eligible
    assert "insufficient_independent_domains" in report.reasons


def test_two_independent_harmless_domain_receipts_can_promote():
    report = assess_strategy_promotion(
        "measured-control",
        (_receipt("repo-rescue"), _receipt("data-repair")),
    )
    assert report.eligible
    assert report.qualifying_domain_families == ("data-repair", "repo-rescue")
    assert report.reasons == ()


def test_harm_regression_blocks_an_otherwise_positive_receipt():
    report = assess_strategy_promotion(
        "measured-control",
        (
            _receipt("repo-rescue"),
            _receipt("data-repair", harm_delta_upper_bound=0.1),
        ),
    )
    assert not report.eligible

