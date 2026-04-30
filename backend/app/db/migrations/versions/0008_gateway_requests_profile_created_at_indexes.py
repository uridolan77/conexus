"""gateway request adapter profile time indexes

Revision ID: 0008_gateway_requests_profile_created_at_indexes
Revises: 0007_gateway_requests_adapter_profile_fields
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op


revision = "0008_gateway_requests_profile_created_at_indexes"
down_revision = "0007_gateway_requests_adapter_profile_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_gateway_requests_gateway_profile_id_created_at",
        "gateway_requests",
        ["gateway_profile_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_gateway_requests_domain_key_created_at",
        "gateway_requests",
        ["domain_key", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_gateway_requests_domain_key_created_at", table_name="gateway_requests")
    op.drop_index("ix_gateway_requests_gateway_profile_id_created_at", table_name="gateway_requests")

