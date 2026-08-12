"""Day 10, gateway half: verify, cache, and never brick.

The exit criterion with teeth: a tampered bundle is rejected AND the
previous valid bundle stays active — fail closed, keep enforcing.
"""

import asyncio
import uuid

from phulax_gateway.control_plane import ControlPlaneError
from phulax_gateway.policy_store import PolicyStore
from phulax_policy import generate_keypair, sign_bundle

ORG = uuid.uuid4()
RULES = [{"id": "allow-read-order", "effect": "allow", "match": {"tool": "read_order"}}]


class StubControlPlane:
    """Serves whatever bundle document it's told to; can simulate outage."""

    def __init__(self) -> None:
        self.response: dict | None = None
        self.outage = False

    async def get_latest_bundle(self, org_id):
        if self.outage:
            raise ControlPlaneError("control plane unreachable")
        return self.response


def _signed_bundle(private_key: str, version: int, rules=None) -> dict:
    rules = RULES if rules is None else rules
    return {
        "version": version,
        "rules": rules,
        "signature": sign_bundle(private_key, version=version, rules_data=rules),
    }


def _store_with(client: StubControlPlane, public_key: str) -> PolicyStore:
    return PolicyStore(client, public_key, ttl_seconds=0)  # refresh on every get


def _get(store: PolicyStore):
    return asyncio.run(store.get(ORG))


def test_valid_bundle_is_served():
    private_key, public_key = generate_keypair()
    client = StubControlPlane()
    client.response = _signed_bundle(private_key, 1)
    bundle = _get(_store_with(client, public_key))
    assert bundle is not None
    assert bundle.version == 1
    assert bundle.rules[0].id == "allow-read-order"


def test_tampered_bundle_rejected_previous_stays_active():
    private_key, public_key = generate_keypair()
    client = StubControlPlane()
    store = _store_with(client, public_key)

    client.response = _signed_bundle(private_key, 1)
    assert _get(store).version == 1

    # v2 arrives with its rules flipped after signing — signature mismatch.
    tampered = _signed_bundle(private_key, 2)
    tampered["rules"] = [{"id": "allow-read-order", "effect": "freeze", "match": {}}]
    client.response = tampered

    active = _get(store)
    assert active is not None
    assert active.version == 1  # previous valid bundle stays active
    assert active.rules[0].effect == "allow"


def test_control_plane_outage_serves_cached_bundle():
    # T14: decisions keep working while the control plane is down.
    private_key, public_key = generate_keypair()
    client = StubControlPlane()
    store = _store_with(client, public_key)
    client.response = _signed_bundle(private_key, 3)
    assert _get(store).version == 3

    client.outage = True
    assert _get(store).version == 3


def test_no_bundle_ever_verified_yields_none():
    _, public_key = generate_keypair()
    client = StubControlPlane()  # responds with None: nothing published
    assert _get(_store_with(client, public_key)) is None

    client.outage = True
    assert _get(_store_with(client, public_key)) is None


def test_signed_but_malformed_bundle_rejected():
    # A signature proves who published, not that the content is safe to
    # evaluate: a well-signed document that fails the constrained parser
    # is rejected the same way tampering is.
    private_key, public_key = generate_keypair()
    client = StubControlPlane()
    store = _store_with(client, public_key)
    client.response = _signed_bundle(private_key, 1)
    assert _get(store).version == 1

    unsafe = [{"id": "allow-everything", "effect": "allow", "match": {}}]
    client.response = _signed_bundle(private_key, 2, rules=unsafe)
    assert _get(store).version == 1  # previous valid bundle stays active


def test_valid_newer_bundle_replaces_the_cache():
    private_key, public_key = generate_keypair()
    client = StubControlPlane()
    store = _store_with(client, public_key)
    client.response = _signed_bundle(private_key, 1)
    assert _get(store).version == 1
    client.response = _signed_bundle(private_key, 2)
    assert _get(store).version == 2
