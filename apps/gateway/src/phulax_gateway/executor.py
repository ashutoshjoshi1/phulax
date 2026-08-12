"""Simulated tool execution (plan §7 Day 11 — the simulator adapter).

Real tool adapters (HTTP upstreams, MCP servers) are a later phase. Phase 2
needs one read and two writes so the policy engine has something to allow,
deny, and idempotency-protect. The write simulators mutate module state on
purpose: tests count side effects to prove "denied means zero calls" and
"duplicate means one call".
"""

import itertools
from typing import Any

_FAKE_ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "status": "delivered",
        "total": {"amount": 129.5, "currency": "USD"},
        "customer_ref": "cus_demo_001",
    },
}

# Side-effect ledgers — the simulator's "destination systems".
SENT_EMAILS: list[dict[str, Any]] = []
ISSUED_REFUNDS: list[dict[str, Any]] = []
_refund_ids = itertools.count(1)


def _read_order(arguments: dict) -> dict[str, Any]:
    order_id = arguments.get("order_id", "")
    order = _FAKE_ORDERS.get(order_id)
    if order is None:
        return {"found": False, "order_id": order_id}
    return {"found": True, "order": order}


def _send_email(arguments: dict) -> dict[str, Any]:
    SENT_EMAILS.append(dict(arguments))
    return {"sent": True, "to": arguments.get("to"), "message_id": f"msg-{len(SENT_EMAILS)}"}


def _issue_refund(arguments: dict) -> dict[str, Any]:
    refund = {
        "refund_id": f"re-{next(_refund_ids):04d}",
        "order_id": arguments.get("order_id"),
        "amount": arguments.get("amount"),
        "status": "succeeded",
    }
    ISSUED_REFUNDS.append(refund)
    return refund


_EXECUTORS = {
    "read_order": _read_order,
    "send_email": _send_email,
    "issue_refund": _issue_refund,
}


def execute(tool_name: str, arguments: dict) -> dict[str, Any]:
    executor = _EXECUTORS.get(tool_name)
    if executor is None:
        return {"simulated": True, "note": "no executor for this tool yet"}
    return executor(arguments)
