import hashlib
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from phulax_api.db import get_db
from phulax_api.models import Agent, AgentVersion, Organization, User
from phulax_api.schemas import AgentOut, AgentRegister, AgentVersionOut, VersionCreate

router = APIRouter(prefix="/v1", tags=["agents"])


def manifest_hash(manifest: dict) -> str:
    """Stable hash of the agent manifest. Deliberately simple (sorted-key
    JSON); request canonicalization proper lives in the gateway."""
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _latest_version(db: Session, agent_id: uuid.UUID) -> AgentVersion | None:
    return db.scalar(
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.created_at.desc(), AgentVersion.version.desc())
        .limit(1)
    )


def _agent_out(db: Session, agent: Agent) -> AgentOut:
    latest = _latest_version(db, agent.id)
    return AgentOut(
        id=agent.id,
        org_id=agent.org_id,
        name=agent.name,
        owner_user_id=agent.owner_user_id,
        revoked_at=agent.revoked_at,
        latest_version=AgentVersionOut.model_validate(latest, from_attributes=True)
        if latest
        else None,
    )


@router.post("/agents", response_model=AgentOut, status_code=201)
def register_agent(body: AgentRegister, db: Session = Depends(get_db)) -> AgentOut:
    if db.get(Organization, body.org_id) is None:
        raise HTTPException(status_code=404, detail="organization not found")
    if db.get(User, body.owner_user_id) is None:
        raise HTTPException(status_code=404, detail="owner user not found")
    duplicate = db.scalar(select(Agent).where(Agent.org_id == body.org_id, Agent.name == body.name))
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="agent already registered")

    agent = Agent(org_id=body.org_id, name=body.name, owner_user_id=body.owner_user_id)
    db.add(agent)
    db.flush()
    version = AgentVersion(
        agent_id=agent.id,
        version=body.version,
        manifest=body.manifest,
        manifest_hash=manifest_hash(body.manifest),
    )
    db.add(version)
    db.flush()
    return _agent_out(db, agent)


@router.get("/agents", response_model=list[AgentOut])
def list_agents(
    org_id: uuid.UUID | None = None,
    name: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(Agent)
    if org_id is not None:
        query = query.where(Agent.org_id == org_id)
    if name is not None:
        query = query.where(Agent.name == name)
    return [_agent_out(db, agent) for agent in db.scalars(query).all()]


@router.get("/agents/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: uuid.UUID, db: Session = Depends(get_db)) -> AgentOut:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return _agent_out(db, agent)


@router.post("/agents/{agent_id}/versions", response_model=AgentVersionOut, status_code=201)
def add_version(
    agent_id: uuid.UUID, body: VersionCreate, db: Session = Depends(get_db)
) -> AgentVersion:
    """New manifest ⇒ new immutable version. There is no update endpoint,
    by design (plan §11.1)."""
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    duplicate = db.scalar(
        select(AgentVersion).where(
            AgentVersion.agent_id == agent_id, AgentVersion.version == body.version
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="version already exists")
    version = AgentVersion(
        agent_id=agent_id,
        version=body.version,
        manifest=body.manifest,
        manifest_hash=manifest_hash(body.manifest),
    )
    db.add(version)
    db.flush()
    return version


@router.get("/agents/{agent_id}/versions", response_model=list[AgentVersionOut])
def list_versions(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    if db.get(Agent, agent_id) is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return db.scalars(select(AgentVersion).where(AgentVersion.agent_id == agent_id)).all()


@router.post("/agents/{agent_id}/revoke", response_model=AgentOut)
def revoke_agent(agent_id: uuid.UUID, db: Session = Depends(get_db)) -> AgentOut:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    if agent.revoked_at is None:
        agent.revoked_at = datetime.now(UTC)
        db.flush()
    return _agent_out(db, agent)
