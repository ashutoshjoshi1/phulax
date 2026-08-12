"""The gateway's action path — Phase 2: the gateway *enforces*.

Order encodes the protected-action definition of done: authenticate →
validate → evaluate policy (§11.4, deterministic) → **record the decision
event** → only then execute. If the allow event cannot be written, the
action does not proceed (docs/security/protected-action-dod.md, point 5).

Execution adds at-most-once semantics (plan §5.5): when the caller supplies
an idempotency key, the side effect happens only for the one request that
wins the control plane's atomic claim; duplicates read the recorded outcome.
"""

import hashlib
import logging
import time
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from phulax_policy import AgentState, Decision, PolicyRequest, evaluate
from phulax_policy.risk import RiskScore, score_request

from phulax_gateway import executor
from phulax_gateway.canonical import args_meta, canonical_hash, canonicalize
from phulax_gateway.control_plane import (
    ControlPlaneClient,
    ControlPlaneError,
    ExecutionConflict,
)
from phulax_gateway.envelope import ActionEnvelope
from phulax_gateway.health import health
from phulax_gateway.policy_store import PolicyStore
from phulax_gateway.settings import Settings, get_settings
from phulax_gateway.tokens import Claims, TokenError, validate_token

logger = logging.getLogger("phulax.gateway")


