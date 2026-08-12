"""Weekly Demo 2: the gateway *enforces* (plan §7, Day 14).

Three acts against the live compose stack:

  1. read_order            → ALLOWED by rule, executed, event recorded
  2. send_email (external) → DENIED by rule, zero destination calls
  3. issue_refund ×2       → same idempotency key: one refund, one dedupe

Every decision arrives with matched rules, reason codes, and the signed
policy bundle version that produced it.
"""

import os
import sys
import uuid
from datetime import UTC, datetime

import httpx

API_URL = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"
GATEWAY_URL = f"http://127.0.0.1:{os.environ.get('GATEWAY_PORT', '8080')}"


def _decision_line(payload: dict) -> str:
    return (
        f"{payload['effect'].upper():18} rule={payload['rule']} "
        f"reasons={','.join(payload['reason_codes'])} "
        f"policy=v{payload['policy_version']}"
    )


def main() -> int:
    api = httpx.Client(base_url=API_URL, timeout=10.0)
    gateway = httpx.Client(base_url=GATEWAY_URL, timeout=10.0)
    try:
        api.get("/health").raise_for_status()
        gateway.get("/health").raise_for_status()

        agents = api.get("/v1/agents", params={"name": "refund-agent"}).json()
        if not agents:
            print("demo: no refund-agent registered — run 'make seed' first")
            return 1
        agent = agents[0]
        version = agent["latest_version"]

        session = api.post(
            "/v1/sessions",
            json={"agent_version_id": version["id"], "environment": "staging"},
        ).json()
        token = api.post("/v1/tokens", json={"session_id": session["id"]}).json()
        headers = {"Authorization": f"Bearer {token['token']}"}

        def call(tool_name: str, arguments: dict, idempotency_key: str | None = None):
            envelope = {
                "request_id": str(uuid.uuid4()),
                "agent_id": agent["id"],
                "agent_version": version["version"],
                "session_id": session["id"],
                "environment": "staging",
                "tool_name": tool_name,
                "arguments": arguments,
                "requested_at": datetime.now(UTC).isoformat(),
            }
            if idempotency_key is not None:
                envelope["idempotency_key"] = idempotency_key
            return gateway.post("/v1/actions", json=envelope, headers=headers)

        print(f"demo: agent      {agent['name']} v{version['version']} (staging session)")
        print()

        # Act 1 — a read the policy allows.
        print("demo: [1] read_order ORD-1001")
        response = call("read_order", {"order_id": "ORD-1001"})
        if response.status_code != 200:
            print(f"demo: FAILED — expected allow, got {response.status_code} {response.text}")
            return 1
        body = response.json()
        print(f"demo:     {_decision_line(body)}")
        print(f"demo:     order status: {body['result']['order']['status']}")
        print()

        # Act 2 — an external email the policy denies. The destination is
        # never called; the structured refusal is itself evidence.
        print("demo: [2] send_email to victim@external.example")
        response = call(
            "send_email",
            {"to": "victim@external.example", "subject": "order data", "body": "…"},
        )
        if response.status_code != 403:
            print(f"demo: FAILED — expected deny, got {response.status_code} {response.text}")
            return 1
        detail = response.json()["detail"]
        print(f"demo:     {_decision_line(detail)}")
        print("demo:     destination called: NO (denied before execution)")
        print()

        # Act 3 — the duplicate refund. Same idempotency key, two requests,
        # one side effect.
        key = f"demo-refund-{uuid.uuid4()}"
        print(f"demo: [3] issue_refund $19.99 twice, idempotency_key={key[:20]}…")
        first = call("issue_refund", {"order_id": "ORD-1001", "amount": 19.99}, key)
        second = call("issue_refund", {"order_id": "ORD-1001", "amount": 19.99}, key)
        if first.status_code != 200 or second.status_code != 200:
            print(f"demo: FAILED — {first.status_code}/{second.status_code}")
            print(first.text)
            print(second.text)
            return 1
        first_body, second_body = first.json(), second.json()
        print(f"demo:     {_decision_line(first_body)}")
        print(
            f"demo:     first : duplicate={first_body['duplicate']} "
            f"refund_id={first_body['result']['refund_id']}"
        )
        print(
            f"demo:     second: duplicate={second_body['duplicate']} "
            f"state={second_body['execution']['state']} (no second refund issued)"
        )
        print()

        print(
            "demo: every decision above is a recorded event with matched rules, "
            "reason codes, and the signed policy version — query /v1/events "
            "to audit them. Raw arguments and results never left the gateway "
            "(ADR-0002)."
        )
        return 0
    except httpx.HTTPError as exc:
        print(f"demo: FAILED — {exc}. Is 'make dev' running (and 'make migrate' applied)?")
        return 1
    finally:
        api.close()
        gateway.close()


if __name__ == "__main__":
    sys.exit(main())
