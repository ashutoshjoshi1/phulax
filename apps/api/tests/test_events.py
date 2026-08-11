"""Event ingestion stores metadata only and is queryable by request id."""

import uuid
from datetime import UTC, datetime


def test_event_ingest_and_query(api_client, seeded):
    request_id = str(uuid.uuid4())
    payload = {
        "action_request": {
            "request_id": request_id,
            "session_id": seeded["session"]["id"],
            "tool_name": "read_order",
            "environment": "staging",
            "canonical_hash": "a" * 64,
            "args_meta": {"order_id": "string"},
            "requested_at": datetime.now(UTC).isoformat(),
        },
        "event": {"verdict": "allow", "rule": "test.rule", "latency_ms": 12},
    }
    response = api_client.post("/v1/events", json=payload)
    assert response.status_code == 201

    events = api_client.get("/v1/events", params={"request_id": request_id}).json()
    assert len(events) == 1
    event = events[0]
    assert event["verdict"] == "allow"
    assert event["rule"] == "test.rule"
    assert event["canonical_hash"] == "a" * 64
    assert event["args_meta"] == {"order_id": "string"}
    # metadata-first: nothing that could contain raw argument values
    assert "arguments" not in event


def test_event_for_unknown_session_rejected(api_client, seeded):
    payload = {
        "action_request": {
            "request_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "tool_name": "read_order",
            "environment": "staging",
            "canonical_hash": "b" * 64,
            "requested_at": datetime.now(UTC).isoformat(),
        },
        "event": {"verdict": "allow", "rule": "test.rule"},
    }
    assert api_client.post("/v1/events", json=payload).status_code == 404
