"""Day 10: signed bundles — corruption and forgery are different threats.

A signature proves *who published*, not *what is wise*. These tests pin the
property that matters: any byte of drift between what was signed and what
was received fails verification (T08).
"""

from phulax_policy.signing import generate_keypair, sign_bundle, verify_bundle

RULES = [
    {"id": "allow-read-order", "effect": "allow", "match": {"tool": "read_order"}},
]


def test_signature_roundtrip():
    private_key, public_key = generate_keypair()
    signature = sign_bundle(private_key, version=42, rules_data=RULES)
    assert verify_bundle(public_key, version=42, rules_data=RULES, signature=signature)


def test_key_order_does_not_matter():
    # JSONB storage may reorder object keys; the canonical payload must not care.
    private_key, public_key = generate_keypair()
    signature = sign_bundle(private_key, version=1, rules_data=RULES)
    reordered = [{"match": {"tool": "read_order"}, "effect": "allow", "id": "allow-read-order"}]
    assert verify_bundle(public_key, version=1, rules_data=reordered, signature=signature)


def test_tampered_rules_rejected():
    private_key, public_key = generate_keypair()
    signature = sign_bundle(private_key, version=1, rules_data=RULES)
    tampered = [{**RULES[0], "effect": "deny"}]
    assert not verify_bundle(public_key, version=1, rules_data=tampered, signature=signature)


def test_tampered_version_rejected():
    # Replaying old rules under a new version number is still tampering.
    private_key, public_key = generate_keypair()
    signature = sign_bundle(private_key, version=1, rules_data=RULES)
    assert not verify_bundle(public_key, version=2, rules_data=RULES, signature=signature)


def test_wrong_key_rejected():
    private_key, _ = generate_keypair()
    _, other_public = generate_keypair()
    signature = sign_bundle(private_key, version=1, rules_data=RULES)
    assert not verify_bundle(other_public, version=1, rules_data=RULES, signature=signature)


def test_garbage_signature_rejected_not_raised():
    _, public_key = generate_keypair()
    assert not verify_bundle(public_key, version=1, rules_data=RULES, signature="not-base64!!")
