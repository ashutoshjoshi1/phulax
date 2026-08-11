"""Agent token validation (plan §7, Day 5; threat T06).

A key says "someone who has the key." A signed claim set says
"refund-agent v1.0.0, staging, expires 14:32, for the gateway only."
"""

import uuid
from dataclasses import dataclass

import jwt

REQUIRED_CLAIMS = ("sub", "org", "avid", "ver", "sid", "env", "exp", "aud")


class TokenError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class Claims:
    agent_id: uuid.UUID
    org_id: uuid.UUID
    agent_version_id: uuid.UUID
    version: str
    session_id: uuid.UUID
    environment: str


def validate_token(token: str, *, key: str, audience: str) -> Claims:
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["HS256"],
            audience=audience,
            options={"require": list(REQUIRED_CLAIMS)},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token_expired", "token has expired") from exc
    except jwt.InvalidAudienceError as exc:
        raise TokenError("wrong_audience", f"token audience is not {audience!r}") from exc
    except jwt.MissingRequiredClaimError as exc:
        raise TokenError("missing_claim", str(exc)) from exc
    except jwt.InvalidTokenError as exc:  # tampered signature, malformed, …
        raise TokenError("invalid_token", str(exc)) from exc

    try:
        return Claims(
            agent_id=uuid.UUID(payload["sub"]),
            org_id=uuid.UUID(payload["org"]),
            agent_version_id=uuid.UUID(payload["avid"]),
            version=payload["ver"],
            session_id=uuid.UUID(payload["sid"]),
            environment=payload["env"],
        )
    except (ValueError, TypeError) as exc:
        raise TokenError("invalid_claims", "claims are not well-formed") from exc
