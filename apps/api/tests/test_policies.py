"""Day 10, control-plane half: versioned, signed bundle publishing."""

from phulax_api.settings import get_settings
from phulax_policy.examples import CANONICAL_BUNDLE_YAML
from phulax_policy.signing import public_key_from_private, verify_bundle


def _publish(api_client, org_id, document=CANONICAL_BUNDLE_YAML):
    return api_client.post("/v1/policy-bundles", json={"org_id": org_id, "document": document})


def test_publish_assigns_monotonic_versions(api_client, seeded):
    # seeded already published version 1
    second = _publish(api_client, seeded["org"]["id"])
    assert second.status_code == 201, second.text
    assert second.json()["version"] == seeded["bundle"]["version"] + 1

    latest = api_client.get(
        "/v1/policy-bundles/latest", params={"org_id": seeded["org"]["id"]}
    ).json()
    assert latest["version"] == second.json()["version"]


def test_published_bundle_signature_verifies(api_client, seeded):
    bundle = seeded["bundle"]
    public_key = public_key_from_private(get_settings().policy_signing_key)
    assert verify_bundle(
        public_key,
        version=bundle["version"],
        rules_data=bundle["rules"],
        signature=bundle["signature"],
    )


def test_invalid_rules_rejected_with_all_errors(api_client, seeded):
    response = _publish(
        api_client,
        seeded["org"]["id"],
        document="""
rules:
  - id: allow-everything
    effect: allow
    match: {}
""",
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "policy.invalid-rules"
    assert any("must constrain" in error for error in detail["errors"])


def test_unknown_org_rejected(api_client):
    response = _publish(api_client, "00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_no_bundle_yet_is_404(api_client):
    org = api_client.post("/v1/organizations", json={"name": "empty-org"}).json()
    response = api_client.get("/v1/policy-bundles/latest", params={"org_id": org["id"]})
    assert response.status_code == 404
