"""Evaluates versioned medical-filter rules against submitted answers.

Rules are stored as JSON, e.g.:
    {"all": [{"field": "pregnant", "operator": "equals", "value": False}]}

This is decision support, not an autonomous diagnosis: `requires_manual_review`
must route to a professional rather than auto-approving or auto-rejecting.
"""

from typing import Any

_OPERATORS = {
    "equals": lambda actual, expected: actual == expected,
    "not_equals": lambda actual, expected: actual != expected,
    "in": lambda actual, expected: actual in expected,
    "greater_than": lambda actual, expected: actual is not None and actual > expected,
    "less_than": lambda actual, expected: actual is not None and actual < expected,
}


def _evaluate_condition(condition: dict[str, Any], answers: dict[str, Any]) -> bool:
    field, operator, expected = condition["field"], condition["operator"], condition["value"]
    if operator not in _OPERATORS:
        raise ValueError(f"Unknown eligibility operator: {operator}")
    return _OPERATORS[operator](answers.get(field), expected)


def _evaluate_node(node: dict[str, Any], answers: dict[str, Any]) -> bool:
    if "all" in node:
        return all(_evaluate_node(child, answers) for child in node["all"])
    if "any" in node:
        return any(_evaluate_node(child, answers) for child in node["any"])
    return _evaluate_condition(node, answers)


def evaluate_rules(rules: list[dict[str, Any]], answers: dict[str, Any]) -> str:
    """`rules` is a list of {"rule": <node>, "result": <outcome>} ordered by
    priority (highest first). Returns the result of the first matching rule,
    or `requires_manual_review` if none match — ambiguity defaults to human
    review rather than silently approving.
    """
    for entry in rules:
        if _evaluate_node(entry["rule"], answers):
            return entry["result"]
    return "requires_manual_review"
