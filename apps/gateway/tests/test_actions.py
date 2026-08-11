"""Day 7, end to end: an authenticated agent call reaches the gateway and
produces a structured decision event — plus every rejection path."""

import uuid
from datetime import UTC, datetime


def _envelope(seeded: dict, **overrides) -> dict:
    body = {
        "request_id": str(uuid.uuid4()),
        "agent_id": seeded["agent"]["id"],
        "agent_version": "1.0.0",
        "session_id": seeded["session"]["id"],
        "environment": "staging",
        "tool_name": "read_order",
        "arguments": {"order_id": "ORD-1001"},
        "requested_at": datetime.now(UTC).isoformat(),
    }
    return body | overrides


def _post(gateway_client, seeded, envelope=None, token=None):
    return gateway_client.post(
        "/v1/actions",
        json=envelope or _envelope(seeded),
        headers={"Authorization": f"Bearer {token or seeded['token']}"},
    )


def test_allowed_call_produces_decision_event(gateway_client, api_client, seeded):
    envelope = _envelope(seeded)
    response = _post(gateway_client, seeded, envelope)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verdict"] == "allow"
    assert body["result"]["order"]["order_id"] == "ORD-1001"

    events = api_client.get("/v1/events", params={"request_id": envelope["request_id"]}).json()
    assert len(events) == 1
    event = events[0]
    # who attempted what, through which agent version, in which session, when
    assert event["session_id"] == seeded["session"]["id"]
    assert event["tool_name"] == "read_order"
    assert event["verdict"] == "allow"
    assert event["canonical_hash"] == body["canonical_hash"]
    assert event["args_meta"] == {"order_id": "string"}  # shape, never values


def test_missing_token_rejected(gateway_client, seeded):
    response = gateway_client.post("/v1/actions", json=_envelope(seeded))
    assert response.status_code == 401


def test_revoked_agent_rejected(gateway_client, api_client, seeded):
    api_client.post(f"/v1/agents/{seeded['agent']['id']}/revoke")
    envelope = _envelope(seeded)
    response = _post(gateway_client, seeded, envelope)
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "identity.agent-revoked"
    # the refusal is itself evidence
    events = api_client.get("/v1/events", params={"request_id": envelope["request_id"]}).json()
    assert events[0]["verdict"] == "block"


def test_environment_mismatch_rejected_before_evaluation(gateway_client, seeded):
    response = _post(gateway_client, seeded, _envelope(seeded, environment="production"))
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "identity.environment-mismatch"


def test_claims_mismatch_rejected(gateway_client, seeded):
    forged = _envelope(seeded, agent_id=str(uuid.uuid4()))
    response = _post(gateway_client, seeded, forged)
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "identity.claims-mismatch"


def test_unknown_tool_blocked(gateway_client, seeded):
    response = _post(gateway_client, seeded, _envelope(seeded, tool_name="drop_database"))
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "tool.unknown"


def test_arguments_violating_tool_schema_blocked(gateway_client, seeded):
    bad = _envelope(seeded, arguments={"order_id": 42})
    response = _post(gateway_client, seeded, bad)
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "tool.args-schema"
