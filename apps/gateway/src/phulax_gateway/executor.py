"""Simulated tool execution for the walking skeleton.

Real tool adapters (HTTP upstreams, MCP servers) are a later phase. Week 1
needs exactly one read-only call to complete end-to-end: ``read_order``.
"""

from typing import Any

_FAKE_ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "status": "delivered",
        "total": {"amount": 129.5, "currency": "USD"},
        "customer_ref": "cus_demo_001",
    },
}


def _read_order(arguments: dict) -> dict[str, Any]:
    order_id = arguments.get("order_id", "")
    order = _FAKE_ORDERS.get(order_id)
    if order is None:
        return {"found": False, "order_id": order_id}
    return {"found": True, "order": order}


_EXECUTORS = {"read_order": _read_order}


def execute(tool_name: str, arguments: dict) -> dict[str, Any]:
    executor = _EXECUTORS.get(tool_name)
    if executor is None:
        return {"simulated": True, "note": "no executor in the walking skeleton"}
    return executor(arguments)