def create_app(
    settings: Settings | None = None,
    control_plane: ControlPlaneClient | None = None,
    policy_store: PolicyStore | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    client = control_plane or ControlPlaneClient(settings.control_plane_url)
    store = policy_store or PolicyStore(
        client, settings.policy_public_key, ttl_seconds=settings.policy_refresh_seconds
    )
    app = FastAPI(title="Phulax gateway", version="0.2.0")
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
    ) -> Any:
        started = time.monotonic()
        hashed = canonical_hash(
            tool_name=envelope.tool_name,
            environment=envelope.environment,
            arguments=envelope.arguments,
        )

        async def refuse(
            rule: str,
            detail: str,
            *,
            status: int = 403,
            verdict: str = "deny",
            decision: Decision | None = None,
            risk: RiskScore | None = None,
        ) -> HTTPException:
            recorded = await _record(
                client,
                envelope,
                claims,
                hashed,
                started,
                verdict=verdict,
                rule=rule,
                reason_codes=list(decision.reason_codes) if decision else [rule],
                matched_rules=list(decision.matched_rules) if decision else [],
                risk_score=risk.score if risk else None,
                policy_version=str(decision.policy_version) if decision else None,
            )
            return HTTPException(
                status_code=status,
                detail={
                    "effect": verdict,
                    "rule": rule,
                    "detail": detail,
                    "reason_codes": list(decision.reason_codes) if decision else [rule],
                    "matched_rules": list(decision.matched_rules) if decision else [],
                    "policy_version": str(decision.policy_version) if decision else None,
                    "event_recorded": recorded is not None,
                },
            )

        # Identity claims must match what the envelope asserts (T06).
        if (
            envelope.agent_id != claims.agent_id
            or envelope.session_id != claims.session_id
            or envelope.agent_version != claims.version
        ):
            raise await refuse(
                "identity.claims-mismatch", "envelope identity does not match token claims"
            )

        # A dev token against a production tool dies here, before evaluation.
        if envelope.environment != claims.environment:
            raise await refuse(
                "identity.environment-mismatch",
                f"token is bound to {claims.environment!r}, "
                f"request is for {envelope.environment!r}",
            )

        agent = await client.get_agent(claims.agent_id)
        if agent is None:
            raise await refuse("identity.agent-unknown", "agent not found in registry")

        tool = await client.get_tool(claims.org_id, envelope.tool_name)
        if tool is None:
            raise await refuse("tool.unknown", f"tool {envelope.tool_name!r} is not registered")
        try:
            Draft202012Validator(tool["args_schema"]).validate(envelope.arguments)
        except ValidationError as exc:
            raise await refuse("tool.args-schema", exc.message) from None

        # Policy evaluation (plan §11.4). No verified bundle ⇒ nothing safe
        # to enforce with ⇒ fail closed, retryably.
        bundle = await store.get(claims.org_id)
        if bundle is None:
            raise await refuse(
                "policy.bundle-unavailable",
                "no verified policy bundle available; failing closed",
                status=503,
            )

        risk = score_request(
            side_effect=tool.get("side_effect"),
            sensitivity=tool.get("sensitivity"),
            environment=envelope.environment,
            amount=envelope.arguments.get("amount"),
        )
        decision = evaluate(
            PolicyRequest(
                tool_name=envelope.tool_name,
                environment=envelope.environment,
                agent_id=str(claims.agent_id),
                arguments=envelope.arguments,
            ),
            bundle,
            AgentState(revoked=agent.get("revoked_at") is not None),
        )
        primary = decision.winning_rules[0] if decision.winning_rules else decision.reason_codes[0]

        if decision.effect in ("deny", "freeze"):
            raise await refuse(
                primary,
                "policy refused this action",
                verdict=decision.effect,
                decision=decision,
                risk=risk,
            )

        # Record first; anything that proceeds only does so with evidence.
        recorded = await _record(
            client,
            envelope,
            claims,
            hashed,
            started,
            verdict=decision.effect,
            rule=primary,
            reason_codes=list(decision.reason_codes),
            matched_rules=list(decision.matched_rules),
            risk_score=risk.score,
            policy_version=str(decision.policy_version),
            raise_on_failure=True,
        )
        base = {
            "request_id": str(envelope.request_id),
            "effect": decision.effect,
            "rule": primary,
            "reason_codes": list(decision.reason_codes),
            "matched_rules": list(decision.matched_rules),
            "policy_version": str(decision.policy_version),
            "canonical_hash": hashed,
            "risk_score": risk.score,
            "event": recorded,
        }

        if decision.effect == "require_approval":
            # The approval that arrives later (Phase 3) authorizes exactly
            # this canonical hash — mutated arguments become a mismatch.
            return JSONResponse(
                status_code=202,
                content=base
                | {"approver_role": decision.approver_role, "approval_binding": hashed},
            )

        # ALLOW. Without an idempotency key there is no dedupe contract.
        if envelope.idempotency_key is None:
            return base | {"result": executor.execute(envelope.tool_name, envelope.arguments)}

        try:
            claim = await client.claim_execution(
                {
                    "org_id": str(claims.org_id),
                    "idempotency_key": envelope.idempotency_key,
                    "request_id": str(envelope.request_id),
                    "canonical_hash": hashed,
                }
            )
        except ExecutionConflict as exc:
            raise HTTPException(status_code=409, detail=exc.detail) from exc
        except ControlPlaneError as exc:
            # No claim ⇒ no side effect. Retry-safe by construction.
            raise HTTPException(
                status_code=502, detail="execution claim could not be recorded"
            ) from exc

        if not claim["claimed"]:
            # A duplicate never re-executes; it reads the recorded outcome.
            # Metadata only — the original result body never left the gateway.
            return base | {
                "duplicate": True,
                "execution": {
                    "execution_id": claim["execution_id"],
                    "state": claim["state"],
                    "result_meta": claim["result_meta"],
                },
            }

        try:
            result = executor.execute(envelope.tool_name, envelope.arguments)
        except Exception:
            await _complete_quietly(client, claim["execution_id"], "FAILED", {})
            raise
        result_meta = {"result_hash": hashlib.sha256(canonicalize(result).encode()).hexdigest()}
        await _complete_quietly(client, claim["execution_id"], "SUCCEEDED", result_meta)
        return base | {
            "result": result,
            "duplicate": False,
            "execution": {
                "execution_id": claim["execution_id"],
                "state": "SUCCEEDED",
                "result_meta": result_meta,
            },
        }

    return app


async def _record(
    client: ControlPlaneClient,
    envelope: ActionEnvelope,
    claims: Claims,
    hashed: str,
    started: float,
    *,
    verdict: str,
    rule: str,
    reason_codes: list[str],
    matched_rules: list[str],
    risk_score: int | None,
    policy_version: str | None,
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
            "reason_codes": reason_codes,
            "matched_rules": matched_rules,
            "risk_score": risk_score,
            "policy_version": policy_version,
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
        logger.warning("%s event not recorded: %s", verdict, exc)
        return None


async def _complete_quietly(
    client: ControlPlaneClient, execution_id: str, state: str, result_meta: dict
) -> None:
    """Completion is evidence, not permission — the side effect already
    happened, so a failure here is logged, never surfaced as an error."""
    try:
        await client.complete_execution(execution_id, state, result_meta)
    except ControlPlaneError as exc:
        logger.warning("execution %s not marked %s: %s", execution_id, state, exc)


app = create_app()
