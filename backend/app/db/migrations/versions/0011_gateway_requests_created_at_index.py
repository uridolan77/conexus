"""Index gateway_requests.created_at for dashboard and time-range scans.

Revision ID: 0011_gateway_requests_created_at_index
Revises: 0010_activation_domain_status_partial_unique
Create Date: 2026-05-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0011_gateway_requests_created_at_index"
down_revision = "0010_activation_domain_status_partial_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_gateway_requests_created_at",
        "gateway_requests",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_gateway_requests_created_at", table_name="gateway_requests")
