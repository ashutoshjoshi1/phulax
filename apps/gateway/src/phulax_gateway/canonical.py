"""Canonical request forms (plan §7, Day 6).

``{"amount": 25.0, "id": "x"}`` and ``{"id":"x","amount":25.00}`` are the
same request. Approval binding (Phase 3) and idempotency (Phase 2) both rest
on that being a *provable* property, so the gateway normalizes before
hashing: sorted keys, minimal separators, canonical number forms (an
integral float collapses to its integer). An approval will later authorize
exactly one canonical hash — argument mutation after approval becomes a hash
mismatch, mechanically.

Strings are hashed as-is (UTF-8, no unicode normalization), matching
RFC 8785's stance.
"""

import hashlib
import json
import math
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, str | int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("NaN/Infinity have no canonical JSON form")
        return int(value) if value.is_integer() else value
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical form requires string keys")
        return {key: _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    raise TypeError(f"type {type(value).__name__} has no canonical JSON form")


def canonicalize(value: Any) -> str:
    """Deterministic JSON text: equivalent inputs produce identical output."""
    return json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(*, tool_name: str, environment: str, arguments: dict) -> str:
    """The hash an approval will bind to: tool + environment + arguments."""
    payload = {"tool": tool_name, "environment": environment, "arguments": arguments}
    return hashlib.sha256(canonicalize(payload).encode()).hexdigest()


def args_meta(arguments: dict) -> dict:
    """Metadata-first (ADR-0002): the *shape* of the arguments — JSON type
    per top-level field — never the values."""
    return {key: _json_type(value) for key, value in arguments.items()}


def _json_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if value is None:
        return "null"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__
