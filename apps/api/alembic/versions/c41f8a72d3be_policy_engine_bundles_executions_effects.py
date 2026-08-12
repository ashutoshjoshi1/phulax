"""policy engine: bundles, executions, four-effect verdicts

Revision ID: c41f8a72d3be
Revises: a9d68ea869f2
Create Date: 2026-08-12 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c41f8a72d3be"
down_revision = "a9d68ea869f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_bundles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("signature", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], name=op.f("fk_policy_bundles_org_id_organizations")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_bundles")),
        sa.UniqueConstraint("org_id", "version", name=op.f("uq_policy_bundles_org_id")),
    )
    op.create_table(
        "executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("result_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('AUTHORIZED', 'EXECUTING', 'SUCCEEDED', 'FAILED')",
            name=op.f("ck_executions_state"),
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], name=op.f("fk_executions_org_id_organizations")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_executions")),
        sa.UniqueConstraint("org_id", "idempotency_key", name=op.f("uq_executions_org_id")),
    )

    # Events learn to explain themselves (plan §4.4).
    op.add_column(
        "events",
        sa.Column(
            "reason_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "matched_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("events", sa.Column("risk_score", sa.Integer(), nullable=True))

    # Verdicts become the four-effect decision model. Walking-skeleton rows
    # map onto it: block → deny, hold → require_approval.
    op.execute("UPDATE events SET verdict = 'deny' WHERE verdict = 'block'")
    op.execute("UPDATE events SET verdict = 'require_approval' WHERE verdict = 'hold'")
    op.drop_constraint(op.f("ck_events_verdict"), "events", type_="check")
    op.create_check_constraint(
        "verdict",
        "events",
        "verdict IN ('allow', 'deny', 'require_approval', 'freeze')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_events_verdict"), "events", type_="check")
    op.execute("UPDATE events SET verdict = 'block' WHERE verdict IN ('deny', 'freeze')")
    op.execute("UPDATE events SET verdict = 'hold' WHERE verdict = 'require_approval'")
    op.create_check_constraint("verdict", "events", "verdict IN ('allow', 'block', 'hold')")
    op.drop_column("events", "risk_score")
    op.drop_column("events", "matched_rules")
    op.drop_column("events", "reason_codes")
    op.drop_table("executions")
    op.drop_table("policy_bundles")
