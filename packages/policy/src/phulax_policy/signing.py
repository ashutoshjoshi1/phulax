"""Signed policy bundles (plan §7.2 Day 10, threat T08).

The control plane signs ``{version, rules}`` with an Ed25519 private key;
the gateway verifies with the public key it was configured with out-of-band.
What this buys: a compromised network path or storage can *corrupt* a bundle
but cannot *forge* one. What it does not buy: protection from a compromised
control plane — the signer can sign anything.

The payload is canonical JSON (sorted keys, minimal separators) over the
*transfer* representation, so JSONB key reordering between publish and fetch
cannot break verification.
"""

import base64
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def generate_keypair() -> tuple[str, str]:
    """A new Ed25519 keypair as (private_b64, public_b64), raw 32 bytes each."""
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    return (
        base64.b64encode(private.private_bytes_raw()).decode(),
        base64.b64encode(public.public_bytes_raw()).decode(),
    )


def public_key_from_private(private_key_b64: str) -> str:
    """Derive the base64 public key for a base64 private seed."""
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64))
    return base64.b64encode(key.public_key().public_bytes_raw()).decode()


def bundle_payload(version: int, rules_data: list[dict[str, Any]]) -> bytes:
    """The exact bytes that are signed — both sides must agree on these."""
    document = {"version": version, "rules": rules_data}
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign_bundle(private_key_b64: str, *, version: int, rules_data: list[dict[str, Any]]) -> str:
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64))
    return base64.b64encode(key.sign(bundle_payload(version, rules_data))).decode()


def verify_bundle(
    public_key_b64: str,
    *,
    version: int,
    rules_data: list[dict[str, Any]],
    signature: str,
) -> bool:
    """True only if the signature covers exactly this version and rules.

    Never raises on bad input: a tampered bundle is a *rejected* bundle,
    not a crashed gateway (fail closed, keep enforcing).
    """
    try:
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        key.verify(base64.b64decode(signature), bundle_payload(version, rules_data))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
