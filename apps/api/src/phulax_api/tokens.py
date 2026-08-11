"""Dev agent-token issuance (plan §7, Day 5).

Agent tokens are short-lived, audience-restricted, environment-bound, and
agent+version-bound — a signed claim set, not a shared API key (T06).
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from phulax_api.settings import Settings


def build_claims(
    *,
    agent_id: uuid.UUID,
    org_id: uuid.UUID,
    agent_version_id: uuid.UUID,
    version: str,
    session_id: uuid.UUID,
    environment: str,
    settings: Settings,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(UTC)
    return {
        "iss": settings.token_issuer,
        "aud": settings.token_audience,  # replay against another service fails
        "sub": str(agent_id),
        "org": str(org_id),
        "avid": str(agent_version_id),
        "ver": version,  # attribution: exactly which agent version
        "sid": str(session_id),
        "env": environment,  # dev token against prod tool: rejected pre-evaluation
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.token_ttl_seconds)).timestamp()),
    }


def sign(claims: dict, settings: Settings) -> str:
    return jwt.encode(claims, settings.gateway_signing_key, algorithm="HS256")
