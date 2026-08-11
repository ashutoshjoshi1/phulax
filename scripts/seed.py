"""Seed the walking skeleton: demo org, owner, agent v1.0.0, three tools.

Idempotent — safe to run repeatedly. Talks to the control-plane API only
(never the DB directly), so the seed exercises the same surface agents use.
"""

import os
import sys

import httpx

API_URL = f"http://127.0.0.1:{os.environ.get('API_PORT', '8000')}"

TOOLS = [
    {
        "name": "read_order",
        "description": "Read one order by id (simulated)",
        "args_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
        "sensitivity": "low",
        "side_effect": "read",
    },
    {
        "name": "send_email",
        "description": "Send a customer email (simulated)",
        "args_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
        "sensitivity": "medium",
        "side_effect": "write",
    },
    {
        "name": "issue_refund",
        "description": "Refund a payment (simulated)",
        "args_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number", "exclusiveMinimum": 0},
            },
            "required": ["order_id", "amount"],
        },
        "sensitivity": "high",
        "side_effect": "write",
    },
]


def get_or_create(client: httpx.Client, path: str, body: dict, lookup: dict) -> dict:
    existing = client.get(path, params=lookup).json()
    if existing:
        return existing[0]
    response = client.post(path, json=body)
    response.raise_for_status()
    return response.json()


def main() -> int:
    try:
        with httpx.Client(base_url=API_URL, timeout=10.0) as client:
            client.get("/health").raise_for_status()

            org = get_or_create(
                client, "/v1/organizations", {"name": "demo-org"}, {"name": "demo-org"}
            )
            owner = get_or_create(
                client,
                "/v1/users",
                {"org_id": org["id"], "email": "founder@demo-org.dev", "name": "Demo Founder"},
                {"org_id": org["id"], "email": "founder@demo-org.dev"},
            )
            agent = get_or_create(
                client,
                "/v1/agents",
                {
                    "org_id": org["id"],
                    "name": "refund-agent",
                    "owner_user_id": owner["id"],
                    "version": "1.0.0",
                    "manifest": {
                        "model": "claude-sonnet-5",
                        "tools": [tool["name"] for tool in TOOLS],
                    },
                },
                {"org_id": org["id"], "name": "refund-agent"},
            )
            seeded_tools = []
            for tool in TOOLS:
                created = get_or_create(
                    client,
                    "/v1/tools",
                    {"org_id": org["id"], **tool},
                    {"org_id": org["id"], "name": tool["name"]},
                )
                seeded_tools.append(
                    f"{created['name']} ({created['sensitivity']}/{created['side_effect']})"
                )

            print(f"seed: org        {org['name']} ({org['id']})")
            print(f"seed: owner      {owner['email']}")
            print(f"seed: agent      {agent['name']} v{agent['latest_version']['version']}")
            print(f"seed: tools      {', '.join(seeded_tools)}")
            return 0
    except httpx.HTTPError as exc:
        print(f"seed: FAILED talking to {API_URL} — is 'make dev' running? ({exc})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
