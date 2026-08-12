"""The constrained rule schema (plan §5.2, §7.2) and its parser.

A rule is data: ``match`` (who/what/where) + ``conditions`` + ``effect``.
The schema is deliberately small — no full Rego/Cedar in v1, because
expressiveness we don't expose is bypass surface we don't test. The parser
is the enforcement point for that constraint: unknown fields, unknown
operators, and unsafely-broad permissive rules are rejected here, before a
rule can ever reach the engine.

The asymmetry that runs through everything: a rule that *grants* (allow,
require_approval) must be tightly scoped; a rule that *restricts* (deny,
freeze) may be broad. "Too strict" is recoverable; "too loose" is an
incident.
"""

from dataclasses import dataclass, field
from typing import Any

import yaml

EFFECTS = ("allow", "deny", "require_approval", "freeze")
PERMISSIVE_EFFECTS = ("allow", "require_approval")

COMPARISON_OPS = ("gt", "gte", "lt", "lte")
MEMBERSHIP_OPS = ("in", "not_in")
STRING_OPS = ("ends_with", "not_ends_with")
EQUALITY_OPS = ("eq", "neq")
OPS = EQUALITY_OPS + COMPARISON_OPS + MEMBERSHIP_OPS + STRING_OPS

MATCH_FIELDS = ("tool", "environment", "agent_id")
RULE_FIELDS = ("id", "effect", "match", "conditions", "approver_role")
CONDITION_FIELDS = ("field", "op", "value")

# Condition fields are dotted paths into a closed set of roots: the request
# arguments and the agent's registry state. Nothing else is reachable.
CONDITION_ROOTS = ("arguments", "agent")

Scalar = str | int | float | bool | None


class PolicyError(ValueError):
    """All validation problems in one raise — authors fix files in one pass."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class Condition:
    field: str
    op: str
    value: Scalar | tuple[Scalar, ...]


@dataclass(frozen=True)
class Match:
    """Every present field must match; an absent field matches anything."""

    tools: tuple[str, ...] | None = None
    environments: tuple[str, ...] | None = None
    agent_ids: tuple[str, ...] | None = None

    def is_unconstrained(self) -> bool:
        return self.tools is None and self.environments is None and self.agent_ids is None


@dataclass(frozen=True)
class Rule:
    id: str
    effect: str
    match: Match
    conditions: tuple[Condition, ...] = ()
    approver_role: str | None = None


@dataclass(frozen=True)
class Bundle:
    """A versioned set of rules — what the control plane signs and the
    gateway evaluates. The pure-function contract: same bundle, same
    request, same state ⇒ same decision."""

    version: int
    rules: tuple[Rule, ...]


@dataclass
class _Errors:
    items: list[str] = field(default_factory=list)

    def add(self, where: str, problem: str) -> None:
        self.items.append(f"{where}: {problem}")


def parse_rules_yaml(text: str) -> tuple[Rule, ...]:
    """Parse and validate a YAML rules document (the authoring format)."""
    return load_rules_document(text)[1]


def load_rules_document(text: str) -> tuple[list[dict], tuple[Rule, ...]]:
    """Validate a YAML document and return both representations:
    the transfer data (what gets signed, stored, and shipped) and the
    parsed rules (what the engine evaluates)."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PolicyError([f"document: not valid YAML ({exc})"]) from exc
    rules = parse_rules_data(data)
    return data["rules"], rules


def parse_rules_data(data: Any) -> tuple[Rule, ...]:
    """Validate an already-loaded rules document (the transfer format).

    The gateway re-validates bundles it receives — a signature proves who
    published, not that the content is well-formed.
    """
    errors = _Errors()
    if not isinstance(data, dict):
        raise PolicyError(["document: must be a mapping with a 'rules' key"])
    unknown = set(data) - {"rules"}
    if unknown:
        errors.add("document", f"unknown field(s) {sorted(unknown)}")
    rules_data = data.get("rules")
    if not isinstance(rules_data, list):
        errors.add("document", "'rules' must be a list")
        raise PolicyError(errors.items)

    rules: list[Rule] = []
    seen_ids: set[str] = set()
    for index, rule_data in enumerate(rules_data):
        rule = _parse_rule(rule_data, index, errors)
        if rule is not None:
            if rule.id in seen_ids:
                errors.add(f"rule {rule.id!r}", "duplicate rule id")
            seen_ids.add(rule.id)
            rules.append(rule)
    if errors.items:
        raise PolicyError(errors.items)
    return tuple(rules)


