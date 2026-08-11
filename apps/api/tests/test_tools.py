"""Day 4 exit criteria: invalid schema rejected; tools carry sensitivity
and side-effect class."""


def _tool(org_id: str, **overrides) -> dict:
    body = {
        "org_id": org_id,
        "name": "issue_refund",
        "description": "Refund a payment (simulated)",
        "args_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
            "required": ["order_id", "amount"],
        },
        "sensitivity": "high",
        "side_effect": "write",
    }
    return body | overrides


def test_tool_registration(api_client, seeded):
    response = api_client.post("/v1/tools", json=_tool(seeded["org"]["id"]))
    assert response.status_code == 201
    body = response.json()
    assert body["sensitivity"] == "high"
    assert body["side_effect"] == "write"


def test_invalid_json_schema_rejected(api_client, seeded):
    bad = _tool(seeded["org"]["id"], args_schema={"type": "not-a-real-type"})
    response = api_client.post("/v1/tools", json=bad)
    assert response.status_code == 422
    assert "JSON Schema" in response.json()["detail"]


def test_duplicate_tool_rejected(api_client, seeded):
    # read_order is already seeded
    response = api_client.post("/v1/tools", json=_tool(seeded["org"]["id"], name="read_order"))
    assert response.status_code == 409


def test_unknown_sensitivity_rejected(api_client, seeded):
    response = api_client.post(
        "/v1/tools", json=_tool(seeded["org"]["id"], sensitivity="catastrophic")
    )
    assert response.status_code == 422
