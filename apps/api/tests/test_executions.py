"""Day 13, control-plane half: the atomic idempotency claim (plan §5.5, T07).

Only one atomic transition may enter EXECUTING for an idempotency key —
proven here at the claim endpoint, and again end-to-end in the gateway's
test_idempotency.py.
"""

import uuid
from concurrent.futures import ThreadPoolExecutor

HASH_A = "a" * 64
HASH_B = "b" * 64


def _claim(api_client, seeded, key="idem-1", canonical_hash=HASH_A):
    return api_client.post(
        "/v1/executions/claim",
        json={
            "org_id": seeded["org"]["id"],
            "idempotency_key": key,
            "request_id": str(uuid.uuid4()),
            "canonical_hash": canonical_hash,
        },
    )


def test_first_claim_wins_and_enters_executing(api_client, seeded):
    response = _claim(api_client, seeded)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["claimed"] is True
    assert body["state"] == "EXECUTING"


def test_duplicate_claim_reads_the_outcome_instead_of_reexecuting(api_client, seeded):
    first = _claim(api_client, seeded).json()
    api_client.post(
        f"/v1/executions/{first['execution_id']}/complete",
        json={"state": "SUCCEEDED", "result_meta": {"result_hash": HASH_B}},
    ).raise_for_status()

    retry = _claim(api_client, seeded).json()
    assert retry["claimed"] is False
    assert retry["state"] == "SUCCEEDED"
    assert retry["result_meta"] == {"result_hash": HASH_B}


def test_idempotency_key_reuse_with_different_request_rejected(api_client, seeded):
    _claim(api_client, seeded, canonical_hash=HASH_A)
    response = _claim(api_client, seeded, canonical_hash=HASH_B)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "execution.key-reused"


def test_complete_requires_executing_state(api_client, seeded):
    first = _claim(api_client, seeded).json()
    complete = {"state": "SUCCEEDED", "result_meta": {}}
    api_client.post(
        f"/v1/executions/{first['execution_id']}/complete", json=complete
    ).raise_for_status()
    again = api_client.post(f"/v1/executions/{first['execution_id']}/complete", json=complete)
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "execution.not-executing"


def test_concurrent_idempotent_claims_admit_exactly_one_winner(api_client, seeded):
    # Scenario #10 at the claim layer: two duplicates race; the DB's
    # compare-and-set admits one into EXECUTING.
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: _claim(api_client, seeded, key="idem-race").json(), range(2))
        )
    assert sorted(result["claimed"] for result in results) == [False, True]
    assert {result["execution_id"] for result in results} == {results[0]["execution_id"]}