def _parse_rule(data: Any, index: int, errors: _Errors) -> Rule | None:
    where = f"rule #{index}"
    if not isinstance(data, dict):
        errors.add(where, "must be a mapping")
        return None
    rule_id = data.get("id")
    if isinstance(rule_id, str) and rule_id:
        where = f"rule {rule_id!r}"
    else:
        errors.add(where, "'id' must be a non-empty string")
        return None

    unknown = set(data) - set(RULE_FIELDS)
    if unknown:
        errors.add(where, f"unknown field(s) {sorted(unknown)}")

    effect = data.get("effect")
    if effect not in EFFECTS:
        errors.add(where, f"unknown effect {effect!r} (one of {list(EFFECTS)})")
        return None

    match = _parse_match(data.get("match"), where, errors)
    conditions = _parse_conditions(data.get("conditions", []), where, errors)
    if match is None or conditions is None:
        return None

    # The unsafe-ambiguity gate: a permissive rule scoped to nothing at all
    # would grant on every request. The parser refuses to create one.
    if effect in PERMISSIVE_EFFECTS and match.is_unconstrained():
        errors.add(where, f"a {effect!r} rule must constrain at least one match field")

    approver_role = data.get("approver_role")
    if effect == "require_approval":
        if not isinstance(approver_role, str) or not approver_role:
            errors.add(where, "'approver_role' is required for require_approval rules")
    elif approver_role is not None:
        errors.add(where, "'approver_role' is only valid on require_approval rules")

    return Rule(
        id=rule_id,
        effect=effect,
        match=match,
        conditions=conditions,
        approver_role=approver_role if effect == "require_approval" else None,
    )


def _parse_match(data: Any, where: str, errors: _Errors) -> Match | None:
    if data is None or not isinstance(data, dict):
        errors.add(where, "'match' must be a mapping (use {} to match broadly)")
        return None
    unknown = set(data) - set(MATCH_FIELDS)
    if unknown:
        errors.add(where, f"unknown match field(s) {sorted(unknown)}")
        return None

    def values(key: str) -> tuple[str, ...] | None:
        raw = data.get(key)
        if raw is None:
            return None
        items = raw if isinstance(raw, list) else [raw]
        if not items or not all(isinstance(item, str) and item for item in items):
            errors.add(where, f"match {key!r} must be a non-empty string or list of strings")
            return None
        return tuple(items)

    return Match(
        tools=values("tool"),
        environments=values("environment"),
        agent_ids=values("agent_id"),
    )


def _parse_conditions(data: Any, where: str, errors: _Errors) -> tuple[Condition, ...] | None:
    if not isinstance(data, list):
        errors.add(where, "'conditions' must be a list")
        return None
    conditions: list[Condition] = []
    for index, item in enumerate(data):
        condition = _parse_condition(item, f"{where} condition #{index}", errors)
        if condition is not None:
            conditions.append(condition)
    return tuple(conditions)


def _parse_condition(data: Any, where: str, errors: _Errors) -> Condition | None:
    if not isinstance(data, dict):
        errors.add(where, "must be a mapping")
        return None
    unknown = set(data) - set(CONDITION_FIELDS)
    missing = {"field", "op"} - set(data)
    if unknown or missing:
        errors.add(where, f"must have exactly {list(CONDITION_FIELDS)}")
        return None

    path = data["field"]
    if not _valid_field_path(path):
        errors.add(
            where,
            f"condition field {path!r} must be a dotted path under one of {list(CONDITION_ROOTS)}",
        )
        return None

    op = data["op"]
    if op not in OPS:
        errors.add(where, f"unknown op {op!r} (one of {list(OPS)})")
        return None

    value = data.get("value")
    if op in COMPARISON_OPS and (isinstance(value, bool) or not isinstance(value, int | float)):
        errors.add(where, f"op {op!r} requires a number value")
        return None
    if op in MEMBERSHIP_OPS:
        if not isinstance(value, list) or not value:
            errors.add(where, f"op {op!r} requires a list of scalar values")
            return None
        if not all(_is_scalar(item) for item in value):
            errors.add(where, f"op {op!r} requires a list of scalar values")
            return None
        value = tuple(value)
    if op in STRING_OPS and (not isinstance(value, str) or not value):
        errors.add(where, f"op {op!r} requires a non-empty string value")
        return None
    if op in EQUALITY_OPS and not _is_scalar(value):
        errors.add(where, f"op {op!r} requires a scalar value")
        return None

    return Condition(field=path, op=op, value=value)


def _valid_field_path(path: Any) -> bool:
    if not isinstance(path, str):
        return False
    parts = path.split(".")
    return (
        len(parts) >= 2
        and parts[0] in CONDITION_ROOTS
        and all(part and part.replace("_", "a").isalnum() for part in parts)
    )


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, str | int | float | bool)
