from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from phulax_api.db import get_db
from phulax_api.models import Agent, AgentSession, AgentVersion
from phulax_api.schemas import SessionCreate, SessionOut, TokenOut, TokenRequest
from phulax_api.settings import Settings, get_settings
from phulax_api.tokens import build_claims, sign

router = APIRouter(prefix="/v1", tags=["sessions"])


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreate, db: Session = Depends(get_db)) -> AgentSession:
    version = db.get(AgentVersion, body.agent_version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="agent version not found")
    agent = db.get(Agent, version.agent_id)
    if agent is not None and agent.revoked_at is not None:
        raise HTTPException(status_code=403, detail="agent is revoked")
    session = AgentSession(agent_version_id=body.agent_version_id, environment=body.environment)
    db.add(session)
    db.flush()
    return session


@router.post("/tokens", response_model=TokenOut, status_code=201)
def issue_dev_token(
    body: TokenRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenOut:
    """Dev-only token issuance. Production issuance (workload identity,
    key rotation) is a later phase; this endpoint refuses outside dev."""
    if settings.phulax_env != "dev":
        raise HTTPException(status_code=403, detail="token issuance is dev-only")
    session = db.get(AgentSession, body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    version = db.get(AgentVersion, session.agent_version_id)
    assert version is not None  # FK guarantees it
    agent = db.get(Agent, version.agent_id)
    assert agent is not None
    if agent.revoked_at is not None:
        raise HTTPException(status_code=403, detail="agent is revoked")

    claims = build_claims(
        agent_id=agent.id,
        org_id=agent.org_id,
        agent_version_id=version.id,
        version=version.version,
        session_id=session.id,
        environment=session.environment,
        settings=settings,
    )
    return TokenOut(
        token=sign(claims, settings),
        expires_at=datetime.fromtimestamp(claims["exp"], tz=UTC),
        claims=claims,
    )
