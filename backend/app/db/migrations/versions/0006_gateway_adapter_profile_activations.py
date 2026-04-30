"""gateway adapter profile activations

Revision ID: 0006_gateway_adapter_profile_activations
Revises: 0005_gateway_adapter_profiles
Create Date: 2026-04-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0006_gateway_adapter_profile_activations"
down_revision = "0005_gateway_adapter_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gateway_adapter_profile_activations",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("domain_key", sa.String(length=120), nullable=False),
        sa.Column("gateway_profile_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("canary_percent", sa.Integer(), nullable=True),
        sa.Column("previous_gateway_profile_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_gateway_adapter_profile_activations_domain_key"),
        "gateway_adapter_profile_activations",
        ["domain_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gateway_adapter_profile_activations_gateway_profile_id"),
        "gateway_adapter_profile_activations",
        ["gateway_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gateway_adapter_profile_activations_status"),
        "gateway_adapter_profile_activations",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_gateway_adapter_profile_activations_status"),
        table_name="gateway_adapter_profile_activations",
    )
    op.drop_index(
        op.f("ix_gateway_adapter_profile_activations_gateway_profile_id"),
        table_name="gateway_adapter_profile_activations",
    )
    op.drop_index(
        op.f("ix_gateway_adapter_profile_activations_domain_key"),
        table_name="gateway_adapter_profile_activations",
    )
    op.drop_table("gateway_adapter_profile_activations")

