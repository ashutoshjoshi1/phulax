"""Day 13, end to end: at-most-once side effect per idempotency key.

Scenario #10 — the concurrent duplicate — is the test that matters: two
identical refund requests race through the full gateway → control plane
path, and exactly one refund reaches the destination. Run it repeatedly
(``pytest -k idempot --count=50``): flaky = broken.
"""

import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from phulax_gateway import executor
from phulax_gateway.canonical import canonicalize


@pytest.fixture(autouse=True)
def clean_ledgers():
    """Each test observes the simulated destination from a known-empty state."""
    executor.SENT_EMAILS.clear()
    executor.ISSUED_REFUNDS.clear()
    yield
    executor.SENT_EMAILS.clear()
    executor.ISSUED_REFUNDS.clear()


def _refund_envelope(seeded: dict, idempotency_key: str, **overrides) -> dict:
    body = {
        "request_id": str(uuid.uuid4()),
        "idempotency_key": idempotency_key,
        "agent_id": seeded["agent"]["id"],
        "agent_version": "1.0.0",
        "session_id": seeded["session"]["id"],
        "environment": "staging",
        "tool_name": "issue_refund",
        "arguments": {"order_id": "ORD-1001", "amount": 19.99},
        "requested_at": datetime.now(UTC).isoformat(),
    }
    return body | overrides


def _post(gateway_client, seeded, envelope):
    return gateway_client.post(
        "/v1/actions",
        json=envelope,
        headers={"Authorization": f"Bearer {seeded['token']}"},
    )


def test_concurrent_duplicates_one_side_effect(gateway_client, seeded):
    key = f"refund-{uuid.uuid4()}"

    def fire(_):
        return _post(gateway_client, seeded, _refund_envelope(seeded, key))

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(fire, range(2)))

    assert all(response.status_code == 200 for response in responses), [
        response.text for response in responses
    ]
    bodies = [response.json() for response in responses]
    assert sorted(body["duplicate"] for body in bodies) == [False, True]
    # one executions row, one winner, one refund at the destination
    assert len({body["execution"]["execution_id"] for body in bodies}) == 1
    assert len(executor.ISSUED_REFUNDS) == 1


def test_sequential_duplicate_reads_recorded_outcome(gateway_client, seeded):
    key = f"refund-{uuid.uuid4()}"
    first = _post(gateway_client, seeded, _refund_envelope(seeded, key)).json()
    assert first["duplicate"] is False
    expected_hash = hashlib.sha256(canonicalize(first["result"]).encode()).hexdigest()

    retry = _post(gateway_client, seeded, _refund_envelope(seeded, key)).json()
    assert retry["duplicate"] is True
    # The duplicate gets outcome *metadata*, never the original result body
    # (ADR-0002: raw results don't leave the gateway that produced them).
    assert "result" not in retry
    assert retry["execution"]["state"] == "SUCCEEDED"
    assert retry["execution"]["result_meta"] == {"result_hash": expected_hash}
    assert len(executor.ISSUED_REFUNDS) == 1


def test_idempotency_key_reuse_with_different_arguments_rejected(gateway_client, seeded):
    key = f"refund-{uuid.uuid4()}"
    _post(gateway_client, seeded, _refund_envelope(seeded, key))
    changed = _refund_envelope(seeded, key, arguments={"order_id": "ORD-1001", "amount": 25.0})
    response = _post(gateway_client, seeded, changed)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "execution.key-reused"
    assert len(executor.ISSUED_REFUNDS) == 1


def test_without_idempotency_key_each_request_executes(gateway_client, seeded):
    # The dedupe contract requires a key; two keyless requests are two
    # distinct actions, and both execute.
    for _ in range(2):
        envelope = _refund_envelope(seeded, idempotency_key=None)
        envelope.pop("idempotency_key")
        assert _post(gateway_client, seeded, envelope).status_code == 200
    assert len(executor.ISSUED_REFUNDS) == 2
