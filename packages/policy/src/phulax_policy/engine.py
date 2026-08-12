"""The evaluation algorithm (plan §11.4) — deterministic, ordered, explained.

::

    1. bundle signature valid? identity valid?   (callers verify, before here)
    2. agent frozen/revoked            → FREEZE  (status overrides everything)
    3. any matching rule says freeze   → FREEZE
    4. any matching rule says deny     → DENY         ← deny-overrides
    5. any matching rule says approval → REQUIRE_APPROVAL
    6. any matching rule says allow    → ALLOW
    7. nothing matched                 → DENY ("DEFAULT_DENY")

``evaluate`` is a pure function over (request, bundle, state): no I/O, no
clock, no randomness — and deliberately no risk score parameter, so a score
can never override a rule (plan §11.5).

Unknown-handling asymmetry: a condition that cannot be resolved (missing
field, wrong type) is UNKNOWN, not false. Permissive rules do not fire on
unknown; restrictive rules do. Both directions fail toward "too strict" —
the recoverable misconfiguration.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from phulax_policy.schema import (
    PERMISSIVE_EFFECTS,
    Bundle,
    Condition,
    Match,
    Rule,
)

__all__ = ["AgentState", "Bundle", "Decision", "PolicyRequest", "RuleTrace", "evaluate"]

_PRECEDENCE = ("freeze", "deny", "require_approval", "allow")

_MATCHED = "matched"
_MATCHED_UNKNOWN = "matched-on-unknown"
_NOT_MATCHED = "not-matched"


@dataclass(frozen=True)
class PolicyRequest:
    tool_name: str
    environment: str
    agent_id: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class AgentState:
    """What the registry knows about the caller at decision time."""

    revoked: bool = False


@dataclass(frozen=True)
class RuleTrace:
    """Why each rule did or didn't apply — the decision's working-out."""

    rule_id: str
    effect: str
    outcome: str
    detail: str


@dataclass(frozen=True)
class Decision:
    effect: str
    reason_codes: tuple[str, ...]
    matched_rules: tuple[str, ...]  # every rule that matched, any effect
    winning_rules: tuple[str, ...]  # the matched rules of the winning effect class
    policy_version: int
    approver_role: str | None
    trace: tuple[RuleTrace, ...]


def evaluate(request: PolicyRequest, bundle: Bundle, state: AgentState) -> Decision:
    # Step 2: registry status outranks every rule in the bundle.
    if state.revoked:
        return Decision(
            effect="freeze",
            reason_codes=("AGENT_REVOKED",),
            matched_rules=(),
            winning_rules=(),
            policy_version=bundle.version,
            approver_role=None,
            trace=(),
        )

    context = {"arguments": request.arguments, "agent": {"revoked": state.revoked}}
    trace: list[RuleTrace] = []
    matched: dict[str, list[Rule]] = {effect: [] for effect in _PRECEDENCE}
    matched_on_unknown: set[str] = set()

    for rule in bundle.rules:
        outcome, detail = _apply_rule(rule, request, context)
        trace.append(RuleTrace(rule.id, rule.effect, outcome, detail))
        if outcome in (_MATCHED, _MATCHED_UNKNOWN):
            matched[rule.effect].append(rule)
            if outcome == _MATCHED_UNKNOWN:
                matched_on_unknown.add(rule.id)

    matched_ids = tuple(rule.id for rules in matched.values() for rule in rules)

    # Steps 3–6: first effect class with a match wins, in fixed order.
    for effect in _PRECEDENCE:
        if not matched[effect]:
            continue
        reason_codes = [_REASON_BY_EFFECT[effect]]
        if effect == "deny" and (matched["require_approval"] or matched["allow"]):
            reason_codes.append("DENY_OVERRIDES")
        if any(rule.id in matched_on_unknown for rule in matched[effect]):
            reason_codes.append("MISSING_CONTEXT")
        approver_role = matched[effect][0].approver_role if effect == "require_approval" else None
        return Decision(
            effect=effect,
            reason_codes=tuple(reason_codes),
            matched_rules=matched_ids,
            winning_rules=tuple(rule.id for rule in matched[effect]),
            policy_version=bundle.version,
            approver_role=approver_role,
            trace=tuple(trace),
        )

    # Step 7: an unknown or unregistered action fails safe.
    return Decision(
        effect="deny",
        reason_codes=("DEFAULT_DENY",),
        matched_rules=(),
        winning_rules=(),
        policy_version=bundle.version,
        approver_role=None,
        trace=tuple(trace),
    )


_REASON_BY_EFFECT = {
    "freeze": "RULE_FREEZE",
    "deny": "RULE_DENY",
    "require_approval": "RULE_APPROVAL",
    "allow": "RULE_ALLOW",
}


def _apply_rule(rule: Rule, request: PolicyRequest, context: Mapping[str, Any]) -> tuple[str, str]:
    mismatch = _match_mismatch(rule.match, request)
    if mismatch:
        return _NOT_MATCHED, mismatch

    saw_unknown = False
    for condition in rule.conditions:
        result = _resolve_condition(condition, context)
        if result is False:
            return _NOT_MATCHED, f"condition {condition.field} {condition.op} is false"
        if result is None:
            saw_unknown = True

    if not saw_unknown:
        return _MATCHED, "matched"
    # UNKNOWN resolves by effect class: restrictive rules fire, permissive don't.
    if rule.effect in PERMISSIVE_EFFECTS:
        return _NOT_MATCHED, "condition unresolvable; permissive rule does not fire"
    return _MATCHED_UNKNOWN, "condition unresolvable; restrictive rule fires"


def _match_mismatch(match: Match, request: PolicyRequest) -> str:
    if match.tools is not None and request.tool_name not in match.tools:
        return "tool mismatch"
    if match.environments is not None and request.environment not in match.environments:
        return "environment mismatch"
    if match.agent_ids is not None and request.agent_id not in match.agent_ids:
        return "agent mismatch"
    return ""


def _resolve_condition(condition: Condition, context: Mapping[str, Any]) -> bool | None:
    """True/False when provable; None (UNKNOWN) when it isn't."""
    present, value = _lookup(condition.field, context)
    if not present:
        return None
    op, expected = condition.op, condition.value

    if op in ("eq", "neq"):
        result = _scalar_eq(value, expected)
        return result if op == "eq" else not result
    if op in ("gt", "gte", "lt", "lte"):
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        assert isinstance(expected, int | float)
        return {
            "gt": value > expected,
            "gte": value >= expected,
            "lt": value < expected,
            "lte": value <= expected,
        }[op]
    if op in ("in", "not_in"):
        assert isinstance(expected, tuple)
        member = any(_scalar_eq(value, item) for item in expected)
        return member if op == "in" else not member
    if op in ("ends_with", "not_ends_with"):
        if not isinstance(value, str):
            return None
        assert isinstance(expected, str)
        return value.endswith(expected) if op == "ends_with" else not value.endswith(expected)
    raise AssertionError(f"unreachable: parser admitted unknown op {op!r}")


def _scalar_eq(value: Any, expected: Any) -> bool:
    """Equality without Python's ``True == 1`` surprise: booleans only
    equal booleans; ints and floats compare numerically; everything else
    must match in type and value."""
    if isinstance(value, bool) or isinstance(expected, bool):
        return isinstance(value, bool) and isinstance(expected, bool) and value is expected
    if isinstance(value, int | float) and isinstance(expected, int | float):
        return float(value) == float(expected)
    return type(value) is type(expected) and value == expected


def _lookup(path: str, context: Mapping[str, Any]) -> tuple[bool, Any]:
    node: Any = context
    for part in path.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return False, None
        node = node[part]
    return True, node
