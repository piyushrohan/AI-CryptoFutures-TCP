"""production spine tables

Revision ID: 0001_production_spine
Revises:
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_production_spine"
down_revision = None
branch_labels = None
depends_on = None


JSONB = postgresql.JSONB


def upgrade() -> None:
    op.create_table(
        "audit_records",
        sa.Column("record_id", sa.Text(), primary_key=True),
        sa.Column("command_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("reasons", JSONB(), nullable=False),
        sa.Column("payload_keys", JSONB(), nullable=False),
        sa.Column("payload_fingerprint", sa.Text(), nullable=False),
        sa.Column("runtime", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "command_ledger",
        sa.Column("command_id", sa.Text(), primary_key=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False, unique=True),
        sa.Column("command_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("payload_fingerprint", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("runtime", JSONB(), nullable=False),
        sa.Column("audit_record_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "account_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("venue_target", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "symbol_metadata_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "fee_policy_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_orders",
        sa.Column("order_id", sa.Text(), primary_key=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_fills",
        sa.Column("fill_id", sa.Text(), primary_key=True),
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "reconciliation_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("venue_target", sa.Text(), nullable=False),
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "model_registry_entries",
        sa.Column("model_id", sa.Text(), primary_key=True),
        sa.Column("approval_state", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "strategy_sessions",
        sa.Column("session_id", sa.Text(), primary_key=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "runtime_config_versions",
        sa.Column("version_id", sa.Text(), primary_key=True),
        sa.Column("runtime", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "runtime_config_versions",
        "strategy_sessions",
        "model_registry_entries",
        "reconciliation_events",
        "paper_fills",
        "paper_orders",
        "fee_policy_snapshots",
        "symbol_metadata_snapshots",
        "account_snapshots",
        "command_ledger",
        "audit_records",
    ):
        op.drop_table(table)
