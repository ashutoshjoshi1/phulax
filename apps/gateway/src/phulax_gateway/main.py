"""The gateway's action path: the walking skeleton's spine.

Order matters and encodes the protected-action definition of done:
authenticate → validate → (policy: skeleton default rules) → **record the
decision event** → only then execute. If the event cannot be written, the
action does not proceed (docs/security/protected-action-dod.md, point 5).
"""

import logging
import time
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from phulax_gateway import executor
from phulax_gateway.canonical import args_meta, canonical_hash
from phulax_gateway.control_plane import ControlPlaneClient, ControlPlaneError
from phulax_gateway.envelope import ActionEnvelope
from phulax_gateway.health import health
from phulax_gateway.settings import Settings, get_settings
from phulax_gateway.tokens import Claims, TokenError, validate_token

logger = logging.getLogger("phulax.gateway")

POLICY_VERSION = "walking-skeleton-0"


def create_app(
    settings: Settings | None = None,
    control_plane: ControlPlaneClient | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    client = control_plane or ControlPlaneClient(settings.control_plane_url)
    app = FastAPI(title="Phulax gateway", version="0.1.0")
    app.get("/health", tags=["ops"])(health)

    def bearer_claims(authorization: str = Header(default="")) -> Claims:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="missing bearer token")
        try:
            return validate_token(
                token, key=settings.gateway_signing_key, audience=settings.token_audience
            )
        except TokenError as exc:
            raise HTTPException(
                status_code=401, detail={"code": exc.code, "detail": exc.detail}
            ) from exc

    @app.post("/v1/actions")
    async def submit_action(
        envelope: ActionEnvelope, claims: Claims = Depends(bearer_claims)
    ) -> dict[str, Any]:
        started = time.monotonic()
        hashed = canonical_hash(
            tool_name=envelope.tool_name,
            environment=envelope.environment,
            arguments=envelope.arguments,
        )

        async def block(rule: str, detail: str) -> HTTPException:
            recorded = await _record(client, envelope, claims, hashed, "block", rule, started)
            return HTTPException(
                status_code=403,
                detail={
                    "verdict": "block",
                    "rule": rule,
                    "detail": detail,
                    "event_recorded": recorded,
                },
            )

        # Identity claims must match what the envelope asserts (T06).
        if (
            envelope.agent_id != claims.agent_id
            or envelope.session_id != claims.session_id
            or envelope.agent_version != claims.version
        ):
            raise await block(
                "identity.claims-mismatch", "envelope identity does not match token claims"
            )

        # A dev token against a production tool dies here, before evaluation.
        if envelope.environment != claims.environment:
            raise await block(
                "identity.environment-mismatch",
                f"token is bound to {claims.environment!r}, "
                f"request is for {envelope.environment!r}",
            )

        agent = await client.get_agent(claims.agent_id)
        if agent is None:
            raise await block("identity.agent-unknown", "agent not found in registry")
        if agent.get("revoked_at") is not None:
            raise await block("identity.agent-revoked", "agent has been revoked")

        tool = await client.get_tool(claims.org_id, envelope.tool_name)
        if tool is None:
            raise await block("tool.unknown", f"tool {envelope.tool_name!r} is not registered")
        try:
            Draft202012Validator(tool["args_schema"]).validate(envelope.arguments)
        except ValidationError as exc:
            raise await block("tool.args-schema", exc.message) from None

        # Record first; execute only if the evidence exists.
        recorded_event = await _record(
            client,
            envelope,
            claims,
            hashed,
            "allow",
            "skeleton.authenticated-known-tool",
            started,
            raise_on_failure=True,
        )
        result = executor.execute(envelope.tool_name, envelope.arguments)
        return {
            "request_id": str(envelope.request_id),
            "verdict": "allow",
            "rule": "skeleton.authenticated-known-tool",
            "policy_version": POLICY_VERSION,
            "canonical_hash": hashed,
            "result": result,
            "event": recorded_event,
        }

    return app


async def _record(
    client: ControlPlaneClient,
    envelope: ActionEnvelope,
    claims: Claims,
    hashed: str,
    verdict: str,
    rule: str,
    started: float,
    raise_on_failure: bool = False,
) -> Any:
    """Ship the metadata-first decision event to the control plane."""
    payload = {
        "action_request": {
            "request_id": str(envelope.request_id),
            "idempotency_key": envelope.idempotency_key,
            "session_id": str(claims.session_id),
            "tool_name": envelope.tool_name,
            "environment": envelope.environment,
            "acting_user_id": (str(envelope.acting_user_id) if envelope.acting_user_id else None),
            "canonical_hash": hashed,
            "args_meta": args_meta(envelope.arguments),
            "requested_at": envelope.requested_at.isoformat(),
        },
        "event": {
            "verdict": verdict,
            "rule": rule,
            "policy_version": POLICY_VERSION,
            "latency_ms": int((time.monotonic() - started) * 1000),
        },
    }
    try:
        return await client.post_event(payload)
    except ControlPlaneError as exc:
        if raise_on_failure:
            # No evidence ⇒ no execution.
            raise HTTPException(
                status_code=502, detail="decision event could not be recorded"
            ) from exc
        logger.warning("block event not recorded: %s", exc)
        return None


app = create_app()
