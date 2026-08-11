"""Day 2 exit criterion: migrations apply AND roll back."""

from alembic import command
from sqlalchemy import create_engine, inspect

from conftest import alembic_config

EXPECTED_TABLES = {
    "organizations",
    "users",
    "agents",
    "agent_versions",
    "tools",
    "sessions",
    "action_requests",
    "events",
}


def test_migrations_apply_and_rollback(db_admin):
    url = db_admin.fresh_database("phulax_test_migrations")
    cfg = alembic_config(url)
    engine = create_engine(url)
    try:
        command.upgrade(cfg, "head")
        tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES <= tables, f"missing: {EXPECTED_TABLES - tables}"

        command.downgrade(cfg, "base")
        engine.dispose()
        remaining = set(inspect(create_engine(url)).get_table_names())
        assert remaining <= {"alembic_version"}, f"left behind: {remaining}"
    finally:
        engine.dispose()
        db_admin.drop("phulax_test_migrations")
