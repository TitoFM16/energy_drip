from medical_api.shared.domain.eligibility import evaluate_rules

ELIGIBLE_RULE = {
    "rule": {"all": [{"field": "pregnant", "operator": "equals", "value": False}]},
    "result": "eligible",
}
NOT_ELIGIBLE_RULE = {
    "rule": {"any": [{"field": "pregnant", "operator": "equals", "value": True}]},
    "result": "not_eligible",
}


def test_eligible_when_all_conditions_pass():
    result = evaluate_rules([NOT_ELIGIBLE_RULE, ELIGIBLE_RULE], {"pregnant": False})
    assert result == "eligible"


def test_not_eligible_when_high_risk_answer_given():
    result = evaluate_rules([NOT_ELIGIBLE_RULE, ELIGIBLE_RULE], {"pregnant": True})
    assert result == "not_eligible"


def test_requires_manual_review_when_no_rule_matches():
    result = evaluate_rules([], {"pregnant": False})
    assert result == "requires_manual_review"
