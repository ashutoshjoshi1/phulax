"""Day 3 exit criteria: registration returns id+version; duplicates rejected."""


def test_agent_registration_returns_id_and_version(seeded):
    agent = seeded["agent"]
    assert agent["id"]
    assert agent["latest_version"]["version"] == "1.0.0"
    assert len(agent["latest_version"]["manifest_hash"]) == 64


def test_duplicate_agent_registration_rejected(api_client, seeded):
    response = api_client.post(
        "/v1/agents",
        json={
            "org_id": seeded["org"]["id"],
            "name": "refund-agent",
            "owner_user_id": seeded["owner"]["id"],
            "version": "9.9.9",
            "manifest": {},
        },
    )
    assert response.status_code == 409


def test_new_manifest_is_a_new_immutable_version(api_client, seeded):
    agent_id = seeded["agent"]["id"]
    response = api_client.post(
        f"/v1/agents/{agent_id}/versions",
        json={"version": "1.1.0", "manifest": {"model": "claude-sonnet-5", "tools": []}},
    )
    assert response.status_code == 201
    assert response.json()["version"] == "1.1.0"
    # same manifest, same version string again → rejected, never updated
    duplicate = api_client.post(
        f"/v1/agents/{agent_id}/versions",
        json={"version": "1.1.0", "manifest": {"anything": "else"}},
    )
    assert duplicate.status_code == 409
    versions = api_client.get(f"/v1/agents/{agent_id}/versions").json()
    assert {v["version"] for v in versions} == {"1.0.0", "1.1.0"}


def test_same_manifest_same_hash_different_key_order(api_client, seeded):
    agent_id = seeded["agent"]["id"]
    a = api_client.post(
        f"/v1/agents/{agent_id}/versions",
        json={"version": "2.0.0", "manifest": {"a": 1, "b": 2}},
    ).json()
    b = api_client.post(
        f"/v1/agents/{agent_id}/versions",
        json={"version": "2.0.1", "manifest": {"b": 2, "a": 1}},
    ).json()
    assert a["manifest_hash"] == b["manifest_hash"]


def test_revoke_agent_sets_revoked_at(api_client, seeded):
    agent_id = seeded["agent"]["id"]
    response = api_client.post(f"/v1/agents/{agent_id}/revoke")
    assert response.status_code == 200
    assert response.json()["revoked_at"] is not None
    # revoked agents cannot open new sessions
    session = api_client.post(
        "/v1/sessions",
        json={
            "agent_version_id": seeded["agent"]["latest_version"]["id"],
            "environment": "staging",
        },
    )
    assert session.status_code == 403
