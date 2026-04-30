"""project usage windows + per-request limit reservations

Revision ID: 0003_project_usage_windows_and_reservations
Revises: 0002_gateway_requests_project_created_at
Create Date: 2026-04-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0003_project_usage_windows_and_reservations"
down_revision = "0002_gateway_requests_project_created_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_usage_windows",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("window_kind", sa.String(length=16), nullable=False),
        sa.Column("window_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_count_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_reserved", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cost_completed", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "window_kind",
            "window_start_utc",
            name="uq_project_usage_windows_project_kind_start",
        ),
    )
    op.create_index(
        op.f("ix_project_usage_windows_project_id"),
        "project_usage_windows",
        ["project_id"],
        unique=False,
    )

    op.create_table(
        "project_gateway_limit_reservations",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("daily_window_id", sa.String(length=32), nullable=False),
        sa.Column("monthly_window_id", sa.String(length=32), nullable=True),
        sa.Column("request_slots", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tokens_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_reserved", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["daily_window_id"], ["project_usage_windows.id"]),
        sa.ForeignKeyConstraint(["monthly_window_id"], ["project_usage_windows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_project_gateway_limit_reservations_project_id"),
        "project_gateway_limit_reservations",
        ["project_id"],
        unique=False,
    )

    op.add_column(
        "gateway_requests",
        sa.Column("limit_reservation_id", sa.String(length=32), nullable=True),
    )
    op.create_foreign_key(
        "fk_gateway_requests_limit_reservation_id",
        "gateway_requests",
        "project_gateway_limit_reservations",
        ["limit_reservation_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_gateway_requests_limit_reservation_id",
        "gateway_requests",
        type_="foreignkey",
    )
    op.drop_column("gateway_requests", "limit_reservation_id")
    op.drop_index(
        op.f("ix_project_gateway_limit_reservations_project_id"),
        table_name="project_gateway_limit_reservations",
    )
    op.drop_table("project_gateway_limit_reservations")
    op.drop_index(
        op.f("ix_project_usage_windows_project_id"),
        table_name="project_usage_windows",
    )
    op.drop_table("project_usage_windows")
