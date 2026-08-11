import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Sensitivity = Literal["low", "medium", "high"]
SideEffect = Literal["read", "write", "irreversible"]
Verdict = Literal["allow", "block", "hold"]


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class OrgOut(BaseModel):
    id: uuid.UUID
    name: str


class UserCreate(BaseModel):
    org_id: uuid.UUID
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    name: str


class AgentRegister(BaseModel):
    """Registration always creates the agent together with its first
    immutable version — an agent without a version is unattributable."""

    org_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    owner_user_id: uuid.UUID
    version: str = Field(min_length=1, max_length=100)
    manifest: dict = Field(description="Code/config/model/tool manifest; hashed for attribution")


class AgentVersionOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    version: str
    manifest_hash: str


class AgentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    owner_user_id: uuid.UUID
    revoked_at: datetime | None
    latest_version: AgentVersionOut | None = None


class VersionCreate(BaseModel):
    version: str = Field(min_length=1, max_length=100)
    manifest: dict


class ToolCreate(BaseModel):
    org_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    args_schema: dict = Field(description="JSON Schema (draft 2020-12) for arguments")
    sensitivity: Sensitivity
    side_effect: SideEffect


class ToolOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str
    args_schema: dict
    sensitivity: Sensitivity
    side_effect: SideEffect


class SessionCreate(BaseModel):
    agent_version_id: uuid.UUID
    environment: str = Field(min_length=1, max_length=50)


class SessionOut(BaseModel):
    id: uuid.UUID
    agent_version_id: uuid.UUID
    environment: str
    started_at: datetime


class TokenRequest(BaseModel):
    session_id: uuid.UUID


class TokenOut(BaseModel):
    token: str
    expires_at: datetime
    claims: dict


class ActionRequestIn(BaseModel):
    """Metadata only (ADR-0002): the gateway never sends raw arguments."""

    request_id: uuid.UUID
    idempotency_key: str | None = None
    session_id: uuid.UUID
    tool_name: str
    environment: str
    acting_user_id: uuid.UUID | None = None
    canonical_hash: str = Field(min_length=64, max_length=64)
    args_meta: dict = Field(default_factory=dict)
    requested_at: datetime


class DecisionIn(BaseModel):
    verdict: Verdict
    rule: str
    policy_version: str | None = None
    latency_ms: int | None = None


class EventIngest(BaseModel):
    action_request: ActionRequestIn
    event: DecisionIn


class EventOut(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    session_id: uuid.UUID
    tool_name: str
    environment: str
    canonical_hash: str
    args_meta: dict
    type: str
    verdict: Verdict
    rule: str
    policy_version: str | None
    latency_ms: int | None
    created_at: datetime
