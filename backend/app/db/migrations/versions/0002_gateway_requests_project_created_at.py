"""composite index for project-scoped usage queries

Revision ID: 0002_gateway_requests_project_created_at
Revises: 0001_baseline
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op


revision = "0002_gateway_requests_project_created_at"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_gateway_requests_project_id_created_at",
        "gateway_requests",
        ["project_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gateway_requests_project_id_created_at",
        table_name="gateway_requests",
    )
