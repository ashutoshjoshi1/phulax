"""The gateway's verified policy cache (plan §7.2 Day 10, T08, T14).

Rules of the cache, in threat order:

- A bundle serves decisions only after its Ed25519 signature verifies
  against the out-of-band public key *and* it re-parses under the
  constrained schema. A signature proves who published, not that the
  content is well-formed.
- A tampered or malformed bundle is rejected and the **previous valid
  bundle stays active** — fail closed, but keep enforcing. A bad publish
  must not brick the gateway (T08).
- A control-plane outage serves the cached bundle (T14). Staleness expiry
  is a Phase 4 concern; v1 keeps enforcing what it last verified.
- No bundle ever verified ⇒ there is nothing safe to enforce with ⇒
  callers fail closed (deny).
"""

import logging
import time
import uuid
from dataclasses import dataclass

from phulax_policy import Bundle, PolicyError, parse_rules_data, verify_bundle

from phulax_gateway.control_plane import ControlPlaneClient, ControlPlaneError

logger = logging.getLogger("phulax.gateway.policy")


@dataclass
class _Cached:
    bundle: Bundle
    fetched_at: float


class PolicyStore:
    def __init__(
        self,
        client: ControlPlaneClient,
        public_key: str,
        ttl_seconds: float = 30.0,
    ) -> None:
        self._client = client
        self._public_key = public_key
        self._ttl = ttl_seconds
        self._cache: dict[uuid.UUID, _Cached] = {}

    async def get(self, org_id: uuid.UUID) -> Bundle | None:
        """The active bundle for an org, or None if none was ever verified."""
        cached = self._cache.get(org_id)
        now = time.monotonic()
        if cached is not None and now - cached.fetched_at < self._ttl:
            return cached.bundle

        try:
            data = await self._client.get_latest_bundle(org_id)
        except ControlPlaneError as exc:
            logger.warning("bundle refresh failed, serving cached policy (T14): %s", exc)
            return cached.bundle if cached else None

        if data is None:
            # Control plane has no bundle for this org — never downgrade
            # to unenforced; keep the last verified bundle if there is one.
            return cached.bundle if cached else None

        bundle = self._verify(data)
        if bundle is None:
            if cached is not None:
                return cached.bundle  # rejected ⇒ previous valid bundle stays active
            return None
        self._cache[org_id] = _Cached(bundle=bundle, fetched_at=now)
        return bundle

    def _verify(self, data: dict) -> Bundle | None:
        version = data.get("version")
        rules_data = data.get("rules")
        signature = data.get("signature")
        if not isinstance(version, int) or not isinstance(rules_data, list):
            logger.warning("bundle rejected: malformed transfer document")
            return None
        if not verify_bundle(
            self._public_key, version=version, rules_data=rules_data, signature=str(signature)
        ):
            logger.warning("bundle v%s rejected: signature verification failed (T08)", version)
            return None
        try:
            rules = parse_rules_data({"rules": rules_data})
        except PolicyError as exc:
            logger.warning("bundle v%s rejected: signed but not well-formed: %s", version, exc)
            return None
        return Bundle(version=version, rules=rules)
