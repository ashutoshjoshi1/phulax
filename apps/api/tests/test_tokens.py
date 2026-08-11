"""Day 5 exit criteria (issuance side): short-lived, audience-restricted,
environment-bound, agent+version-bound dev tokens."""

import jwt
from phulax_api.settings import Settings, get_settings


def test_dev_token_carries_the_binding_claims(api_client, seeded):
    response = api_client.post("/v1/tokens", json={"session_id": seeded["session"]["id"]})
    assert response.status_code == 201
    body = response.json()
    claims = jwt.decode(
        body["token"],
        "fake-dev-key-change-me-not-a-secret-0001",
        algorithms=["HS256"],
        audience="phulax-gateway",
    )
    assert claims["sub"] == seeded["agent"]["id"]
    assert claims["ver"] == "1.0.0"
    assert claims["sid"] == seeded["session"]["id"]
    assert claims["env"] == "staging"
    assert claims["exp"] - claims["iat"] == 900  # minutes away, not months


def test_token_issuance_refused_outside_dev(api_app, api_client, seeded):
    api_app.dependency_overrides[get_settings] = lambda: Settings(phulax_env="production")
    response = api_client.post("/v1/tokens", json={"session_id": seeded["session"]["id"]})
    assert response.status_code == 403


def test_token_refused_for_revoked_agent(api_client, seeded):
    api_client.post(f"/v1/agents/{seeded['agent']['id']}/revoke")
    response = api_client.post("/v1/tokens", json={"session_id": seeded["session"]["id"]})
    assert response.status_code == 403
