"""gateway request adapter profile association fields

Revision ID: 0007_gateway_requests_adapter_profile_fields
Revises: 0006_gateway_adapter_profile_activations
Create Date: 2026-04-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0007_gateway_requests_adapter_profile_fields"
down_revision = "0006_gateway_adapter_profile_activations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gateway_requests", sa.Column("gateway_profile_id", sa.String(length=64), nullable=True))
    op.add_column("gateway_requests", sa.Column("adapter_profile_id", sa.String(length=64), nullable=True))
    op.add_column("gateway_requests", sa.Column("domain_key", sa.String(length=120), nullable=True))
    op.add_column("gateway_requests", sa.Column("adaptation_mode", sa.String(length=32), nullable=True))
    op.create_index(
        op.f("ix_gateway_requests_gateway_profile_id"),
        "gateway_requests",
        ["gateway_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gateway_requests_domain_key"),
        "gateway_requests",
        ["domain_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_gateway_requests_domain_key"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_gateway_profile_id"), table_name="gateway_requests")
    op.drop_column("gateway_requests", "adaptation_mode")
    op.drop_column("gateway_requests", "domain_key")
    op.drop_column("gateway_requests", "adapter_profile_id")
    op.drop_column("gateway_requests", "gateway_profile_id")

