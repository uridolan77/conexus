"""m5 usage events and model aliases

Revision ID: 0009_m5_usage_events_and_model_aliases
Revises: 0008_gateway_requests_profile_created_at_indexes
Create Date: 2026-05-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_m5_usage_events_and_model_aliases"
down_revision = "0008_gateway_requests_profile_created_at_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_api_keys",
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "gateway_model_aliases",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("alias", sa.String(length=120), nullable=False),
        sa.Column("primary_provider", sa.String(length=40), nullable=False),
        sa.Column("primary_model", sa.String(length=120), nullable=False),
        sa.Column("fallback_provider", sa.String(length=40), nullable=True),
        sa.Column("fallback_model", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias", name="uq_gateway_model_aliases_alias"),
    )
    op.create_index(
        op.f("ix_gateway_model_aliases_alias"),
        "gateway_model_aliases",
        ["alias"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gateway_model_aliases_status"),
        "gateway_model_aliases",
        ["status"],
        unique=False,
    )

    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("gateway_request_id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("requested_model", sa.String(length=120), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gateway_request_id"], ["gateway_requests.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "gateway_request_id",
            name="uq_usage_events_gateway_request_id",
        ),
    )
    op.create_index(
        op.f("ix_usage_events_created_at"),
        "usage_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usage_events_gateway_request_id"),
        "usage_events",
        ["gateway_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usage_events_model"),
        "usage_events",
        ["model"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usage_events_project_id"),
        "usage_events",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usage_events_provider"),
        "usage_events",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usage_events_requested_model"),
        "usage_events",
        ["requested_model"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_events_requested_model"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_provider"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_project_id"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_model"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_gateway_request_id"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_created_at"), table_name="usage_events")
    op.drop_table("usage_events")

    op.drop_index(op.f("ix_gateway_model_aliases_status"), table_name="gateway_model_aliases")
    op.drop_index(op.f("ix_gateway_model_aliases_alias"), table_name="gateway_model_aliases")
    op.drop_table("gateway_model_aliases")

    op.drop_column("project_api_keys", "last_used_at")
