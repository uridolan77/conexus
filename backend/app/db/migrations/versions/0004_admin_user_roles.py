"""admin users roles json

Revision ID: 0004_admin_user_roles
Revises: 0003_project_usage_windows_and_reservations
Create Date: 2026-04-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0004_admin_user_roles"
down_revision = "0003_project_usage_windows_and_reservations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admin_users",
        sa.Column(
            "roles_json",
            sa.Text(),
            nullable=False,
            server_default='["Admin"]',
        ),
    )


def downgrade() -> None:
    op.drop_column("admin_users", "roles_json")

