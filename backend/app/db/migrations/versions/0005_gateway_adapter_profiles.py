"""gateway adapter profiles registry

Revision ID: 0005_gateway_adapter_profiles
Revises: 0004_admin_user_roles
Create Date: 2026-04-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0005_gateway_adapter_profiles"
down_revision = "0004_admin_user_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gateway_adapter_profiles",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("gateway_profile_id", sa.String(length=64), nullable=False),
        sa.Column("adapter_profile_id", sa.String(length=64), nullable=False),
        sa.Column("domain_key", sa.String(length=120), nullable=False),
        sa.Column("profile_version", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Registered"),
        sa.Column("source_run_id", sa.String(length=64), nullable=True),
        sa.Column("source_plan_id", sa.String(length=64), nullable=True),
        sa.Column("composite_score", sa.Float(), nullable=True),
        sa.Column("evidence_hash", sa.String(length=128), nullable=True),
        sa.Column("semantic_context_hash", sa.String(length=128), nullable=True),
        sa.Column("slod_model_version", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("adapter_profile_id"),
        sa.UniqueConstraint("gateway_profile_id"),
    )
    op.create_index(
        op.f("ix_gateway_adapter_profiles_gateway_profile_id"),
        "gateway_adapter_profiles",
        ["gateway_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gateway_adapter_profiles_adapter_profile_id"),
        "gateway_adapter_profiles",
        ["adapter_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gateway_adapter_profiles_domain_key"),
        "gateway_adapter_profiles",
        ["domain_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gateway_adapter_profiles_status"),
        "gateway_adapter_profiles",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_gateway_adapter_profiles_status"), table_name="gateway_adapter_profiles")
    op.drop_index(op.f("ix_gateway_adapter_profiles_domain_key"), table_name="gateway_adapter_profiles")
    op.drop_index(
        op.f("ix_gateway_adapter_profiles_adapter_profile_id"),
        table_name="gateway_adapter_profiles",
    )
    op.drop_index(
        op.f("ix_gateway_adapter_profiles_gateway_profile_id"),
        table_name="gateway_adapter_profiles",
    )
    op.drop_table("gateway_adapter_profiles")

