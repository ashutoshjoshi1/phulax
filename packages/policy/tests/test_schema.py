"""Day 8: the constrained rule schema.

Good rules validate; unsafe ambiguity is rejected *by the parser*, before a
rule can ever reach the engine. Expressiveness we don't expose is bypass
surface we don't test (plan §5.2).
"""

import pytest
from phulax_policy.examples import CANONICAL_BUNDLE_YAML
from phulax_policy.schema import PolicyError, parse_rules_yaml


def test_canonical_bundle_parses():
    rules = parse_rules_yaml(CANONICAL_BUNDLE_YAML)
    assert [rule.id for rule in rules] == [
        "allow-read-order",
        "allow-small-refund",
        "approve-large-refund",
        "block-external-sensitive-email",
        "freeze-on-revoked-agent",
    ]
    approval = rules[2]
    assert approval.effect == "require_approval"
    assert approval.approver_role == "finance_approver"
    assert approval.conditions[0].op == "gt"
    assert approval.conditions[0].value == 50


def test_match_accepts_a_list_of_tools():
    rules = parse_rules_yaml(
        """
rules:
  - id: deny-both
    effect: deny
    match:
      tool: [send_email, issue_refund]
"""
    )
    assert rules[0].match.tools == ("send_email", "issue_refund")


def _rejects(document: str, needle: str) -> None:
    with pytest.raises(PolicyError) as excinfo:
        parse_rules_yaml(document)
    assert needle in str(excinfo.value)


# --- unsafe ambiguity: the tests the spec names ---


def test_unsafe_ambiguous_rule_rejected_by_parser():
    # A permissive rule with an empty match would allow *everything*.
    # "Too loose" is an incident; the parser refuses to create one.
    _rejects(
        """
rules:
  - id: allow-everything
    effect: allow
    match: {}
""",
        "must constrain at least one match field",
    )


def test_unknown_rule_field_rejected():
    # A typo like `efect` must never silently widen a rule.
    _rejects(
        """
rules:
  - id: allow-read-order
    efect: allow
    match:
      tool: read_order
""",
        "unknown field",
    )


def test_unknown_match_field_rejected():
    _rejects(
        """
rules:
  - id: allow-read-order
    effect: allow
    match:
      tol: read_order
""",
        "unknown match field",
    )


def test_unknown_effect_rejected():
    _rejects(
        """
rules:
  - id: allow-read-order
    effect: permit
    match:
      tool: read_order
""",
        "unknown effect",
    )


def test_unknown_operator_rejected():
    _rejects(
        """
rules:
  - id: allow-small-refund
    effect: allow
    match:
      tool: issue_refund
    conditions:
      - field: arguments.amount
        op: roughly_equals
        value: 50
""",
        "unknown op",
    )


def test_duplicate_rule_ids_rejected():
    _rejects(
        """
rules:
  - id: allow-read-order
    effect: allow
    match:
      tool: read_order
  - id: allow-read-order
    effect: allow
    match:
      tool: read_order
""",
        "duplicate rule id",
    )


def test_condition_field_outside_allowed_prefixes_rejected():
    _rejects(
        """
rules:
  - id: deny-weird
    effect: deny
    match:
      tool: send_email
    conditions:
      - field: os.environ.SECRET
        op: eq
        value: x
""",
        "condition field",
    )


def test_comparison_operator_requires_a_number():
    _rejects(
        """
rules:
  - id: allow-small-refund
    effect: allow
    match:
      tool: issue_refund
    conditions:
      - field: arguments.amount
        op: gt
        value: "fifty"
""",
        "requires a number",
    )


def test_in_operator_requires_a_list():
    _rejects(
        """
rules:
  - id: allow-known
    effect: allow
    match:
      tool: read_order
    conditions:
      - field: arguments.region
        op: in
        value: eu-west-1
""",
        "requires a list",
    )


def test_approval_rule_requires_approver_role():
    _rejects(
        """
rules:
  - id: approve-large-refund
    effect: require_approval
    match:
      tool: issue_refund
""",
        "approver_role",
    )


def test_approver_role_forbidden_on_other_effects():
    _rejects(
        """
rules:
  - id: allow-read-order
    effect: allow
    match:
      tool: read_order
    approver_role: finance_approver
""",
        "approver_role",
    )


def test_all_errors_reported_at_once():
    # An author fixes the whole file in one pass, not error-by-error.
    with pytest.raises(PolicyError) as excinfo:
        parse_rules_yaml(
            """
rules:
  - id: bad-one
    effect: permit
    match:
      tool: read_order
  - id: bad-two
    effect: deny
    match:
      tol: send_email
"""
        )
    message = str(excinfo.value)
    assert "unknown effect" in message
    assert "unknown match field" in message


def test_non_yaml_and_non_mapping_documents_rejected():
    _rejects("- just\n- a\n- list\n", "mapping")
    _rejects("rules: {}\n", "list")
