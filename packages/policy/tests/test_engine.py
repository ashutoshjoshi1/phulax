"""Day 9: the §11.4 evaluation algorithm, table-driven.

Default-deny and deny-overrides are proven here by tests, not by reading
code (exit criterion). The engine is a pure function over
(request, bundle, state) — no I/O, no clock, no randomness.
"""

import pytest
from phulax_policy.engine import AgentState, Bundle, PolicyRequest, evaluate
from phulax_policy.examples import CANONICAL_BUNDLE_YAML
from phulax_policy.schema import parse_rules_yaml


@pytest.fixture(scope="module")
def bundle() -> Bundle:
    return Bundle(version=1, rules=parse_rules_yaml(CANONICAL_BUNDLE_YAML))


def _request(tool: str, arguments: dict | None = None, environment: str = "staging"):
    return PolicyRequest(
        tool_name=tool,
        environment=environment,
        agent_id="agent-1",
        arguments=arguments or {},
    )


def test_default_deny_when_no_rule_matches(bundle):
    decision = evaluate(_request("drop_database"), bundle, AgentState())
    assert decision.effect == "deny"
    assert "DEFAULT_DENY" in decision.reason_codes
    assert decision.matched_rules == ()


def test_allow_path_matches_the_allow_rule(bundle):
    decision = evaluate(_request("read_order", {"order_id": "ORD-1001"}), bundle, AgentState())
    assert decision.effect == "allow"
    assert decision.matched_rules == ("allow-read-order",)
    assert "RULE_ALLOW" in decision.reason_codes


def test_deny_overrides_allow_same_request():
    # An overlapping permissive rule can never silently defeat a
    # restrictive one — the whole reason the order is fixed.
    rules = parse_rules_yaml(
        """
rules:
  - id: allow-email
    effect: allow
    match:
      tool: send_email
  - id: block-external-sensitive-email
    effect: deny
    match:
      tool: send_email
    conditions:
      - field: arguments.to
        op: not_ends_with
        value: "@demo-org.dev"
"""
    )
    bundle = Bundle(version=7, rules=rules)
    decision = evaluate(
        _request("send_email", {"to": "victim@external.example"}), bundle, AgentState()
    )
    assert decision.effect == "deny"
    assert "DENY_OVERRIDES" in decision.reason_codes
    assert set(decision.matched_rules) == {"allow-email", "block-external-sensitive-email"}


def test_freeze_overrides_deny():
    rules = parse_rules_yaml(
        """
rules:
  - id: deny-email
    effect: deny
    match:
      tool: send_email
  - id: freeze-email
    effect: freeze
    match:
      tool: send_email
"""
    )
    decision = evaluate(
        _request("send_email", {"to": "a@b.c"}), Bundle(version=1, rules=rules), AgentState()
    )
    assert decision.effect == "freeze"
    assert "RULE_FREEZE" in decision.reason_codes


def test_revoked_agent_freezes_before_any_rule(bundle):
    # Step 2: status overrides everything — even a matching allow rule.
    decision = evaluate(
        _request("read_order", {"order_id": "ORD-1001"}),
        bundle,
        AgentState(revoked=True),
    )
    assert decision.effect == "freeze"
    assert "AGENT_REVOKED" in decision.reason_codes


def test_revoked_agent_freezes_even_unmatched_tools(bundle):
    # Status outranks default-deny too: a revoked agent gets FREEZE, not
    # DEFAULT_DENY, so the event tells the true story.
    decision = evaluate(_request("drop_database"), bundle, AgentState(revoked=True))
    assert decision.effect == "freeze"
    assert "AGENT_REVOKED" in decision.reason_codes


def test_large_refund_requires_approval(bundle):
    decision = evaluate(
        _request("issue_refund", {"order_id": "ORD-1001", "amount": 120.0}),
        bundle,
        AgentState(),
    )
    assert decision.effect == "require_approval"
    assert decision.matched_rules == ("approve-large-refund",)
    assert decision.approver_role == "finance_approver"
    assert "RULE_APPROVAL" in decision.reason_codes


def test_small_refund_allowed(bundle):
    decision = evaluate(
        _request("issue_refund", {"order_id": "ORD-1001", "amount": 19.99}),
        bundle,
        AgentState(),
    )
    assert decision.effect == "allow"
    assert decision.matched_rules == ("allow-small-refund",)


def test_reason_codes_list_matched_rules(bundle):
    decision = evaluate(
        _request("send_email", {"to": "x@external.example", "subject": "s", "body": "b"}),
        bundle,
        AgentState(),
    )
    assert decision.effect == "deny"
    assert decision.matched_rules == ("block-external-sensitive-email",)
    assert decision.policy_version == 1
    # The trace names every rule the engine looked at — explainability
    # is the brand (plan §4.4).
    assert {entry.rule_id for entry in decision.trace} == {rule.id for rule in bundle.rules}


def test_missing_context_fails_safe_by_effect_class():
    # A condition that cannot be resolved is UNKNOWN. Permissive rules
    # must not fire on unknown (no accidental allow); restrictive rules
    # must fire on unknown (no bypass by omission). Both directions err
    # toward "too strict" — the recoverable failure.
    rules = parse_rules_yaml(
        """
rules:
  - id: allow-small-refund
    effect: allow
    match:
      tool: issue_refund
    conditions:
      - field: arguments.amount
        op: lte
        value: 50
  - id: block-external-sensitive-email
    effect: deny
    match:
      tool: send_email
    conditions:
      - field: arguments.to
        op: not_ends_with
        value: "@demo-org.dev"
"""
    )
    bundle = Bundle(version=3, rules=rules)

    # allow rule, missing amount → rule does not match → default deny
    decision = evaluate(_request("issue_refund", {"order_id": "X"}), bundle, AgentState())
    assert decision.effect == "deny"
    assert "DEFAULT_DENY" in decision.reason_codes

    # deny rule, missing recipient → rule matches → deny, flagged as such
    decision = evaluate(_request("send_email", {}), bundle, AgentState())
    assert decision.effect == "deny"
    assert decision.matched_rules == ("block-external-sensitive-email",)
    assert "MISSING_CONTEXT" in decision.reason_codes


def test_type_mismatch_is_unknown_not_a_crash(bundle):
    # amount arrives as a string: comparisons cannot be proven, so the
    # permissive rules don't fire and the request falls to default deny.
    decision = evaluate(
        _request("issue_refund", {"order_id": "X", "amount": "9999"}),
        bundle,
        AgentState(),
    )
    assert decision.effect == "deny"
    assert "DEFAULT_DENY" in decision.reason_codes


def test_environment_match_scopes_a_rule():
    rules = parse_rules_yaml(
        """
rules:
  - id: allow-read-order-staging
    effect: allow
    match:
      tool: read_order
      environment: staging
"""
    )
    bundle = Bundle(version=2, rules=rules)
    staging = evaluate(_request("read_order", environment="staging"), bundle, AgentState())
    production = evaluate(_request("read_order", environment="production"), bundle, AgentState())
    assert staging.effect == "allow"
    assert production.effect == "deny"


def test_decision_carries_policy_version(bundle):
    decision = evaluate(_request("read_order"), bundle, AgentState())
    assert decision.policy_version == 1
