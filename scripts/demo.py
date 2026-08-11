"""Weekly Demo 1: an authenticated agent call reaches the gateway and
produces a structured decision event (plan §7, Day 7).

Flow: session → short-lived agent token → gateway call → decision event,
fetched back from the control plane to prove it landed in the database.
"""

import json
import os
import sys
import uuid
from datetime import UTC, datetime

import httpx

API_URL = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"
GATEWAY_URL = f"http://127.0.0.1:{os.environ.get('GATEWAY_PORT', '8080')}"


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

        print(f"demo: agent      {agent['name']} v{version['version']}")
        print(f"demo: session    {session['id']} (staging)")
        print(f"demo: token      expires {token['expires_at']} (aud=phulax-gateway)")

        request_id = str(uuid.uuid4())
        envelope = {
            "request_id": request_id,
            "agent_id": agent["id"],
            "agent_version": version["version"],
            "session_id": session["id"],
            "environment": "staging",
            "tool_name": "read_order",
            "arguments": {"order_id": "ORD-1001"},
            "requested_at": datetime.now(UTC).isoformat(),
        }
        response = gateway.post(
            "/v1/actions",
            json=envelope,
            headers={"Authorization": f"Bearer {token['token']}"},
        )
        if response.status_code != 200:
            print(f"demo: gateway refused the call: {response.status_code} {response.text}")
            return 1
        body = response.json()
        print(f"demo: verdict    {body['verdict']} ({body['rule']})")
        print(f"demo: result     order {body['result']['order']['status']}")

        events = api.get("/v1/events", params={"request_id": request_id}).json()
        if not events:
            print("demo: FAILED — no decision event found in the database")
            return 1
        print("demo: decision event recorded in the control plane:")
        print(json.dumps(events[0], indent=2))
        print(
            "demo: note args_meta carries the argument *shape* only — "
            "raw values never left the gateway (ADR-0002)."
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
